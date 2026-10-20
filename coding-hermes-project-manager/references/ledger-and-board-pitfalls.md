# Ledger and Board Pitfalls

## Two censuses disagreeing is a stop signal, not a finding

When a jq stream census and a python line-wise parse of the SAME board disagree (jq emits rows the python census cannot find — phantom pending rows), trust NEITHER output and rerun a byte-level census (python, `l.strip().startswith('{')` + `isinstance(r, dict)` guard) against a PINNED snapshot (copy the file first, parse the copy) before any dedupe, gating, or before/after claim. Do not report either census as truth, and do not file a duplicate-id or stale-row finding off the minority output: jq's per-line streaming over a board being concurrently written can yield per-line results that no stable snapshot contains. The python line-wise parse (which also silently skips and counts non-object lines) is the arbiter; the discrepancy itself goes in the cycle log, not the board.

## DB-workdir fallback for shared-board audit families

On multi-lane audit families (python-audit-* and any family whose lanes share ONE board), `projects.workdir` in scheduler.db can BE a stand-in path with NO board inside it — the DB row and fleet.toml disagree, and the DB is only authoritative when they agree. When the DB-resolved board path does not exist, read the lane's entry in `~/.hermes/fleet.toml` (`grep -A8 'name = "<target>"'`) and use ITS `workdir` — that is where the family's shared `.coding-hermes/board/` actually lives. Verify the file exists (`ls -la`) before trusting it, attribute every liveness/row query to the whole family prefix (`LIKE '<family>%'`), and run the G8 raw audit + all RMW edits against the fleet.toml-resolved board.

## Scheduler DB queries: PRAGMA before column names

Never author a ticks/projects query from remembered column names: run `PRAGMA table_info(ticks)` (and `projects`) FIRST. Ticks time columns are `spawned_at`/`completed_at` (no `started_at`, no `heartbeat_at` — heartbeat lives in `tick_workers`, and foreman worked-task rows live in `tick_workers`, not `ticks`). `projects` has snake_case `cooldown_s/cooldown_pin_s/cooldown_pin_by/enabled` (there is no PascalCase `CooldownS` and a liveness query mis-authoring a `LIKE` pulse-match row goes hungry; column-mismatched WHERE silently `Parse error` / returns None rather than erroring loudly). Availability per host may differ (a pre-`heartbeat` DB answers ticks liveness by MAX `completed_at` recency instead) — after grabbing the real header set, re-evaluate every column the query planned to use, and always pin `project_name='...'` EXACT-CASE with the PRIMARY's exact name — `LIKE '<t>%'` confounds the target lane with its family/lanes.

## Counting board rows: `.get`, sets, not Counters

Legacy rows can omit fields entirely — read census fields with `r.get('status')`, never `r['status']` (a bare KeyError mid-scan kills the whole census). For before/after row counts, diff the id SETS (`added = after_ids - before_ids`) and report `len(set(ids))`, never Counter totals: duplicate-id lines inflate a status Counter while the unique-id set stays correct, so a line-level append and a duplicate id look identical through a Counter.

## Extracting the reconciler's machine summary

Split the summary JSON out with awk, not `sed -n '/BEGIN/,/END/p'`: the marker line prints ABOVE
the JSON and sed's range INCLUDES the start line, so the slice begins with
`<<<RECONCILE-SUMMARY-JSON-BEGIN>>>` and `jq` on it dies with `Invalid numeric literal at line
2, column 0` — a parse error that looks like corrupt reconciler output but is only the marker.
Use `awk '/RECONCILE-SUMMARY-JSON-BEGIN/{f=1;next}/RECONCILE-SUMMARY-JSON-END/{f=0}f'`, whose
`next` drops the marker line, then `jq` the slice normally. In python the equivalent is
`json.JSONDecoder().raw_decode(text_after_first_brace)` — do NOT slice with
`text[find('{'):rfind('}')+1]`: the block's own nested objects make rfind land inside the JSON,
and human SUMMARY/CLASSIFICATION lines beside it yield `Extra data`. The per-project
CLASSIFICATION table (lines shaped `<project>  aged=N open_work=N drift_close=...`) can omit the
target entirely — an absent line is NOT evidence of zero aged items; scan the ledger directly
for the target's `status != verified` items.

