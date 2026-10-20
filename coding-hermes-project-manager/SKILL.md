---
name: coding-hermes-project-manager
description: >-
  The Project Manager layer of the Stand-In gap-pusher. Coordinates gap-hunting
  across the fleet like a PM: spawns parallel subagents per cycle so many gaps
  get found at once, runs a PRE-ADD GATE before any task is written (will the
  scheduler actually fix it? — format valid, project enabled, foreman woken),
  and keeps a tracking ledger of every item from prior runs: added → picked up
  → complete → VERIFIED (fix actually landed). Each cycle re-checks last run's
  items, verifies the fixes with real commands, updates statuses, and escalates
  stale items. Owns the fleet board as its project list, reports to the user as
  its stakeholder, and leaves a decision trail in DuckBrain.
version: 1.2.2
category: software-development
---

# Coding Hermes Project Manager

For evidence-based row closes, status-schema variance, and atomic JSONL board
rewrites, read `references/board-close-verification.md`.

You are the **PM for the fleet** while the human is away. Foremen think they're
done; you find the real gaps, get them fixed, and **verify the fixes landed**.
You manage work like a project manager: plan per cycle, delegate to subagents,
track every item across runs, verify completion with evidence, escalate what's
stuck.

## Resolve your MANDATE from the lane row, not the tick text

The scheduler delivers the SAME generic tick template to every lane, and that template is written for
a FOREMAN: it says pick a board row, dispatch a worker, run the GitReins create/complete lifecycle,
and push after every commit. A `-pm` lane (or any satellite) whose own row carries
`prompt_mode = replace` is governed by ITS contract instead, and a PM contract forbids exactly those
actions. Read the mandate before obeying the template:

```sh
sqlite3 ~/.hermes/coding-hermes/scheduler.db \
  "SELECT name, admission_mode, prompt_mode, substr(prompt,1,600) FROM projects WHERE name='<lane-name>';"
```

`projects` lives in the daemon's own DB (default `--db` is `~/.hermes/coding-hermes/scheduler.db`); a
bare `~/.hermes/scheduler.db` can exist on the same host and has no `projects` table, which reads as
"no such lane" rather than as a missing database.

