# Step 2 — Delegate Parallel Gap-Hunters (find MANY per cycle)


One agent poking 2 projects per hour is too slow. **As PM you spawn subagents**
via `delegate_task` (batch mode) so multiple things get found per cycle.
First respect the lane's WAVE_BUDGET (tick env; 0 = serial tick, 1 = one worker
slot): with a budget of 0 there is NO hunter wave (serial tick); with a budget of 1 or more you may run that many hunter subagents. **An empty cycle with 0 rows
gated-in is a VALID outcome**, not a failure: when the backlog is already deep
(two dozen pending rows) and the foreman is actively consuming it (recent ticks
in `ticks` completing; fresh `task_completed`/`audit` events in events.jsonl),
Adding rows is the shotgun anti-pattern — the cycle's value is verification,
ledger hygiene, and escalation. **WAVE_BUDGET is a ceiling, not a mandate**: even with budget > 0,
skip the hunter wave only when the backlog is deep AND the target foreman is demonstrably productive
(recent target `task_completed` events or a completed tick with `code_commits > 0` / a verified row close).
A merely frequent `dry_run`, `code_commits=0`, or satellite/PM tick is not active consumption; it does not justify
withholding the hunter slot. If the foreman is not productive, use the allowed hunter wave or spend the serial
slot on the target's open-row premise walk. An unfired budget is correct only when the evidence supports it. On a serial tick (WAVE_BUDGET=0) — or on a skipped
wave — make that operational: spend the slot verifying the foreman's 1-3 most recent
`task_completed` rows with real commands (commit containment + fix present on the live tree +
remote parity — for a code fix, 'fix present' means running the tests the fix commit itself
touched: take the test files from `git show --stat <commit>`, grep each for its real `func Test`
names, run those packages with `-short -count=1`), then walk the target's own open rows and re-verifying
each premise with a real command (anti-slop rule 1). **Small open set ⇒ the walk IS the cycle:**
when the target's open-row set is ≤ ~5, spend the slot probing each open row's premise against
the workdir's CURRENT tip (fetch/clone fresh, assert tip sha — never a stray same-day-earlier
clone, which pins HEAD behind the repo silently) and report the verdicts as a row-coupled table
(ID | priority | verified-live / blocked-parent / stale-premise | evidence + probe command)
instead of empty-cycle boilerplate; with few rows the premise walk is the cycle's whole content.
Full probe recipe (grep the target's own tree only, build before -run, name the tip sha in the
annotation): `references/board-close-verification.md` § Premise verification probes.

