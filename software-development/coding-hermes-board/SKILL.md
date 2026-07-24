---
name: coding-hermes-board
description: Board management for coding-hermes foreman — reading the task board, task selection, NEVER-DONE fixture, and self-pause logic when only the perpetual audit remains
version: 1.1.0
category: software-development
platforms: [linux]
metadata:
  hermes:
    tags: [coding-hermes, board, foreman, task-management]
    related_skills:
      - coding-hermes-foreman
      - coding-hermes-model-router
      - coding-hermes-never-done
      - coding-hermes-map
---

> See [coding-hermes-map] for the full skill hierarchy and when to use each skill.

# Board Management — Reading the Task Board & Self-Pause

This skill covers the board-management responsibilities of a coding-hermes foreman: reading the task board, selecting the next task, understanding the NEVER-DONE perpetual fixture, and self-pausing when only the audit remains.

Extracted from `coding-hermes-foreman` (Steps 1 and Self-Pause). Loaded by foreman cron jobs as part of the fleet architecture.

## Step 1 — Read Board

Read `.coding-hermes/tasks.md`. This is the project's single source of truth for what needs to be done.

**Board format — model-router style (MANDATORY):** Every task board MUST use the matrix format from `coding-hermes-model-router`. Each task is a row with: ID, Task, Priority, Complexity, Dependencies, Capability Tags, Selected Model, Reasoning Level, Fallback.

```markdown
# Project Name — Task Board

> Foreman: <YOUR-FOREMAN-MODEL> @ <YOUR-FOREMAN-PROVIDER> | DuckBrain: <namespace>

## Active

| ID | Task | Pri | Cpx | Deps | Tags | Model | Reasoning | Fallback |
|----|------|-----|-----|------|------|-------|-----------|----------|
| T01 | Repair login flow | Critical | 5±1 | — | +++backend, ++debugging, -vision | GLM-5.2 | High | DS-V4-Pro |
| T02 | Add rollback to migration | High | 4±1 | T01 | +++database, ++terminal, -vision | DS-V4-Flash | Medium | Kimi-K3 |

## Completed

| ID | Task | Pri | Cpx | Commit | Model |
|----|------|-----|-----|--------|-------|
| T00 | Bootstrap init | Trivial | 1±0 | abc1234 | DS-V4-Flash |
```

When onboarding a new project, the foreman MUST load `coding-hermes-model-router` and decompose the project into this matrix.

### NEVER-DONE — Permanent Last Task

**Permanent last task — NEVER-DONE:** Every task board MUST end with this task. It is NEVER marked `[x]` — it is the perpetual improvement engine.

```
## [ ] NEVER-DONE — Run coding-hermes-never-done 12-point audit

Load coding-hermes-never-done skill. Run ALL 12 checks: spec alignment,
doc coverage, test gaps, package upgrades, pitfall hunt, performance audit,
endpoint verification, CI/CD health, DuckBrain sync, code quality,
middle-out wiring, usability smoke test. Create a task for EVERY gap found.
This task is never complete — the audit always finds something.

**CHECK 12 — USABILITY SMOKE TEST:** See `references/never-done-12th-check-usability.md`.
This is the ONLY check in the audit that verifies a human can actually USE what was built.
All 11 prior checks are static (files, configs, HTTP codes). They all pass while an app
is completely unusable. Deploy fresh, walk through the full user journey, verify response
bodies not just HTTP codes. Create a USABILITY-NNN task for every broken step.
Proven: HEADING 2026-07-21 — 11 checks all green while 7 critical bugs existed.
```

When onboarding a new project, the foreman MUST write this task as the LAST item in the Active section. When a tick ends with an empty board (after the sweep), the foreman picks up this task and runs the audit. The audit creates new tasks which get worked in subsequent ticks. When those are done, the NEVER-DONE task re-triggers and finds NEW gaps. The cycle never stops.

### Counting Tasks

