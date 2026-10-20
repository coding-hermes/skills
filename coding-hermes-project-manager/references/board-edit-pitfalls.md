# Board Edit Pitfalls (PM Cycle)

## Make the row edit BEFORE running any prepared landing script

Never run a pre-written landing/commit script (commit-message file + `git add` + `git commit` + push) before the board edit it is meant to land actually exists in the working tree. A clean-tree commit attempt prints `nothing to commit`, looks like a landing failure, and tempts a `--no-verify` retry — both attempts are no-ops and the --no-verify retry is a bypass with nothing behind it. Order: RMW edit → assert re-parse + `git diff --numstat` shows the expected shape (e.g. `1 1` for a single-row in-place edit) → only then run the landing script. `nothing to commit` after a landing attempt means the edit was never made, not that the landing failed — go back and make the edit; never escalate to --no-verify for a no-op commit.

## board_append.py argv semantics

`board_append.py <board> <json-row>...` takes JSON row **strings** as argv, not file paths or stdin. Never `echo '{...}' | board_append.py` or `cat file | board_append.py` — the script reads argv as JSON and will reject '-' or file paths as invalid JSON. For multiple rows, pass each as a separate argv: `python3 ~/.hermes/scripts/board_append.py <board> '{"id":"X"}' '{"id":"Y"}'`. Shell-quote each row to prevent interpolation.

## Verify JSONL line-wise BEFORE the rename — whole-file json.load always fails

