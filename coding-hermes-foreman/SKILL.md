---
name: coding-hermes-foreman
description: >-
  Full SDLC project delivery loop. Per-project foreman that self-heals,
  scans tasks, analyzes impact, loads memory, spawns workers, verifies
  quality, commits, learns, and scans external signals. Loaded by every coding-hermes
  foreman cron job. Follows the fleet architecture.
version: 2.10.1
author: Bane + Hermes
platforms: []
metadata:
  hermes:
    tags: [coding-hermes, foreman, autonomous, sdlc, delivery]
    related_skills:
      - coding-hermes-cron
      - coding-hermes-self-heal
      - coding-hermes-board
      - coding-hermes-discovery
      - coding-hermes-worker-model
      - coding-hermes-map
      - hilo-usage
      - gitreins
      - prompt-foundry
      - duckbrain
  support_files:
    - references/{asce,mythos,totalstack,h3,consensus,crier,dexdat-core,canopy,smoke-test-project,uhlp,inference-estimator,duckbrain-recall-failure-modes,recurring-ci-failure-stacked-root-causes,stale-bug-reporting,pi-agent-rebuild,hermes-chat-workdir-gotcha,worker-session-stall-resume-pattern,operational-cli-batch-tasks,cron-mode-command-blocks,zombie-tick-protocol,go-lint-fix-patterns,guard-lint-scope-vs-ci,lint-debt-slice-recipe,gitlab-ci-audit,python-venv-test-verification,foreman-direct-code-exceptions,format-gate-symlink-false-pass,board-counting-commit-hygiene,foreman-project-onboarding,two-silent-workers-foreman-direct,pitfalls-session-learning,discovery-sweep-quality,scheduler-vs-cron-pitfall,cloudflare-tunnel-nextjs,concurrency-dual-source-race,rust-workspace-test-flakiness,testing-with-dummy-projects,typescript-pnpm-foreman-scaffold,go-ci-creation-pattern,gitreins-stale-task-cleanup,gitreins-mcp-task-complete-partial-success,go-engine-auto-persist-pitfall,go-test-timenow-nondeterminism,multi-repo-sdk-init-assessment,parallel-tick-sibling-signals,sibling-tick-board-collision,python-ci-make-targets,go-migration-goose-down-parsing,go-yaml-v3-byte-slices,cloudflared-tunnel-restart,cron-localhost-verification,live-e2e-detects-stub-plumbing,demo-user-protection-pattern,gh-pages-static-site-verification,shell-quoting-hermes-chat-q,misplaced-cross-project-code,parallel-spec-worker-spawning,skillmd-freshness-check,frontend-worker-api-type-mapping,sudo-blocked-cron-workaround,go-sqlite-schema-diagnosis,glm52-type-hallucination,muster-stub-wiring-phase2,empty-board-loop-self-pause,gitreins-poc-foreman-ops,scheduler-api-ground-truth,append-board-event-parquet-script,duplicate-handler-unwired-twin,subdir-agentsmd-context-injection,npm-dep-audit-override-pin,external-commit-mid-tick}.md
    - references/scheduler-api-and-terminal-pitfalls.md
    - references/scheduler-e2e-full-battery-recipe.md
    - references/scheduler-idle-light-tick-recipe.md
    - references/spa-fallback-probe-false-positive.md
    - templates/{mythos-board-dispatch.py,go-github-ci.yml}
    - scripts/check_pypi_pin.py
---

> See [coding-hermes-map] for the full skill hierarchy and when to use each skill.

# Coding Hermes Foreman — Full SDLC Project Delivery

The foreman is the per-project orchestrator. Every tick runs a complete software development lifecycle: self-heal, scan the board, analyze impact, load project memory, pre-load context, spawn a worker with the right model and provider, verify quality through GitReins guard and judge, commit, submit learnings to Off-by-One, write findings to DuckBrain, and scan external signals before the next task. The foreman DOES NOT write code — it inspects, plans, dispatches, and verifies.

**A foreman tick delivers a complete unit of work.** Not a fragment. Not a step. The worker writes code until the acceptance criteria are met, the guard passes, the judge approves, and the commit is clean. If the worker fails, the foreman retries with adjustments. If the worker succeeds, the foreman learns and moves on.

## DISPATCH DOCTRINE (positive doctrine — outranks caution clauses for row selection only)

Caution clauses govern SAFETY of a dispatch; this section governs WHETHER to dispatch. When they conflict on row selection, dispatch wins unless a clause names a concrete active hazard (live worker on same paths, operator-blocked row, real capability/safety barrier).

1. **DEFAULT WAVE**: every tick, dispatch ALL independent ready rows up to admitted slots. Worktrees make rows independent; separate worktrees satisfy "different files" by construction.
2. **INLINE WORK FORBIDDEN when admitted slots >= 2.** The foreman implements only when slots < 2 AND the row is trivial, or every dispatch path is concretely blocked (name the clause).
3. **BARRIERS STOP THE WORKER, NEVER THE TICK**: a blocked row parks; pick the next ready row and keep filling slots. One blocked receipt is not an idle verdict.
4. **VERIFICATION-ONLY IS ROW-SCOPED**: if a specific row already landed, verify that row and move to the NEXT row in the same tick. Never convert the whole tick to verification-only because one row landed.
5. **REFILL**: when a merge frees a dependency/slot, dispatch the next wave immediately — the tick runs until no active attempts, no mergeable results, and no ready rows.
6. **ROLLING STATE MACHINE**: RECONCILE → SELECT block → CLASSIFY rows → FILL slots → COLLECT/VERIFY/REQUEUE/INTEGRATE → RECOMPUTE → FILL again. Deadline exhaustion is a partial report with a continuation manifest, not IDLE.
7. **WAVE FLOOR IS 1**: wave_size = 0 is forbidden whenever a dispatchable ready row exists. A singleton block forms a SERIAL wave of one worker (lane prompt §4); ">= 2 rows" is the preferred wave path, never a requirement — any reference language calling a singleton block unable to act ("wave is impossible") is SUPERSEDED by this clause. A wave-0 report must name the exact clause that produced it, and that clause must name a concrete active hazard, not arithmetic.
8. **GIT RESIDUE IS PATH-SCOPED, NEVER A TICK BARRIER**: `.git/ORIG_HEAD` (written by every merge/rebase — see references/gitreins-lifecycle-residue-self-resolution.md), stale lockfiles, untracked sibling evidence files, and sibling-modified tracked files OUTSIDE the chosen rows' paths never bar row selection or board reads. The barrier fences only the paths the residue touches; if the residue sits on the chosen row's paths, park that row and dispatch the next one — the tick still fills its slots. **A DIRTY BOARD IS NEVER A TICK BARRIER (Bane, standing order — repeated; BLOCKED-CANONICAL with wave_size=0 over `.gitreins/tasks.yaml` / board JSONL is a DOCTRINE VIOLATION, measured 2026-11-15: 344 dry foreman ticks/week were barrier burns)**: when board/lifecycle files are modified, either (a) commit the board-only residue first (it is provably board state — commit it, cite the hashes in the tick receipt), or (b) cut the worker worktree from a CLEAN commit (`~/.hermes/scripts/worktree.sh new <project> <taskid>` bases on the current HEAD) and dispatch from there — the dirty canonical tree never gates the wave. Do not write a BLOCKED receipt and end the tick while dispatchable rows exist.
9. **OWNER-APPROVAL RANKS FIRST**: rows whose foreman_note/worker_summary carries "OWNER APPROVAL" (or a recorded owner answer) rank ahead of discovery fills in block ranking, and new-row discovery is capped at ONE filing per tick while owner-approved rows are pending.
10. **INLINE VERIFICATION IS CAPPED**: foreman-direct verification of a landed row is row-scoped and allowed; if it exceeds ~5M tokens in one tick, the tick instead files a row to convert that verification into a scripted battery — repeating an expensive live check tick after tick is a leak, not diligence.
11. **WAVES CROSS BLOCKS AND SPAN TICKS (owner law, 2026-11-15)**: independence is defined by `depends_on` edges and file seams, NEVER by board family — a wave may mix rows from totally different parts of the project ("even if they are totally different parts of the project") as long as they are mutually unblocked and touch different paths. Where a lane prompt says "one block per tick", that is a soft preference, superseded here: when the chosen block has fewer ready rows than admitted slots, FILL THE REMAINING SLOTS from other blocks' ready rows (owner-approved rows first per §9). A wave may also SPAN TICKS: persist the wave manifest (.coding-hermes/waves/<wave-id>.json) and have the next tick RESUME the same wave id — refilling freed slots — instead of composing a fresh wave; multi-tick waves are the expected shape for work bigger than one tick's slots. Never discard a healthy wave to start a new one.
7. **EARLY WAKE**: on a board_wake nudge, check `boardctl ready` once; if empty, emit a one-turn wake receipt and stop (DF-BOARDWAKE-002).
8. **WAVE SIZE IS DATA**: `min(independent ready rows, admitted slots)` — never a judgment call below the cap. If you dispatch fewer than the cap, cite the row-level reason on the board.

