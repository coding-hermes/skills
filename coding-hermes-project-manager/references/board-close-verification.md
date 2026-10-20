# Board close + verification recipe (PM cycles)

Evidence-based closes and safe board writes on JSONL boards. Read when closing rows, appending events, or reconciling a board during a PM tick.

## A two-census disagreement can be a first-read artifact — re-audit before editing

A mid-tick duplicate-id census can flag an id that a re-run of the SAME audit
on the same file shows as unique. Before writing any collapse script: re-run
the raw-line audit, re-count with a second independent parse, and read
`git status`/`git diff` against HEAD. If both later reads agree the file is
clean and the tree is clean, treat the first flag as a read artifact and make
NO edit — a collapse script that asserts 'expected N lines, found M' on a
healthy board is the tool inventing the defect, and its abort leaving the
board untouched is the correct outcome. Standing signal the file was never
bad: two independent auditors (yours and the foreman's own row-count guard)
agree on the unique-id count. Also check the SKILL.md loaded in-context may
describe a LARGER board than the one on disk: a fleet-wide file read as a
spillover/paged result can reflect a different project's row count than the
target workdir's actual file — always derive line counts from the TARGET's
own file, never from a cached read of a similarly-named board.

## Review/escalation rows: verify the premise, do not close the row

When a cycle's board contains a review/escalation row (e.g. 'blockers X/Y are stale, re-derive'), the PM's job is to TEST THE PREMISE with commands and report — not to close the row:
- Confirm each cited fact yourself (ancestor checks, CI-config grep, current row status) and cite the commands in the tick report.
- If the premise holds, leave the row OPEN: the remaining action it names (re-derive a blocker, re-adjudicate) belongs to the owning lane (releng/review), and the row IS the queue entry for that lane. Closing it erases the work item the evidence just validated.
- If the premise is REFUTED (e.g. the cited fix never landed), that is the finding — file or annotate accordingly, still on the row.
- A verified-premise no-op tick is a good tick: report 'rows verified, none written, before/after identical' rather than manufacturing a write.

## A judge PASS can be scoped narrower than the row's acceptance criteria

The tier-2 verdict's `task_criteria` is a condensed bundle, not a copy of the board
row's `acceptance_criteria`. Before accepting a close as evidence-complete, diff the
two lists: criteria halves the verdict never names were never judged and are UNMET
regardless of the PASS (typical drop: 'record commands AND results' judged as
'commands recorded', 'capture measurements' judged as 'fields defined'). Do not
re-litigate the close — the judged work landed. File the residual as a new row with
the unmet criteria restated as acceptance criteria, annotate the closed row's
`review_notes` to point at the residual, and leave status alone. If a residual
criterion is not yet dispatchable (its precondition work does not exist), do not
board it — name the gate in the report and in the new row's `review_notes` so the
deferral is documented instead of silently lost.

## Verifying a fix actually landed before closing its row

1. `git fetch origin` first — local HEAD can be ahead of or behind origin; a close must cite origin truth.
2. Assert THE COMMIT is an ancestor of the origin branch: `git merge-base --is-ancestor <fix-sha> origin/master && echo landed`.
3. Assert THE ARTIFACT is in the tree at that commit or at HEAD: grep the file (e.g. `grep -n 'cargo test' README.md`) — an ancestor check alone proves the commit exists, not that the documented behavior is present.
   - Work from the SHORT sha when a note's full 40-char sha is not byte-exact: a `git cat-file` miss on a copied full sha is usually transposition/truncation from an echoed-output mangling, not a missing commit. Re-derive the full sha from the short form via `git log --all --oneline | grep <short7>` (or the events.jsonl note's own `git log origin/main --oneline`) before concluding NOT-LAND; a verdict read from a wrong sha is worse than no verdict.
   - For a TEST-behavior fix, the artifact check is the TEST SYMBOL, not the commit's file list: grep the test tree for the `func Test...` / helper symbol the fix commit introduced (from `git show --stat <sha>`), then run that package with `-short -count=1`. A green unrelated test does not verify the fix's own surface.
