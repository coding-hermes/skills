#!/usr/bin/env python3
"""Stand-in agent picker — picks 1-2 projects per hourly wake for gap-pushing.

The stand-in (human proxy while Bane is away) picks projects that THINK they
are done (idle/self-paused foremen, low pending) and pokes them: dogfood-lite,
find gaps, WRITE tasks to their board so the foreman spins up real work.

Selection weights:
  - Never/seldom poked recently (state file) → higher chance
  - Self-paused projects (CooldownS >= 14400) → higher chance (stuck-idle risk)
  - Enabled only. Disabled = human intent, never picked.
Output (stdout) is injected into the agent prompt as the briefing.
"""
import json, os, random, sys, time, urllib.request

API = 'http://127.0.0.1:9090'
STATE = os.path.expanduser('~/.hermes/state/standin-picks.json')
MIN_GAP_HOURS = 8      # don't re-poke the same project within 8h
PICKS_PER_RUN = 2      # poke 2 projects per hourly wake

def api_get(path):
    try:
        with urllib.request.urlopen(API + path, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {'error': str(e)}

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

def count_pending(workdir):
    """Quick board pending count — best-effort."""
    for cand in (os.path.join(workdir, '.coding-hermes', 'tasks.md'),
                 os.path.join(workdir, 'tasks.md')):
        if os.path.isfile(cand):
            try:
                with open(cand) as f:
                    c = f.read()
                return c.count('- [ ]') + c.count('| [ ]') + c.count('⬜')
            except Exception:
                return -1
    return -1

def main():
    data = api_get('/api/v1/projects')
    if 'error' in data or not data.get('projects'):
        print(f"STAND-IN PICKER FAIL: cannot reach scheduler API ({data.get('error')})")
        return 1

    now = time.time()
    state = load_state()
    # Skip: disabled, no workdir, HEADING ghosts (exact dup names), infra projects
    skip = {'heading', 'my-project', 'sim-alpha', 'sim-beta', 'sim-delta', 'sim-gamma',
            'global-fast', 'global-slow', 'ch-alpha', 'ch-beta', 'ch-delta', 'ch-epsilon',
            'ch-eta', 'ch-gamma', 'ch-zeta', 'dc-prune', 'dc-rotate', 'dc-vacuum'}
    candidates = []
    for p in data['projects']:
        p = norm(p)
        name = p['name']
        if not p.get('enabled') or not p.get('workdir'):
            continue
        if name in skip or not os.path.isdir(p['workdir']):
            continue
        cd = p.get('cooldown_s', 900)
        last = state.get(name, 0)
        age_h = (now - last) / 3600 if last else 999
        if age_h < MIN_GAP_HOURS:
            continue
        pending = count_pending(p['workdir'])
        # Score: stale pick = strong; self-paused (>=14400) = strong; high pending = weaker (already working)
        score = age_h / 24.0
        if cd >= 14400:
            score += 2.0
        if pending == 0:
            score += 1.0          # board clean = "thinks it's done" = prime target
        elif pending is not None and pending <= 3:
            score += 0.5
        candidates.append((score, name, p))

    if not candidates:
        print("STAND-IN PICKER: no eligible projects this hour (all recently poked).")
        return 1

    candidates.sort(reverse=True)
    picks = candidates[:PICKS_PER_RUN]
    for score, name, p in picks:
        state[name] = now
    save_state(state)

    print("STAND-IN WAKE — poke these projects with gap-pushing work (Bane is away):")
    print()
    for i, (score, name, p) in enumerate(picks, 1):
        wd = p['workdir']
        cd = p.get('cooldown_s', '?')
        pending = count_pending(wd)
        print(f"--- TARGET {i}: {name}")
        print(f"  Workdir: {wd}")
        print(f"  Repo: {p.get('RepoURL', '')}")
        print(f"  Cooldown: {cd}s  Decay: {p.get('decay_rate', '?')}  Enabled: {p.get('enabled')}")
        print(f"  LastTickStarted: {p.get('LastTickStarted', 'never')}")
        print(f"  Board pending markers: {pending if pending >= 0 else 'n/a'}")
        print(f"  Pick score: {score:.1f} (self-paused/idle + clean board = prime gap target)")
        print()
    print("Job: for EACH target — read the board, ask the basic questions a user would,")
    print("dogfood-lite (run it / use it / check the docs), find REAL gaps (integration,")
    print("testing, UX, usability, docs), WRITE 2-6 concrete tasks onto the board,")
    print("then wake the foreman (API PUT CooldownS=900 if it was >=14400). Log every")
    print("run to DuckBrain via MCP (namespace=coding-hermes, key=/stand-in/YYYY-MM-DD/<project>).")
    return 0

if __name__ == '__main__':
    sys.exit(main())
