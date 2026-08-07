# deliver=origin Gap — Scheduler Can't Use Context-Dependent Delivery

## Problem

Some paused cron jobs have `deliver: "origin"` instead of `telegram:chat_id:thread_id`.
`origin` auto-detects the delivery context from the session that triggered the cron —
it resolves to the correct platform, chat, and thread based on who asked. This works
because cron jobs run in-process with session context.

The scheduler has no origin context. It spawns `hermes chat` as a subprocess and
delivers via `hermes send --to <target>`. Without a hard target, delivery defaults
to thread 83996 (the scheduler foreman thread).

## Affected Projects (2026-07-18)

- **mafia-ai-benchmark**: `deliver=origin` → thread 4409 in KaraHermes - Set
  - Manually set to `telegram:-1003310984808:4409`
  - Verified with `hermes send --to telegram:-1003310984808:4409` → "sent"

## Detection

```bash
# Find projects with deliver=origin in cron
python3 -c "
import json
with open('/tmp/hermes-results/<cron-list>.txt') as f:
    data = json.load(f)
for j in data['jobs']:
    if j.get('enabled') and j.get('deliver') == 'origin' and 'coding-hermes-foreman' in ' '.join(j.get('skills',[])):
        print(f'{j[\"name\"]:50s} deliver=origin → needs manual thread ID')
"
```

## Fix

Ask Bane for the correct thread ID. These threads live in the KaraHermes - Set group
(-1003310984808). The Hermes system prompt (system_prompt segment) shows the current
session's thread ID for reference. Set with:

```sql
UPDATE projects SET deliver='telegram:-1003310984808:<thread_id>' WHERE name='<project>';
```

## Why Not Fix Automatically

- The scheduler can't call `hermes send` with `origin` — there's no session context
- `hermes send --list telegram` shows KNOWN threads but not undiscovered ones
- New threads need a human to identify them
- Defaulting to 83996 is safe but means the project shares the scheduler thread
