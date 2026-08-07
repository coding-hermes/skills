# Hermes Send — Delivery Target Discovery

## Finding valid thread IDs

`hermes send --list <platform>` discovers all known chat/channel/thread targets:

```bash
hermes send --list telegram
# Output:
# telegram:KaraHermes - Set / topic 83996  [-1003310984808:83996]
# telegram:KaraHermes - Set / topic 17441  [-1003310984808:17441]
# telegram:KaraHermes - Set / topic 59430  [-1003310984808:59430]
```

Parse the format: `platform:name / topic thread_id [chat_id:thread_id]`

Use `chat_id:thread_id` as the `deliver` value in the scheduler's `projects` table.

## If a thread doesn't appear in --list

Threads that Hermes hasn't sent to before won't appear. Use the known chat_id
and thread_id manually: `telegram:<chat_id>:<thread_id>`. The send will still work
— Telegram API accepts any valid thread_id regardless of whether Hermes has cached it.

## Pro tip: backfill from paused crons

When migrating foreman crons to the scheduler, extract delivery targets:

```python
import json, sqlite3
with open('/tmp/hermes-results/cron-snapshot.txt') as f:
    data = json.load(f)
for j in data['jobs']:
    name = j.get('name','').lower()
    deliver = j.get('deliver','')
    workdir = j.get('workdir','')
    if 'foreman' in name and 'telegram' in deliver:
        # Map workdir → project name in scheduler DB
        print(f'{workdir} → {deliver}')
```

**Proven:** 2026-07-18 — 29 of 30 projects backfilled from paused cron targets.
Mafia-ai-benchmark was `deliver=origin` (context-dependent) and needed manual `--list` discovery.