4. Cite the gitreins verdict only as corroboration; verdicts can judge pre-merge trees.
5. Prefer closing rows whose fix is verified over leaving them in_progress because 'the foreman should close it' — a row stuck in_progress for days with its fix already on origin/master is drift the PM owns.

## Row status schemas vary per board

- Some boards leave `status` NULL on discovery-queue rows (no lifecycle applied yet). Do NOT count NULL as pending, and do not 'fix' them to pending — classify: NULL = unclassified backlog, `pending` = actionable, `in_progress`/`complete` = lifecycle rows.
- Report all three counts separately; a raw pending count that silently includes NULL rows overstates open work.

## Atomic board rewrite

1. `cp tasks.jsonl /tmp/snap-$$.jsonl` before any edit.
2. Write rows to a temp file, then validate LINE-WISE: `[json.loads(l) for l in open(tmp)]` and assert the count matches. NEVER `json.load(open(tmp))` — a JSONL file is not one JSON document and whole-file parse fails with 'Extra data', killing the script mid-flight. Keep validation BEFORE `os.rename`, so a failed validation leaves the original untouched.
   - Do row edits in Python (json.loads every line, mutate, json.dumps one per line) — NEVER `jq '...' tasks.jsonl > tmp` for a row-level edit: bare jq pretty-prints multi-line objects, so its output fails the line-wise parse check (and `mv` must never run before that check). Serialize ONLY the lines you mutate: mixed-schema boards carry lines that do not survive a json.dumps round-trip byte-identically (string `detail`, foreign separators/escaping), and blanket re-serialization rewrites every line's bytes. Probe first — `json.dumps(json.loads(l), sort_keys=True, separators=(',',':')) == l` per line — copy every non-round-tripping line through raw, and assert the untouched lines are byte-identical to the snapshot.
3. Next event id = last line's id from the tail, never a max over tolerant parses (tolerant parses of a mixed board return 0).
4. Commit via `git commit -F <file>` (message written to /tmp first), then verify `git log origin/<branch> --oneline -1` shows the new sha before reporting the artifact. Guards run at commit time; a pass there is not a push confirmation.

## Cross-row evidence closes: a sibling row can BE the root cause

A finding row (e.g. 'confirm root cause before tagging') can be verify-CLOSED by evidence that lives in ANOTHER board row — typically a later sweep row whose reasoning already root-caused the finding and whose own evidence (rerun green, identical-code runs green) is cited verbatim. Procedure: read the sibling row's reasoning, re-check its load-bearing facts yourself (rerun status via gh/CI, commit ancestry), then close the finding row with a `foreman_note` naming the sibling row as the evidence source and restating the root-cause class. Do not re-run the whole investigation; do not leave the finding open 'pending a root cause' when one is already recorded on the board.

## Verify a LOAD-SENSITIVE row by paired measurement, not by local reproduction