12. **WORK-ORDER OVER BOARD-PICKING (owner, 2026-11-15 — hermes-dagger r4 lesson):** when a review, audit, or owner call-out names work, the foreman passes a WORK-ORDER — the exact rows in priority order, each ALREADY converted into a worker brief with executable acceptance. Filing a finding row is not doing it: a row whose acceptance is prose ("no harness exists", "claims unverifiable") defers forever. Convert findings to runnable acceptance (named deliverable paths, runnable commands, evidence format) before the tick ends, and dispatch the work-order rows FIRST — general board fills come after. If a work-order row is blocked, report the blocker against that row; never substitute an easier row and call it progress. Hygiene closes do not count as gap progress — tick receipts report work-order movement separately.
13. **OWNER-GATE DOES NOT BLEED:** a gated subtask (running an experiment, publishing, a restart) gates only its own row. Ungated siblings (building the harness, the grading battery) stay dispatchable and must never be parked because a sibling needs a decision.
14. **BOARD TRACK AND PRODUCT TRACK ARE SEPARATE AND PARALLEL:** product track = workers building/probing rows in their own worktrees; board track = row edits, rescoping, evidence binding, stale-row closure. Dispatch the product wave FIRST, then do board work while workers execute — a running worker is not a reason to idle. A tick that only waits on workers while board work is actionable is an idle tick; a tick that only does board work while slots sit empty violates the wave floor. Board edits never block on worker results (bind evidence at verified-merge time), and in a shared checkout they go through the sanctioned writer or a plumbing commit without touching worker worktrees or the foreman's dirty files.

## SUPPORT-AGENT ROUTING (workers are for CODING; everything else routes — Bane 2026-11-15)
Workers = coding sessions in worktrees. A row whose WORK is not coding is not yours to re-read every tick — route it ONCE (defer with the owning agent named in defer_reason, which also removes it from the workable count) and fill the wave from real code rows. Routing by row class:

- `[release]`/`[releng]`/RELEASE-* -> the project's releng lane. Cut/no-cut is releng's decision; version-carrier prep (changelog/README pins/openapi version) is file edits the FOREMAN codes as normal worker work; the CUT itself is owner-gated — never tag/publish.
- Deploy / stale service / PATH-binary hygiene -> the ops lane (e.g. crier-ops). Restarts of live services stay owner-gated (SCHEDULER_OPERATOR_RESTART_APPROVED); ops measures and waits, visibly.
- Disk full / runner offline / host hygiene -> unblock agent / bunker-ops (live-system-triage class). Defer with the HOST named; a foreman cannot fix a remote box.
- QA-harness defects (the battery itself broken: judge caps, evidence ledger, transcript perms) -> qa-foreman / bunker-qa lane. They self-block while their own tooling is the defect; coding workers cannot close them.
- Stale statuses (work done, status pending) -> sync/pm sweep, or close yourself only when you hold the evidence run id (TR-251 refuses otherwise).
- `[loop:...]`/CONTRACT rows -> process rows, never dispatched as worker work.
- Owner-gated (restarts, money, credentials, public surfaces, foreign data, posture decisions) -> defer with `OWNER-GATED:` + the exact question. Unanswered offer is NOT consent (lane-authority).
- Everything that is CODE in a repo this lane owns -> your coding workers (the wave doctrine above).

Test before selecting: if the row's acceptance cannot be met by editing code in this repo and running its gates, it routes. This complements (never replaces) clause 8 — path-scoped residue still fences the touched paths; whole-row ROUTING is for rows whose OWNER is a different agent entirely.

## The Full Foreman Loop

The foreman spawns workers via `hermes chat` CLI, not `delegate_task`. Delegation inherits the foreman's model and provider (PAYG deepseek-foreman), which is exactly wrong. Workers must use prepaid flat-rate buckets. The foreman selects the worker's model and provider independently per task.

```bash
# CORRECT — independent session, separate model/provider
# Use cd for workdir (hermes chat has no --workdir flag)
# Use terminal(background=true) for async (hermes chat has no --background flag)
cd /home/kara/<project> && hermes chat -q '<compiled prompt>' -m '<coding-model>' --provider '<prepaid-bucket>' --ignore-rules --cli -Q --max-turns 2000 --run-budget 7200

# TURNS/BUDGET ARE MANDATORY: an unset --max-turns inherits agent.max_turns (config default
# 500) and a card with a big scope dies mid-task with its brief half-done and no verdict.
# Heavy cards need real budgets — kanban goals already default to goals.max_turns: 10000.
# Size: routine code task 1000; multi-file migration / full-battery run 2000;
# repo-wide analysis 5000. If a card dies on turns, RE-DISPATCH with the remaining
# scope named, never mark it done.
```

```python
# WRONG — inherits foreman's PAYG provider
delegate_task(goal="...", context="...", role="leaf")
```