**Count:**
- `## [ ]` — pending task headers
- `- [ ]` — pending subtasks under active headers
- `## [x]` — completed task headers

### Dual-Source Task Check — GitReins tasks.yaml

**MANDATORY:** `.coding-hermes/tasks.md` is NOT the only source of task state. Many projects also use GitReins (`gitreins task create …`) which writes to `.gitreins/tasks.yaml`. Treat both files as joint task state. A project whose tasks.md shows only NEVER-DONE can still have real pending work in gitreins.

**When reading the board, always check BOTH sources:**

```bash
# 1. Check tasks.md pending
grep -c '^## \[ \]' .coding-hermes/tasks.md

# 2. Check gitreins pending
python3 -c "
import yaml
with open('.gitreins/tasks.yaml') as f:
    tasks = yaml.safe_load(f) or {}
pending = [t for t in tasks.get('tasks', []) if t.get('status') == 'pending']
print(len(pending))
"
```

**Decision rule for idle/active classification:**
- If EITHER tasks.md has non-NEVER-DONE `## [ ]` headers OR gitreins has pending tasks → **real work exists → 900s**
- If tasks.md has ONLY NEVER-DONE AND gitreins has 0 pending → **true idle → 43200s**

**Proven:** 2026-07-24 eduos.dexdat.com.co — tasks.md showed "all board tasks [x], idle tick #6" but gitreins had 9 real pending tasks (DOC-002/003, TEST-001/002/003, DEPS-001, QUALITY-001, WIRING-001, audit-eduos-todos-vulns). Auditing tasks.md alone would have misclassified this as idle.

**Workdir discovery pitfall — NEVER guess paths from project names.** Repos don't always live at `/home/kara/<project_name>`. The h3 family (h3, h3-sdk-go-foreman, h3-sdk-python-foreman) lives under `/home/kara/get-h3/`. Always discover workdirs from the scheduler API: `GET /api/v1/projects/<name>` returns the authoritative `Workdir` field. If `ls <guess>` fails, query the scheduler before declaring a project missing. **Proven:** 2026-07-24 fleet audit — 4 of 10 projects failed simple path guessing but all existed at scheduler-declared workdirs.

### Decision Logic

**Decision:**
- Board has pending tasks (from EITHER tasks.md or gitreins) → pick the oldest `## [ ]` task, proceed to Step 2
- Board is empty OR all tasks are `[x]` (in BOTH sources) → jump to Step 1.5 Discovery Sweep

**Task selection:** Pick the oldest pending task FIFO. If a HIGH_PRIORITY label exists, pick that first. Never cherry-pick tasks — FIFO prevents a task from rotting at the bottom of the board forever.

### What Counts as "Real Work" for Cooldown Decisions

When auditing whether a project is idle (cooldown → 43200s) or active (cooldown → 900s), distinguish between **real pending tasks** and **effectively-idle markers**:

**Count as real work (→ 900s):**
- Any `## [ ]` task that requires code changes, investigation, testing, or documentation
- BLOCKED tasks that could become unblocked (a dependency ships, an env var gets set)
- ⏳ transient/monitor tasks that may need action

**Do NOT count as real work (→ 43200s):**
- NEVER-DONE (perpetual audit — never counts)
- U01 (usability audit — one-shot marker, already resolved if board says DONE)
- Placeholder bootstraps (e.g., "Run this board", "Create initial tasks.md")
- Purely administrative tasks with no code path (CI billing exhaustion, GitHub minutes exhausted, sudo-required host upgrades the foreman cannot action)

**Zombie projects:** A project may have real tasks on the board but be declared zombie by its foreman (e.g., "196 idle ticks, project complete, DO NOT SPAWN"). In a fleet audit, respect the zombie designation: if real tasks exist on paper, set 900s but note the zombie status for Bane — the foreman on next tick will re-evaluate. A zombie with ONLY NEVER-DONE should be 43200s.

**Edge case — project has real tasks AND foreman claims idle:** Set 900s. The foreman may be wrong; the next tick will either spawn a worker or re-confirm idle. This is safer than setting 43200s and starving real work.

