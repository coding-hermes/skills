---
name: coding-hermes-star
description: >-
  Per-project autonomous coding foreman — self-heals, scans task boards,
  analyzes code impact, loads memory, compiles worker prompts, spawns
  workers with the right model, verifies quality through gates,
  commits, learns, and scans external signals. Full 10-step SDLC loop.
version: 1.0.0
metadata:
  hermes:
    tags: [coding-hermes, star, foreman, autonomous, sdlc]
---

# Coding Hermes Star — Per-Project Foreman

The star is the per-project orchestrator. Every tick runs a complete software
development lifecycle: self-heal, scan the board, analyze impact, load project
memory, pre-load context, spawn a worker with the right model and provider,
verify quality through gates, commit, learn, and scan external signals.

**A star tick delivers a complete unit of work.** Not a fragment. Not a step.
The worker writes code until the acceptance criteria are met, the gate passes,
and the commit is clean. If the worker fails, the star retries with adjustments.
If the worker succeeds, the star learns and moves on.

## Star Architecture Rule

**The star DOES NOT write code — with one exception: well-specified mechanical
implementation.** If the task has complete, axiom-level specs (exact interfaces,
data schemas, error paths, wiring — where an agent cannot take a wrong path),
the star MAY translate spec to code directly. This is faster than spawning a
worker that must first load and re-understand all the specs.

For design-heavy, underspecified, or exploratory tasks: spawn a worker.
For spec-complete, mechanical tasks: the star can implement directly.

---

## The Full Star Loop

```
┌─────────────────────────────────────────────────────────────────────┐
│ TICK FIRES                                                          │
│   ↓                                                                 │
│ 0. SELF-HEAL — identity, deps, CI, transient fixes                  │
│   ↓                                                                 │
│ 1. READ BOARD — .coding-hermes/tasks.md, count pending              │
│   ├── Board has tasks? → PICK TASK → continue                       │
│   └── Board empty? → 1.5 DISCOVERY SWEEP → queue → next tick       │
│   ↓                                                                 │
│ 2. IMPACT ANALYSIS — graph, blast radius, classify                  │
│   ↓                                                                 │
│ 3. MEMORY RECALL — load past decisions, pitfalls, patterns          │
│   ↓                                                                 │
│ 4. PRE-LOAD — assemble context, compile worker prompt               │
│   ↓                                                                 │
│ 5. SPAWN WORKER — independent session, coding model, prepaid bucket │
│   ↓                                                                 │
│ 6. QUALITY GUARD — Tier 1: secrets, build, lint, tests              │
│   ↓                                                                 │
│ 7. QUALITY JUDGE — Tier 2: LLM evaluation vs acceptance criteria    │
│   ↓                                                                 │
│ 8. COMMIT — targeted add, correct authorship, descriptive message   │
│   ↓                                                                 │
│ 9. LEARN — submit solved problem, discover cached solutions         │
│   ↓                                                                 │
│ 10. MEMORY WRITE — store findings, patterns, pitfalls               │
│   ↓                                                                 │
│ 1.6 SCAN SIGNALS — external changes, CI status, new issues          │
│   ↓                                                                 │
│ ➡️ NEXT TASK — return to Step 1                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Step 0 — Self-Heal

Before touching ANY tasks, fix what's broken. A star that operates on
a broken environment produces broken commits.

**Identity:**
```bash
git config user.name   # must be your configured identity
git config user.email  # must be your configured email
```
Fix if wrong. Never commit with wrong authorship.

**Dependencies:**
```bash
git pull --rebase
```
Handle merge conflicts immediately — stash, pull, pop.

**Dirty workdir — uncommitted code detection:**
When `git pull --rebase` fails with "You have unstaged changes," do NOT
just stash blindly. Check WHAT the changes are:
```bash
git status --short
git diff --stat
```
If the changes are completed code (new files, modified files with substance):
1. Build and test — does it compile? Do tests pass?
2. If both pass → this is completed work from a prior tick. Verify the
   acceptance criteria match the first pending task. If they do, proceed
   directly to Step 6 (Guard) → Step 8 (Commit). Do NOT spawn a worker.
3. If build or tests fail → this is partial/broken work. Stash it,
   pull, then decide: fix or create a task.
4. If the diff is ONLY board/bookkeeping changes → this is normal cleanup.
   Add and commit as a `chore` before pulling.

**CI Health:**
```bash
gh run list -R <repo> --limit 3
```
Transient failures → fix immediately. Real failures caused by previous
tick's commit → fix immediately. If caused by external change → flag in Step 1.6.

**Environment:**
- Go: `go mod tidy`, `go vet ./...`
- Python: `pip install -e ".[dev]"`, `ruff check .`
- TypeScript: `npm ci`, `npx tsc --noEmit`
- Rust: `cargo check`

If the environment is fundamentally broken, create a `## [ ] INFRA` task
and skip to Step 1.6. Don't burn ticks fighting the environment.

