# Pending Audit → Cooldown Pattern

Batch-audit GitReins pending task counts across N projects, then set bunker
cooldowns by result. Use when the schedule seems off, or when told to "audit
N projects and set cooldowns."

## Step 1: Find project workdirs

Projects may live in subdirectories (e.g., `get-h3/sdk-typescript`) or at
the top level. Use `search_files(target='files')` to locate repos, but the
authoritative source is the bunker scheduler API:

```bash
curl -s http://127.0.0.1:9090/api/v1/projects | python3 -c "
import json,sys
for p in json.load(sys.stdin)['projects']:
    print(f\"{p['Name']:35s} {p['Workdir']}\")
"
```

## Step 2: Query GitReins pending tasks

For each project, call `mcp__gitreins__task_list` with `status='pending'` and
the project's `Workdir`. **Use the MCP tool, not curl** — it reads directly from
each repo's `.gitreins/tasks.yaml`.

**Critical filter:** NEVER-DONE tasks and tasks with IDs matching `U0*` (utility
bookkeeping) do NOT count as real pending work. Exclude them.

## Step 3: Count and categorize

```python
# Pseudocode for counting
real_pending = [
    t for t in tasks
    if t['status'] == 'pending'
    and not t['id'].startswith('NEVER-DONE')
    and not t['id'].startswith('U0')
]
```

## Step 4: Set cooldowns via bunker API

- **0 real pending** → set `CooldownS: 43200` (12h — don't waste foreman cycles)
- **Has real pending** → set `CooldownS: 900` (15m — frequent pickup)

The single-project update endpoint:

```bash
curl -s -X PUT "http://127.0.0.1:9090/api/v1/projects/<name>" \
  -H "Content-Type: application/json" \
  -d '{"CooldownS": 43200}'
```

**Pitfall:** The single-project GET endpoint returns nested JSON:
`{"project": {"Name": "...", "CooldownS": 900, ...}, "latest_tick": {...}}`.
When verifying, access `project.CooldownS`, not the top-level.

## Step 5: Confirm

Batch-verify the final state:

```bash
for p in proj1 proj2 ...; do
  curl -s "http://127.0.0.1:9090/api/v1/projects/$p" | \
    python3 -c "import sys,json; d=json.load(sys.stdin)['project']; print(f'{d[\"Name\"]:30s} CooldownS={d[\"CooldownS\"]}')"
done
```

## Proven pattern

2026-07-24: Audited 10 projects (h3-sdk-typescript-foreman, <project>,
helix, hermes-canopy, <project>, <project>, hivemind-pulse,
<project>, <project>, mafia-ai-benchmark). Two had real pending work:
<project> (4 tasks) and <project> (1 task). Set their cooldowns to
900s; the 8 idle projects to 43200s.