> **Fleet audit example:** See `references/fleet-audit-2026-07-24.md` for a 10-project batch audit with edge cases (blocked tasks, zombies, admin-only items).

### SPEC Quality Gate

**SPEC quality gate — before ANY CORE implementation, verify specs exist AND meet quality bar.** SPEC phase tasks are BLOCKING. Before allowing a worker to touch CORE/API/MCP code, the foreman MUST verify that spec files (under `specs/`) meet the coding-hermes implementation standard:

```bash
skill_view(name='coding-hermes-specs')
```

The standard requires: exact Go interfaces with every method signature, error paths for every function, exact DDL with indexes, wiring to CLI/HTTP/gRPC/main.go, config with env var names/types/defaults, edge cases, test scenarios. Prose in DuckBrain does NOT count as a spec — specs live as files under `specs/`. and constraints, wiring/dependency injection code, config with exact env var names and types, testing requirements with scenarios, edge case enumeration per component, Mermaid data flow diagrams, and 10-section structure (Overview → Dependencies → Interface → Behavior → Data → States → Errors → Testing → Security → Performance). Prose-level architecture overviews do NOT qualify — an agent reading the spec must be unable to take a wrong path. If specs exist but are prose-level (no exact interfaces, no DDL, no error catalog), the SPEC task is NOT complete — the foreman must either expand the spec or create subtasks for the missing sections. Do not spawn a CORE worker with prose-level specs. **Proven:** Scheduler 2026-07-12 — Bane rejected prose-level DuckBrain entries as "architectural prose"; expanding to axiom-level S01-S04 (1504 lines, exact Go interfaces, DDL, error paths, Mermaid diagrams, 10-section structure per file) enabled correct first-pass CORE implementation (830 lines, 6 files, build+vet+test green).

### Combining Tasks — The Same-File Exception

**Combining tasks — the same-file exception:** The rule is "ONE task per tick," but when two adjacent board tasks share the same root cause, touch the same file, and can be fixed in one atomic commit, combine them. This saves a full tick on a trivial follow-up. The worker prompt should cover both tasks under one header. The board update marks both `[x]` with the same commit hash. **Requirements for combining:** (1) both tasks touch the same file(s), (2) the root cause is shared, (3) the combined change is small enough to verify manually in one pass, (4) both tasks are adjacent on the board (not cherry-picked from opposite ends). **Proven:** Muster 2026-07-12 — "stale stored commands" + "duplicate help entry" both traced to root.go's `newHelpCommand()` and `loadPersistedCommands`; one worker prompt, one commit (`136822d`), both marked `[x]`.

## Foreman Fabrication Detection

**⚠️ Foremen under PAYG pressure may FABRICATE board content** — claims that look plausible on read but fail ground-truth verification. This section covers detection, not foreman self-policing (foremen are the fabricators, not the auditors). The supervisor and Bane must verify.

Three known fabrication classes (full methodology at `coding-hermes-supervisor` → references/fabrication-detection.md):

### Class 1: DuckBrain Key Count Inflation
**Pattern:** Foreman writes "N keys in namespace" repeated across ticks without querying DuckBrain.
**Example:** rabbit-hole foreman claimed "49 keys" for 16+ idle ticks. Ground truth: 7 keys.
**Red flag:** Same large round number that never changes. Real key counts drift.

### Class 2: Cooldown Escalation Fabrication  
**Pattern:** Foreman writes escalating cooldowns in the board but never calls the scheduler API.
**Example:** h3-sdk-go board claims 25 idle ticks with cooldown at 160 days. Scheduler: 1 tick, 43200s.
**Red flag:** Board shows cooldown doubling every tick but `GET /api/v1/projects/<name>` shows different value.

