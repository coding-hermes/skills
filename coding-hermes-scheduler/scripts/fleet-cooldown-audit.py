#!/usr/bin/env python3
"""Fleet cooldown-vs-pending audit — catches projects parked at 12h+ cooldown
with real pending work. Runs via cron every 6h (no_agent watchdog). Exits 0
with a report ONLY when problems found; silent otherwise.

Created 2026-07-31 after the 21/35-project flapping incident: foremen were
self-pausing to 43200s while real pending work sat unread (asce PH2-001/002/003,
Kobayashi-Maru 5 gitreins tasks, <project> 26 rows, helix/mythos/<project>/etc.).
Installed at ~/.hermes/scripts/fleet-cooldown-audit.py, cron job
'Fleet Cooldown Audit' (dda7f27db73f, 0 */6 * * *).

Detection methods per coding-hermes-board skill M1-M4:
  M1: '## [ ]' headers    M2: '- [ ]' subtasks
  M3: emoji markers       M4: matrix rows without ✅
Plus GitReins dual-source check (tasks.yaml status=pending) and fleet.toml
awareness (a fleet.toml entry pinning cooldown_s >= 43200 is ADMIN INTENT —
not a problem; do not flag).
"""
import json, os, re, subprocess, sys

try:
    import yaml
except ImportError:
    yaml = None

def board_pending(path):
    try:
        with open(path) as f:
            c = f.read()
    except Exception:
        return 0
    m1 = len(re.findall(r'^## \[ \]', c, re.M))
    m2 = len(re.findall(r'^- \[ \]', c, re.M))
    m3 = len(re.findall(r'🔴 Open|⬜ Not Started|🟡 Blocked', c))
    m4_total = len(re.findall(r'^\|+ [A-Z]+[0-9]+', c, re.M))
    m4a = len(re.findall(r'^\|+ ✅ [A-Z]+[0-9]+', c, re.M))
    m4b = len(re.findall(r'^\|+ [A-Z]+[0-9]+ \| ✅', c, re.M))
    m4c = len(re.findall(r'^\|+ [A-Z]+[0-9]+ \| .+\| ✅', c, re.M))
    m4_done = max(m4a, m4b, m4c)
    m4 = max(0, m4_total - m4_done)
    fixture_rows = len(re.findall(r'^\|+ [A-Z0-9-]* ?[✅🟡🔴⬜ ]*.*(?:NEVER-DONE|E2E-001|GITREINS-JUDGE)', c, re.M))
    m4 = max(0, m4 - fixture_rows)
    m3_open = len(re.findall(r'^\|+ [^|]*🔴 Open[^|]*\|.*(?:NEVER-DONE|E2E-001|GITREINS-JUDGE)', c, re.M))
    m3 = max(0, m3 - m3_open)
    return m1 + m2 + m3 + m4

def gitreins_pending(workdir):
    if yaml is None:
        return 0
    for sub in ['.gitreins/tasks.yaml', 'gitreins/tasks.yaml']:
        p = os.path.join(workdir, sub)
        if os.path.isfile(p):
            try:
                with open(p) as f:
                    tasks = yaml.safe_load(f) or {}
                return len([t for t in tasks.get('tasks', []) if t.get('status') == 'pending'])
            except Exception:
                return 0
    return 0

def fleet_toml_pins(project_name):
    """Return cooldown_s from fleet.toml if the project has an entry, else None."""
    path = '~/coding-hermes-scheduler/coding-herms-scheduler/fleet.toml'
    try:
        with open(path) as f:
            c = f.read()
        blocks = re.findall(r'\[\[projects\]\](.*?)(?=\n\[\[projects\]\]|\Z)', c, re.S)
        for b in blocks:
            if re.search(r'^\s*name\s*=\s*"' + re.escape(project_name) + r'"\s*$', b, re.M):
                m = re.search(r'^\s*cooldown_s\s*=\s*(\d+)', b, re.M)
                return int(m.group(1)) if m else None
    except Exception:
        pass
    return None

def main():
    try:
        r = subprocess.run(['curl', '-s', '-m', '10', 'http://127.0.0.1:9090/api/v1/projects'],
                           capture_output=True, timeout=15)
        projects = json.loads(r.stdout)['projects']
    except Exception as e:
        print(f"AUDIT FAIL: cannot reach scheduler API: {e}")
        return 1

    problems = []
    for p in projects:
        if not p.get('Enabled'):
            continue
        cd = p.get('CooldownS', 0)
        if cd < 43200:
            continue  # only check slow-parked projects
        name = p['Name']
        workdir = p.get('Workdir', '')
        if not workdir or not os.path.isdir(workdir):
            continue
        board = os.path.join(workdir, '.coding-hermes', 'tasks.md')
        if not os.path.isfile(board):
            board = os.path.join(workdir, 'tasks.md')
        pending = board_pending(board) if os.path.isfile(board) else 0
        pending += gitreins_pending(workdir)
        pinned = fleet_toml_pins(name)
        if pending > 0:
            if pinned is not None and pinned >= 43200:
                continue  # admin intent IS slow — not a problem
            problems.append((name, cd, pending, pinned))

    if not problems:
        return 0  # silent — watchdog pattern

    print(f"⚠️ FLEET COOLDOWN AUDIT — {len(problems)} project(s) at 12h+ cooldown with pending work:")
    for name, cd, pending, pinned in problems:
        pin = f" (fleet.toml pins {pinned}s)" if pinned is not None else " (no fleet.toml entry)"
        print(f"  {name}: cooldown={cd/3600:.0f}h, pending={pending}{pin}")
    print("Fix: PUT CooldownS=900 via scheduler API, or add fleet.toml entry if admin intent differs.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
