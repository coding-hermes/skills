# PM tick pitfalls — overflow notes

SKILL.md is at the 100K char cap; lessons that cannot fit there live here.
Move a rule UP into SKILL.md only together with an equal-size trim.

## Resumed tick = continuation, not restart

A RESUMED tick (scheduler resume after a gateway drop/drain_timeout) is a
CONTINUATION, not a restart — check what the prior session already landed
before doing anything. Read `git log --oneline -3` for a board commit whose
message names this tick's id, `git rev-list --count origin/<branch>..HEAD`
(0 = it pushed), the G8 raw-line audit, and `git status --porcelain` for
stranded sibling writes. Skip every step the prior session already completed;
the resumed session's remaining work is verification of the open rows, the
CI-health check, and the DuckBrain cycle log (marked as a continuation).
Re-running the board cycle mints duplicate rows and double-stamped evidence.

## Verify a row premise against the LIVE tree's real symbols

A fresh-QA row can name test symbols and package paths that grep does not find
at HEAD (the row was minted against a different clone/HEAD than the workdir's).
Probe before counting the row as backlog: grep the workdir for the exact symbol
(`grep -rln '<symbol>' <workdir> --include='*.go'`) and EXCLUDE `.worktrees/` —
stale worktree copies false-positive the grep and read as "premise true". When
the symbol genuinely does not exist at HEAD, the premise is UNVERIFIABLE from
the PM lane: leave the row open for the foreman to premise-check and say so in
the report. Never close it as fixed (you never ran the suite) and never file a
duplicate for it — "not verifiable" is a distinct verdict from "not done".

## A 'stranded' event line may already be landed by the primary foreman

Before planning any dead-writer rescue landing, read the board's last
board-file commit: `git log -1 --format='%h %ci %s' -- <board>/tasks.jsonl`.
If a foreman committed minutes ago naming that event, `git diff --numstat`
on the file reads dirty but `git commit` says 'nothing to commit' — the
working tree already matches HEAD and the diff you saw was against a stale
local ref. `git push` then reports up-to-date; verify remote parity with
`git fetch && git rev-list --count origin/<branch>..HEAD` (expect 0), never
by trusting an earlier count taken before the foreman's commit landed.

## Same-class pending rows: cross-link IN PLACE, never fold, never re-mint

When an open row from another producing lane is the SAME failure class as a family
row the PM is tracking (same load-sensitivity class, same root-cause family), the
move is an IN-PLACE annotation on the sibling row — set priority to the family
row's level if lower, append a `review_notes` note naming the family row and
requiring the family fix to cover this member — NOT a fold (the sibling is its own
live finding, superseding it deletes work) and NOT a fresh duplicate mint (G7). If
the sibling row has no priority at all, that missing priority is itself a gap: an
unprioritized pending row sorts below every prioritized one and is never picked.
Snapshot the board to /tmp, edit exactly one row, and assert the edit shape is
exactly 1 file, 1 insertion, 1 deletion (`git diff --stat`) before committing.

## Attribute family liveness aggregates to the owning lane before citing them

A liveness query with `LIKE '<target>%'` returns the WHOLE family's ticks, which
on a mature project can be thousands — citing the raw count plus `MAX(completed_at)`
as the target's liveness is an unattributed aggregate: the last completion may
belong to a sibling lane and prove nothing about the target's own foreman. Break it
down per lane (`SELECT project_name, COUNT(*), MAX(completed_at) FROM ticks WHERE
project_name LIKE '<target>%' GROUP BY 1`) and name the owning lane in the report.
Also confirm the exact key once per unfamiliar DB with `PRAGMA table_info(ticks)`
before trusting any tick query — the sqlite3 error for a wrong column misreports as
a shell quoting problem, not a schema problem.

## Count open rows from a status census, never from an id-prefix scope

Satellite lanes file rows under the producing lane's id scheme (`QA-CHS-*`,
`QA-TROUBLE-*`), not the target project's prefix — a `<TARGET>-*`-scoped
census silently reports a QA-filed backlog as an empty lane. Count the
target's real open rows from the `status` values (pending/blocked/
in_progress/review) over the whole board, then attribute rows to the target
by their detail/cited repo, not by id prefix.