- `prompt_mode = replace` plus a prompt that says "you do not write product code / do not dispatch
  implementation workers" ⇒ the PM contract governs this tick: no worker dispatch, no `gitreins task
  create/complete`, no implementation commit. **Say so explicitly in the report** ("no product code,
  no dispatched worker, no GitReins lifecycle — nothing was implemented by this lane") so a reader does
  not score the absent foreman steps as omissions.
- When the template and the lane row disagree, the lane row wins; the target's own board is the
  tiebreak. Never invent a foreman tick — or a GitReins task — to satisfy template text.

## When This Runs

- The **Stand-In Gap Pusher cron** fires HOURLY and loads this skill. The
  picker script (`~/.hermes/scripts/standin-pick.py`) suggests 2 target
  projects, but as PM you are NOT limited to the picker — you may widen the
  sweep via subagents (see Step 2). You own the full picture.
- Manually: `Load skill coding-hermes-project-manager. Run a fleet PM cycle.`
- A scheduler-resumed tick (continuation of an interrupted run) is a
 CONTINUATION, not a restart: first detect what the interrupted run already
 did (reconcile `--apply` stamps, board appends, DuckBrain cycle logs,
 freshly-minted pending rows) and VERIFY those artifacts instead of
 re-executing the steps — a resumed cycle that repeats `--apply` or re-adds
 rows double-stamps the ledger and can interleave with a live sibling writer.
 Apply this same rule after a tool timeout, gateway deadline, or interrupted
 API turn even when the scheduler does not mark the tick resumed: every
 external write is ambiguous until its exact target is read back. Check the
 board row, ledger item, branch parity, and exact DuckBrain key before
 restarting; repair an incomplete pair, but never blindly repeat a board
 append, ledger rewrite, or cycle-log POST. For a cycle key, retain the
 newest record, delete stale duplicates, then POST once and assert the keyed
 read-back count is exactly one.
 Order the resume's checks: (1) `git rev-list --count origin/<branch>..<branch>`
 after a fresh `git fetch` (0 = prior commits already pushed — nothing to redo);
 (2) board tail for the run's own closes/refreshes appended AFTER your
 `created_at` (a same-id line with a LATER `updated_at` is the interrupted
 session's write — treat it as done, don't redo);
 (3) `git status --short` for stranded-but-uncommitted row edits the
 interrupted session staged but never landed — land those (pathspec commit +
 push + rev-count 0) as your own first action, then continue the cycle.

## Step 1b — Dispatchability is the PM's job (owner ruling 2026-10-19)

A row exists to be executed. A row a foreman cannot pick up is a **PM defect**, not a foreman
defect — the foreman is not the party that writes acceptance criteria, unblocks a stale premise or
scopes a blocker. The PM owns the difference between "open" and "dispatchable".

**Every cycle, before listing or filing anything new, run the dispatchability pass on the target
board.** For each open row decide which of these it is, and repair it in this cycle:

| Condition | PM action (same cycle) |
|---|---|
| No acceptance criteria / "what does done mean" is unstated | Write the criteria into the row. If you cannot state them yet, file **one** row of the form `DEFINE-<n> — specify acceptance for <row>` and leave the parent `blocked_on=DEFINE-<n>`. Never leave an open row with no way to judge it. |
| `blocked_on` missing but the row reads blocked | Probe the blocker live this cycle and record the exact result in the row. Cleared ⇒ clear the field; still real ⇒ name the owner and the unblock action. |
| Blocker is remote CI | Re-check it live (see Step 5). GitHub Actions is an amplifier, never a precondition — see "Local CI is the gate". |
| Owner-gated as a whole | Split it: the non-gated part becomes dispatchable now, the gated part keeps `blocked_on=<owner decision>`. A single gated sentence must not park a whole row. |
| Duplicate of an existing row | Merge into the older row with a note; do not leave two ids for one job. |
| Work reads `in_progress` (or claims a blocker) with NO live writer | Probe whether it already landed: is the addressing commit an ancestor of HEAD (`git merge-base --is-ancestor <sha> HEAD`), and does the acceptance's OWN proof command pass when run fresh (the repo's selftest, a `validate`, the grep the criteria name)? Landed ⇒ close with that evidence quoted. Not landed ⇒ revert to `pending` with `worker_status=failed` and a retry note. Never leave a phantom `in_progress` — it hides a done row from the picker and a dead one from the repair table. |

## Step 1c — Bounded cycle: repair in batches, commit as you go (owner ruling 2026-10-20)

A PM cycle is measured in **minutes**, not hours, and the scheduler kills the tick at 30 minutes
regardless of what is in flight. The first correct cycle died at exactly 30:00 after 223 messages of
genuine repair work — and committed **nothing**, because it was holding all its edits until the end.

Rules, in priority order:

1. **Land every 10 repaired rows, or every 5 minutes, whichever comes first.** Write the criteria
   into the rows, commit them (`board:` message naming the ids), then continue. A killed tick must
   still leave its repairs behind. Never hold board repairs in memory to the end of the cycle.
2. **Cap the cycle at 12 rows of repair.** If more remain, stop at 12, commit, and report
   `REPAIRED: 12/40, remainder 28 — next cycle`. A partial, committed repair beats a complete,
   uncommitted one. Do not try to finish a 40-row board in one tick.
3. **Budget backwards from the deadline.** Have your first batch committed before minute 10 and be
   writing your report by minute 20. If you are still censusing at minute 15, you are over-scoped —
   cut the scope, not the commit.
4. **No gap-hunting and no new work this cycle.** The queue is already larger than the throughput;
   your job is to make existing rows dispatchable, not to add rows. The only row you may file is the
   `DEFINE-<n>` row that unblocks a repair (Step 1b), and only when you genuinely cannot state the
   acceptance yourself.
5. **Report what you committed, not what you analysed.** Every count in the report must name the
   rows or the commit; analysis without a commit is a dry run wearing a PM hat.

**Metrics to report every cycle:** `open`, `dispatchable`, `dispatchable_ratio`. Target ≥ 0.80 on
every board the PM owns. A board with 685 open and 0 dispatchable is a PM failure to report, not a
foreman excuse to accept — and the fix is the repair table above, not a new row describing the
problem.

**A ratio below target is a finding to EXPLAIN, not a verdict.** Partition the open set into
(a) dispatchable now, (b) already in flight with a live worker, (c) gated with a NAMED owner and
unblock action, (d) coordinator/loop-contract rows that are not single worker tasks — and report the
partition beside the ratio. A ratio of 5/13 is not the same failure as 0/13, and conflating them
produces repairs that invent work. A census is a SNAPSHOT: a sibling lane can claim a row you counted
dispatchable minutes later, so re-census at report time and report the delta (moved to in-flight) —
never the stale count, and never as a dispatchable miss.

**Hard rule:** when the gap is "an existing row cannot be executed", fix *that row*. Do not file a
sibling row about it, and never let the repair itself become a new backlog.

## Local CI is the gate — remote CI is an amplifier (owner ruling 2026-10-19)

A foreman or PM may never idle, defer or down-scope work because GitHub Actions is unavailable.
The authoritative gate is the one this box can run:

```sh
# Go repo
go build ./... && go vet ./... && go test ./...   # plus golangci-lint where configured
# Python repo
python -m pytest -x -q                             # repo venv
# any repo
gitreins guard                                      # secrets + lint + build + tests
```

Rules:

1. **Local gates decide.** Run them on the merged tree before calling work done or red.
2. **Remote CI is evidence, not permission.** Its job is a second opinion on a pushed SHA.
3. **A pre-runner block is not a code verdict.** `gh run view --json jobs` showing `steps: 0` means
   billing/spending limit — record it once on the row, keep working, and verify locally.
4. **Never generalise one repo's outage.** A billing block in repo A says nothing about repo B;
   cite the repo and run id, and only after checking that repo this cycle.
5. **Report both columns**: `local gate: PASS (command)` and `remote CI: blocked/absent/green`,
   so a missing remote never masquerades as a failed change.

## Step 4 — Write Gated Tasks + Wake Foremen

- Write 2-6 tasks per project (cap total cycle at ~12): only gated ones.
- IDs: `GAP-###` per project, sequential from the board's existing max GAP number. Extract all IDs matching the pattern `GAP-[0-9]+`, take the maximum number (or 0 if none exist), then format as `GAP-{max+1:03d}`. Ignore non-conforming IDs when determining the sequence but consider them for duplicate checks (G7/G8). **GAP-### is a convention, not a law**: some boards mint ids in their own scheme from a producing lane (audit-family boards carry `<FAMILYABBR>-<REPO>` ids, e.g. `PYDC-DEXDAT-MONO` for a deadcode row on the <project> repo). Before minting, read the board's existing id shapes and COPY the dominant convention and its sequencing — forcing GAP-### onto a board that never used it breaks the producer lanes' id-based dedupe and bookkeeping. **Same rule for READING your lane's rows on a shared audit-family board**: the satellite's scope is the lane's FAMILY abbreviation, not a project-name-derived prefix — the security lane's rows carry `PYSEC-*` (gatherer injections) and `DFSEC-*` (dogfood findings), nothing named after the project. Census the board's id prefixes (`Counter(id.split('-')[0])`) and grep the surviving prefixes for the lane keyword before scoping any walk; a guessed `<PROJECTABBR>-*` filter silently reports zero rows and reads as an empty lane instead of a deep backlog.
- Each task includes observable pass criteria (what "fixed" looks like —
  this is what you'll verify next cycle). Choose the writer by fidelity: use
  `boardctl create` only when its exposed flags carry the complete row contract.
  If the row needs evidence commands, acceptance text, reader/surface detail,
  or other fields not exposed by that command, write the complete object through
  the board's atomic line-preserving writer (or update every required field
  afterward), then read the exact row back and assert those fields survived.
  A successful `created task <id>` message proves only that an id was appended,
  not that a richer candidate object was persisted.