When the board carries ZERO `task_completed` events at all (gatherer-minted audit rows the foreman has never picked), that branch is empty — 'recent foreman commits'
then means the OTHER family lanes' `git log -- .coding-hermes/board/` commits (their `pm:`/`dogfood:` commits
prove the shared board's writers are alive), and the slot goes to verifying the lane's own rows' premises
against the producing gatherer's FRESH artifact (`generated_at` newer than each row's `created_at`, then exact
count match to the digit — see the ARTIFACT-premise verification bullet). Reading liveness with
`LIKE '<target>%'` returns the whole family — for the TARGET's own cadence query `project_name =` exactly.
Also fold the content-duplicates
you find (superseded_by + foreman_note), evidence-refresh the rows whose premise
is still true and has moved (drift counts, new duplicate ids), and leave the rest untouched.
When the walk finds nothing to verify (zero prior-run ledger items, all rows
gatherer-minted and premise-fresh), LAND the sibling lanes' uncommitted board writes
if any exist (see the sibling-row pitfall) — a serial tick that verifies nothing and lands
nothing is a skipped tick, not a full-value one. BUT never land when a writer is LIVE with the change staged, not dead — and the live writer is not only a sibling lane: on a shared board the PRIMARY foreman itself (its tick `running` with a fresh heartbeat in the ticks table) often holds row closes staged in its working tree, because it closes rows it just verified. That foreman lands its own work in its own commit — STAND DOWN on ALL board writes this cycle: no commit, no reset, no touching the staged set. Before deciding, query the ticks table for `project_name LIKE '<family>%' AND status='running'` (the primary included) and judge liveness by `heartbeat_at` — a ticks-table column queried directly, never via events.jsonl text, and normalized to ONE timezone before diffing: a raw string compare between an offset-carrying heartbeat (`-05:00`) and a UTC now mislabels a minutes-fresh writer as hours-stale, polluting both the tick report and the DuckBrain log with a false liveness verdict; on a re-query an advancing heartbeat = the writer is mid-tick). The landing rule exists to rescue DEAD writes; landing under a live writer turns one commit into two and can strand the sibling's rows behind yours. Spend the slot on premise verification instead and defer the land (and any deferred evidence stamps) to the next cycle. That deferral covers escalation rows too: an escalation whose content is a worker-deliverable (e.g. a NEW failing member of a recurring defect class) is deserved, but appending it under a live writer risks interleaving into that writer's commit — queue it on a handoff line in the report (id, fix direction, pass criteria) and append it next cycle once the writer's commit lands and frees the board. When a push just landed and its CI run still reads in_progress, cite the most recent COMPLETED run on that head as the health baseline and mark the new run provisional — do not poll remote CI inline mid-tick.
Landing mechanics (dead-writer case only): `git diff --stat
<board>` FIRST to identify what siblings staged (never sweep with `git add` blind — a
shared file can carry a sibling's WIP hunks), commit with the co-author trailer, then PUSH
and re-read `git rev-list --count origin/<branch>..<branch>` to 0 before reporting — an
unpushed landing is invisible to any remote-reading foreman. Spot-verify the cheapest
premises of the landed rows against the tree in the same pass (grep a cited path/line) so
the landing carries at least one proven claim.
On a SHARED board with dozens of same-day pending rows (audit
families, satellite-produced rows), scope the walk instead of burning the tick
re-running every evidence command: verify the rows the target's own foreman will
pick first (its lane prefix / highest priority), and pick the CHEAPEST probe
per row, not the same one for all: a premise backed by a live-reproducible
counter (ruff --statistics, test tally, endpoint total) is verified by
re-running that command and comparing counts — exact match proves the premise,
drift is an evidence refresh; a premise about landed history (merge hash,
untracked-files claim, CI state) is verified by containment
(`git merge-base --is-ancestor` / `git status`) and nothing else. Budget the
tick: re-probe the few live-counter rows, containment-check the rest, and the
un-walked remainder is covered by the producer lanes' own QA cycles, not
silently skipped. Stamp evidence refreshes DEDUPE-BY-`run_id`: before appending
an evidence entry to a row's `detail.evidence`, skip when an entry with the same
`run_id` already exists — a repeated tick otherwise stacks identical evidence
lines. Also check for UNCOMMITTED rows-only board staging before planning any
edit: a sibling satellite lane killed mid-commit leaves its rows in the index or
working tree; land them (git add + commit, timeout ≥300s in gitreins-gated
repos) so a foreman tick can actually see them. Confirm the split with
`git diff --cached --stat` (staged sibling rows) vs `git diff --stat` (working
tree) BEFORE staging anything of your own, then stage your row edits on top and
commit ONCE — a landed sibling refresh you re-proved yourself is a full-value
land, not a no-op. NEVER `git checkout -- <board>` to 'clean up' staged rows
you did not write: that silently erases a sibling lane's mid-flight verification
work. Commit the board, push the lane's published branch, and re-read
`git rev-list --count origin/<branch>..<branch>` as 0 BEFORE writing the DuckBrain
cycle log so the log names a published commit, not a local claim. If a cycle log
was written before a later landing or parity correction, append a correction
record at the same key with `correction=true` and `supersedes=<prior-record-id>`;
do not silently leave the earlier state as the latest operational truth. Never use
placeholder trace values such as `commit=to-be-filled`: a pre-commit row marker
must use explicit pending/none semantics, and a closed-row marker may name only
the actual published SHA. Cite a durable repo-local evidence artifact (or the
exact reproducible command in the row) rather than a `/tmp`-only file, because a
later verifier cannot rely on ephemeral evidence. A 0-rows cycle that proved or
retired its rows' premises is a
full-value cycle. Prove the backlog-freshness half with a census,
not a count: `Counter(r.get('created_at','')[:10] for r in rows)` over the board
— a pending set minted entirely within the last day means the producing lanes
(audit/dogfood/QA) are actively filing and the foreman has not had a pick window
yet, so 0 `task_completed` events is EXPECTED, not starvation. Read the event census with the RIGHT key: events.jsonl names the event under `event_type` (legacy `type`/`event` keys appear only on foreign-schema lines) — a census that counts `e.get('type')` reports 0 `task_completed` on a live foreman and misreads mid-flight work as idle. For a shell-only census, anchor BOTH the key and the value in one literal — `grep -c '"event_type":"task_completed"' events.jsonl` — so foreign-schema lines (legacy `type`, notes, staging ids) do not inflate the count. Pair it with the
the last tick's `outcome` (`committed`, exit 0) and note both in the report — but read WHAT
the last completed tick recorded before citing it as productive: a committed tick with
`code_commits=0` may only have landed a board note (e.g. recording a failed worker run),
which is honest bookkeeping, not progress on a row. Also
check foreman liveness before concluding
starvation: a lone `completed` tick hours old plus live MCP edits in the
worktree means work is mid-flight, not stalled. When verifying a code fix on
the foreman's own repo, check the lane-vs-origin gap: unpushed commits on the
default branch are fix-at-risk (a sibling deploy/rebase can wipe the local
tip) — push them and re-count `git rev-list --count origin/<branch>..<branch>`
to 0 BEFORE stamping verification; a stale FETCH_HEAD makes the pre-push
count look stranded even when the push is a no-op, so judge by pushing, not
by counting. On multi-foreman audit families
that share ONE board and workdir (`<audit>-typing` / `-lint` / `-deadcode` /
`-complexity` / `-security` + their satellites all reading the same
tasks.jsonl), query liveness FAMILY-wide — `SELECT project_name,
MAX(completed_at) FROM ticks WHERE project_name LIKE '<family>%' GROUP BY 1` —
before reading a stale target-only last tick as starvation: the target's own
foreman may be deep in a 24h cooldown (or fresh, one tick ever) while sibling
foremen actively consume the same board, so 0 task_completed events on the
target's rows is EXPECTED, and the right output is an armed escalation ("if the
next cooldown-expired tick no-ops with rows on scope, escalate") not a filed stall.
Before the batch:

**Check WAVE_BUDGET**: read env `WAVE_BUDGET` (unset/0 = serial tick: no hunter wave — spend the slot verifying foreman completions and open-row premises as described below). N>0 = max concurrent hunter subagents in ONE delegate_task call; with budget=2 the natural split is two complementary lenses on ONE project. The `tasks` param must be a JSON array of `{goal, context, output_schema?}` objects — never a bare string or non-array. Validate every `output_schema` as Draft 2020-12 before dispatch: the root is an object, each `properties` entry is itself a schema, and array schemas put `type: array` and `items` beside `properties` rather than nesting `type: object` as a property. A schema-validation error is a malformed brief, not a worker failure; correct the schema and retry once before falling back. **On unattended surfaces (api_server/cron) delegate_task often fails via JSON transport double-encoding — validate the payload first (retry once with a minimal test array `[{"goal": "t", "context": "t"}]`); if minimal passes but the real payload fails, fall back to MANUAL gap hunting with the same brief a hunter would get (workdir, board path, README, tests, docs) plus a re-verification of open ledger items with real commands, and note the delegation failure in the cycle report.**

- Give each a SELF-CONTAINED brief: project workdir, board path, what the
  project claims (paste the README purpose + board status line), what to
  probe (their 15-20 min gap sweep: does the promised workflow run? do docs/
  integration guides exist? is there a real API reference? test suite sane?),
  and the output format: **max 4 findings**, each = `ID candidate | problem |
  how a user hits it | fix direction | observable pass criteria`.
- Optionally specify an `output_schema` in the delegate_task call to validate
  the subagent's response structure.
- **On a project with a deep pending backlog, split the wave into TWO
  complementary lenses instead of N generic hunters:** (a) a LIVENESS auditor
  that filters the board's pending P1/P2 rows and returns a verdict per row —
  `LIVE` (defect still present: evidence_command + snippet), `FIXED`
  (positive evidence the defect is gone at HEAD), or `UNCLEAR` (cannot
  determine, one-line why) — and (b) a claims-vs-reality gap hunter that
  picks 3 concrete README/spec claims and verifies each with a command,
  returning only command-proven findings. Lens (a) is what makes the cycle's
  verification half parallel-safe (hunters re-probe premises read-only; you
  close/refresh rows from their verdicts after spot-checking), and lens (b)
  keeps new-row flow alive without duplicating the backlog. Both briefs:
  READ-ONLY, no git writes, respond in English, `output_schema` enforced —
  treat every child summary as an untrusted lead, not evidence. Re-run the
  exact cited command yourself before closing, refreshing, escalating, or
  filing anything; reconcile paths, heads, and counts against the current
  target tree because a schema-valid hunter can still cite a stale path or
  stale checkout. A hunter's grep can prove the wrong token.
- Tell them explicitly: findings only, NEVER fix code, never touch git.
- Collect their summaries. Each subagent's result will be in the `summary` field of the delegate_task result object. You now have up to WAVE_BUDGET * 4 candidate gaps per cycle (or the manual findings).
- If a finding is already on the board (matching ID or content fingerprint), note it but do not add a duplicate task. The PM's role is to verify and escalate existing items, not to create duplicates.
- Note: delegate_task results include a `summary` field containing the subagent's output. If a subagent times out (status: `timeout`), treat it as no findings for that project and consider manual gap-finding as a fallback. Avoid relying on external API calls that may hang; prefer local file and git inspection for gap hunting.

**Verify documentation claims against the current test tree before filing.** For every documented test path or node, run `test -f <path>` and the exact collector command (`<venv>/bin/python -m pytest <path>::<node> --collect-only -q`). A missing file or node is a documentation claim failure, not a product-test failure; cite the exit code and current tree evidence, then deduplicate it against existing onboarding/docs rows before gating a new task. For findings in generated or duplicated documentation, trace the source-of-truth and every published/generated copy before filing; acceptance criteria must correct the authoritative source and regenerate or reconcile derived artifacts, or the defect will return at the next generation. When a documentation row is marked complete, rerun the repository-wide claim census rather than checking only the lines named by the row: if residual copies still contradict the claim, reopen that same row in place, preserve the partial-fix commit/evidence, and state the remaining copies and exact probe. Do not mint a sibling row for residual drift in the same claim class.






**Example**: the hunter `tasks` payload (one {goal, context, output_schema?} object per hunter; output_schema a valid Draft 2020-12 object schema) lives in `references/delegate-task-schema-example.md` — generate it with Python json.dumps or `jq -c`, never hand-written.








**Do not spawn subagents that would edit the same board concurrently** —
hunters only READ; you (the PM) are the only one who WRITES boards. That is
the coordination rule that keeps the fleet safe.