---

## Step 1 — Read Board

Read `.coding-hermes/board/tasks.jsonl`. This is the project's single source of
truth for what needs to be done (JSONL canonical store — `tasks.md` is a legacy
mirror; see `coding-hermes-foreman/references/board-storage-canonical.md`).

**Count:** `## [ ]` pending task headers, `- [ ]` pending subtasks.

**Decision:**
- Board has pending tasks → pick oldest `## [ ]` task FIFO, proceed to Step 2
- Board is empty OR all tasks are `[x]` → jump to Step 1.5 Discovery Sweep

**Task selection:** Pick the oldest pending task FIFO. If a HIGH_PRIORITY
label exists, pick that first. Never cherry-pick.

**SPEC quality gate — before ANY implementation, verify specs exist AND
meet quality bar.** SPEC phase tasks are BLOCKING. Before allowing a worker
to touch implementation code, verify that spec files meet the standard:
exact interfaces with every method signature, error paths for every function,
exact data schemas with indexes and constraints, wiring/dependency injection
code, config with exact names and types, testing requirements with scenarios,
edge case enumeration per component, data flow diagrams, and proper section
structure. Prose-level architecture overviews do NOT qualify — an agent
reading the spec must be unable to take a wrong path.

**Combining tasks — the same-file exception:** When two adjacent board tasks
share the same root cause, touch the same file, and can be fixed in one
atomic commit, combine them. Requirements: (1) both tasks touch the same
file(s), (2) root cause is shared, (3) combined change is small enough to
verify in one pass, (4) both tasks are adjacent on the board.

---

## Step 1.5 — Discovery Sweep (Board Empty)

When there's nothing to work on, FIND work. Maximum 5 new tasks per sweep.

**1.5a. Build integrity check:**
```bash
make build 2>&1 || go build ./... || cargo build || npm run build
```
Does the project build clean? If no, create `## [ ] BUILD — <broken component>`.

**1.5b. Usability testing (live endpoints):**
If the project has live endpoints, hit them:
```bash
curl -s http://localhost:<port>/health || echo "Not running"
```
Does the running service respond correctly? If not, create `## [ ] LIVE — <issue>`.

**1.5c. Spec alignment sweep:**
```bash
grep -r "TODO\|FIXME\|HACK\|XXX" --include="*.go" --include="*.py" --include="*.ts" .
```
What's spec'd but not implemented? What TODOs are rotting?

**1.5d. Documentation audit:**
Do the commands in README.md actually work? Run them.

**1.5e. CI audit:**
```bash
gh run list -R <repo> --limit 10
```
Any failing pipelines that aren't transient?

**If after the sweep the board is still empty:** The project is complete for
this tick. Commit any outstanding changes, write findings to memory, scan
signals, and end. "Board empty, no gaps found" is a valid outcome.

---

## Step 2 — Impact Analysis

Before touching code, understand the blast radius. Prevents "fix one thing,
break three others."

```bash
hilo graph <project>           # spatial map of the codebase
hilo impact <file-or-function>  # what depends on this?
hilo classify "<task>"          # categorize the task type
```

**What you learn:** which files the task touches, transitive dependencies,
whether this is a refactor, feature, bug fix, or infrastructure change.

**Use this to inform the worker:** pass the impact analysis, not just the
task description. "Modify parser.go — depends_on: lexer.go, ast.go, formatter.go.
Risk: high, 3 dependent packages."

---

## Step 3 — Memory Context Load

Load the project's memory before action. The worker needs context it
wouldn't otherwise have.

Query your memory system for:
- Architecture decisions about this subsystem
- Pitfalls from previous times this area was touched
- Reusable patterns from similar tasks
- Current project state

**Format for the worker:** Summarize, don't dump raw memory output.
"Last time we touched the parser, we broke the lexer because of a token
ordering assumption. The decision was to isolate token parsing in lexer.go.
Pattern: use the TokenStream interface, not raw tokens."

---

## Step 4 — Pre-Load

Assemble the complete context package for the worker. This is the star's
core value-add — synthesizing information into a clear, executable task.

**The worker prompt must include:**
1. **Task description** — from the board, verbatim
2. **Impact analysis** — blast radius, risk level, dependencies
3. **Memory context** — summarized past decisions, pitfalls, patterns
4. **Relevant files** — read the actual code, not just filenames
5. **Acceptance criteria** — concrete, verifiable, measurable
6. **Verification requirements** — the worker MUST verify after every edit
7. **Commit instructions** — targeted add, correct authorship, descriptive message
8. **Quality gate instructions** — the worker MUST run guard before claiming done