```
┌─────────────────────────────────────────────────────────────────────┐
│ TICK FIRES                                                          │
│   ↓                                                                 │
│ 0. SELF-HEAL — identity, deps, CI, transient fixes                  │
│   ↓                                                                 │
│ 1. READ BOARD — .coding-hermes/tasks.md, count pending              │
│   ├── Board has tasks? → PICK TASK → continue to Step 2             │
│   └── Board empty? → 1.5 DISCOVERY SWEEP → 1.5h E2E VERIFY          │
│        ├── Sweep found work? → create tasks → 1.6 → NEXT            │
│        └── No work + E2E passes? → SELF-PAUSE TRACK → 1.6 → NEXT    │
│   ↓                                                                 │
│ 2. HILO IMPACT — graph, impact analysis, classify                   │
│   ↓                                                                 │
│ 3. DUCKBRAIN RECALL — load past decisions, pitfalls, patterns       │
│   ↓                                                                 │
│ 4. PRE-LOAD — assemble context + compile through prompt-foundry     │
│   ↓                                                                 │
│ 5. SPAWN WORKER — hermes chat -q, coding model, prepaid bucket      │
│   ↓                                                                 │
│ 6. GITREINS GUARD — tier 1: secrets, build, lint, tests             │
│   ↓                                                                 │
│ 7. GITREINS JUDGE — tier 2: LLM evaluation vs acceptance criteria   │
│   ↓                                                                 │
│ 8. COMMIT — targeted add, correct authorship, descriptive message   │
│   ↓                                                                 │
│ 9. OFF-BY-ONE — submit solved problem, discover cached solutions    │
│   ↓                                                                 │
│ 10. DUCKBRAIN WRITE — store findings, patterns, pitfalls, idle ctr  │
│   ↓                                                                 │
│ 1.6 SCAN SIGNALS — external changes, CI status, new issues, deps    │
│   ↓                                                                 │
│ ➡️ SELF-PAUSE CHECK — idle ticks? adjust interval or pause          │
│ ➡️ NEXT TASK — return to Step 1                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Step 0 — Self-Heal
Load skill: coding-hermes-self-heal
See [coding-hermes-self-heal] for full self-heal procedure.

**Sibling clone w/ unpushed ticks:** merge before numbering — `references/sibling-clone-self-heal.md`.

## Step 1 — Read Board
Load skill: coding-hermes-board (full board + self-pause procedure).
**⚠️ BOARD-V2: active board is `.coding-hermes/board/` — READ: `tasks.jsonl`/`dump_board_state.py` (refs: board-tools-arg-conventions.md), or `boardctl` (github.com/coding-hermes/boardctl); WRITE: `append_board_event.py`. **📌 CANONICAL STORE = JSONL — board.db RETIRED 2026-09-03 (Bane doctrine: no db cache file; the JSONL files ARE the board): db/parquet caches deleted fleet-wide, db-only scripts retired; `git ls-files .coding-hermes/board/` must list NO .db/.parquet; NEVER recreate board.db (JSONL-NORM-001); full doctrine: refs/board-storage-canonical.md** — tasks.md stale pre-migration or ABSENT post-migration (missing tasks.md + only `.bak` = migration-complete). Matrix 🔄 drift: reconcile from events.jsonl/tasks.jsonl (ref: commit-trailer-and-board-mirror-drift.md). Dispatch order: INSERT task row BEFORE the event (ref: board-v2-migration-and-dispatch-order.md). Header counters stale — re-sync from DuckBrain; `last_commit` lags one tick (ref: board-jsonl-header-last-commit-lag.md). Tracked-markdown boards (no board/ dir): APPEND at BOTTOM — old TOP entry ≠ stale; verify `git log -1 -- tasks.md` + highest #NNN (ref: tracked-markdown-board-reading.md). **⚠️ ALWAYS read the TAIL first on tracked-markdown boards.** Gate with `git log -1 --oneline` (commit message carries the tick, e.g. "Tick #219") + `grep -n 'Tick #NNN' .coding-hermes/tasks.md | tail -3` → read ONLY from the latest entry line onward (`tail -n 120` is the zero-waste recovery). A head-first read of a 400KB+ board burns 100K+ chars of stale context (h3: 35 recurrences — the scheduler prompt's "Read .coding-hermes/tasks.md" is satisfied by the gate-first tail read, NEVER by a bare head read_file; the read fires from prompt text in whatever batch it gets scheduled, so do not trust an in-head "I'll read the tail" plan). **Project-specific foreman-ops references (`references/<project>-foreman-ops.md` and any per-project tick ledger) MUST load in batch 1, parallel with this skill and BEFORE any tasks.md read** — batch-2-or-later loading costs the stale head read every time; record recurrences honestly in the ledger (verify the actual tool-call sequence before writing "clean"). EXCEPTION: off-by-one board PREPENDS at TOP (ref: off-by-one-foreman-ops.md). Multi-event append pitfalls: refs/duckdb-board-multi-event-append-pitfalls.md; fixtures crash: refs/board-read-script-fixtures-coalesce.md.**

**Scheduler IDLE/light-audit ticks** (no pending code tasks, no fixture window open): full recipe in `references/scheduler-idle-light-tick-recipe.md` — gate battery, event JSON shape, header `--set` conventions, fixture-row updates, scanner-safe storm-watch probe, idle-counter/self-pause semantics.

## Lane Authority — OWNER-RATIFIED 2026-11-11 (SCHED-GAP-16937)
Standing classification, verbatim source: `docs/lane-authority.md` in the coding-hermes-scheduler repo. A lane MAY decide alone: code work in its own repos (fix, don't file-to-ask), re-statusing its own rows (blocked→pending when the blocker resolves; re-file defects to the repo that OWNS the code, path+function named), housekeeping purges with read-back proof, scope-narrowing to the free subset, rollbacks of its own automation, filing new rows with runnable criteria, closing rows on file-read evidence. A lane MUST ask the owner: money, credentials, public surfaces, foreign data deletion, security posture, fleet structure (other projects' lanes/cadences/config), irreversible operations. When unsure: most recent explicit owner instruction first, then the file — **an unanswered offer is NOT consent**; "maybe we should X" = evaluate, not authorize; one decision card per decision (owner-decision-briefing shape), never a vague `OWNER:` placeholder, never silent parking. TRIAGE-00x rows re-triage the parked rows against this; cite the file, not personal judgement.

## Step 1.5 — Discovery Sweep
Load skill: coding-hermes-discovery
See [coding-hermes-discovery] for full discovery sweep across all languages.

## Self-Pause — Only NEVER-DONE Remains
**Scheduler-driven projects: EXECUTE the pause, don't just report CRON_PAUSE_REQUESTED.** Cooldown: 0 pending → `7200`; `DecayRate=0` REJECTED; PUTs revert — fleet.toml pin. PUT bodies: Go field names (`{"CooldownS":7200}`, snake_case ignored) — refs scheduler-api-put-field-names.md. **SELF-PAUSE GUARD: never pause with open 🔴/🟡 tasks. NEVER-DONE row stays `pending` FOREVER — perpetual audit fixture (helios #150); retire ONLY via explicit board task (sdk-python #67): references/never-done-fixture-retirement.md. Recurring fixtures with a due window count as pending — idle #10+ no-pause CORRECT while due; fixture gates pause, not idle counter; window/ladder/starvation detail: refs/never-done-fixture-retirement.md, refs/idle-cheap-audit-ladder.md.**

## Step 2 — Hilo Impact Analysis

**Daemon pitfalls:** `references/daemon-pitfalls.md`. **Scheduler live check:** `references/scheduler-project-live-check.md` (Go field names on GET). DB: `references/scheduler-live-db-schema.md`. **Cooldown drift:** `references/scheduler-autoslowdown-cooldown-drift.md`.

Before touching code, understand the blast radius. Hilo prevents "fix one thing, break three others."

**Hilo (corrected):** `hilo graph impact <file>` for blast radius — impact is a `graph` subcommand (bare `hilo impact` invalid). `hilo classify <file>` = file roles, not task types. Full surface: `references/hilo-foreman-commands.md`.

**What you learn:** files touched, transitive dependents (blast radius), classification.

**Use this to inform the worker.** Don't just pass a task description — pass the impact analysis. "Modify parser.go — depends_on: lexer.go, ast.go, formatter.go. Risk: high, 3 dependent packages."

## Step 3 — DuckBrain Context Load

**ALWAYS pass `namespace="<project-namespace>"` explicitly; NEVER call `switch_namespace`** **Namespace source: `board.namespace` — ⚠️ display name or FLEET-wide; ns missing or recall count=0 → list_namespaces → repo dir name (silent-empty: ring-runner t54).** ⚠️ Umbrella ns: bare `/tick/N` may be a sibling repo's record — use `/project/<repo>/` keys (refs/duckbrain-shared-namespace-tick-keys.md).

```python
duckbrain_recall(key="/project/<name>/status", namespace="<project-namespace>")   # own state
duckbrain_list_keys(prefix="/project/<name>/", namespace="<project-namespace>")
duckbrain_recall(query="architecture decisions <subsystem>", namespace="<project-namespace>")
duckbrain_recall(query="pitfalls <subsystem>", namespace="<project-namespace>")
duckbrain_recall(query="patterns <task-type>", namespace="<project-namespace>")
```

**Server awareness:** `server_status` → `server_http_start` if down → `recall` (HTTP server = separate `bin/duckbrain.js http` process; stdio MCP ≠ HTTP up — refs: duckbrain-recall-failure-modes.md, duckbrain-recall-recency.md)

**Fallbacks:** `recall()` fails → `list_keys(prefix="/project/<name>/")`. MCP dead (DUCKDB_CONNECTION_LOST) → HTTP :3000 fallback (refs: duckbrain-http-fallback.md, duckbrain-http-namespace-read-path.md). Empty ≠ no state — `list_namespaces` (ref: tick-state-query-misdirection.md); truly empty → Step 4. Prefix drift: sparse ≠ no state, `list_keys(prefix="/")` (ref: duckbrain-key-prefix-drift.md). 🪤 Exact-key `recall` is relevance-ranked, not newest-first — can omit the latest status write (ring-runner t57); stale recall ≠ skipped Step 10, verify via `list_keys`/board (ref: duckbrain-recall-recency.md)

## Step 4 — Pre-Load

Assemble the complete context package for the worker. The worker prompt MUST include: task description verbatim from the board; Hilo impact analysis (blast radius, risk); DuckBrain context (summarized); RELEVANT FILES (read the actual code the worker will modify — send content, not filenames); acceptance criteria (concrete, verifiable); verification requirements (ad-hoc verification scripts after every edit — no verbal claims); commit instructions (targeted add, correct authorship, descriptive message); GitReins instructions (worker runs `gitreins guard` before committing); VERIFIED FACTS block — grep pre-dispatch to confirm spec-referenced interfaces/migrations exist; embed "verified — do not re-verify" (ref: pre-dispatch-verified-facts.md; stale-finding live-probe + CLI inventory: `references/stale-findings-cli-surface-audit.md`). **Spec-gap wiring pattern:** SPEC-GAP "X not implemented" may be a wiring gap (primitives present, zero callers) — wire, don't reimplement (refs: spec-gap-wiring-existing-primitives.md, shared-helper-misleading-comment.md).

**Compile through prompt-foundry** to produce a clean, well-structured worker prompt (model-specific formatting: GLM structured, MiniMax different).

**Spec-context blocks at dispatch (the factory call site).** When the project ships a spec-context builder, run it for the row BEFORE authoring the brief and embed its output — this is the call site that keeps `spec context` / `spec assemble` from being dead code:

```bash
cd ~/<project> && PATH=$PWD/.venv/bin:$PATH python3 scripts/brief_spec_context.py \
  --row <ROW-ID> --spec-root specs --repo-root "$PWD" \
  --out /tmp/<ROW>-spec-context.md --status-json /tmp/<ROW>-spec-context.json