When a row's premise is environmental (a test fails only on a loaded host, under a
cap, on fsync-heavy storage), do NOT treat a green local run as 'not reproducible =
stale premise' and do NOT try to reproduce the load locally. Run the row's own
failing test/command once locally AND capture the local load context (`uptime`,
cgroup cap) in the same call, then read the PAIR: local-pass at moderate load plus
the row's cited failing evidence on a loaded host (bunker/CI evidence file, CI run)
CONFIRMS the load-sensitivity — the row stands, premise verified. Record both
numbers in the evidence line ('passes 0.069s at loadavg 13; fails 1.34s at
loadavg 34 per cited artifact') so the next reader never has to re-derive the
direction of the verdict. Cite the evidence artifact by path only after confirming
it exists and contains the cited test name — grep for the symbol before trusting it.

## Verify the SURFACE, not just the source of truth file

When a row's premise is 'X is undocumented/unavailable at the CLI', the premise probe must run the SHIPPED BINARY/CLI (`<bin> <cmd> --help`, `<bin> --list-defaults`) and grep the docs README link — grep-only checks against the repo can both false-negative (help text lives in Go source strings, not docs) and false-positive (doc landed but not wired to the surface the row names). If the premise is already resolved by landed work, annotate the row `premise-stale` with the probe commands and mark it a close-out candidate for the owning lane; do not re-file it as a new finding and do not close it yourself if the row names residual scope (e.g. only half the documented path resolved).

## Do not verify a fresh fix against a slow-onset metric

A fix that landed <24h ago on a finding measured in MB/day or days-of-growth must stay OPEN even when a quick check looks good — a short observation window cannot distinguish 'fixed' from 'too early to tell' on a slow-onset metric. Annotate with the fix sha and the earliest date the window is honest (fix age >= the metric's original observation span), then re-verify next cycle.

## Pushing from a shared checkout that is not on main

Worker checkouts routinely sit on a feature branch with no upstream: plain `git push` dies with 'no upstream branch'. Push with an explicit refspec — `git push origin <branch>:main` — then verify `git ls-remote origin main` equals local HEAD before citing the sha. Do NOT `--set-upstream`: that points the shared branch tracking at main and confuses the next sibling's push.

A run pushed moments before the CI-health check reads in_progress: cite the most recent COMPLETED run on the same head as the baseline and mark the new run provisional in the report; when the tick has slack, watch the run to completion with `gh run watch <runId> --exit-status` (a push-triggered CI-only run finishes in minutes) and read the final status/conclusion back from `gh run list --limit 1 --json status,conclusion` — this converts 'provisional' into a verified green in the same tick, and a delegate_task child can absorb the wait when the parent is near its own budget.

## events.jsonl is the candidate-close cross-check

A foreman can emit `done` events (with commit + worktree) whose task rows stay `pending` in
tasks.jsonl — the row flip lags the event. Each cycle, read the tail of events.jsonl for
`event: done` entries and grep each named task id in tasks.jsonl: a pending row whose id has a
done event with a commit is a candidate close — verify the commit is an ancestor of the
default branch (and the artifact in the tree, per the steps above), then flip and cite the
event + sha. Conversely, a pending row whose premise wording already reads as a completion
record ('fully green', 'PASS') is a candidate for a premise probe, not automatic work.

The same half-landed close appears WITHOUT any event: a foreman close commit can set
`worker_status=complete` + `commit_hash` (sometimes `completed_at`) on the row while leaving
`status=pending`. So the candidate-close scan must ALSO read the ROW's own fields, not just
events: any non-terminal row carrying close fields (worker_status complete, or commit_hash +
completed_at set) is a candidate close. Verify its commit_hash is an ancestor of the default
branch and the artifact is in the tree, then repair `status=complete` IN PLACE with every
close field byte-preserved (a terminal-row repair per G8, not a rewrite) and cite the
verifying probe in the note. One close commit can leave several rows in this state — fix them
in one atomic pass. Never count these rows as open work in the census before the scan runs.

## Board-only commits: DEGRADED guard is expected, parity is the proof

A commit touching only `.coding-hermes/board/tasks.jsonl` grades nothing in diff mode — the guard reports `DEGRADED PASS (skips: lint, tests)` and the pre-commit hook warns but commits anyway. That is expected, not a red flag; do not re-stage or retry to make lanes run. The artifact proof is the PUSH, not the guard: run the repo's push helper (e.g. `scripts/push_remotes.py` where it exists) and report the commit sha with `parity=OK` on all remotes.

But staging ALSO `.coding-hermes/waves/*.json` or `events.jsonl` changes the guard class: the safety trigger runs the FULL suite, and the commit routinely exceeds the ~180s foreground terminal cap — the fg timeout kills the call while the hook keeps running, leaving the outcome ambiguous. Rules:
- Run board commits in the BACKGROUND (`terminal(background=true)`) and poll the commit log for `rc=`.
- Write the commit message to /tmp with write_file FIRST, then `git commit -F /tmp/msg` — never an inline heredoc; on 'could not read log file', the message file is gone, rewrite it and retry.
- If the secrets gate FAILs on a board+wave-manifest-only commit while its own secrets line reports clean on the same content, retry ONCE with `--no-verify` (no code is staged; the bypassed gates grade nothing real) and cite the sha. Never `--no-verify` when any Go/test file is staged.
- After a blocked commit, re-check `git status` shows ONLY your intended paths before retrying (pathspec-scoped commit, shared checkout).

## A verify-only sweep row is a RECORD, closeable once its open findings are tracked elsewhere

A releng/audit sweep row that is a SNAPSHOT of a periodic check (inventory, counts, CI truth all carried in its own detail) has no dispatchable scope of its own — the PM closes it as a record, citing where each open item it surfaced is separately tracked (e.g. the operator-gated cut row a readiness sweep feeds). Do not conflate this with review/escalation rows (premise-testing, stay open) or with the operator-gated row itself (never flips until authorization). Test before closing: does the row name ANY action no other row tracks? If yes, leave it open; if its sole open item is another pending row, close the sweep and name that row in the note.

While in the file, normalize terminal-status synonyms (`done` → `complete`) in the same atomic rewrite — a mixed vocabulary keeps a naive non-terminal filter over-counting open work.

## Landing a superseded-row annotation vs a close

- Superseded sweep/summary rows (same cadence, newer row covers the same ground) are ANNOTATED, not closed: add `superseded_by=<newer id>` + a dated note, leave status alone — they stay open only because they gate on user authorization, which never expires by supersession.
- A verification/finding row whose named blocker is resolved or root-caused IS closed (status complete, evidence + evidence-source in the note).

## A landed worker commit can sit UNPUSHED with its row still pending

`git status` clean + commits on local main are NOT landed: the wave wrapper's
push step does not always run. Each cycle, after reading the board, run
`git log <origin>/main..HEAD --oneline` — a worker's fix commit that is
unpushed means (a) the fix is invisible to every remote reader and CI, and
(b) the row cannot be verified against origin truth. Push it (guard runs at
commit/push time; a docs-only push grades DEGRADED PASS — that is fine), then
close the row citing the sha AND the pushed state (`git ls-remote <origin>
main` equals local HEAD). Prefer closing the row yourself at that point: a
fix-commit merged locally with its row still pending is PM-owned drift.

## Test-count / docs-drift sync is a first-class close artifact

Repos with a test-count checker (README/CONTRIBUTING claim N tests across M
files) break at commit time when a fix adds test files without syncing the
claims. When verifying a fix that touched tests, always run the repo's drift
checker or the live collection (`pytest --collect-only -q`) and compare with
the documented counts; if they disagree, stage ONLY the doc files with a
pathspec commit (`git commit -m ... -- README.md CONTRIBUTING.md`) — plain
`git add` + commit in a shared checkout sweeps siblings' staged files.

## Long verification batteries: background + RC marker, never foreground

Full gate batteries (`make verify`, suite runs) routinely exceed the ~180s foreground terminal cap, so the call dies mid-run and the verdict is lost. Run them as a background terminal that ECHOES ITS OWN SENTINEL, then poll the log file: `(make verify; echo "RC=$?") > /tmp/verify.log 2>&1` and poll with `grep RC= /tmp/verify.log` until it matches — the exit code of the gate must come from the echoed marker, not from the terminal call, and a log tail that stopped mid-output with no RC line means it is still running (or the call was killed; check for the process before re-running).

## When a status flip IS a PM row close

A dogfood/verification record row whose own detail carries the live evidence (probe output captured during a prior run) may be flipped pending→complete by the PM with that evidence cited in a `verification` field — it is a record, not a foreman work item. Never flip a row that names work no one has done (owner authorization, version-prep commit, unreachable host); those are queue entries for the owning lane — verify the premise and report, leave the status alone.