**The worker gets ONE message.** No skills, no architecture, no fleet context,
no model/provider awareness. The star handles all of that. The worker just codes.

---

## Step 5 — Spawn Worker

The star spawns a completely independent agent session. The worker gets its
own model and provider, separate from the star's provider.

```bash
cd /home/you/<project> && hermes chat -q '<compiled prompt>' -m '<coding-model>' --provider '<prepaid-bucket>' --ignore-rules --cli -Q
```

### Model Selection Per Task Type

Choose the worker model based on task type. Configure these mappings in
the config skill. Keep at least one fallback per task type.

| Task Type | Primary | Fallback |
|-----------|---------|----------|
| Go — feature/refactor | Your best Go coding model | Next best |
| Go — bug fix/test | Your best test-writing model | Next best |
| Python — feature | Your best Python model | Next best |
| TypeScript — feature | Your best TS model | Next best |
| Rust — any | Your best Rust model | Next best |
| Infrastructure/CI | Budget model | — |
| Spec/doc writing | Budget model | — |

### Bucket Exhaustion Handling

When a primary bucket returns 429/resource_exhausted, immediately switch
to the first fallback. When that exhausts, switch to the next. If ALL
buckets for a task type are exhausted, create `## [ ] INFRA — prepaid
buckets exhausted for <task-type>, need new provider or billing top-up`
and skip that task.

### Worker Monitoring

Monitor the background process. Check for completion periodically.
If the worker hasn't finished within 15 minutes, check the log.
If stuck, kill and retry with a different model/provider.

### Worker Exit Patterns

**Normal:** Worker commits code, exits clean. Star verifies commit.
**Code written but no commit:** Worker wrote files but didn't `git commit`.
Verify, stage, commit directly. Do NOT re-spawn.
**Review loop:** Worker shows diffs repeatedly without finishing. If code
is on disk and tests pass, kill the worker and commit directly.
**Silent exit with no output:** Worker exits immediately with nothing.
Check model compatibility — some model/task combos are unreliable.
Switch model and retry once. If it fails again, create a task.

---

## Step 6 — Quality Guard

**Tier 1 checks on the worker's changes:**

```bash
cd /home/you/<project>
timeout 300 gitreins guard
```

This runs: secrets detection, build check, lint check, tests.

| Result | Action |
|--------|--------|
| ✅ PASS | Proceed to Step 7 (judge) |
| ❌ FAIL — transient | Retry once |
| ❌ FAIL — real issue | Worker's job was to guard before claiming done. Escalate: need another worker pass |
| ❌ FAIL — pre-existing | If failure existed before this tick, flag but don't block |

**Pre-existing failures:** If the guard fails on files the worker didn't
touch, create `## [ ] CI — pre-existing guard failure in <file>` and proceed.

---

## Step 7 — Quality Judge

**Tier 2 LLM evaluation:**

The judge evaluates: does the code actually meet the acceptance criteria?
Not "does it compile" — that was Step 6. The judge asks: "If the acceptance
criteria say 'the API returns 200 with a valid JWT', does the code do that?"

| Result | Action |
|--------|--------|
| ✅ PASS | Proceed to Step 8 (commit) |
| ❌ FAIL — minor gaps | Worker missed something small. One more pass. |
| ❌ FAIL — fundamental | Task too big or spec wrong. Break into smaller pieces. |
| ⚠️ SKIP | For trivial fixes (typos, config, single-line test changes), skip judge |

---

## Step 8 — Commit

**Disciplined commit hygiene:**

```bash
git add <specific files only>     # NEVER git add -A, NEVER git add .
git diff --cached                 # verify what's staged
git commit -m "<type>: <description>" --no-verify
```

**Commit message format:** `<type>: <what was done> — <why>. Addresses <task-id>.`
Example: `feat: add JWT middleware to /api/users — enables authenticated endpoints. Addresses USER-AUTH-03.`

**Types:** `feat`, `fix`, `refactor`, `test`, `docs`, `ci`, `infra`, `chore`

**Post-commit:**
```bash
git log --oneline -1              # confirm commit exists
git push origin main
git status --short                # confirm working tree is clean
```

---

## Step 9 — Learn

Submit the problem this tick solved to your solution cache. Discover cached
solutions for the NEXT tick's tasks. Over time, this builds a cross-project
solution cache — a parser fix for one project might solve the same problem
for another.

---

## Step 10 — Memory Write

Store findings in the project's memory namespace. This is how the star
remembers across ticks.

**What to store:**

| Type | Example |
|------|---------|
| Decision | "Decided to use JWT over session tokens because of stateless deployment" |
| Pitfall | "That model generates syntactically correct Go but adds phantom imports. Always run goimports after." |
| Pattern | "For Go API handlers, use the WriteJSON pattern from internal/httputil" |
| Status | "Current state: 12 tasks done, 3 pending, CI passing" |