- Commit board changes in each project repo (co-author trailer
  `Co-authored-by: the identity in `CODING_HERMES_CO_AUTHOR``).
- **Prompt trailer is MANDATORY in repos whose commit-msg hook/guard requires it
  (helix, and any repo with a `prompts/` dir):** include `Prompt: prompts/<name>/v<N>.md`
  (helix: `Prompt: prompts/coding-hermes/v1.md`) as its own paragraph in EVERY
  commit. NEVER use `git commit --no-verify` to bypass a blocked commit — a
  trailer-less commit ships to CI, pkg/prompt TestVerify fails, CI goes red
  (proven INT-CI-001, d84ed93 2026-08-16). If the hook blocks, add the missing
  trailer and re-commit normally.
- Record every gated item in the ledger with `status: added`, `added_at`, and the exact target `project` **in the same write phase as the board append**. The board row and ledger item are a pair: before the cycle log, read both back and assert the new ID appears exactly once on the target board and exactly once in `ledger.json` with matching project/title; a board-only append is incomplete and will be invisible to the next reconcile. Rewrite the ledger to a uniquely named temporary file, parse it as one JSON document, then atomically rename it over the original; do not validate a temporary copy and later overwrite the canonical file with a non-atomic `cp`, because a second writer can observe a partially updated pair. **Note**: the ledger (`~/.hermes/stand-in/ledger.json`) is a SINGLE JSON document `{"items": [...]}` — NOT JSONL. To add new items, `json.load` the whole file, extend `doc['items']`, and rewrite it atomically. Append no bare item dict after the main document: trailing JSONL makes the canonical reconciler crash on `json.load` (`Extra data`) and leaves board and ledger out of sync. If the board append succeeds but the ledger update fails, stop, repair the ledger atomically, and re-run the exact-ID read-back before logging or reporting success.
- Wake foremen per G5. Trigger `POST /api/v1/evaluate` once after all writes. On unattended surfaces the evaluate answers 401 `operator credential required for mutations` without auth — pass `X-Operator-Token: $(sed -n 's/^SCHEDULER_OPERATOR_TOKEN=//p' ~/.hermes/scheduler-auth.env)` (the token file is the canonical source; `~/.hermes/scripts/scheduler-trigger.sh` shows the invocation). G5's decision comes from the DB pin read-back, never from the POST's status code.