## Reconciler detail arrays are CAPPED SAMPLES, not inventories

The machine summary's detail arrays (`board_open_work_items`, `no_id_matches`, `stuck_48h`) are
grouped and truncated — a run can print a fleet-wide `board_open_work_count` near 100 while
listing only ~20 items and zero entries for a target whose own board carries dozens of open rows.
Never conclude 'my target has no open work' from an empty detail array: attribute the fleet
counts, then read the TARGET's real open work from its own board (raw-line census + status
filter), never from the reconciler's detail lists. Also: `no_id_matches` is a list of
`{count, items, ...}` GROUPS — project through the nested `.items[]`, a flat iteration over the
groups silently reports zero target items.

## Ledger JSON shape

The ledger at `~/.hermes/stand-in/ledger.json` is `{"items": [...], "last_updated": ...}`, NOT a bare array. A naive `jq '.[] | select(.project=="x")'` or python list comprehension over the top level crashes (`Cannot index array with string` or `'str' object has no attribute 'get'`). Always access `.items` first:

- jq: `jq '.items[] | select(.project=="crier") | ...'`
- python: `data = json.load(...); items = data['items']`

The reconciler script (`ledger_board_reconcile.py`) handles this internally, but direct ledger queries must too.

## Landing the serial tick's verification in one RMW script

On a serial tick that verified a fix, the row-close is one FRESH-read RMW script run from the target workdir: re-read tasks.jsonl, edit only rows matching `id==X and status=='pending'`, keep every other line byte-identical, write `.tmp`, re-parse it, `os.rename`, then `git add <board>` + rows-only commit (co-author trailer) + `git rev-list --count origin/main..HEAD`. **After pushing, re-check the count and push the whole branch if any unpushed commits remain — the foreman's own fix commit is the one a sibling deploy/rebase can wipe, and a pushed board commit does not protect it; end every push with the count re-read to 0** (`git push origin HEAD:main` carries both commits).

## Pure-deletion stranded writes: dedupe, not data loss

A working-tree diff of `0 added, 1+ deleted` on the board is a stranded-write class of its own.
Before landing, diff each removed line against HEAD: a removed line that DUPLICATES a row
already present elsewhere in the committed board is a redundant double-append from an earlier
writer (typically a complete-row for an id the foreman already closed in its own commit), not
lost work. Land the dedupe (rows-only commit, co-author trailer, timeout >=300s in gitreins
gated repos), name the duplicated id in the commit body, and assert the surviving id set is
unchanged (parse-all-lines + unique-ids check) before pushing and re-reading
`git rev-list --count origin/<branch>..<branch>` to 0.

## DuckBrain cycle log, working shape

Build the POST body with `jq -n --arg ... > /tmp/body.json` and send it via `curl --data-binary @/tmp/body.json` with `content-type: application/json` — passing the same jq-built string through a shell variable with plain `-d "$BODY"` can hit a server-side INTERNAL_ERROR on well-formed JSON (the file-based path is the reliable form), so verify by keyed read-back before writing off the log step. Token: `~/.duckbrain/standin-pick.token`, `x-api-key` header, `POST /api/memories?namespace=coding-hermes`, key `/pm/<project>/<date>/cycle`, domain `raw_note`.

## jq per-line filters crash on non-object board lines

Guard every per-line jq filter over tasks.jsonl with `select(type=="object")` (e.g. `jq -r 'select(type=="object") | select(.id|startswith("RELEASE-")) ...'`): a board can carry bare JSON-string documents between the row objects, and `.id` on a string throws `Cannot index string with string "id"` PER LINE — the command spews dozens of errors and looks like board corruption when the parse is fine. Same guard for python: `if not isinstance(r, dict): continue` inside the line loop. The raw-line census (unique ids, thin-row detection) should skip non-dict lines silently but COUNT them and report the count.