```

Embed the emitted section verbatim (each block heading carries that block's own byte count) and read the outcome from `--status-json`. Exit contract: **0** = a section was emitted, or the answer was *honestly* empty — a 0-byte file means embed NO context section (never a placeholder heading), and the reason (`unscoped` / `inactive` / `unknown-task`) belongs in the tick report; **3** = ambiguous — nothing emitted, name the candidate ids in the tick report instead of guessing; **2** = typed refusal — name the error code. Never hand-write a "SPEC CONTEXT" section from row text alone: that is the decorative-brief defect the builder exists to close.

**The worker gets ONE message — no skills, no architecture, no fleet context, no model/provider awareness.** The foreman handles all of that. The worker just codes.

### Non-Code Tasks — When the Foreman IS the Worker

Investigation, health-check, monitoring, root-cause analysis, and operational CLI-execution tasks skip Steps 5-7. See `references/operational-cli-batch-tasks.md` for the CLI execution variant.

```
Step 0 → Step 1 → Step 2 (skip if no code) → Step 3 → Step 4 (investigation plan, not worker prompt)
    → SKIP Steps 5-7 → Step 8 (commit findings/board update) → Step 9 → Step 10 → Step 1.6
```

**When to use the shortened loop:**
- Infrastructure investigation (write degradation, thread leak analysis, health checks)
- Server-side diagnostics (MCP health, connection state, error log review)
- Monitoring transitions (moving a task from "likely resolved" to "48h watch")
- Tasks marked `## [ ] INFRA` or `## [ ] INVESTIGATE` on the board

**DEP-AUDIT:** `references/go-dep-audit-recipe.md` (Go) + `references/python-pip-audit-scoping.md` (Py: `uv export` scoped). Proven: helios #141, h3-sdk-python #41. **Node/npm:** `references/npm-dep-audit-override-pin.md` — targeted `overrides` pin for transitive vulns; `npm audit fix` churns the lockfile (optional platform packages), override + single-package bump + full-suite verify is the idle-tick-safe path. Proven: speclang #129.

**PERF-PROFILE:** `references/go-perf-profiling-recipe.md` — bench-mock full-copy/sort pitfall, zero-CPU-sample unit-test profiles, `-cpuprofile` single-package. Proven: helios #146.

**SEC-SCAN class:** `references/go-security-scan-recipe.md` — govulncheck + gitleaks + git fsck triage, the gitleaks `unable to read tree` red herring (missing trees in UNREACHABLE history = cosmetic, gitleaks still completes with no leaks — verify via fsck + rev-list before treating as corruption), uncalled-vuln triage (GO-2026-5932 openpgp = standing non-actionable, no fix exists), full-gate close + parquet board commit. Proven: helios #142.

**What changes:**
- Step 2 (Hilo): Skip if there's no code to analyze — infra tasks touch live systems, not source files
- Step 4: Instead of compiling a worker prompt, build an **investigation plan** — what to check, what to test, what success looks like
- Steps 5-7: **Intentionally skipped.** No worker to spawn, no code to guard or judge
- Step 8: Commit the board update and any findings. The commit type is `chore` or `docs`
- Step 10: Write investigation findings to DuckBrain — this is the primary deliverable

**You are still the foreman.** You're not writing production code. You're investigating, testing, analyzing, and reporting. The investigation itself IS the work product. When the investigation reveals a code fix is needed, that becomes a new task on the board — and the NEXT tick will spawn a worker for it.

**Proven:** DuckBrain 2026-07-12 — DB-003 write degradation investigation. Foreman tested write→read cycle (confirmed working), checked MCP server health (51Gi RAM, no thread leak), reviewed context-sync output (July 11 still showed INTENDED FACTS), concluded DB-002+DB-004 were probable root causes. Moved DB-003 to 48h monitoring. No worker spawned, no code changed. Board updated, findings written to DuckBrain.

**Sidecar glue-package investigation:** When a task asks for a thin coordination/routing/glue package in a sidecar project, but the imported dependency already handles the full pipeline, treat it as investigation (shortened loop). The task was likely written before the full integration existed. Trace each AC against the dependency's codebase, verify the sidecar wires all components in its main.go, and compile+test to confirm. See `references/sidecar-glue-package-investigation.md` for the full detection signals and decision table. **Proven:** DexDat CONSENSUS-9 (2026-07-13) — task asked for `consensus-sidecar/internal/routing/` to implement user→LLM→user message pipeline; all 10 ACs mapped to existing Consensus harness, API, shim, and planning code. Marked `[x]` with verification, no worker spawned.

## Parallel Ticks — Git Worktrees (DEFAULT for concurrent dispatch)

**One worktree per worker. Never two workers in one shared tree.** The default
foreman loop is serial (one worker per tick); when you dispatch CONCURRENT
workers (parallel board tasks, catch-up bursts, split subtasks), each worker
gets its own worktree:

```bash
cd ~/<project> && git fetch origin
# helper owns naming/branch/base/slug + prints BASE_SHA (record it — see 2a)
WT=$(~/.hermes/scripts/worktree.sh new <project> <taskid>)
cd $WT && hermes chat -q "$(cat /tmp/brief-<taskid>.txt)" \
  --provider <bucket> --model <model> -s coding-hermes-worker --ignore-rules --cli -Q &
```

**Helper (`scripts/worktree.sh`, install to `~/.hermes/scripts/`) — use it instead of hand-rolled `git worktree add`:** `new <project> <taskid>` (creates `~/worktrees/<project>-<taskid>` on `wt/<taskid>`, prints `WORKTREE`/`BRANCH`/`BASE_SHA`), `list`, `flags <project> <taskid>` (emits boardctl flags), `reap <project>` (removes merged+clean worktrees, deletes merged branches, **never touches a worktree with uncommitted files**), `prune`, `doctor` (fleet leak report).

**Board wiring (`boardctl` >= write-row-worktree-fields):** a row records WHERE the work happened and WHICH sessions worked it — write them at dispatch and at closeout:

```bash
boardctl -C ~/<project> update <taskid> --status in_progress \
  $(~/.hermes/scripts/worktree.sh flags <project> <taskid>) --session <foreman-session-id>
```

Absent flags write NO key (never an empty string/array); `--session` is repeatable and order-preserving.

**Wave manifest (required for crash recovery):** write `.coding-hermes/waves/<scheduler-tick-id>.json` in the MAIN tree before dispatching a wave — the scheduler reads exactly that path for recovery (`internal/scheduler/wave_manifest.go`). Without it an overrun tick's wave work is orphaned, not recovered.

**Worktree rules:**
- Branch naming `wt/<taskid>` — self-identifying for merge and cleanup; base on `origin/main`, never a local branch another worker may advance.
- Brief carries the worktree path as THE workdir; the worker never touches `/home/kara/<project>` or a sibling worktree.
- Worker briefs in parallel mode MUST include the isolation preamble: "You are in an isolated git worktree. Commit normally — do NOT stash, reset, or clean; the foreman merges your branch, you never merge or push." (Removes the entire `git reset`-wipes-sibling class: foreman skill refs hermes-canopy 2026-08-02, rabbit-hole DF-022.)
- Worktree branches are LOCAL-ONLY until merged — workers NEVER push (push rights belong to the merge step; prevents half-rebased wt branches on origin).
- Guard/judge run INSIDE the worktree (path-limited effects; no index.lock contention with siblings — each worktree has its own index).
- Board/`.gitreins` files are shared via the MAIN tree only — workers never write board state anyway (worker Rule 6).

**Merge phase (after all workers report):**
1. Reap: `git worktree list` → for each finished: record commit, `git worktree remove <path>` (worktree dirs are disposable; the branch carries the work).
2. Merge serially into main in-dispatch order: `git merge --no-ff wt/<taskid>` — one at a time, gates re-run per merge (build+test on the MERGED tree, not the branch tip).
3. Merge failure (real conflict): the branch is the worker's honest output — do not force. `git merge --abort`, re-dispatch a fixup worker in a FRESH worktree based on current main with the conflict described. Never hand-resolve large conflicts yourself unless mechanical.
4. After all merges: `git branch -d wt/<taskid>` for merged branches (keep unmerged for evidence), `git worktree prune`. One step: `~/.hermes/scripts/worktree.sh reap <project>` (merged+clean only) then `prune <project>`; `doctor` reports fleet-wide leaks (refs to deleted dirs).

