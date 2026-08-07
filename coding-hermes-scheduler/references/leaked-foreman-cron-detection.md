# Leaked Foreman Cron Detection

Run this to detect foreman cron jobs that are still enabled alongside the scheduler.
Double-spawns cause tick timeouts because the cron process and scheduler process compete
for the same project.

## Detection Script

```python
import json
with open('~/.hermes/cron/jobs.json') as f:
    data = json.load(f)

foreman_leaks = []
for j in data['jobs']:
    skills = str(j.get('skills', [])).lower()
    paused = j.get('paused_at')
    is_supervisor = j.get('name') == 'Coding Hermes Supervisor'
    if 'foreman' in skills and not paused:
        foreman_leaks.append(j)
        print(f"LEAKED: {j.get('id','?')} {j.get('name','?')} schedule={j.get('schedule')}")

print(f"\nTotal: {len(foreman_leaks)}")
if not foreman_leaks:
    print("Clean — only Supervisor should remain.")
```

## How to Pause (except Supervisor)

```python
# DO NOT pause the Supervisor (check name first)
for j in foreman_leaks:
    if j['name'] != 'Coding Hermes Supervisor':
        # Pause via cronjob tool: cronjob(action='pause', job_id=j['id'])
        print(f"PAUSE: {j['id']} {j['name']}")
```

## Proven Cases

**2026-07-18:** 5 leaked foreman crons found enabled:
- `4112021d6998` helix-foreman (every 30m)
- `d7949401cfe0` <project>-foreman (every 60m)  
- `83c72b749566` <project>-coding-hermes-foreman (every 30m)
- `e17630cea8c9` h3-foreman-bootstrap (every 5m)
- `56351fc56f98` <project>-coding-foreman (every 30m)

These caused <project> to get 11 consecutive timeout ticks (2-3min each)
because the scheduler-spawned process was killed by the competing cron process.

**2026-07-18 (earlier):** ~40 foreman crons were paused during initial scheduler migration.
The Supervisor re-enabled some during a schedulerd outage.

## Root Cause

The `coding-hermes-supervisor` skill (v2.20.0) has daemon guards in Phase 0B and 0D,
but during a schedulerd outage, those guards pass (daemon is unreachable = looks like
it doesn't exist), triggering the Supervisor to re-create foreman cron jobs.

**Mitigation:** Always re-run the detection script after any schedulerd outage to
catch re-enabled crons before they cause double-spawn chaos.