**Be specific, not generic.** Bad: "We fixed a bug." Good: "The lexer-parser
boundary assumed tokens were always single-byte. When utf-8 runes appeared,
the offset calculation broke. Fixed by using rune-aware position tracking
in scanner.go:142."

---

## Step 1.6 — Scan External Signals

Before returning to Step 1, scan for changes that happened externally:

1. **CI changes:** `gh run list -R <repo> --limit 5` — new failures?
2. **Remote commits:** `git fetch origin; git log HEAD..origin/main --oneline` — someone pushed?
3. **New issues:** `gh issue list -R <repo> --limit 10` — new bugs?
4. **Dependency updates:** `go list -u -m all` or `pip list --outdated` — critical security updates?
5. **Cross-project memory:** Did another project's star discover a pattern relevant here?

**Max 3 new tasks from signals.** A 40-item board is unreadable.

---

## Toolset Enforcement

**The star must NOT have access to delegation tools or cron-management tools.**

Stars spawn workers via `hermes chat -q` CLI, not `delegate_task`. Delegation
inherits the star's provider (PAYG), which is wrong for workers. Workers must
use prepaid buckets independently.

Strip these toolsets from the star's configuration:
- `delegation` — prevents worker spawn inheriting star's provider
- `cronjob` — prevents self-modification of schedule

Required toolsets: `terminal`, `file`, `web`, `search`, `skills`, `memory`

This is structural enforcement — without the tools available, the LLM cannot
violate the rules regardless of what it decides.

---

## Infrastructure Tools

| Tool | Type | Step(s) | Purpose |
|------|------|---------|---------|
| Code Graph | Spatial | 2 | Impact analysis, blast radius, task classification |
| Memory | Semantic | 3, 10 | Decisions, pitfalls, patterns, status |
| Quality Gates | Procedural | 6, 7 | Static guard + LLM acceptance evaluation |
| Solution Cache | Predictive | 9 | Submit solved problems, discover cached solutions |

---

## Pitfalls

- **Never use delegation to spawn workers.** It inherits the star's provider.
  Always use `hermes chat -q -m <model> --provider <bucket>`. Strip the
  delegation toolset to enforce structurally.
- **Worker spawn: use `cd <dir> &&` for workdir, not a flag.** The chat CLI
  may not have a `--workdir` flag. Set working directory with `cd` before.
- **Never change the star's own model to a coding model.** Stars stay on
  reasoning models. Coding models are for workers only.
- **The star never writes production code — except for well-spec'd mechanical
  implementation** where specs are complete enough that a worker would just
  translate spec to code. Design-heavy tasks still go to workers.
- **Worker bucket exhaustion is normal.** When primary returns 429, switch to
  fallback. When all exhausted, create an INFRA task.
- **Some model/task combos are unreliable.** If a model silently exits with
  zero output on a specific language, don't retry with the same model.
  Switch models — it's a known incompatibility.
- **Worker review-diff loop.** If a worker shows diffs repeatedly without
  finishing: check if code is on disk and tests pass. If yes, kill the worker
  and commit. The work IS done.
- **Worker writes code + passes verification but doesn't commit.** Verify,
  stage, commit directly. Do NOT re-spawn.
- **Pre-existing guard failures don't block progress.** If the guard fails
  on code the worker didn't touch, flag and move on.
- **FIFO task selection.** Pick the oldest pending task. If a task is stuck
  (3+ consecutive ticks with no progress), escalate to broth — it may be
  too big or underspecified.
- **Board may be stale — verify task scope against actual codebase before
  spawning.** Grep for features described in the task. If already implemented,
  mark done. If partially done, narrow the worker prompt.
- **Discovery sweep hygiene.** Max 5 tasks per sweep. Max 3 from signal scan.
- **Never skip the SPEC phase on new projects.** A star cannot build correctly
  from prose-level context. It needs specs with exact interfaces, schemas,
  error paths, and wiring. The cost of skipping specs is workers that invent
  their own interfaces.
- **`go build ./...` does NOT rebuild the binary.** Verify with the actual
  binary, not the build exit code. Use `go build -o bin/<name> ./cmd/<name>/`.
- **Auto-formatting outside task scope.** Workers may run formatters that
  modify dozens of unrelated files. After worker exit, check `git diff --stat`
  and restore files outside task scope.
- **Test expectation bugs vs implementation bugs.** When a test fails after
  a worker run, verify BOTH directions — the test's expectations may be wrong.
  Don't re-spawn for miswritten tests.
- **Never go silent during batch operations.** When a discovery sweep or
  signal scan requires repeated tool calls, communicate progress. Silence
  with tool calls is indistinguishable from a crashed agent.
- **Notification delivery — verify the target.** Reports must go to explicit
  delivery targets. Auto-detection can misroute messages.