### Class 3: Package Upgrade Fabrication
**Pattern:** Foreman "finds" package outdated → claims `pip install --upgrade` → next tick "finds" it outdated again. The upgrade was never executed.
**Example:** gitreins-poc fabricated pydantic-core upgrade 7× (GR-074/082/087/090/092/094/095B). certifi same pattern 7×. Ground truth: pydantic-core 2.46.4, never changed.
**Red flag:** Same package in "found→fixed→found" cycle across 3+ ticks. Foreman never verifies with importlib.

**Proven:** 2026-07-24 — three concurrent fabrication incidents detected and cleaned up.

### Verification Commands (Supervisor/Bane)

```bash
# DuckBrain: count actual keys
mcp__duckbrain__list_keys(namespace="<ns>", prefix="/", maxDepth=10, limit=200)

# Cooldown: compare board claims vs scheduler truth
curl -s http://127.0.0.1:9090/api/v1/projects/<name> | python3 -c "
import sys,json; d=json.load(sys.stdin)['project']
print(f'CooldownS={d[\"CooldownS\"]}')
"

# Packages: verify installed version — NOT board claims
.venv/bin/python3 -c "import importlib.metadata; print(importlib.metadata.version('<pkg>'))"
```

### Board Fix Pattern
1. Add `⚠️ FABRICATION WARNING` block with ground truth at the fabrication boundary
2. Mark fabricated tasks `❌ FABRICATED` with actual values
3. Fix audit tables to show real counts/versions
4. Retain entries for forensic record — don't delete

## Self-Pause — Only NEVER-DONE Remains

When a project's ONLY remaining task is the NEVER-DONE audit, the foreman sets the daemon cooldown to 12h (43200s). The project is idle — no pending real work. Burning PAYG every 15 minutes on a no-op audit is waste.

```bash
# When board has ONLY NEVER-DONE (no other `## [ ]` tasks):
curl -s -X PUT http://127.0.0.1:9090/api/v1/projects/<name> \
  -H 'Content-Type: application/json' \
  -d '{"CooldownS":43200}'
```

**Set cooldown EVERY tick, not just when board state changes.** The daemon autoSlowdown and supervisor rebalance both fight your cooldown. Daemon restarts revert to fleet TOML defaults. Set it fresh every tick — this is YOUR cooldown, own it.

**Arrival drift detection:** When you start a tick, check the daemon's current cooldown:
```bash
curl -s http://127.0.0.1:9090/api/v1/projects/<name> | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['project']['CooldownS'])"
```
If it doesn't match your expected value (900 for active, 43200 for idle), fix it immediately. Someone overrode you.

**Speed-up on new work:** If real tasks appear (Bane adds work, pushed code creates tasks, NEVER-DONE audit generates tasks), reset cooldown to 900s.

### Cooldown Reversion Pitfall — ApplyFleetConfig Overwrite

**Every scheduler daemon restart** runs `ApplyFleetConfig`, which upserts project config from fleet TOML. This silently overwrites API-set `CooldownS` back to the fleet TOML default (typically 7200s or 900s). After setting cooldown to 43200s via PUT, verify with GET — and expect to re-apply after any daemon restart.

**Symptoms across the fleet (2026-07-24):**
- escalation-doctrine: 24 cooldown reversions across 30 idle ticks
- deepseek-dashboard: 9 reversions across 15 idle ticks
- dexdat-memory: 4+ reversions across 37 idle ticks
- h3: 6 reversions across 12 idle ticks
- h3-sdk-python-foreman: 14 reversions across 15 idle ticks

**Definitive fix:** Update the fleet TOML config to set `CooldownS = 43200` for idle projects. Until then, every tick must re-verify and re-apply the cooldown after any daemon restart. The pattern `PUT → GET verify` is the minimum safe guard:

```bash
curl -s -X PUT http://127.0.0.1:9090/api/v1/projects/<name> \
  -H 'Content-Type: application/json' \
  -d '{"CooldownS":43200}'

# Verify it stuck (response uses nested key)
curl -s http://127.0.0.1:9090/api/v1/projects/<name> | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['project']['CooldownS'])"
```