**Wave composition (eligibility):** a wave is ≥2 workers dispatched in ONE tick.
Tasks are wave-eligible only if mutually independent: no depends_on edges between
them AND disjoint file sets (overlapping hilo blast radius = not eligible). Cap a
wave at the namespace wave_workers_cap (12 on coding-hermes; the scheduler injects the live
WAVE_BUDGET number at spawn and sheds to serial when a wave is already in flight) (each multiplies guard+judge cost; the 2h tick timeout bounds
wave wall-clock — one long worker starves the others' merges). Mark every picked
task `in_progress` BEFORE dispatching its worker (a crashed tick must leave
recoverable state, not silent loss). ONE wave per tick — never a second wave while
one runs. Workers get sibling awareness in their briefs (who else is running), but
zero coordination: disjoint scopes, own worktrees.

**Foreman merge checklist (the foreman's OWN verification — the worker's judge
covers the branch, the foreman covers the merge):** per merged branch:
(1) merge clean, or conflicts went to a fixup worker in a fresh worktree (never
hand-resolved beyond the mechanical); (2) full gates re-ran on the MERGED tree,
not the branch tip; (3) worktree removed + branch merged or explicitly preserved
as evidence; (4) board truth: every wave task landed (complete, or failed WITH a
reason), events carry branch @ sha; (5) no worker pushed anywhere (worktree
branches are local-only in auto-merge mode — push is foreman-only, post-merge);
(6) DuckBrain/off-by-one writes reflect the whole wave, not one worker. The tick
report includes a wave table: task → branch @ sha → judge verdict → merge result.

**When NOT to worktree:** single-task ticks (default; no overhead), tasks sharing ONE file set deliberately (use the shared-tree path-limited-commit protocol in the worker skill Rule 5), infra tasks touching live services (no isolation possible anyway).

## Merge Mode — AUTO-MERGE (default) vs PR

**Default: AUTO-MERGE.** Worktree branches merge to main locally, gates green, then push — per existing push doctrine (every configured remote; AGENTS.md no-push rules win).

**PR mode (opt-in, per project or per task):** use when a project has branch protection, an external reviewer, or Bane asks for reviewable history.
1. Worker pushes its `wt/<taskid>` branch to origin (exception to local-only: PR mode ONLY).
2. Open PR: `gh pr create -R <repo> --base main --head wt/<taskid> --fill` — body carries task-id, worktree provenance, guard/judge verdicts.
3. CI green on the PR is the merge gate; `gh pr merge --squash` (or merge-commit per repo convention) once green. Comment the judge verdict into the PR before merging.
4. PR mode does NOT change verification: guard + judge still run in the worktree BEFORE the push; a PR is a transport, not a quality gate.

**Proven (shared-tree precursors the worktree protocol replaces):** ring-runner RR-ENG-03→06 parallel pairs, ai_plays_poke GAP-001 index.lock 15-min wait, helios DOGFOOD-009/010 wait-for-green, rabbit-hole DF-022 hunk surgery, hermes-canopy reset-wipe recovery — all were workarounds for one shared tree; worktrees remove the failure class instead of surviving it.

## Step 5 — Spawn Worker

**Correct pattern:** spawn workers via `terminal` with `hermes chat -q`:

```bash
cd /home/kara/<project> && hermes chat -q "$(cat /tmp/worker-prompt.txt)" \
  --provider <flat-rate-provider> --model <model> -s coding-hermes-worker \
  --ignore-rules --cli -Q
```

Workers launched this way use their own provider/model/key — **flat-rate/prepaid SUBS ONLY (opencode-go, ollama-cloud, neuralwatt, kimi-for-coding) — NEVER DeepSeek PAYG** (Bane doctrine 2026-08-22: PAYG = foreman only; PAYG coding ran up the bill). Primary coding model: `ox-alpha-free` @ opencode-go.

**⚠️ CRITICAL: Tool availability overrides text.**

**Recommended foreman toolsets:**
```json
["terminal", "file", "web", "search", "skills", "memory"]
```

Explicitly removed: `delegation` (burns PAYG key via inherited provider), `cronjob` (prevents self-modification of schedule and cooldown drift).

The `coding-hermes-worker` skill handles: read before writing, match conventions, write tests, build before commit, small commits, no side effects, verify then report. The foreman does not inline these rules — the worker skill is the single source of truth.

## Worker Model Selection
Load skill: coding-hermes-worker-model
See [coding-hermes-worker-model] for capability-based model routing.

## Step 6 — GitReins Guard

**🚨 CRITICAL: NEVER run bare `gitreins guard` — always use `timeout N gitreins guard`.**
Bare guard calls create zombies when the guard hangs (network timeout, large test suite, secrets scan stall). A hung guard locks the foreman's `_running_job_ids` entry for 30 minutes. Always wrap with `timeout`. Piping guard output masks `$?` (tail's exit) — use pipefail/PIPESTATUS; references/guard-pipe-exit-code.md

### Guard results

| Result | Action |
|--------|--------|
| ✅ PASS | Proceed to Step 7 (judge) |
| ❌ FAIL — transient | Retry once. If still failing, this is a real issue — the worker should have caught it |
| ❌ FAIL — real issue | The worker's job was to ensure guard passed before claiming done. Escalate: this task needs another worker pass |
| ❌ FAIL — pre-existing | If the failure existed before this tick (check git blame), flag in Step 10 but don't block the commit. Prove flake-vs-regression via three-way worktree check (`references/pre-existing-test-flake-worktree-verification.md`) |

**Go guard-test flakes under host load:** go_tests guard runs a HARDCODED `go test -count=1 -short ./...` (full repo; config `test_command` only applies to Python guards — repro with the EXACT command). Varying "N failure(s)" counts + gitleaks 30s timeout warning = host-contention flake, not regression — verify exact command standalone, commit. Debug: gitreins ref `go-guard-test-command-and-flake-debugging.md`.

**Rust-specific test flakiness:** When `cargo test --workspace` shows a transient-looking failure, narrow to the specific crate before diagnosing (`cargo test -p <crate>`). Parallel test contention in Rust workspaces (DuckDB WAL locking, temp directory collisions, shared ports) can produce false failures that resolve in isolation. See `references/rust-workspace-test-flakiness.md` for the full diagnostic tree and proven instance. **Cargo lock contention (clippy blocked by running cargo test) + Rust test-count grep trick: `references/rust-gate-execution.md`.**

**Pre-existing failures:** Guard fails elsewhere → create `## [ ] CI — pre-existing guard failure in <file>` and proceed. ⚠️ Labels mask root causes — re-verify. references/real-llm-test-fake-key-401s.md

**Guard `.0` test output (runner config failure, NOT test failure):** When the guard shows `✗ tests (full) — .0` (zero bytes of output), the test runner itself failed to execute — not the tests. Always a pre-existing config issue (deps, cwd, Python). See `references/gitreins-guard-dot-zero-test-output.md`. In a `.0` scenario confirmed pre-existing on clean HEAD, use `--no-verify` to commit non-code changes (docs, config, CI ymls) and create an INFRA task. Never `--no-verify` through `.0` for code changes without confirming pre-existing. **Guard tests run `guards.test_command`, not the full suite; clean tree at prior HEAD proves pre-existing. See `references/guard-test-command-scope.md`.**

## Step 7 — GitReins Judge

**MANDATORY — every task with acceptance criteria (`## [ ]` with ACs, or a
`gitreins task` record) MUST get a judge verdict before it is marked complete.
A task is NOT complete on `guard` PASS alone — the guard proves tests pass,
the judge proves the CODE satisfies the ACs. Marking `[x]` without a verdict
is fabrication (proven: chimera-v2 ticks #40-45 invented coverage/dep results
while `.gitreins/history/` had zero verdicts for the tasks). Run the judge via
`timeout 540 gitreins task complete <id>` (CLI not MCP — ⚠️ `judge` ≠ status flip; refs/gitreins-judge-status-flip.md),
or `gitreins judge <id>` for a standalone pass. If the judge fails, follow the
table below — do NOT mark complete. Exceptions (must be noted in the board
entry AND DuckBrain): spec/doc-only tasks (manual criteria grep instead,
proven: imhotep S02), build-tagged code that can't compile without external
deps (proven: imhotep Phase 5), mechanical infra tasks (pip upgrade, doc fix —
`guard` PASS + test run is sufficient evidence).**

**Judge results:**