## Reconciler --apply on an already-clean ledger: "nothing to do" is success

A prior cycle's `--apply` may have already stamped the drift_closable item, so this cycle's dry-run shows `drift_closable=0` and the `--apply` re-run exits `items_closed=0 applied=False ... nothing to do; NOT writing (exit 0)`. That is the correct outcome, not a broken tool: report the zero and move on — never force a rewrite or hand-stamp ledger statuses to make the apply "do something". (`--apply` deliberately no-ops without writing when nothing is closable, so a no-op run does not even churn the ledger file.)

## DuckBrain cycle log token fallback

Per-lane tokens under `~/.duckbrain/*.token` come and go — if the token named for the lane is missing, `~/.duckbrain/schedulerd-sync.token` is a standing fallback that POSTs fine. Plain `POST http://127.0.0.1:3000/api/memories` (no namespace query) with `domain: event` and a key like `/project/<name>/pm-cycle/<timestamp>` returns 201; verify by the 201 + read-back body, and probe with `ls ~/.duckbrain/*.token` instead of assuming one exists.

## Match the repo's test runner on the serial tick: pytest/vitest take no -short/-count

The serial-tick recipe says 'run the tests the fix commit touched with `-short -count=1`' — that is GO syntax. For a Python repo the equivalent is plain `pytest <files> -q` on the project venv (`.venv/bin/python -m pytest ...` or the repo's `uv run pytest -q`): pytest has no `-short`/`-count` flags and mangles a stray `-c` into an `-o/--override-ini` error, which reads like a broken test config but is only the wrong flag set. Extract the test files from `git show --stat <commit>`, grep for `def test_`, run those files. If the repo declares a runner (AGENTS.md Build/Test section — e.g. `uv run pytest`), use it: bare `pytest` exits 127 on a uv-only workdir with no system venv. The same runner-matching rule covers Node/Vitest repos: run the fix commit's touched test files with `npx vitest run <file...>` (vitest has no `-count`/`-short`; `run` executes once and exits — both fix-commit test files green in one invocation), and extract the file list from `git show --stat <commit>` the same way. Do not run `pnpm test` for a targeted verification: it runs the whole suite and burns the tick budget.

## A failed tick's .gitreins state is not board work

A FAILED foreman tick can leave `.gitreins/tasks.yaml` rows `in_progress` (plus other .gitreins scratch) uncommitted in the working tree. That is foreman-harness state mid-death — the harness will resume or retire it on its next tick — NOT a stranded sibling board write to land or clean. Leave it untouched; the landing rule covers rows in the BOARD files, not harness bookkeeping.

## Normalize timezones before comparing ticks-table rows to board events

`scheduler.db` ticks timestamps are LOCAL server time WITH an explicit offset (e.g. `-05:00`), while events.jsonl `timestamp` is UTC (`+00:00`). Compare them only after converting both to one zone — reading the ticks table's MAX(completed_at) against a board `task_completed` event verbatim makes hours of real same-day work look like it happened before the last tick or with no tick behind it, and reads as a contradiction when both records are simply in different zones. Convert with `date -d '<ts>' -u` (GNU date parses the offset) or python `datetime.fromisoformat` before any 'tick didn't do this' conclusion. A `failed` latest tick whose timestamp precedes board closes that landed after it is mid-flight work past the recorded tick, not starvation — the escalation trigger is a REPEATED failed tick with rows on scope, not one.

## CI red: diagnose the FIRST failing step, file the gate, not the stale row

For a `conclusion=failure` run with steps>0, read WHICH step failed before deciding what to file (`gh run view <runId>` shows the job's step list with ✓/X; `gh run view <runId> --log` shows the failing step's output). The FIRST failing gate is the actual blocker — later gates never ran, so their state proves nothing: a test-failure row stays open while a formatting gate is the red, and vice versa. Reproduce the gate failure locally (`gofmt -l .` for a format gate; capture `gofmt -d` for the row's evidence) and confirm the later gates pass locally (targeted `go test -short -run`, the repo's selfcheck) before filing — then file the gate failure as its OWN gated row with that reproduction. When an existing open row tracks a different, now-stale blocker (e.g. an old test failure the current run no longer hits), do NOT refresh it as the same failure: note in the cycle log that the old row's blocker list needs a foreman refresh, and leave editing the other lane's release row to the foreman.

## Verify an auth-gate fix CREDENTIAL-FREE first

The negative arms of an auth-header fix need no secret: probe the guarded endpoint three ways —
missing header, empty token, real token read from its env file INSIDE the script (never on a
command line) — plus a DB read-back of the field the request mutates. The 401/401/200 triad plus
the read-back proves the gate live with zero secret exposure; run it as ONE /tmp urllib script.

## Verify with the bare command, never through a tail pipe

Never judge a verification command's result through a `| tail`/`| head` pipe: the tool result shows the LAST pipeline command's status, so `make x | tail -4` reports success while the `make` itself failed (`No rule to make target`). Run the verification bare (long output auto-truncates to a saved file) or capture the code explicitly: `make x; echo "RC=$?"`. Related: a missing script path (a selfcheck under `specs/tools/`, not `scripts/`) fails the command, not the premise — locate the real entrypoint with find/grep before concluding a row premise unverified.

## Verify a generator/fixture fix through the fix commit's own test package, not by hand-driving the CLI

A wall-clock-anchored generator cannot be re-pointed at a scenario ('near midnight') by guessing flags: read the fix commit's changed files (`git show --stat <commit>`), grep each test file for `func Test`, run that package with `-count=1`, and pair with containment (`git merge-base --is-ancestor <commit> origin/main`). Hand-deriving the scenario via the CLI burns the tick on flag guessing — an unknown flag makes the binary print its usage banner and exit nonzero, which reads as a broken premise when the code is fine. To learn a helper CLI's real knobs, `grep -n 'flag.' <main.go>` beats `--help` guessing.

## Re-probing a growth-rate premise needs a per-day histogram, not one size number

A log-growth row ('X MB/day, unbounded') is verified by splitting the file's lines by timestamp (`Counter(ts[:10])` per day) so the drift rate is visible — a single `du`/`wc` reading cannot distinguish 'premise true, still growing' from 'premise stale, rate changed'. Budget the probe: a `timeout 120` on the per-line parse keeps a 200MB file from eating the tick.

## Superseded-by-a-complete-row: leave the pending originals for the foreman

A releng sweep can append a NEW complete row that explicitly declares older pending rows superseded (same-origin no-go rolled up), while the old rows stay `pending` and a rolling `updated_at` keeps them from looking stale to the reconciler. That is not a missed dedupe to force this cycle: the foreman closes/rolls the superseded rows on its own tick, and editing another lane's release rows risks colliding with exactly that close. Verify the supersede premise instead (the new row exists, is complete, names the old ids), note it in the cycle log, and leave the board untouched — the stand-down/landing rule outranks the content-dedupe pass whenever a writer is live.

## boardctl dangling-dep on mature boards

Mature boards accumulate `depends_on` refs to old spec/feature rows (CR-SPEC-*, CR-FEAT-*, RELEASE-*) where the depended-on row was completed and pruned, or references to free-text strings like `"server running"`. `boardctl validate --fail-on dangling-dep` rejects legitimate PM commits on such boards.

**Do not** run boardctl with `--fail-on dangling-dep` as a commit gate on mature boards. Use `boardctl validate` without that flag, or accept the warnings. The PM commit path should validate schema and id uniqueness, not enforce referential integrity on historical dependency chains.

To find actual dangling deps for cleanup (not as a gate):

```bash
jq -r 'select(.depends_on != null and .depends_on != []) | .id as $id | .depends_on[] as $dep | "\($id) -> \($dep)"' tasks.jsonl | while read line; do
  dep=$(echo "$line" | awk '{print $3}')
  if ! grep -q "\"id\":\"$dep\"" tasks.jsonl 2>/dev/null; then
    echo "DANGLING: $line"
  fi
done
```
