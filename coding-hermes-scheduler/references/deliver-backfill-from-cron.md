# Deliver Target Backfill — Extracting Thread IDs from Paused Cron Jobs

When migrating foremen from Hermes cron to the scheduler, each project needs a
`deliver` column set to `telegram:<chat_id>:<thread_id>`. This is extracted from
the paused cron jobs.

## Extracting Deliver Targets

### Step 1 — Dump cron state
```bash
hermes cron list --json > /tmp/cron-snapshot.json
```

### Step 2 — Backfill by workdir matching (recommended)

Workdir matching is more reliable than name matching because project names
differ between cron ("Speclang Coding Foreman") and scheduler ("speclang").

```python
import json, sqlite3

with open('/tmp/cron-snapshot.json') as f:
    data = json.load(f)

db = sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')

# Build cron workdir → deliver map
cdirs = {}
for j in data['jobs']:
    w = j.get('workdir','')
    d = j.get('deliver','')
    if w and d and 'telegram' in d:
        cdirs[w.strip('/')] = d

# Match by workdir
for r in db.execute("SELECT name, workdir FROM projects WHERE deliver='' OR deliver IS NULL"):
    pname, pdir = r[0], r[1].strip('/')
    if pdir in cdirs:
        db.execute("UPDATE projects SET deliver=? WHERE name=?", (cdirs[pdir], pname))
        print(f'{pname:30s} → {cdirs[pdir]}')
    else:
        print(f'{pname:30s} NO MATCH — workdir={pdir}')

db.commit()
```

### Step 3 — Name-based fallback (for unmatched projects)

Some cron names have suffixes that don't match scheduler names. Strip common
suffixes before matching:

```python
# Strip common cron name suffixes
for sfx in ['-coding-foreman','-foreman','-dev-loop','-foreman-infra']:
    if cron_name.endswith(sfx):
        cron_name = cron_name[:-len(sfx)]

# Also handle '-work' suffix: helios-work → helios
if pname.replace('-work','') == cron_name:
    match
```

### Step 4 — Handle `deliver=origin`

Some cron jobs use `deliver: "origin"` which auto-detects the chat context.
This does NOT work for the scheduler — origin resolves to the scheduler's
own chat (thread 83996), not the project's. These must be set manually.

**Proven:** `mafia-ai-benchmark` had `deliver=origin` → defaulted to 83996.
Thread 4409 is in "KaraHermes - Set" group, not "Home". Verified with
`hermes send --list telegram` (threads in same supergroup share chat ID
`-1003310984808`). Manual fix: `telegram:-1003310984808:4409`.

### Step 5 — Verify

```bash
python3 -c "
import sqlite3
db = sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
for r in db.execute(\"SELECT name, deliver FROM projects WHERE deliver='' OR deliver IS NULL
    AND name NOT LIKE 'sim-%' AND name NOT LIKE 'ch-%' AND name NOT LIKE 'mon-%'
    AND name NOT LIKE 'dc-%' AND name NOT LIKE 'global-%'\"):
    print(f'MISSING: {r[0]}')
"
```

### Step 6 — Verify delivery with test send

```bash
hermes send --to telegram:-1003310984808:<thread_id> --subject "Test: <project>" --message "Test delivery to thread <thread_id>"
```

## Edge Cases

### Workdir mismatch
Cron job workdir paths may differ from scheduler project workdir paths
(e.g., `~/project` vs `~/project-work`). Match by
the most specific path component or use name-based fallback.

### Thread in different supergroup
Telegram supergroup topics share the same chat ID. The `hermes send --list`
output shows all known threads — if thread 4409 isn't listed but should
exist, create the thread in Telegram first, then `hermes send --list` again.

## Results (2026-07-18)

- 30 projects backfilled (workdir matching: 12, name matching: 8, manual: 1)
- 1 manual (`mafia-ai-benchmark` → thread 4409, was `deliver=origin`)
- sim-*, ch-*, mon-*, dc-*, global-* test/infra projects left empty (disabled)
