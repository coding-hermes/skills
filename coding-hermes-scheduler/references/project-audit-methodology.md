# Cross-Source Project Audit Methodology

Auditing coding-hermes projects for real pending task count requires cross-referencing three independent sources. No single source tells the full story.

## Three Sources (Query All Three)

| Source | What it tells you | How to query |
|--------|-------------------|-------------|
| **GitReins MCP** | Git-native task list (all statuses: pending, in_progress, complete) | `mcp__gitreins__task_list(workdir="~/<project>")` |
| **Foreman board** | `.coding-hermes/tasks.md` — authoritative task state, idle counters, blocked reasons | `read_file` on `{workdir}/.coding-hermes/tasks.md` |
| **Scheduler API** | CooldownS, Enabled, priority, weight, last tick times | `curl http://localhost:9090/api/v1/projects` |

## Counting "Real Pending" Tasks

**Exclude:**
- `NEVER-DONE` — recurring audit sweep, runs every tick, never "done"
- `U01` or `U0*` — usability/coverage audits, one-shot quality checks

**Distinguish BLOCKED from actionable:**
- **BLOCKED** (don't count as real pending): human-gated (CI billing, API keys, code review), content-gated (needs creative input like episode scripts), infra-blocked (no sudo, no kernel support, host resource), external dependency
- **Actionable pending** (count these): tasks a foreman worker could pick up and implement without human intervention

**GitReins vs foreman board conflict:** When GitReins says `in_progress` but the foreman board says `✅ DONE`, the foreman board wins. GitReins tasks are set at creation time; the foreman board reflects actual tick-by-tick state. Example: speclang `PITFALL-WORKFLOW-001` — GitReins shows in_progress, board says DONE.

**Foreman board format:** Uses model-router table format (`| ID | Task | Priority | Complexity | ...`), NOT markdown checkboxes. `grep '^- \[ \]' .coding-hermes/tasks.md` will find 0 results even when real pending tasks exist. Read and parse the tables instead.

## Setting Cooldowns

```bash
# Check current
curl -s http://localhost:9090/api/v1/projects | python3 -c "
import sys,json; data=json.load(sys.stdin)
for p in data['projects']:
    print(f\"{p['Name']:20s} CooldownS={p['CooldownS']:5d} Enabled={p['Enabled']}\")"

# Set cooldown (43200s = 12h for idle projects)
curl -s -X PUT http://localhost:9090/api/v1/projects/<name> \
  -H 'Content-Type: application/json' \
  -d '{"CooldownS": 43200}'
```

**Idle projects get 43200s (12h).** Active projects with real pending work should stay at their dynamic cooldown or a shorter manual value.

## Known Pitfalls

### Case-Sensitive Project Names
`Speclang` (capital S, workdir `~/SpecLang`) ≠ `speclang` (lowercase, `~/speclang`). Two different directories, two different scheduler entries. Always verify workdir when cross-referencing.

### Cooldown Reversion Bug
Setting CooldownS via API PUT lasts only until the next daemon restart. `ApplyFleetConfig` on startup overwrites API-set values with fleet TOML defaults. This is a known bug — the API PUT is a bandage, not a fix. Root cause: fleet TOML `CooldownS` field.

### Foreman Board May Show Different State Than GitReins
The foreman's `.coding-hermes/tasks.md` is updated every tick with live state. GitReins tasks are created once and only updated when explicitly completed via `task_complete`. If a foreman resolves a task but doesn't call `task_complete`, GitReins stays stale. Read the board first.

## Example: Full 12-Project Audit

```bash
# 1. Get scheduler state
curl -s http://localhost:9090/api/v1/projects | python3 -c "
import sys,json
targets = ['muster','<project>','mythos','off-by-one','<project>',
           'rethinkdb','speclang','<project>','<project>','<project>',
           '<project>','wojons-mythos']
data = json.load(sys.stdin)
for p in data['projects']:
    if p['Name'] in targets:
        print(f\"{p['Name']}: Enabled={p['Enabled']}, CooldownS={p['CooldownS']}, Workdir={p['Workdir']}\")"

# 2. GitReins tasks (parallel calls for all 12)
# Use mcp__gitreins__task_list for each workdir

# 3. Foreman boards (parallel reads)
# read_file on each {workdir}/.coding-hermes/tasks.md

# 4. Count real pending (exclude NEVER-DONE, U01; distinguish BLOCKED from actionable)

# 5. Set cooldowns for idle projects at 43200s
```