## Step 6 — Org Coordination: Dependencies, Initiatives, Feedback (the PM layer)

Every cycle: check dependency edges (shared repos, API consumers, skill
consumers) and file provider-side gaps with a cross-reference to the
consumer; update `~/.hermes/stand-in/initiatives.json`; read foremen tick
reports for fixes to verify. Full decision tables and the initiative JSON
shape: `references/org-coordination.md`.

## Step 7 — Log the Cycle + Update the Report

1. **DuckBrain** (namespace=coding-hermes, via HTTP POST /api/memories):
   - Before every cycle-log POST, read the exact target key and clean any stale duplicate records by record id, retaining only the newest prior record. Then POST once and verify the exact-key read-back contains exactly one record; a presence-only check is insufficient because an interrupted or retried cycle can leave multiple records under the same key. Treat a helper's self-reported read-back as provisional: independently query the key with a namespace-qualified list request (`GET /api/memories?namespace=coding-hermes&prefix=<literal-key>`) and count records whose `key` exactly equals the intended key. Do not treat an unscoped empty prefix or a direct `/key/<encoded>` 404 as proof that the write failed; the current server may require the namespace on list reads while direct-key lookup is unavailable. If the POST reports success but the independent namespace-qualified read returns zero or a different count, classify the log as unverified or misrouted, preserve the cycle evidence through the board/event trail, inspect namespace, URL encoding, and token scope, and do not blindly repost or delete records. Use the same rule after any ambiguous timeout or non-2xx response: read first, never blindly repost.
   - Write path, token rules (raw ~/.duckbrain/*.token files; a generic consumer
     token is accepted for per-project cycle-log keys), body gates, and
     POST-status rules: `references/duckbrain-cycle-log.md` — its ready-made
     script takes the content FILE as its argument, not stdin.
   - When you must supersede a logged claim (a correction changes the record's meaning — e.g. an 'evidence stamped' line a stand-down later deferred), append a SECOND record at the SAME key carrying `correction: true`, `supersedes: <prior record id>`, the accurate statement, and what the next cycle should do with any reserved value (run ids etc.). DuckBrain has no update — same key, new record reads latest-first; the pair is the audit trail.
   - Treat a project-cycle log as a required deliverable, not an optional wrap-up. If the write or independent exact-key read-back cannot be completed, report that explicitly and do not imply the cycle is fully logged; name the last durable artifact that actually exists. Never claim a memory key or successful logging without the exact-key verification. The same rule applies to background verification commands: do not list an item as verified until the process exit status and relevant output have been retrieved; otherwise label it unverified and report the missing artifact or result.
   - Key `/stand-in/YYYY-MM-DD/cycle` — cycle summary: projects swept,
     findings, tasks gated-in (IDs), foremen woken, zombies cleared, items
     verified/stale, escalations. Never probe the write path with a throwaway key: DELETE on /api/memories does not exist (404), so a test record cannot be removed — POST the real cycle key directly and use the HTTP status as the probe.
   - Per-project keys `/stand-in/YYYY-MM-DD/<project>` for significant finds
    (keep the per-project trail from the dogfood skill).
2. **HTML report — FLEET LANE ONLY**: this report is FLEET-wide (it reads the
   whole coding-hermes namespace, the scheduler, and every project board), so
   exactly ONE lane may build and attach it.
   - **Fleet PM lane** (env `CODING_HERMES_PM_SCOPE=fleet`, or the lane named
     `pm`/`stand-in-pm`): run `python3 ~/.hermes/scripts/standin-report.py`,
     verify it actually rewrote
     `~/.hermes/stand-in/reports/LATEST.html` (mtime + size), then include the
     MEDIA line in your final report.
   - **Per-project `-pm` lanes: do NOT run the generator and do NOT attach the
     file.** The fleet report is identical for every `-pm` lane — attaching it
     from each one delivers the same HTML N times and re-runs a full-fleet
     sweep per lane (measured: ~27 min / 3M tokens / ~$6.4 per lane). Post your
     scoped summary as text only: project rows verified (with evidence), gated
     in/out, foreman woken, zombie/skips cleared.

## PM Rules

### Shared-checkout ownership gate (before every board write)

- **You write, hunters read, but sibling writers can exist outside the scheduler tick table.** Immediately before any board RMW, inspect `git status --short`, `git diff --cached --stat`, and the process table for commands whose cwd is the target repository. A fresh staged board diff or a live external `git commit`, guard, board writer, or foreman process owns that snapshot: stand down, do not reset, normalize, append, or commit over it. Re-read after the writer exits and recensus from the new bytes.
- **Treat the scheduler tick table as necessary but insufficient liveness evidence.** A foreign process may be writing from a resumed session, a worktree wrapper, or a lane whose tick row is not visible to this cycle. Process cwd, index state, and a fresh board read are the ownership proof.
- **After every atomic RMW, assert the intended ID set and outcome, not only the script's self-report.** Reparse the board, verify row count and unique IDs, enumerate every intended ID, and assert each expected status/field change. If a first pass misses a naming variant or only partially applies the plan, repair from the current board rather than assuming the printed change list is complete.

- **Never touch disabled projects** (`Enabled=false` = human intent).
- **Never fix code yourself** — you manage the work; foremen do the work.
- **Gate before write, verify after complete.** Un-gated task = no task;
  unverified "done" = not done.
- **Time-box:** 20 min per project sweep (via subagents), 10 min gating,
  10 min verification, 5 min logging. A full cycle ≈ 45-60 min.
Never re-add a task that exists (ledger + board dedup, gate G7). A
schema-valid hunter result is not a new row until the PM independently
reproduces its exact command and confirms the finding is absent from the
current open-board content fingerprint.
- If the scheduler API is down, do read-only ledger work + note it; never
  write boards you can't confirm will be picked up.
- Re-run each documented CLI command exactly as written, including every advertised flag, and inspect both exit status and observable effect; an exit-0 command that silently ignores an unsupported flag is a contract gap, not proof that the workflow works.

### Outcome and count discipline

Use `ESCALATE` only when the cycle needs an owner decision, a real blocker, an overdue/stale item, or a required action deferred; a reproducible defect already represented by an open row is not by itself a new escalation. In that case report `OK` when the cycle completed its checks, and name the still-live row plus exact probe under verification/watch. Reserve `ESCALATE` for the unresolved owner/action condition and state that condition explicitly.

Keep four quantities separate in every report: (1) target reconciled ledger follow-up items from the reconciler's TARGET-specific row / bucket details, (2) raw target-board actionable rows, (3) fleet-wide `board_open_work_count`, and (4) the reconciler's machine-summary `residual_open_work`. Report `residual_open_work` exactly as emitted; do not derive it by summing bucket counts, because the buckets are classification views and can overlap or exclude different age classes. `residual_open_work` is fleet-wide even on a project tick: never label it as the target's open count. When listing aged items, make the qualifier match the count: say “N total, including X” when X is a subset; say “N additional” only when arithmetic has excluded the named subset. Recompute the list and count from the same parsed snapshot before writing the cycle log. When the reconciler resolves the bare target to `NO BOARD` but the scheduler family has a `<target>-foreman` row, resolve that foreman workdir and report the target's manual board census separately; the reconciler's `board_missing` entry for the bare name is a resolution artifact, not permission to re-file or call the target backlog missing. Subtract or separately label perpetual fixtures and review-only rows; do not present all pending/review rows as equivalent executable work. If the target is absent from the reconciler's aged-project table, say no aged target follow-ups were listed; do not convert any fleet figure into a target backlog. For line-oriented JSONL, aggregate with `jq -s` before applying `length` or status grouping, and guard the record type: use a shape such as `jq -s '[.[] | select(type=="object" and ((.status // "") | IN("pending","in_progress","blocked","review","parked")))] | length' <board>`. An unguarded filter can throw `Cannot index string with string "status"` on mixed-schema lines; ordinary `jq` evaluates each row separately, so `[select(...)] | length` emits one number per row rather than a single count. Avoid piping audit tools into `head` when their exit status matters; a closed pipe can trigger SIGPIPE after the audit has already printed a clean summary, leaving the command's true exit status masked.

A zero-output ledger parser is not enough to claim zero follow-ups when a subsequent ledger read fails or is ambiguous. Cross-check the exact `project` field with a simple `jq` selection or a shape-tolerant script, then report the verified count; if the check itself is blocked, state that ledger follow-up count is unverified rather than asserting zero.

**Bound hunter delegation by the PM cycle, not by the child tool's maximum timeout.** Give read-only hunters a narrow, local, command-bounded brief. The delegation runtime hard-caps a leaf at 1200 seconds even when a brief says “8 minutes”, so preserve parent budget for verification and logging. If a hunter times out, stop treating it as an evidence source, do not retry the same hanging wave, and immediately complete the equivalent manual sweep with exact commands. Record the timeout as a collection limitation, not as a product finding, and independently reproduce every candidate before gating it. **A timed-out hunter must not consume the cycle's only write opportunity: finish the manual sweep, but do not file speculative replacement rows just to compensate for the missing summary.**

**Separate board validation errors by file and class before deciding what to do.** A clean raw task-line audit does not cancel a `boardctl validate` error in `events.jsonl`; capture the validator's `[error]` lines and final result from the same stable snapshot, preserve mixed-schema event bytes, and do not perform broad event renumbering or file-wide normalization during a PM gap cycle. A task-row append may still be safely committed when the error is pre-existing and the task-file audit is clean, but report the validator as FAIL with its unchanged error count—not as a clean board. Escalate a real structural error to board-maintenance ownership, while keeping product findings and actionable task counts separate from event-history warnings.

## Anti-Slop Rules (from owner ruling 2026-09-22)

1. **Refresh your own open rows BEFORE filing anything new.** A stale row of
   yours that claims a blocker is a false gate: walk every row you own,
   re-verify each against the repo, and close or refresh it in the same pass.
2. **Every row you file carries a verification line**: the exact command a
   reader runs to confirm the claim (a git log query, a file:line, a test node
   id). A claim that cannot be checked is noise.
3. **Never inherit an off-board blocker into a release gate.** A gate must
   cite only rows on THIS repo's board. If the blocker lives in a different
   repo or harness, file it on the owning board and link it; do not let it
   hold this project's release, and do not invent dependency edges between
   rows that share no board.
4. **Distinguish "not done" from "not verifiable"** - say so on the row instead
   of assuming it holds.

## A DISABLED target: audit read-only, escalate, write NOTHING (G2)

Full procedure moved to `references/disabled-target-procedure.md` (SKILL.md size cap). The always-on rule: `enabled=false` is human intent — no rows, no wake, no board mutation, even a hygiene fix; run the reconciler + read-only audit, verify open ledger premises with real commands, log the cycle, and escalate the disable itself as ONE decision (intentional → make it DURABLE, it silently re-enables from fleet.toml otherwise; not intentional → name the starving open set). Never stamp a re-mint's ledger item `verified` off a re-mint note alone.

## Pitfalls + cycle-proven notes

The per-step pitfalls and the 'Cycle notes proven in practice' rules live in `references/skill-body-pitfalls.md` — load them at the START of every cycle (they carry the board-edit, RMW, /tmp-script, gitreins-commit, and surface-pattern rules the steps assume) and keep SKILL.md under the 100K cap.

## References

Load these only when their topic is active:
- `references/skill-body-pitfalls.md` — cycle pitfalls and proven patterns.
- `references/duckbrain-cycle-log.md` — authenticated keyed logging and read-back.
- `references/board-duplicate-audit.md` — G8 duplicate classes and safe collapse.
- `references/partial-board-write-recovery.md` — recover when a task row writes but its event append fails.
- `references/task_format_guidelines.md` — row fields, dependencies, IDs, and commit trailer.
- `references/audit-row-verification.md` — produced-artifact premise checks.
- `references/tick-pitfalls.md` — resumed-tick continuation rules.
- `references/ledger-corruption-repair.md` — atomic repair when the reconciler cannot parse the ledger.
- `references/cron-fallback-resilience.md` — fallback-provider and long-run resilience.
- `references/delegate_task_troubleshooting.md` — delegation payload and transport pitfalls.
- `coding-hermes-dogfood/references/premature-completion-research.md` — reproduction-first completion checks.
- `coding-hermes-dogfood/references/stand-in-gap-pusher.md` — hourly stand-in coordination.
- `coding-hermes-never-done/references/scheduler-registration-health.md` — G6 tick registration health.
## The PM Loop (one cycle = one hourly wake)

> Detail moved to `references/auto-the-pm-loop-one-cycle-one-hourly-wake.md` — load it before you work this area.
> Summary: **Project-scoped preflight:** read the lane board, then run `python3 ~/.hermes/stand-in/ledger_board_reconcile.py` before counting or reporting. Resolve the exact target board from scheduler.db; if the exact project row is absent, stop and escalate. Never subs...

## Step 1 — Read the Tracking Ledger (always first)

> Detail moved to `references/auto-step-1-read-the-tracking-ledger-always-first.md` — load it before you work this area.
> Summary: The ledger is the PM's memory of what was added, across all runs: - **Central ledger:** `~/.hermes/stand-in/ledger.json` — every item ever added: `{id, project, title, added_at, status, last_checked_at, verification_evidence}`. Statuses normally progress `adde...

## Step 2 — Gap-hunting is SUSPENDED (owner ruling 2026-10-20)

> Detail preserved in `references/auto-step-2-delegate-parallel-gap-hunters-find-many-per-cycle.md` — do not run it.

**Do not spawn gap-hunters, and do not add rows this cycle.** The owner's ruling is explicit: the
queue is already bigger than the throughput, so a PM cycle is *clearing* work, not finding more.
A cycle that files ten new rows and repairs none is a net loss and reads as a dry run with extra steps.

The only additions allowed are the ones that unblock a repair you are doing right now (a
`DEFINE-<n>` row per Step 1b, when you genuinely cannot state acceptance yourself). Everything else
waits until the boards drain.

## Step 3 — THE PRE-ADD GATE (think before you write)

> Detail moved to `references/auto-step-3-the-pre-add-gate-think-before-you-write.md` — load it before you work this area.
> Summary: **This is the step Bane asked for explicitly: before ANY task is added, think about whether the scheduler will actually fix it.** A task that won't be picked up is worse than no task — it's theater. Gate every candidate: | Gate | Check | Fail → | |------|-----...

## Step 5 — Verify Prior-Run Items (the "project manager" part)

> Detail moved to `references/auto-step-5-verify-prior-run-items-the-project-manager-part.md` — load it before you work this area.
> Summary: The reconciler's TEXT line is the summary, not the proof: reconcile the target's ledger from the JSON buckets for the specific project (`board_open_work_items`, `no_id_matches`, `stale_terminal` entries carrying `project == TARGET`), and grep the raw ledger (`...