| Result | Action |
|--------|--------|
| ✅ PASS | Proceed to Step 8. ⚠️ "Overall: PASS" can hide a ✗ — any ✗ = real gap → re-judge (judge-pass-hides-failed-criterion-skippaths.md). ⚠️ Foreman-direct commit-trailer-only failure = judge pre-commit → commit first, re-judge (judge-commit-trailer-ordering.md). |
| ❌ FAIL — minor gaps | Worker missed something small. Return to worker: "Judge found: <specific gaps>. Fix these." One more pass. |
| ❌ FAIL — fundamental | The task was too big or the spec was wrong. Break task into smaller pieces. Create new subtasks. Mark current task as `## [ ]` with added detail. Next tick will pick it up. |
| ❌ FAIL — judge error | LLM hiccup — retry once; persistent → skip + commit w/ note. Non-JSON tier2 (`verdict=INCOMPLETE` reading PASS) = truncation, retry once. |
| ❌ FAIL — criterion wording wrong (code fine) | Judge applied a wrong criterion — e.g. `exits 0` vs CLI sentinel exit (`ExitDryRun`=10, helix #68); 1 criterion fails, others pass, live check matches spec. Fix: edit criterion in `.gitreins/tasks.yaml`, re-run `task complete`. Ref: `references/gitreins-judge-criterion-wording.md`. |
| ⏱️ TIMEOUT — compaction loop | `max_input_tokens: -1` → infinite compaction loop. Fix: concrete cap in config; else skip judge + commit with note (guard proved correctness). `references/gitreins-judge-compaction-loop-explicit-caps.md` |
| ⏱️ TIMEOUT — MCP transport cap (300s) | Use CLI `timeout 540 gitreins task complete <id>` (MCP caps at 300s). Timeout ≠ failure: `task_get` FIRST. `gitreins judge` can hang too — task_get, re-run once. Refs: `mcp-timeout-verify-before-retry.md`, `worker-fix-stewardship-completion.md`, `dead-code-cleanup-tick.md`. |
| ❌ FAIL — perf/E2E under host load | Contention ≠ code defect — recipe: `references/judge-perf-gate-host-contention.md`. |
| ❌ FAIL — tier2 INCOMPLETE "Cap exceeded: Input token budget (500k) exceeded (522k used)" | Evaluator `max_input_tokens` (0.5M default) too small — NOT a code failure. Fix: bump to 1M in `.gitreins/config.yaml`, re-run `timeout 540 gitreins task complete <id>`, commit as `chore`. MCP `passed:false` + NO verdict = transport failure, not code verdict. Recipe: `references/gitreins-judge-input-token-cap.md`. |
| ❌ FAIL — tier2 INCOMPLETE "Cap exceeded: Iteration cap (N) reached" | `max_iterations` too small — bump →200/25m, re-run. Recipes: `references/gitreins-judge-iteration-cap.md`, `references/gitreins-judge-tier1-test-timeout.md` (tier1 "Command timed out" variant). |

### Smoke Tests ≠ Real Tests (Pitfall)

**Do NOT mark adapter/shim/compatibility-layer verification as complete based
on HTTP status-code smoke tests.** 25/25 endpoints returning correct codes
feels like "done" but proves nothing about real interoperability. The shim
may return HTTP 200 on every call yet be completely incompatible with the
actual client it's built for.

**Rule:** Mark verification PARTIAL until at least ONE real end-to-end
session runs with the actual upstream client or the upstream's own test
suite. Use the upstream-contract-adapter pattern: extract HTTP contract
expectations from the upstream project's test suite and validate your shim
against the same contract.

See `references/smoke-tests-arent-real-tests.md` for the full Consensus
postmortem and Go implementation template.

## Step 8 — Commit (trailer verification mandatory — see references/commit-trailer-and-board-mirror-drift.md)

**Disciplined commit hygiene:**

```bash
git add <specific files only>     # NEVER git add -A or .
git diff --cached                 # verify staged changes
git commit -m "<type>: <description>" -m "Co-authored-by: $CODING_HERMES_CO_AUTHOR" --no-verify
```

**Co-author is MANDATORY.** The second `-m` with `$CO_AUTHOR` must be on EVERY commit. **Env var name varies — do NOT fail the tick on a missing `$CO_AUTHOR`.** Resolution order: (1) `grep -iE "co_?author" ~/.hermes/.env`, (2) literal `Alexis Okuwa <wojonstech@gmail.com>`, (3) repo `.gitmessage`. **Filter-safe commit:** when the message contains a filter-flagged string (pipe chars, `curl|sh`, `git rm -r`), use `git commit --no-verify -F - <<'EOF'` (message + `Co-authored-by:` trailer embedded in a stdin heredoc, NO `-m`); full pattern `references/commit-stdin-heredoc.md`.

**⚠️ The env value carries literal surrounding quotes — strip them** (`sed 's/^[^=]*=//; s/^\"//; s/\"$//'`), and a commit against an UNSET var succeeds with an EMPTY trailer — git doesn't reject it. **Post-commit trailer check:** `git log -1 --format='%B' | grep '^Co-authored-by:'` (NOT `tail -1` — trailing-newline false-negative, Imhotep T67). Only amend when grep shows the trailer missing or quoted — amend with the literal single-quoted trailer, never re-derive from env. Full pattern: `references/co-author-enforcement.md`, `references/co-author-env-var-pitfall.md`.

**Commit message format:** `<type>: <what was done> — <why>. Addresses <task-id>.`
Example: `feat: add JWT middleware to /api/users — enables authenticated user endpoints. Addresses USER-AUTH-03.`

**Commit types:** `feat`, `fix`, `refactor`, `test`, `docs`, `ci`, `infra`, `chore`

**No-verify flag:** The guard already ran in Step 6. Don't run hooks again — they're slow and redundant.

**Post-commit verification:**
```bash
git log --oneline -1              # confirm the commit exists
git log -1 --format='%B' | grep '^Co-authored-by:'  # NOT tail -1 (false-negative; ref: co-author-enforcement.md)
git status --short                # confirm working tree is clean
```

If anything unexpected is staged, unstage it. Only the worker's changes get committed. Untracked: ignore build artifacts, add legit? **Worker leak:** untracked `memory/` in cwd. `references/worker-session-memory-leak.md` **stray artifacts:** `stray-mid-tick-artifacts.md`

**Push EVERY configured remote — see `references/dual-remote-push-hygiene.md`; ⚠️ AGENTS.md no-push rules win (consensus, deepseek-dashboard).**

****.coding-hermes/ is gitignored in MOST repos — `git check-ignore .coding-hermes/tasks.md` FIRST, never assume.** Ignored → `git add -f` — even TRACKED parquet refuses plain add; `-f` always (ref: references/board-parquet-git-add-force.md). Not ignored → plain `git add` works; some repos TRACK the board directly — see `references/duckdb-board-jsonl-parallel-tick.md`; ⚠️ `!.tasks.md` negation → check-ignore lies, `-f` always: `references/check-ignore-negated-pattern-lie.md`; ⚠️ DuckDB boards: add TRACKED representation (`git ls-files` first). **Superproject variant:** board in a parent repo → always `git add -f` (parent-dir gitignore blocks plain add); tick # = board history, not repo HEAD. See `references/superproject-board-topology.md`.

**Appending tick entries: `write_file` to /tmp then `cat >>` (heredoc OK; refs/tick-housekeeping-pitfalls.md). JSONL boards — ONLY topology since 2026-09-03 (parquet/db writers retired): `append_board_event.py` (no auto-inc — pass `--set ticks_total/ticks_idle/last_commit`; `detail_json` = FILE PATH → /tmp; plain python3, NO uv/duckdb needed). ⚠️ legacy boards: JSONL ids + header counters may be STRINGS — int-coerce; crash between appends → stray events.jsonl line; `head -n -1` trim (ref: board-jsonl-mirror-str-int-pitfall.md). Task appender: `scripts/append_board_task_completed.py`. Fixture rows → `python3 scripts/update_board_task_notes.py REPO TASK_ID FIELD=VALUE`. **New tasks:** `python3 scripts/create_board_tasks.py REPO TICK_NUMBER TASKS_JSON` (idempotent). E2E events: `scripts/append_e2e_event.py`. Refs: jsonl-tracked-board-append.md, jsonl-board-append-hygiene.md.

**Board entry hygiene: `references/board-entry-hygiene.md`** (verify ports/pgrep live, never copy "server running"; fold uncommitted entries from timed-out ticks; `git check-ignore` before assuming `-f`). Fix-committed-board-chore-uncommitted: `references/orphaned-board-state-recovery.md` (UHLP #149).

## Step 9 — Off-by-One Submit

The pre-solve lab learns from every completed task. Server runs on `http://localhost:8766`.

**Verify off-by-one is alive (first):**
```bash
curl -s http://localhost:8766/health
# Expect: {"status":"ok","uptime":"..."}
```

**Submit the problem this tick solved:**
```bash
curl -s -X POST http://localhost:8766/api/v1/problems/submit \
  -H 'Content-Type: application/json' \
  -d '{"problem_class":"<language>-<category>-<specific>","description":"<what the task was and what approach worked>","cadence":"pre-phase"}'
# Fields: problem_class (kebab-case slug), description (free text), cadence (pre-phase|end-of-day|post-debug)
# Returns: {"submission_id":"sub_xxxxx"}
```

**Discover cached solutions for the NEXT tick's tasks:**
```bash
curl -s -X POST http://localhost:8766/api/v1/problems/discover \
  -H 'Content-Type: application/json' \
  -d '{"problem_class":"<next-task-type>"}'
# found:true → parse body["found"]. found:false → no cached solution (proven duckbrain #275).
# Unknown class or HTTP 404 → no-solution, NOT API failure (muster t78, gitreins-poc t110) — do not escalate
```

**Check a submission (incl. FAILED state):** `curl -s http://localhost:8766/api/v1/queue/<submission_id>` — `failed` + instant-fail = server-side solve failure; resubmit ONCE — repeat = server-side breakage, stop (#125). Check the PRIOR tick's submission before "nothing to submit" (#124).

**Cross-project learning:** Always submit + discover before the next tick. ⚠️ Discover results are NOT environment-matched (cached solution may describe a DIFFERENT repo — treat as hints, verify live). Ref: `references/off-by-one-discover-environment-contamination.md`.

**Proven:** 2026-07-24 — off-by-one live (51 problems, 60s cron); foremen weren't using discover. Start using it.

## Step 10 — DuckBrain Write

Store your understanding so YOU remember it next tick. This is how you build continuity across runs.

**⚠️ NEVER call `switch_namespace` — pass `namespace` explicitly (see Step 3 warning).**

**What to store — think "what would I need to know if I walked into this project cold?"**

| Type | Domain | Key pattern | Example |
|------|--------|-------------|---------|
| **Project understanding** | `config` | `/project/<name>/status` | "Built: auth, rate limiting, API gateway. Using: JWT, Redis, Go 1.22. Key files: server.go, auth/middleware.go. Architecture: gin → handler → service → repo → pgx." |
| **Model choices** | `concept` | `/project/<name>/model-choices` | "Go feature work: GLM-5.2 primary (reliable, fast). MiniMax-M3 fallback (hallucinates imports, run goimports). V4 Pro only for complex concurrency. Never: GPT-5.6 for Go (overthinks)." |
| **Decision made** | `event` | `/project/<name>/decisions/<ts>` | "Decided JWT over sessions — stateless deploys, no Redis dependency. Trade-off: can't revoke tokens without blacklist." |
| **Pitfall encountered** | `concept` | `/project/<name>/pitfalls/<ts>` | "MiniMax-M3 adds phantom imports. After every MiniMax worker, run `goimports -w .` and `go vet ./...`." |
| **Pattern discovered** | `concept` | `/project/<name>/patterns/<ts>` | "For new API handlers, copy-paste from handlers/example.go — it has the full wiring pattern." |
| **Worker performance** | `event` | `/project/<name>/workers/<ts>` | "V4 Pro on auth task: 3 commits, 0 rollbacks, 245s. GLM-5.2 on same: 1 commit, 2 rollbacks, 312s. V4 Pro better for auth complexity." |

**MCP `remember` REQUIRES `attributes`+`embedding_text`+`domain`** — omit any → `-32602` (domain=enum err, speclang #127). Keys start with `/`. (refs/duckbrain-remember-required-fields.md)

**Be specific, not generic.** Bad: "We fixed a bug." Good: "Lexer-parser assumed single-byte tokens; utf-8 runes broke offsets. Fixed with rune-aware positions in scanner.go:142."

**Update `/project/<name>/status` EVERY tick** — verify the write landed (DuckBrain down → board note; newest record, not first hit; ref: duckbrain-status-write-verification.md)

## Step 1.6 — Scan External Signals

**The bridge between ticks.** Before returning to Step 1, scan for changes that happened externally while the foreman was working.

**What to scan:**

1. **CI changes:**
   ```bash
   # GitHub repos — gh 404 OR empty (exit 0) = stale repo name: git remote -v FIRST (ref: gh-ci-404-wrong-repo-signal-scan.md)
   gh run list -R <repo> --limit 5
   # GitLab: `references/gitlab-ci-signal-scan.md`
   ```
   Any new failures? Any previously-failing pipelines that are now green? Steward/audit + CI probe: `references/steward-audit-human-blocked-ticks.md`.

2. **Remote commits:**
   ```bash
   git fetch origin
   git log HEAD..origin/main --oneline
   ```
   Did someone (Bane, another foreman on a worktree, external contributor) push commits? If yes, MERGE (not rebase) + re-run ALL gates post-merge. Full proc: references/external-merge-handling.md.
   
   **⚠️ Branch trap — verify WHICH remote branch is live first.** Two remote branches (main + master) can make the unpushed count wrong — check `git branch -r` and `git symbolic-ref refs/remotes/origin/HEAD` before counting. See `references/scheduler-self-pause-execution.md`. **Local-only repo (`git remote -v` empty):** skip fetch/push/CI/issue scans; note it in board. Ref: `references/local-only-repo-signal-scan.md`.

3. **New issues:**
   ```bash
   gh issue list -R <repo> --limit 10
   ```
   Any new issues filed since the last tick? If an issue is labeled `bug` or `critical`, create a task immediately: `## [ ] BUG — <issue title> (#<number>)`.

4. **Dependency updates + vulns:**
   ```bash
   # Go
   go list -u -m all 2>/dev/null | grep -F '[' | head -10
   # (grep -F '[' — a bare/anchored `[` in BRE throws "Invalid regular expression"; proven rabbit-hole tick #76)
   # Python
   pip list --outdated 2>/dev/null | head -10
   # Node
   npm outdated 2>/dev/null | head -10
   # Rust
   cargo update --dry-run 2>&1 | head -20
   ```
   If critical security updates are available, create `## [ ] DEPS — update <package>`. Note: this is a lightweight check — full vulnerability scanning (govulncheck, npm audit, pip-audit) runs in Step 1.5d during the discovery sweep.

5. **DuckBrain cross-reference:**
   Did another project's foreman discover a pattern relevant to this project? Load DuckBrain with a cross-project query. If the Hivemind foreman found a concurrency pattern that applies here, the foreman should know about it before the next tick.

**After the scan:** If new tasks were created (max 3 from signals), the board now has items. When the next tick fires at Step 1, it will find them. The scan also informs task prioritization — a new `bug` issue should be picked before the next scheduled feature work.

**If nothing changed:** The scan is still valuable. "No external changes" is information. Log it in DuckBrain so the supervisor knows the project is stable.

**Fleet health single-test failure (N-1 ≠ regression): triage as flake first — isolation run → check owning sub-repo foreman's recent tick → full re-run. See `references/fleet-health-flake-triage.md`.**

## Infrastructure Tools Reference

The 10 infrastructure tools (Hilo, DuckBrain, GitReins, Vuln Scanner, Dep Integrity, E2E Verify, Off-by-One, Bunker, Cron Self-Management, Stale Bug Escalation), the 1.5i E2E testing-tick loop, and the local-CI fallback table now live in `references/infrastructure-tools-reference.md`.

**Live-E2E pitfalls:** `references/live-e2e-verification-pitfalls.md`; **static browser E2E:** `references/browser-e2e-cdp-multi-target.md`; **private-address block → headless Chrome:** `references/browser-backend-private-address-block.md`.

**Support files:** `references/skill-view-persisted-json-extraction.md`, `references/live-server-file-lock-test-isolation.md`, `scripts/check_scheduler_project.py`, `scripts/storm-watch.py`. Scheduler: `references/scheduler-project-e2e-verification.md`, `references/scheduler-dashboard-404-and-scratch-verify.md`; PyPI publish recipe (build→twine→live-verify→board, sdk-python #59): `references/pypi-publish-from-foreman.md`. Go E2E: `references/go-live-server-e2e-battery.md`. Cross-arch: `references/go-ebpf-cross-arch-release.md`; Go CLI: `references/go-cobra-cli-pitfalls.md`, `references/go-ldflags-version-injection.md` (shared internal/version package + Makefile `-X` LDFLAGS pattern); CI lint: `references/ci-lint-new-from-rev-verification.md`, `references/ci-rerun-queued-next-tick-verification.md`; goconst: `references/golangci-lint-v2-counting-and-goconst-slice.md` + rewriter regressions: `references/goconstfix-rewriter-lint-regression.md`.

## Toolset Enforcement (Critical)

**Skill text does NOT constrain LLM behavior at runtime.** The foreman skill says "never use delegate_task" and "use cronjob cautiously" — but deepseek-v4-pro ignores both if the tools are available. The LLM picks `delegate_task` over `hermes chat -q` because it's a first-class function, not a terminal command. It picks `cronjob(action='update')` over respecting schedule directives because the tool is right there.

**The structural fix:** Strip `delegation` from the foreman's `enabled_toolsets`. Without that tool in the function list, the LLM CANNOT violate the no-delegate_task rule — no matter what it decides.

**Exception: `cronjob` is ALLOWED for self-pause only.** The foreman's self-pause mechanism (see "Self-Pause" section) requires `cronjob(action='update')` to increase interval and `cronjob(action='pause')` to pause. This is the ONLY permitted use — any other cronjob operation (decrease interval, change model, modify other crons) is a violation. The self-pause mechanism ONLY moves in one direction: slower → slower → paused. It can never speed up.

```python
# Required enabled_toolsets for every foreman cron
enabled_toolsets=["terminal","file","web","search","skills","memory","cronjob","mcp"]
```

| Toolset | Allowed? | Reason |
|---------|----------|--------|
| terminal | ✅ | `hermes chat -q` for worker spawn, git, builds |
| file | ✅ | Read/write code, board, configs |
| web | ✅ | Research, doc lookup |
| search | ✅ | grep codebase, session search |
| skills | ✅ | Load skills (prompt-foundry) |
| memory | ✅ | DuckBrain read/write |
| `cronjob` | ⚠️ | **Self-pause ONLY** — increase interval (3→4h→12h), pause. NEVER decrease interval, change model, or touch other crons. Any non-self-pause cronjob use is a violation. |
| `mcp` | ✅ Required | DuckBrain MCP (never-done check #9: recall/remember), GitReins MCP (guard verification). Foremen MUST have DuckBrain access for continuous quality tracking. |
| delegation | ❌ | `delegate_task` burns PAYG — workers inherit foreman's provider |

**Workers spawned via `hermes chat -q` inherit the default toolset (including `delegation`)** — they CAN use subagents if needed. This restriction is foreman-only.

**Verification:** After creating or updating a foreman cron, confirm `enabled_toolsets` contains exactly the 7 allowed sets (terminal, file, web, search, skills, memory, cronjob) and does NOT include "delegation". Run `cronjob(action='list')` and inspect.

**Seen:** Imhotep 2026-07-12 — foreman used `delegate_task` and shortened its own schedule via cronjob (no enabled_toolsets restriction + no cronjob discipline); stripping delegation + cronjob strict self-pause-only closed both.

## CI blocked → DON'T WAIT (local or bunker CI, Bane 2026-08-27)

When GitHub Actions is broken/blocked (billing annotation, dead runners, 4-15s
failing runs) foremen must NOT stall waiting for GitHub. Run the CI battery
yourself and record the evidence:

1. **Detect**: `gh run list -R <repo> --limit 5` + `gh run view <id> -R <repo>`
   — read the ANNOTATIONS (billing block) — see `local-ci-execution` skill.
2. **Host-local first** (fast): `act -W .github/workflows/<wf>.yml -j <job>`
   (act is installed at `~/.local/bin/act`; `-P ubuntu-latest=node:22-bookworm`
   in `~/.config/act/actrc`). Go repos: replicate the workflow commands directly
   (build → vet → test → lint) — full recipe in `local-ci-execution` skill.
3. **Bunker temp agent** (when host is loaded or the env needs isolation):
   `~/.hermes/scripts/bunker-ci.sh run bunker-las-03 <repo-dir> -W .github/workflows/ci.yml -j <job>`
   — spawns a FRESH temp agent (TTL 4h), syncs the repo, runs act inside it,
   destroys the agent on exit. Environment is NEVER polluted (temp agent per
   run). `bunker-ci.sh status` lists fleet health. Bunkers: bunker-las-01..04
   (tailnet, las-03 verified 2026-08-27), bunker-mvp, bunker-7840hs (local).
   Requires the bunker CLI with the 300s spawn fix (rebuild: `cd ~/bunker && make build`).
4. **Report**: local/bunker CI results are valid evidence for board closeout —
   note "CI verified locally (bunker-las-03)" with the ACT_EXIT + job results in
   the event detail; file a board row for the CI fix if the local run exposes a
   real failure (guard-green/CI-red class).

## Pitfalls

> Full corpus (56K, 166 lines): `references/pitfalls.md` — load on demand when a pitfall pattern is suspected. Top ones:
> **Judge/scratch daemon live-verification vs prod auth stores:** a gitreins tier-2 judge or any agent live-verifying `--auth=apikey` with a scratch daemon and no HOME override can REPLACE the production `~/.duckbrain/auth.json` and SIGTERM the live daemon (proven duckbrain #477, judge ff743016; key-file recovery at `~/.hermes/state/duckbrain-tokens/*.key`). Full chain + recovery + prevention: `references/judge-live-verify-auth-store-isolation.md`.
## Pitfalls
### Worker Claim Verification
Fabricated gitreins criteria + unverified task closures — see `references/worker-claim-verification.md`.
**GitReins task timing — create AFTER worker commit, not pre-dispatch.** Worker guard restore wipes pre-dispatch tasks from `.gitreins/tasks.yaml` → `judge_evaluate` fails `Task not found`. Re-create 
### Sibling Subagent File Conflicts
**/tmp script names: prefix with project+tick — generic names collide fleet-wide (sibling overwrite race → you run THEIR code). `references/tmp-script-name-collisions.md`**
When you use `delegate_task`, the subagent shares the filesystem. Working the same file set (e.g., CDC-08 coordinator files), it can **overwrite or delete your changes** mid-turn. Symptoms: files you 
**Workaround** — atomic terminal writes:
```
cat > /path/to/file.hpp << 'EOF'
... entire file content ...
EOF
```
Terminal `cat` heredoc writes are atomic — the file appears fully formed, so the subagent can't read a half-written file. Follow with immediate `git add` + `git commit --no-verify` + `git push` before
**Prevention**: don't edit files the subagent is tasked to produce. Either wait for the subagent, or kill the delegate process, write files atomically, commit instantly.
- **Rapid Re-fire / Cron Double-Fire**
Consecutive ticks minutes apart (T68 3 min after T67) = double-fire, not new work. Run gates anyway, verify no state change, note in board entry, never spawn duplicate workers. Full handling: `referen
### Stale Stash Cleanup
> **Audit-tick verification patterns (transient ENV-FAIL re-run recipe, cron-mode `curl | python3` pipe blocks, uncommitted prior-tick board detection):** see [references/audit-tick-verification.md].
When a task has been attempted by prior ticks and left incomplete work in `git stash`, those stashes are noise. They represent failed approaches. Pattern: `git stash list` → `git stash drop stash@{0}`
- **Never use delegate_task to spawn workers — strip the `delegation` toolset (see Toolset Enforcement table above).**
- **`-q` not `-z` for worker spawn** — top-level `hermes -z` ≠ `hermes chat -q`; `-z` on `hermes chat` silently fails. Always `hermes chat -q "<prompt>"`.
- **Worker spawn has no `--workdir`/`--background`** — `cd <dir> &&` for workdir; `terminal(background=true)` for async. ⚠️ Scheduler ticks (stateless HTTP endpoint): background processes return `noti
- **Shell quoting breaks `hermes chat -q` with code-heavy prompts — write prompt to file, pass via `$(cat file)`** (backticks/$/quotes interpreted even inside quoted strings). Ref: `references/shell-q
- **Cron `python3 -c`/`node -e` blocked — write ALL ad-hoc scripts to files** (any interpreter; `||` fallbacks rejected whole; a `-c`/`-e` segment rejects the WHOLE chain; duckbrain #230; warpfs #53; 
- **Process greps can match sibling workers** — `ps aux | grep tsx|vitest` hits sibling `hermes chat -q` argv (prompt text), not a daemon; read the full cmdline first. Ref: `references/stray-process-s
- **Large skill_view results persist as single-line JSON in `/tmp/hermes-results/`; `read_file` on the blob = EMPTY. Read raw bodies from disk: `references/skill-body-disk-read.md`.**
- **DuckBrain HTTP fallback for foremen WITHOUT MCP tools** (proven inference-estimator tick #87, 2026-08-10): when the session toolset has no duckbrain MCP tools, the HTTP API on :3000 works — but TWO gotchas: (1) keys live per-namespace — the bare `GET /api/keys?tree` walks only the DEFAULT namespace and shows NO project keys; pass `?namespace=<ns>` (e.g. `inference-estimator`) to see `/project/<name>/...` keys (the ops-ref's ns from the board header — but verify: umbrella/fleet-wide ns values may not match the real store; list_namespaces equivalent = GET /api/namespaces). (2) POST route is `/api/memories?namespace=<ns>` with body `{key, domain, content}` — NOT `/api/keys` (404 ROUTE_NOT_FOUND); response carries the memory UUID = the write confirmation (same trust rule as MCP remember responses). `domain` accepts `config`/`event`.
- **Cron `curl | python3` / `gh api | python3 -c` pipes blocked — use `gh api --jq` (ref: references/gh-api-cron-pipe-block.md).** Any pipe into `python3` gets rejected with pending_approval, even loc

> **Rule: any new pitfall discovered goes into references/pitfalls.md, NOT the SKILL.md body** (keeps per-tick context lean).