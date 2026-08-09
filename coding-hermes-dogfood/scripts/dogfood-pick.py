#!/usr/bin/env python3
"""Dogfood picker — picks ONE random enabled project for the coding-hermes-dogfood cron.

Output (stdout) is injected into the agent prompt as the briefing. Picks are
weighted toward projects not recently dogfooded (state in ~/.hermes/state/dogfood-picks.json).
Silent-ish: always prints a briefing (the agent needs it), never fails loudly.
"""
import json, os, random, subprocess, sys, time, urllib.request

API = 'http://127.0.0.1:9090'
STATE = os.path.expanduser('~/.hermes/state/dogfood-picks.json')
MIN_SECONDS_BETWEEN = 7 * 86400  # don't re-pick the same project within a week

def api_get(path, tries=2):
    last_err = None
    for _ in range(tries):
        try:
            with urllib.request.urlopen(API + path, timeout=10) as r:
                return json.loads(r.read())
        except Exception as e:
            last_err = e
            time.sleep(2)
    return {'error': str(last_err)}

_ALIAS = {'name': 'Name', 'repo_url': 'RepoURL', 'workdir': 'Workdir',
          'cooldown_s': 'CooldownS', 'decay_rate': 'DecayRate', 'model': 'Model',
          'provider': 'Provider', 'enabled': 'Enabled', 'created_at': 'CreatedAt',
          'updated_at': 'UpdatedAt', 'last_tick_started': 'LastTickStarted',
          'consecutive_failures': 'ConsecutiveFailures'}

def norm(p):
    """Normalize project dict: scheduler API moved to lowercase json tags
    (2026-08-05, schedulerd build Aug 4 19:28); expose PascalCase aliases too."""
    out = dict(p)
    for k, v in p.items():
        if k in _ALIAS and _ALIAS[k] not in out:
            out[_ALIAS[k]] = v
    return out

def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, 'w') as f:
        json.dump(st, f, indent=1)

def main():
    data = api_get('/api/v1/projects')
    if 'error' in data or not data.get('projects'):
        print(f"DOGFOOD PICKER FAIL: cannot reach scheduler API ({data.get('error')})")
        return 1

    now = time.time()
    state = load_state()
    projects = [p for p in (norm(p) for p in data['projects'])
                if p.get('enabled') and p.get('workdir')]

    if not projects:
        print("DOGFOOD PICKER: no enabled projects with workdirs.")
        return 1

    # Filter out projects picked within the cooldown window
    eligible = []
    for p in projects:
        last = state.get(p['name'], 0)
        if now - last >= MIN_SECONDS_BETWEEN:
            eligible.append(p)
    if not eligible:
        # All picked recently — take the stalest anyway
        eligible = sorted(projects, key=lambda p: state.get(p['name'], 0))[:1]

    # Weighted random: prefer least-recently-picked among eligible
    eligible.sort(key=lambda p: state.get(p['name'], 0))
    pool = eligible[:max(1, len(eligible) // 2)]  # top half by staleness
    pick = random.choice(pool)

    name = pick['name']
    state[name] = now
    save_state(state)

    # Briefing for the agent
    wd = pick.get('workdir', '')
    print(f"DOGFOOD TARGET: {name}")
    print(f"Workdir: {wd}")
    print(f"Repo: {pick.get('RepoURL', '')}")
    print(f"Cooldown: {pick.get('cooldown_s', '?')}s  Decay: {pick.get('decay_rate', '?')}  Enabled: {pick.get('enabled')}")
    print(f"LastTickStarted: {pick.get('LastTickStarted', 'never')}")
    # Board pending quick count
    board = os.path.join(wd, '.coding-hermes', 'tasks.md')
    if os.path.isfile(board):
        try:
            with open(board) as f:
                c = f.read()
            pend = c.count('- [ ]') + c.count('| [ ]')
            print(f"Board: {board} (pending markers ~{pend})")
        except Exception:
            print(f"Board: {board}")
    else:
        print("Board: (no .coding-hermes/tasks.md found)")
    print("---")
    print("Load skill coding-hermes-dogfood and field-test this project with REAL USE depth.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