A JSONL file is concatenated JSON objects, so `json.load(open(tmp))` raises `Extra data: line 2` on ANY valid multi-row file — a verification step built on it fails every time, AFTER tmp is written. Verify line-wise inside the RMW script, before `os.replace`: re-parse tmp with `[json.loads(l) for l in open(tmp)]`, assert count matches the input AND the specific edit (target id's new status/field) is present, THEN rename. Never verify by `json.load`. Blank separator lines are legal board content — filter with `if l.strip()` in BOTH the re-parse and the line-count assert, or a board carrying separators fails its own verification.

Also: never let the follow-up commit land without the row edit — if the RMW raises after a separate step already appended the events line, committing both files captures a task_completed event WITHOUT the row flip (board shows a completion for a still-pending row). Keep RMW, assert, rename, git add, and commit in ONE script so a mid-script failure stops the commit too; if it does split, repair with a second commit that actually lands the row flip and say so in the report.

## In-place row edits (superseded_by, status flips)

board_append.py is append-only. For metadata edits on existing rows (adding `superseded_by`, flipping status), use read-modify-write:

```python
import json, tempfile, os
rows = [json.loads(l) for l in open('<board>') if l.strip()]
for r in rows:
    if r['id'] == '<target-id>':
        r['superseded_by'] = '<completed-id>'
        r['foreman_note'] = 'PM cycle <date>: <reason>'
fd, tmp = tempfile.mkstemp(dir='<board-dir>', suffix='.jsonl')
with os.fdopen(fd, 'w') as f:
    f.writelines(json.dumps(r) + '\n' for r in rows)
os.rename(tmp, '<board>')
```

Atomic via tempfile+rename in the same directory. Always verify the edit landed: `python3 -c "import json; rows=[json.loads(l) for l in open('<board>')]; print([r.get('superseded_by') for r in rows if r['id']=='<id>'])`.

**Rewrite only the edited LINE, byte-preserve every untouched line.** A whole-file `json.dumps` re-serialization silently reformats any row whose on-disk spacing/key order differs from `json.dumps` defaults — that makes `git diff --numstat` report edits on lines you did not intend to touch, which is the exact signature auditors use to distrust a board commit. Collect the raw lines, replace only the target line with the re-serialized row, and keep all other lines verbatim; then assert the numstat shows exactly the lines you meant to edit.

## boardctl validate fails on pre-existing dangling deps

If the board has rows with `depends_on` referencing IDs that don't exist on THIS board (e.g., cross-project deps like LOGSEY-001 on a digest board), `boardctl validate --fail-on dangling-dep` rejects the commit. For board-only metadata edits (superseded_by annotations, status flips), use `git commit --no-verify` to bypass the pre-commit hook. The validation failure is pre-existing, not caused by your edit. Report the bypass honestly in the commit message. The guard-hook (battery-failure) variant of the bypass is the next section.

## jq one-liner RMW on no-heredoc surfaces (api_server)

The api_server runtime BLOCKS `python -c` and python heredocs, so the python RMW recipe above is unavailable there — do row edits and header edits with `jq` instead:

```sh
jq -c 'if .id=="<ID>" and .status=="pending" then .status="complete" | .worker_status="complete" | .updated_at="<ts>" | .resolution="<evidence>" else . end' tasks.jsonl > /tmp/tb.json
wc -l /tmp/tb.json   # MUST equal the source line count
jq -r 'select(.id=="<ID>") | .status' /tmp/tb.json   # read back the edit BEFORE cp
```

- ALWAYS `jq -c`: bare `jq` pretty-prints, turning one-row-per-line JSONL into thousands of lines and silently corrupting the board if copied over. `wc -l` equal to the source plus the status read-back are the two asserts before `cp` replaces the board.
- Board hygiene rows (stale `board.jsonl` header: `last_commit` behind HEAD, `last_tick` behind recent board commits) are PM-OWNED — fix directly with the same jq pattern on `board.jsonl` (`jq '.last_commit="<head-sha>"' board.jsonl > /tmp/bh.json`), commit the header refresh, close the row with that commit as evidence.
- Verify every push by `git ls-remote origin <branch> | cut -c1-8` matching local HEAD's short sha — a push command's exit or output tail is not proof.
- Before leaving a row pending as 'not yet fixed', check whether work landing AFTER the row was created already satisfies part of its premise (grep the cited file/line at HEAD): a fix may have added the documentation/config the row asks for, narrowing the row to what still stands — note the partial satisfaction in the report instead of treating the row as untouched.

Tokens are named per-purpose, not per-project. Check `ls ~/.duckbrain/*.token` for the right name (e.g., `fleet-cost-digest.token` not `digest.token`). If no matching token exists, skip the DuckBrain log step and report it honestly — don't fabricate a token path or guess the name.

## G7 dedupe: supersede, don't delete

When a pending row is a content-duplicate of a completed row, annotate `superseded_by: <completed-id>` in-place (via the read-modify-write pattern above), don't delete the duplicate. Deletion loses the audit trail of why the row was filed; supersession preserves it. The foreman's pick step should skip rows with `superseded_by` set.

## Landing a stranded board write: toplevel-relative pathspecs

Resolve `git rev-parse --show-toplevel` BEFORE staging — a lane workdir can sit INSIDE a larger checkout (toplevel is a parent of the project dir; board paths are prefixed `<project>/`), so a `git add` run from the project dir either fails the pathspec or stages the wrong scope. Run the whole landing script from the toplevel and use toplevel-relative paths consistently in `git add`, the staged-numstat assert, and the read-back (`git show HEAD:<prefixed-path>`). Keep the pre-state read (`git log -1`) in the same script so a sibling commit landing mid-landing is visible in the output.

## Event-shaped lines misplaced in tasks.jsonl

Alert-router and other injectors can append EVENT lines into tasks.jsonl instead of events.jsonl — they parse as JSON but carry no `status` key and event-shaped keys (`type: alert-resolved`, `endsAt`). Detect before editing: flag rows whose keys are event-shaped or whose `status` is null/absent. Relocate them BYTE-IDENTICAL to events.jsonl (never re-serialize), skipping ids already present there, and fold any duplicate `-RESOLVED` twin ROWS (same id as the misplaced event) in the SAME RMW pass — the twins are the event content re-filed as rows. Post-write asserts, both files: duplicate-id census clean, line accounting exact (`out + folded == original`), every line re-parses, then land as one rows-only commit. Expect `git diff --numstat` to show `N added / 0 deleted` on events.jsonl and `N deleted / 0 added` plus edits on tasks.jsonl — anything else means a byte changed somewhere it should not have.

## A transient index.lock blocks the landing — check, then retry once

`Unable to create '<toplevel>/.git/index.lock'` with exit 128 on the first `git add`/`git commit` is often a transient lock from a JUST-FINISHED sibling git process, not a crashed one: check `ps aux | grep -E 'git (commit|add|merge)'` for a LIVE process and whether the lock file still exists. No process + no lock file = safe to retry the identical command unchanged; do not delete the lock preemptively and do not re-plan the edit.

## Guard-hook commit block vs validation block — the --no-verify discipline

A tier-1 battery failure (test red, or the battery's own timeout) blocks the commit and leaves the edit STAGED with HEAD unmoved — the file change is not lost, only the commit is blocked. Surface details lie twice: a runbook foreground timeout may actually be the hook still running (terminal foreground calls die at ~180s even under a larger timeout_s — run the commit in the background and wait on the process), and a nonzero exit carrying the guard FAIL text is the hook's real verdict, not a lost command. Re-check `git diff --cached --name-only` before retrying so you know exactly what is staged.

Then decide the bypass: for board-only/annotation commits, `git commit --no-verify` is sanctioned when the failing gate is (a) pre-existing (see dangling-deps above) or (b) a known load-headroom defect that a fix worker is ALREADY dispatched on — verify the staged set is the board file ONLY, disclose the bypass in the commit body with the failing row id and the live defect evidence (e.g. loadavg at the moment), push, and prove containment on the remote (`git log -1 origin/<branch>`). NEVER --no-verify a diff that touches product code, and never bypass a gate that guards YOUR change.

## Closure shape, row premises, hunter verdicts (relocated cycle-note rules)

- **Determine the closure edit shape from the board's id-uniqueness, not from the fold doctrine.** The 'append a superseding line' rule is correct only on a true append-log board (per-id multiple lines, keep-last resolution). On a board that carries ONE line per id (boardctl refuses ambiguous-id writes, so writers dedupe in place), a closure is an IN-PLACE line edit — status flip plus evidence on that single line; appending a second copy of the id leaves the original line unchanged, which the post-write `unique_ids == lines` assert correctly rejects. Probe the shape before writing (`jq -r '.id' <board> | sort | uniq -d | wc -l` → 0 means one-line-per-id), and expect the post-write numstat to read `1 1` (one modified line), not `1 0` (an appended line), on a one-line-per-id board.
- **A row whose `detail` carries only a content fingerprint has no evidence command — the title IS the premise.** Satellite-produced rows (dogfood/qa gatherers) frequently store `detail` as `{fingerprint: ...}` with nothing else. Verify the title's claim directly with a real command against the repo and record the command + result in the cycle log; never file such a row as unverifiable (the fingerprint makes it verifiable — against the title, not a detail field that does not exist) and never skip it as unreadable.
- **Re-test a row's blocked_reason every cycle the row is revisited — a blocker is a premise like any other.** Sanctioning paths land between ticks (a protected-file sync script gets a proven use, an approval gate gets a documented bypass): verify the blocker's own claim with a real command before leaving the row parked, and when the blocker is gone, unblock WITH fresh evidence in the same edit rather than re-minting a sibling row.
- **Hunter verdicts are claims, re-verify them.** A hunter flagged a board row `STALE-FALSE` from the script it grepped, but the row was about a *wrong* token while the harness only fingerprints the token *source* — the premise was still true. Read the row's own `detail` and check exactly that claim before retiring it; keep the row and say why in the report when the hunter overreached.
- **Match the RMW id-selector to the board's actual serialization.** A grep/string-match edit keys on the RAW line, and raw lines vary in key spacing (`"id": "X"` vs `"id":"X"`) — a selector matching one variant silently replaces nothing. Read the target line's raw text before writing the selector and match BOTH variants (or parse-then-compare); an assert that the replacement count is exactly 1 catches the miss before the swap. A no-op replacement that still "succeeds" ships an unchanged row as an edit.
- **A per-line re-parse loop needs a no-op body shape that passes lint and the harness.** `for x in [...]: pass` is the canonical form — a bare `for ... :` on one line fails compile, and an expression-statement body can trip lint gates before the commit.
- Cycle-log POST status rules (break on any 2xx — 201 is Created, not 200; a 429 = rate limit, back off and retry the SAME script, never probe more token candidates; duplicate-copy cleanup by record DELETE): references/duckbrain-cycle-log.md.
