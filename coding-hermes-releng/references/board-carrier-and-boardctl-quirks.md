# Board-carrier chain and boardctl quirks (task-router releng lane)

## boardctl write flags that refuse one at a time

`create`/`update` evidence flags are a chain: `--evidence-artifact` refuses without `--evidence-fingerprint`, which refuses without `--evidence-run-id`. Read the three together from the refusal text and supply all of them in the first populated call; iterating refusal by refusal costs one wasted invocation per missing flag and each refusal leaves the board untouched but the tick older.

`create` and `update` accept DIFFERENT flag sets, so a row filed and closed in one call is impossible and attempting it costs a dead invocation: verification and close-out flags (`--worker-status`, `--guard`, `--ci`, `--summary`, `--note`, `--status complete`) are update-only, while `create` owns `--id`, `--title`, `--type`, `--priority`, `--complexity`, `--reasoning`, `--acceptance-criteria` plus the evidence chain above. File the row with create's complete surface first, then complete it with update's complete surface — two populated writes, each whole on its own — instead of retrying `create` with successive subsets of terminal fields.

Where they land: `detail.evidence[]` entries of `{run_id, ts, tree_fp, artifacts}`, not the row's top-level `evidence`. Reading `evidence: null` after a successful create means the shape moved into `detail`, not that the write failed — check `jq '.detail'` before retrying. Re-issuing the same flags through `update` appends a duplicate entry with a new `ts`; dedupe on `(run_id, tree_fp)` inside the one row's line, prove the rewrite with a `+1/-1` diff and a line count, and re-run `boardctl validate`.

IDs: `next-id --family <FAMILY>` answers a counter (`FAMILY-001`, `max: -1`, `width: 3`) even on a board whose rows are `FAMILY-YYYY-MM-DD-NN`. Supply `--id` from the lane's existing convention and confirm the new id does not already exist in the tip's `tasks.jsonl` before writing.

## Plain `tasks.jsonl` boards without boardctl: append via the fleet helper

Not every project board has a boardctl vocabulary — some are a bare `.coding-hermes/board/tasks.jsonl` (often a symlink to the lane's live board). Write those with the fleet helper, one argv word of JSON:

```
ROW=$(jq -cn --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{id:"RELEASE-<date>-NN",title:"...",priority:"P2",status:"pending",
    created_by:"<lane>",created_at:$now,updated_at:$now,branch:"",commit_hash:"",
    complexity:"",worktree:"",capability_tags:[...],foreman_note:"...",
    acceptance_criteria:"...",detail:{artifact:...,artifact_sha256:...,evidence:"..."}}')
python3 ~/.hermes/scripts/board_append.py .coding-hermes/board/tasks.jsonl "$ROW"
```

It prints `APPENDED=1 PRIOR=<n> TOTAL=<n+1>`; anything else means read the helper's refusal instead of retrying.

- Mirror the key set of an existing row in the same family (`jq -c 'select(.id|startswith("RELEASE"))' tasks.jsonl | tail -1`) rather than inventing fields: a row missing shared keys still parses but drops out of the selectors other lanes use to find work.
- Derive the free id from the board itself (`jq -r 'select(.id|startswith("RELEASE-<date>"))|.id'`), not from an id-minting helper — QA-style scripts in the fleet run their real action on `--help`.
- Prove the write in three ways in one call: `git diff --numstat` shows `+1` on the board with no `-` lines, `jq -r 'select(.id=="<id>")|[.id,.status]|@tsv'` reads back the status you set, and `tail -c 1 tasks.jsonl | xxd` confirms the trailing newline survived so the next append does not concatenate onto the last row.
- Build payloads with `jq -cn`, never a shell heredoc or hand-escaped quotes: `$()` and backticks inside a quoted argv word are expanded by the shell, and a truncated JSON row is accepted by the file and rejected by every reader.

## `boardctl event --detail @file` stores the file as a STRING

`event` does not parse the `@file` payload the way `create --evidence-artifact` does: a valid JSON object is stored as a JSON *string* on the event. The append still succeeds and `validate` still reports `OK`, so the only symptom is a query failure — `jq '.detail.<field>'` aborts with `Cannot index string with string "<field>"`, and a later `jq -c 'select(.id==N)'` over the whole file dies on the first string-shaped event in the file, not on yours. Expect the stringification and repair the line you just wrote; do not conclude the write failed and re-append, which leaves a duplicate event.

Repair ONLY the last line. Never re-serialize the whole file with a single jq pass: that reformats every legacy line the board's tolerances depend on and turns a one-line fix into a full-file diff.

```
F=.coding-hermes/board/events.jsonl
N=$(wc -l < "$F")
head -n $((N-1)) "$F" > "$SCRATCH/events.fix"
tail -n 1 "$F" | jq -c 'if (.detail|type)=="string" then .detail = (.detail|fromjson) else . end' >> "$SCRATCH/events.fix"
cp "$SCRATCH/events.fix" "$F"
```

Prove it with two facts, not one: `wc -l` unchanged, and `git diff --stat` showing exactly `1 insertion(+)` — the second proves every earlier line reproduced byte-identically. Then re-read the field with a type guard.

Query boards defensively, because they accumulate both shapes. `jq 'select(.id==N) | .detail.pass'` aborts the entire query when any scanned event holds a string detail; gate the access instead: `jq -c 'select(.detail|type=="object") | select(.id==N) | .detail.pass'`.

Event `id` is a counter, not a line number. `wc -l` and the appended `id` diverge (the counter skips gap and legacy ids), so a query filtered to the line count you expect finds nothing while the event is in fact present. Read the appended record with `tail -1` and confirm its `id`, `event_type`, `task_id`, and detail shape there. The field names are `event_type` and `timestamp`: a readback of `.type` or `.ts` returns `null` on this shape — including on events the writer itself just minted — so a `null` there is a wrong key, not a dropped write. Project the four keys you know exist before deciding anything failed:

```bash
tail -1 <board>/events.jsonl | jq -c '{id,event_type,task_id,kind:(.detail|fromjson?.kind)}'
```

Check `boardctl event --help` before using narrative or tick flags: the installed build can reject a flag whose behaviour the help text documents (`--narrate-text` and `--tick` have both drifted). When a narration flag is unavailable, put the narrative in the commit message body, which is durable and readable without the board, rather than dropping it.

Long prose fields survive shell quoting when staged as files: build `reasoning.txt` and `acceptance.txt` with the file writer, then pass `--reasoning "$(cat …/reasoning.txt)"`. Do not inline multi-line prose into the command line — the evidence artifact path belongs in the reasoning text as well, since the artifact pointer alone is not readable by the foreman.

## The carrier chain only terminates if you stop writing

Every board push to `main` mints a new CI run (~36 min on task-router). "Refresh the row once the carrier is green" therefore regresses forever: the certification commit becomes the next uncertified carrier.

Rule: decide the LAST board commit up front. Refresh the rolling row once with the run ids you already hold, push it, then poll only that carrier's run to terminal and stop. Deliver on that green run rather than committing the certification. Never set `board_carrier` to the previous tip and push a new commit to make it current: the write immediately invalidates its own claim. Omit final-carrier metadata from the tracked payload and bind it externally through the remote commit containing the row plus the exact-SHA hosted run. Keep historical CI receipts explicitly paired with their evaluated SHA. Cite the whole chain (pre-write candidate, intermediate carrier, delivering carrier) with each SHA's own terminal conclusion, e.g.

- `5f5f1129` — run 42630703946, terminal success
- `6edfd8cf` — board/evidence carrier, run 42708695233, terminal success 22:42:05Z
- `6547421b` — delivering carrier, run 42714310424, terminal success 23:19:11Z (36m21s)

Do not claim green for a carrier whose run is still `in_progress` — cite the run id and say in-flight.

Bind the run to the carrier by head SHA prefix, never by recency. A sibling lane pushes within
seconds, so `--limit 1` or "the newest run" certifies someone else's commit:

```bash
for i in $(seq 1 20); do R=$(gh run list --repo <org/repo> --limit 5 \
    --json databaseId,headSha,status,conclusion \
  | jq -r '.[] | select(.headSha|startswith("<carrier-short-sha>")) | "\(.databaseId) \(.status)/\(.conclusion)"');
  if [ -n "$R" ]; then echo "$R"; case "$R" in *completed*) break;; esac; fi; sleep 15; done
```

An empty result is the honest answer while the run has not registered yet — do not substitute
the previous carrier's green run for it. Use the full 40-character SHA for `gh run list --commit`;
when that lookup is empty, filter the unfiltered recent list by exact `headSha` and cross-check
commit check-runs before declaring absence. Resolve and validate a nonempty run ID in a separate
step before calling `gh run view` or `gh run watch`; do not embed an unchecked lookup in command
substitution, because an empty result invokes the command without its required ID.

## A board carrier's diffstat reads 0/0, and that is not an empty commit

Board and event JSONL are commonly marked `-diff` (or `binary`) in `.gitattributes` so review
surfaces do not render them. A commit that lands a task row or an audit event therefore reports
`N files changed, 0 insertions(+), 0 deletions(-)`, and `git show --stat` of a real carrier looks
exactly like an aborted no-op — the shape that makes a lane re-commit and duplicate its write.

Never judge a board carrier by diffstat. Assert the payload inside the committed tree:

```bash
git show <sha>:<board>/events.jsonl | grep -c '<event-id>'        # exactly 1
git show <sha>:<board>/tasks.jsonl \
  | jq -r 'select(.id=="<ROW>") | "\(.status) note_len=\(.foreman_note|length)"'
git cat-file -e <sha>:<board>/events.jsonl; echo "exists=$?"
```

When the ids, rows and byte counts are present the commit is complete — report the masked diffstat
as a gitattributes artifact rather than redoing the write.

## `boardctl` write quirks

- `update --note` **appends** to `foreman_note`; it is a rolling audit log that grows past 20k chars across ticks. It does not replace. Verify with a marker count — `jq '[.foreman_note|splits("MARKER")]|length-1'` must equal 1.
- A `null` at `.foreman_note`, or a `detail` object whose only keys are `["evidence","fingerprint"]`, is NOT evidence that the writer dropped the note: the note can live in a different physical occurrence of a duplicated id, under another key, or in a row image you captured before the write. Locate the payload by VALUE before concluding anything — `jq -c 'select(.id=="<ROW>")' <board> | grep -cF '<distinctive fragment>'` — and dump the row's real keys with `jq -r 'select(.id=="<ROW>")|keys[]'` instead of asserting a field name you guessed. Do not tell a delivery that "the writer replaced my note" until a value-level search of the COMMITTED tree comes back empty; an unverified claim about the writer is worse than an unverified field, because it sends the next reader hunting a defect that may not exist.
- Some rows carry a `title` that is not a string (legacy rows written by an older writer). Any `jq` expression that does a string operation on it dies — `.id + " " + .title`, `test()`, `ascii_downcase` — and because a `select` pipeline aborts on the first bad row, a verification that should print five rows exits 1 with no output. Coerce instead of trusting the field: `jq -c 'select(.id|tostring|test("^RELEASE-02[4-8]$")) | {id, status, title: (.title // "" | tostring)}'`, or filter with `select(.id == "<ID>")` and read only the fields you need. A reader-side crash is not board corruption and needs no repair row; `boardctl validate` legitimately still reports OK.
- `next-id --family RELEASE` returns a bare `RELEASE-001` and ignores the `<FAMILY>-YYYY-MM-DD-NNN` convention the rows actually use. Grep the board for existing same-day ids and construct the dated id by hand. A non-zero exit from `next-id` changes nothing about that procedure: it is not evidence the board is broken, so construct the id and pass it explicitly with `create --id` rather than abandoning the write or hand-editing JSONL.
- `--acceptance-criteria`, `--reasoning` and `--note` pass through the shell: `$(...)` and backticks are command-substituted, so a criterion quoting a command in backticks does not merely truncate — the command EXECUTES and its output is stored where the criterion was, leaving a row that reads as plausibly written while carrying program output instead of a contract. Write plain text (`VENV_PY (.venv/bin/python)`, not `$(...)`) and stage long criteria as `--acceptance-criteria "$(cat <file>)"`; after any write whose payload quoted shell metacharacters, re-read the stored row and look for stray command output before committing.
- Before using the bundled row-repair helper, inspect the target row's actual top-level keys and dry-run the entire payload: it refuses added top-level keys, even optional ones. If a blocker field is absent, use an existing supported field or an explicitly sanctioned writer; do not claim a nested field updates an existing top-level blocker. After any create/update, re-read the row (`boardctl show <id>`) and confirm the criteria survived intact before committing. Also inspect the candidate, carrier, decision, `detail.evidence[-1]`, and note marker; a writer can append empty/stale evidence entries while exiting successfully, so validate the stored shape rather than trusting its status line.
- Commit board + evidence only; leave a sibling lane's `.gitreins/tasks.yaml` change unstaged. Read the committed tree afterwards — `git show <carrier>:<board> | jq` — because the guard verifies the working tree, not the commit.
- The lane's pre-commit guard reports `deleted task rows: N` for an ordinary row rewrite: a `1 1` line change reads to it as one removal plus one addition. That is not row loss — prove it with `wc -l` on both sides plus a readback of the target row, and never revert a good carrier to silence the counter. Row-count integrity is a `wc -l` comparison, not an interpretation of the guard's wording.
- `update` takes the row id **positionally** (`boardctl update RELEASE-<n> --status complete …`); `--id` is rejected with `flag provided but not defined: -id`. The flag sets differ between verbs, so read `--help` or probe on a scratch board copy instead of guessing — every rejected form costs a round trip.
- `show` has NO machine-readable flag: `boardctl show <ID> --json` is refused with `flag provided but not defined: -json`, and the verb accepts only `[--events] [--skip-bad-lines] [-C dir]`. When a report needs VALUES rather than prose, read the row from the file (`jq -c 'select(.id=="<ID>")' <board>`) or use the row helpers — do not spend a retry guessing at a `--json`/`-o json` form.
- The `create` flag set is NARROWER than `update`'s, and the refusals read as if the whole payload were invalid. `--blocked-reason` exists only on `update`, and there is no `--detail` flag on this build at all; prose metadata goes in through repeatable `--meta k=v`, which lands as `detail.metadata.<k>` beside a writer-minted `detail.fingerprint`. So an owner-gated row is TWO calls, staged as one payload: `create --status blocked` (the status vocabulary is `{blocked,complete,failed,pending,in_progress,review}`) and then `update <id> --blocked-reason "..."`. Probe the refusals instead of iterating them on the live board — `create --status bogus` prints the accepted set in one line, and `--type` is a closed list too (`bug,chore,feat,task`); there is no `release` type, so release rows are `task` with a `RELEASE-*` id.
- A `***` in a readback is usually the OUTPUT filter, not a corrupted store. A row title or acceptance criterion containing a word the transport redacts reads back as `no *** and no Release`, which looks exactly like a writer that mangled the payload — and rewriting it "to repair" duplicates the field on a write that was correct. Verify the stored bytes before reacting: `jq -r 'select(.id=="<ID>")|.title' <board> | od -c | head -3`, or assert the CHARACTER COUNT you intended. Only a mismatch in the raw bytes is a bad write.
- **A row's surfaces disagree after an `update`, and the DETAIL is the one a dispatcher believes.** `update` rewrites the top-level fields it is handed (`title`, `blocked_reason`, `foreman_note`, `updated_at`) and leaves the structured `detail` OBJECT exactly as it found it. Retitling a rolling row to a new pass therefore produces a row whose title advertises pass N and candidate X while `detail.pass`/`detail.candidate` still name pass N-1 and a superseded SHA — and a reader who opens the detail implements against the old candidate while every write-level proof (exit 0, `updated_at` moved, one line changed) passes. After retitling across a pass, rewrite `detail` in the SAME commit (row helper, or the `+`-merge line splice below) and assert the surfaces agree before staging:

```bash
jq -r 'select(.id=="<ROW>") | "detail pass=\(.detail.pass) candidate=\(.detail.candidate[0:8])"' <board>
# must equal the pass and candidate the title and note advertise
```

Correcting only the prose is a lying row, not a refresh: the fix is a content rewrite of the target's `detail`, proven by one changed physical line and no other row touched.
- `create` accepts `--id --priority --complexity --title --reasoning --acceptance-criteria`; it rejects `--created-by`, `--description` and `--acceptance`, and it does **not** populate `created_by`/`description`. `--acceptance-criteria` is the free-text contract a foreman dispatches against — it is the field that makes a row actionable, so write it as executable clauses (path, command, expected exit) rather than a goal statement; the structured `acceptance` ARRAY stays empty after a `create`, which is the normal shape and not a dropped write, so never hand-append one to "repair" it. Where the board validator treats those as fatal on P0/P1 rows, a bare create reddens the default branch: create, then patch the physical row's evidence body, run the validator, and only then push.
- `create` writes TWO files: the row into `tasks.jsonl` and an event into `events.jsonl`. Stage both, or the carrier ships with a dirty event file that the next directory-wide `git add` by any lane publishes under someone else's message. After a create, `git diff --text -U0 -- <board>/events.jsonl | grep '^+'` returning lines means amend before pushing (`git add <board>/tasks.jsonl <board>/events.jsonl && git commit --amend --no-edit`), Then re-check `git rev-list --left-right --count origin/<branch>...HEAD` still reads the single commit you intended.

**An inherited orphan event is published, never discarded.** A prior pass can land its row change and leave the paired event uncommitted in its worktree: the row is canonical on the remote while the event exists only in a scratch checkout no lane will ever push again. On entering a REUSED worktree, sweep `git status --porcelain` and diff the board files before composing anything — an uncommitted `events.jsonl` hunk whose row change is already present in `origin/<branch>` is inherited residue, not your write. Publish it byte-identical inside the next evidence carrier and name its provenance in the commit body (which pass minted it, why it was orphaned), rather than deleting it or narrating it as your own write: the event is the only audit trail for a change that already shipped, and rewriting it would misrepresent the pass that produced it. Prove it landed the usual way (`git show <carrier>:<board>/events.jsonl | grep -c '<event-id>'` equals 1) and confirm the re-publication left the row itself untouched.
- The three evidence flags are all-or-nothing, in both directions: `--evidence-artifact` is refused with `boardctl: --evidence-artifact requires --evidence-fingerprint`, and a fingerprint without a run id is refused too. Supply the whole triple or none. The fingerprint is the SHA-256 of the durable artifact BYTES (`FP=$(sha256sum <artifact> | cut -d' ' -f1)`), not the candidate commit SHA — and `create` validates only its FORM: anything that is not exactly 64 hex characters is refused outright (`boardctl: evidence fingerprint "<value>" must be exactly 64 hexadecimal characters`), so a 40-char commit or tree object id never gets stored at all, while a tree-listing hash (`git ls-tree -r --full-tree <sha> | sha256sum`) or any other 64-hex value is accepted just as readily. Format-valid is not content-valid: A successful create proves the flag was supplied and nothing about what the digest describes; derive the value from the artifact bytes only, and if a tree hash was stored, call it a tree hash in the correction note instead of reporting it as the artifact digest. It is also never the row's own `detail.fingerprint` — that dedup hash stores into `tree_fp` and then reads back as release-tree provenance it does not represent. If it is already stored, append a correction-of-record note to `foreman_note` naming exactly what the field is and binding the real artifact hash and run id: notes are append-only, so the correction lives beside the error instead of erasing it. Where a row must be filed before any hosted run for it exists, file it plain and attach the triple on the closing `update`, or stage the artifact, hash it, and cite a run you actually hold.

Order the two writers so the correctly LABELLED shape is the one that survives. `boardctl update` is what mints `updated_at` and the audit event, and it is also what stores the supplied fingerprint into an evidence entry's `tree_fp`; the row helper mints neither. So call `boardctl` FIRST with the scalar fields and CI receipt, then write the authoritative `detail` object with `board-row-set-json.py` LAST, carrying `tree_fp` (the tree-listing hash) and `artifact_sha256` (the artifact bytes) as separate keys. Inverting the order makes the helper's correct object the one that gets overwritten; skipping the helper leaves a row whose structured evidence calls an artifact digest a tree fingerprint. Verify after both calls that `.detail.evidence[-1]` shows the two hashes under their own names and that `updated_at` still equals the value `boardctl` stamped.

**Receipts with no writer flag go in through an INDEXED dotted path.** `head_sha`, a CI-run receipt and a fire label have no `boardctl` flag at all — the evidence triple writes only `run_id`, `ts`, `tree_fp`, `artifacts` — so an entry minted that way names its artifact but cannot say which commit or run it binds, and the next reader has to trust prose. Set them on the LIVE row immediately after the `boardctl` call, using the row helper's list-index syntax (a segment written `<key>[-1]` addresses the list's last element):

```bash
S=<skill-dir>/scripts/board-row-repair.py
python3 "$S" <board>/tasks.jsonl <ROW> \
  --set 'detail.evidence[-1].head_sha=<40-hex>' \
  --set 'detail.evidence[-1].ci=success (run <id>)' \
  --set 'detail.evidence[-1].fire=b'                        # dry run
python3 "$S" <board>/tasks.jsonl <ROW> --set '…' --write    # same sets, applied
```

The dry run prints `row <ID> at line N/M` plus `changed keys: detail`; the apply prints `WROTE <file>`. Prove `git diff --numstat <board>` reads `1 1` with `wc -l` unchanged, then read the entry back (`jq -c 'select(.id=="<ROW>") | .detail.evidence[-1]'`): `head_sha`, `ci` and `fire` present, and `tree_fp` still whatever the evidence flags stored there.

**An `update` does not always append an audit event.** On some boards `update` rewrites the row, stamps `updated_at` and appends the note while leaving `events.jsonl` untouched — the counter has NOT advanced, and the record of WHY the row moved exists nowhere unless you append it. Read `tail -1 <board>/events.jsonl` after every update; when no new event names your row and tick, append one (`event --type audit --task-id <ROW>` carrying the delta) and prove it by id (`jq -c 'select(.id==<n>)|{id,event_type,task_id,actor}'`). Never report an audit event as filed because the update exited 0.

**Prove a duplicate event id is not yours before repairing anything.** A `group_by` uniqueness probe over a long-lived board routinely flags a legacy id — two lines sharing the same number, which `validate` tolerates as benign legacy state while still ending `RESULT: OK`. Run the SAME query against the fetched remote copy and only repair what you introduced:

```bash
git show origin/<branch>:<board>/events.jsonl \
  | jq -s 'map(.id)|map(select(type=="number"))|group_by(.)|map(select(length>1)|.[0])'
```

A duplicate present in that output pre-dates the pass: report it as inherited, name the `validate` warning text, and do not "fix" a counter other lanes own.
- `--status complete` is refused while no judge run exists for that row. When none does, mint one in the same checkout: `gitreins task create <ROW>-CLOSE "<title>" "<criteria>"` → `gitreins task start <ROW>-CLOSE` → `gitreins judge <ROW>-CLOSE` (the CLI verb is `judge <task-id>`; `judge evaluate` is an MCP tool name, not a CLI subcommand). Do not read the id off the console — that line is routinely swallowed and a wrong id is refused as `--evidence-run-id "<id>" is not an existing directory under .gitreins/history/`. Resolve it by content:

```bash
grep -rl '<ROW>-CLOSE' .gitreins/history/*/*/verdict.json     # -> .gitreins/history/<date>/<hash>/verdict.json
# evidence id = <hash>, the JUDGE RUN dir; not the task id, not a GitHub Actions run id
```

Then `--evidence-run-id <hash>` closes the row. Pass the BARE directory name: the `date/<hash>` path you just grepped is refused with `--evidence-run-id "<date>/<hash>" must name a directory under .gitreins/history/`, which reads like "wrong id" when the id is right and only the FORM is wrong — strip it to `<hash>` and retry rather than re-minting the judge run. `gitreins task complete <ROW>-CLOSE` afterwards flips the task record but leaves `.gitreins/tasks.yaml` dirty — commit and push it, or the remote copy still reads the task as in progress. Blanket the whole leg into one rule: the row's evidence id, the gitreins task id, and the hosted CI run id are three DIFFERENT IDENTIFIER SPACES and the board accepts only the first, in bare-hash form. Each rejection names the space it wanted, so read the refusal instead of cycling guesses across all three.

**A repo with no `.gitreins/config.yaml` has no exact-SHA judge path at all.** `gitreins task create` cannot run there, so a row that demands judge evidence on the exact commit is unsatisfiable in this checkout. Do not fabricate a run id and do not hand-set `complete`. When a verdict exists on a tree that CONTAINS your commit, close with that run id only if you can prove the containment (`git merge-base --is-ancestor <commit> <verdict-tree>` or the row's own commit is that tree), and write the substitution rationale into `review_notes` — acceptance criteria routinely demand the rationale live in a named field, so a rationale that exists only in a commit message fails the row. Say in the delivery that the evidence is a substitute on a containing tree, not an exact-SHA verdict. Write criteria as FACT-ONLY assertions the judge can re-derive from the tree (paths, hashes, counts, exit codes) — self-narrated process claims fail on things outside the diff. A judge PASS that independently re-derives your residual claim is the strongest receipt to quote in the row.

**`--force` does not lift that binding.** Retrying a refused `--status complete` with `--force` returns the identical refusal: the check is `--evidence-run-id` resolving to an existing directory under `.gitreins/history/`, not a soft warning. When no judge run can be minted in this checkout (the unattended command gate can decline the probe outright, and a verify-only lane is not the row's owner), do not fabricate a run id, do not hand-edit the row to `complete`, and do not stonewall the tick. Park the row and hand the closure over:

```bash
boardctl update <ID> --deferred true \
  --defer-reason "PREMISE SATISFIED re-measured <ts>; closure blocked: no .gitreins/history/<run-id> dir for this lane" \
  --defer-review-by <date> \
  --note "<per-clause measurements with commands+results>; artifact=<repo-relative path> sha256=<hex>"
```

A deferred row carrying a fingerprinted PASS receipt is honest, dispatchable state; a forced completion is the debt the evidence gate exists to catch. Say in the report that closure was deferred rather than met, and why.

A row whose evidence is a HOSTED CI run has no `.gitreins/history` entry, and passing the Actions run id as `--evidence-run-id` fails as `"<id>" is not an existing directory` — the two id spaces never meet. Do not fabricate a judge run to close a CI row. Either mint `<ROW>-CLOSE` whose criteria are facts a judge can re-derive from the TREE (paths, exit codes, version stamps, byte counts) — never "the hosted run at <id> is green", which the judge cannot reach — or park the row with the run ids in a `--note` and file the remaining work as its own row. The commonest instance is a CI-blocker row whose premise the new run DISPROVES: annotate the disproof with both run ids and the exact steps that executed, then put the downstream work (here, publishing) in a fresh row so the stale blocker stops being re-litigated every pass.

The fingerprint is bare hex — pass `$(sha256sum <artifact> | cut -d' ' -f1)`; a `sha256:` prefix is not accepted as the value.

- A NESTED field (a count or note living inside `detail`) is not addressable by the CLI or by a dotted `--json` name. Use the row helper, but pass the whole sub-object: extract it (`jq -c 'select(.id=="<ROW>") | .detail' > <scratch>/det.json`), mutate append-only (`jq -c '. + {raw_count: 39}'`) and hand it back with `--json detail=<scratch>/det.new.json --write`. Adding an unknown top-level key instead aborts with `ABORT: top-level key order changed; refusing to rewrite a row whose shape moved`; an append-only `+` preserves key order, while building the object from `{}` reorders it and trips the same guard. That mechanism is the fallback when the ADDED key is genuinely required and no writer exposes it: splice the single line with a `+` merge on the ORIGINAL parsed object, which appends the new key at the end and leaves every existing key in place — `jq -c --rawfile n <textfile> '. + {review_notes:$n}' row.orig.json` — then substitute that one line into the file, keeping every other line byte-identical (backup first, `awk` swap on the located line number, assert `wc -l` unchanged and `git diff --numstat` equal to the touched line count, then `boardctl validate`). A `+` merge that only ADDS a key is shape-stable; anything that rebuilds, sorts or re-serializes the object is not.
- Release authorization is a STRUCTURAL fact, never a phrase match. Grepping row titles for `RELEASE-cut` returns the NO-CUT record that denies one (its own text states no such row exists), so a substring count reports 1 authorization where the true number is 0. Decide from the row's status/fields, and say "0 authorization rows" with the count method named. Filter with `.title?` while doing it — legacy rows carry `title: null` and a `test()` on it throws, killing the whole select pipeline so the query prints nothing at all.
- A `P0`/`P1`/`P2` literal inside a row's `title` feeds the validator's priority-consistency check, so a P2 row whose title narrates another row's `P0` reads as a priority mismatch among the `validate` warnings. Keep severity out of titles: name the other row's id, or describe it as `top-priority`. Never downgrade or raise the row's own `--priority` to silence a warning that came from prose.
- An event you append to CORRECT a prior event must be a new event with its own type and a `corrects_event` field naming the id it withdraws — append-only, never an edit of the prior line. Re-read the stored shape afterwards: `events.jsonl` stores `detail` as a JSON-encoded STRING, so `jq -r '.detail|fromjson|.corrects_event'` (or `try fromjson catch .`) is the projection that works.

## A correction that changes only `updated_at` never happened

The row editor's dry run reports what it will WRITE — the keys it touches and the new character count — not whether the value differs from what is already stored. Rewriting a row with identical text therefore prints `changed keys: reasoning; reasoning: N chars`, exits 0 on `--write`, and lands as the expected one-removed/one-added physical line. Every write-level proof passes while the content never moved, and a carrier whose message promises a correction ships only a new `updated_at`.

Compare the VALUE before writing, then prove the FIELD across the two revs after:

```bash
F=<board>/tasks.jsonl
[ "$(jq -r 'select(.id=="<ROW>")|.<field>' $F)" = "$(cat <scratch>/<field>.txt)" ] \
  && echo IDENTICAL-DO-NOT-WRITE
git show <rev>~1:<board> | jq -c 'select(.id=="<ROW>")|{updated_at, <field>}' > a.json
git show <rev>:<board>   | jq -c 'select(.id=="<ROW>")|{updated_at, <field>}' > b.json
diff a.json b.json && echo IDENTICAL-FIELD
```

Command substitution strips one trailing newline on both sides, so a payload file ending in `\n` compares equal to `jq -r` output — a one-byte difference between the written char count and the file size is not a mismatch and needs no repair.

When the diff shows only `updated_at`, the correction did not happen. Do not quietly rewrite the row a second time: it now carries a premise the next pass inherits and reports as fact. Replace the annotation in place with an explicit withdrawal naming the run ids that refute it, commit that as a NEW carrier whose message names the previous one as a no-op, and file the no-op as its own row when the lane's own output produced it. A commit message asserting a board change is not the change; only the field value in the committed tree is.

The same check applies to the row you are about to write: re-read the current value from the staged tree, not from the payload you just composed, or a re-fired pass restamps `updated_at` and reports a refresh that carries no new measurement.

## Running a gate battery without mutating the candidate

A project's `make test` is not always a pure read: a prerequisite target can shell into a formatter that REWRITES files (`terraform fmt`, `gofmt -w`, `prettier --write`), so invoking the aggregate target edits the tree you are certifying and makes the "clean tree after gates" claim false. Run the legs individually in check mode in a detached worktree at the exact candidate, and record each leg's `rc` plus its salient line:

```bash
git worktree add --detach <scratch>/<lane>-gates <candidate-sha>
( cd <scratch>/<lane>-gates && terraform fmt -check -recursive )   # -check, never bare fmt
```

Write per-leg results to a log file and read the FILE back before quoting any number. A long command's output can arrive collapsed to a single "N lines output" line, and the report then carries counts the pass never actually read — capture `rc` and the tail into `gates.log` you can open, not into terminal scrollback. Report the aggregate as "constituent legs green" when the make target was decomposed, and say the target itself was not run; calling a decomposed battery "`make test` green" is an overclaim a reviewer can disprove in one command.

## Your own writes may already be committed by a sibling

Between your `create` calls and your commit, another lane can sweep the whole `tasks.jsonl` into its commit. Your working diff then shows only the edits made AFTER that sweep: a row you created minutes ago is absent from your diff and already present in HEAD, and a `--numstat` reading `3 added / 3 removed` looks like you only updated three rows. Resolve per ID, never by line arithmetic:

```bash
git show HEAD:./.coding-hermes/board/tasks.jsonl | grep -oE '"(<FAMILY>-[0-9]+|<ID>)"' | sort -u   # already published
grep -oE '"(<FAMILY>-[0-9]+|<ID>)"' .coding-hermes/board/tasks.jsonl | sort -u                      # working tree
git diff -U0 .coding-hermes/board/tasks.jsonl | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' \
  | grep -oE '"(<FAMILY>-[0-9]+)"' | sort | uniq -c                                                # what the commit carries
```

Report the already-published ids as committed by the sibling (cite its SHA), commit only what your diff carries, and verify the pushed tree with `git show <carrier>:<board> | jq 'select(.id=="<ID>")'` — the create and the update can land in different commits, which is fine, but a report that assumes one commit holds all of them is not.

### A sibling's UNPUSHED commit makes the shared tree unpublishable

Uncommitted sibling rows are one hazard; an unpushed sibling COMMIT is a different one and it is
worse, because every write-level proof still passes. `git rev-parse HEAD` reads ahead of
`origin/<branch>` while the working tree also carries your rows: committing there parents your
carrier on their unpublished work, and the eventual `git push` publishes their commit under your
message. Assert the relationship before choosing a commit root:

```bash
T=$(git rev-parse origin/<branch>); H=$(git rev-parse HEAD)
git rev-list --count "$T..$H"          # >0 with a foreign author = sibling work not yet published
```

Build the carrier in a detached worktree at the fetched remote tip and copy the live board bytes
into it only after proving the diff is yours alone:

```bash
git fetch <alias> <branch> --quiet
git worktree add --detach <scratch>/<lane>-carrier <alias>/<branch>
git diff --name-only <alias>/<branch> -- <board>/            # must list ONLY your rows' files
cp <board>/tasks.jsonl <board>/events.jsonl <scratch>/<lane>-carrier/<board>/
```

A board diff that names a row you did not write means the live file holds sibling writes — stop and
resolve those first (liveness check above), never copy them into your carrier. Commit the evidence
and the board as separate commits there, then publish from the detached checkout with an explicit
refspec (`git push origin HEAD:<branch>`; a bare push has no upstream).

After the push, prove the live tree CONVERGES instead of assuming it: the working copy's board files
must be byte-identical to the new remote tip, which is exactly the state that lets the sibling's
later rebase resolve without dropping either side's rows.

```bash
for f in <board>/tasks.jsonl <board>/events.jsonl; do
  a=$(sha256sum "$f" | cut -d' ' -f1); b=$(git show origin/<branch>:"$f" | sha256sum | cut -d' ' -f1)
  [ "$a" = "$b" ] && echo "IDENTICAL $f" || echo "DIVERGED $f"
done
```

Do NOT `git checkout -- <board>` to clean the shared tree on a mismatch: those bytes are the rows a
foreman is reading right now, and reverting them removes live work to make your status output tidy.
Report the divergence and leave the file.

### The mirror case: a sibling's writes are in YOUR staging area

Board JSONL is line-granular, so `git add <board>/tasks.jsonl` publishes every line currently in the
working tree — staging the PATH is all-or-nothing. That is a limitation of `git add`, not of git: an
index entry is a blob you may build yourself (see "Committing one row from HEAD's blob" below).
Whether publishing the working tree is safe depends on LIVENESS, not on the diff:

```bash
ps -eo pid,etimes,cmd | grep -iE '<sibling-lane>'   # is a writer still alive?
git reflog -3 --date=iso                            # who committed, and when
```

A dirty board with NO live writer is orphaned residue — the lane exited before its commit. Treat it
as inherited bytes: publish it with its provenance named, or leave it, never revert it. A dirty board
with a live writer is a race you lose gracefully: take `PRE=$(git rev-parse HEAD)` before your writer
call and `POST` after, and expect one of three legal outcomes — HEAD unchanged (commit the merged
file yourself), HEAD moved while your earlier commit is still an ancestor (`git merge-base
--is-ancestor <your-commit> HEAD`), or HEAD moved onto lines that collide with yours (re-run the
writer against the new file; never hand-merge JSONL).

When the sibling is about to commit, the cheapest resolution is a bounded wait then a re-check of
`git status --porcelain`: once its commit lands, your `boardctl update` reads post-sibling content and
your own commit's diff collapses to your row automatically. Prove that instead of asserting it:

```bash
comm -3 <(git show HEAD:<board> | jq -r '.id' | sort) <(jq -r '.id' <board> | sort)   # empty = no rows added/removed
wc -l < <(git show HEAD:<board>) <board>                                             # equal = no row lost
git diff --numstat -- <board>/tasks.jsonl <board>/events.jsonl                       # your row (1 1) + one event (1 0)
```

Then say it where a reader will look: "No <sibling-family> rows carried here; row count N before and
after" in the commit body, and the sibling's SHA named as interleaved in the artifact's publication
table. A carrier whose message is silent about a mid-window sibling commit reads to the next auditor
as a lane that either clobbered or silently adopted work it did not do.

### Committing one row from HEAD's blob

When a sibling's uncommitted rows sit in the shared working copy and waiting is not an option (a
foreman is mid-tick, or the tick is closing), build the index entry yourself instead of staging the
file: take HEAD's bytes, apply ONLY your row edit to them, and stage that blob. Your commit then
carries exactly one changed row, and the sibling's edits stay in the working tree for its own commit.

```bash
S=<scratch>
git show HEAD:<board>/tasks.jsonl > $S/base.jsonl          # sibling-free base
# apply the target-row edit to $S/base.jsonl, line-preserving
BLOB=$(git hash-object -w $S/base.jsonl)
git update-index --cacheinfo 100644,$BLOB,<board>/tasks.jsonl
git diff --cached --name-only                              # exactly the board path
```

Apply the SAME edit to the working copy before committing. A working file left behind the index is
the trap: the next `git add <board>` by any lane publishes a version that has the sibling's rows but
MISSING yours, silently reverting the refresh you just certified. With both copies edited, the
working file equals the new HEAD content and later sweeps are harmless.

Verify by content, not by the writer's exit line: `git show HEAD:<board> | jq -c 'select(.id=="<ROW>")'`
shows the new payload, `git diff --numstat HEAD~1 HEAD -- <board>` reads `1 1` (or one line per target)
for a single-row refresh, no other id appears in that diff (`git diff -U0 HEAD~1 HEAD -- <board> |
grep -oE '"id": *"[^"]+"' | sort -u`), and `wc -l` on both revs is equal. Afterwards `git status`
still shows the sibling's rows as unstaged — that is the intended end state, not a leftover write to
clean up or republish.

## When the project under release management IS the board tool

**Build the writer from the certified candidate.** Writing through a shared install records one
finding while evaluating a tree that is not the candidate:

```bash
go build -trimpath -o <scratch>/boardctl-cand ./cmd/boardctl   # from the candidate checkout
<scratch>/boardctl-cand validate
```

**Probe each installed binary's PROVENANCE; never inherit the "stale dev build" premise.** The
fleet-shared install is frequently a stamped release build, and repeating the assumption is how a
pending row's premise goes false underneath it. `boardctl` has no `--version` flag — the probe is
the `version` SUBCOMMAND, and the stamp comes from Go build info:

```bash
for B in ~/.local/bin/boardctl ~/go/bin/boardctl; do
  [ -x "$B" ] || continue
  "$B" version 2>/dev/null                                            # v0.4.0, or `dev` when unstamped
  go version -m "$B" | grep -E 'vcs\.(revision|modified)|^\s+mod\s'    # release SHA + dirty flag
  done
```

`vcs.modified=false` with `vcs.revision` equal to the release commit means that install IS the
release, not drift: refute the pending staleness row by appending the measurement (both commands
and their output) to its `foreman_note` and leave the status transition to the row's owner instead
of filing a duplicate row. Staleness is per BINARY, not per host — a stale second copy (one
directory resolving an old module version while the other is current) is the usual real finding and
needs its own row.

**File the readiness event bound to the row that owns the finding**, so the foreman sees it
from `show <id> --events`. `--detail` takes JSON from a file (staged with the file writer,
not a shell heredoc, which the unattended gate treats as an inline-interpreter one-liner):

```bash
<bin> event --type audit --task-id RELEASE-<id> --actor releng --detail @<payload>.json
tail -1 <board>/events.jsonl | jq -c '{id,event_type,task_id,actor,timestamp}'
```

**A re-fired pass appends its event with `--no-tick-write`.** A dispatch can run the same tick id a second time after the first pass already counted it; without the flag the board's tick counter increments twice for one tick and every later tick-attribution read is off by one. The event itself (id, payload, `task_id`) is unchanged — only the counter write is suppressed — so cite the event id as the write receipt exactly as usual.

**`doctor` reports inherited header state, and you do not repair counters you do not own.** A long-lived board can show `RESULT: FAIL` because the header's `ticks_total` lags the events (e.g. header 910 vs max event tick 6025); `boardctl` prints the suggested `--set-ticks-total=<max>`. Leave it. That counter is written by the lanes that fire ticks, a `--no-tick-write` event deliberately does not advance it, and re-basing it from a verify-only lane rewrites accounting a foreman depends on. Report the observed numbers as inherited, name the command that would change them, and do not run it.

Event ids continue the board's counter, but the counter is MIXED-SHAPE: numeric ids live
beside string ids (`EVT-RELEASE-...`), so `jq -s 'map(.id|tonumber)|max+1'` fails twice —
first on a null id, then on the string — and each failure is the whole append leg. Filter to
numeric-looking ids before taking the max, append exactly one line, and prove the file grew
by one:

```bash
NEXT=$(jq -s 'map(.id|tostring)|map(select(test("^[0-9]+$")))|map(tonumber)|max+1' events.jsonl)
```

**`--detail` lands as a JSON-encoded STRING, not an object.** The stored event reads
`"detail": "{\n  \"kind\": ..."`, so `jq '.detail|keys'` fails with `string ("{\n  ...") has no
keys` and any projection written against an object shape returns nothing. Parse it explicitly:

```bash
jq -r '.detail | fromjson' <<<"$(tail -1 events.jsonl)"      # or: > f; jq -r '.detail' f | fromjson
```

Do the same when reading a sibling pass's event back to prove your write landed — a `null` from
`.detail.kind` is the double encoding, not an empty detail.

A non-zero exit from `event --detail @file` is a REFUSED write, not a soft warning: nothing was
appended, so do not re-run the identical payload and do not treat the missing event as done. The same
rule applies to deferred memory calls: an empty wrapper invocation is not a write attempt, and
repeating it only burns the tick; use one visibly populated direct payload or mark the memory leg
UNVERIFIED. First fallback is prose, not JSONL surgery — carry the pass record in the rolling row's append-only note
(`update <ROW> --status <current> --note "…"`, same content, exits 0) and say in the report that the
event leg was refused and the note is the durable record. Coerce the stored line
(`.detail |= (try fromjson catch .)`) only when a raw event append is mandatory, and keep the
verified string form in mind: other readers may parse events as strings, so an object-repaired
event must be disclosed in the report rather than presented as the normal shape.

The REVERSE shape holds on `tasks.jsonl`: `update` stores `detail` as an OBJECT
(`{"evidence":[...],"fingerprint":...}`), so piping that through `.detail | fromjson` dies with
`object ({...}) only strings can be parsed` on the first row it touches. Probe the shape before
parsing — `jq -r 'select(.id=="<ID>") | .detail | type'` — and treat the two board files as
different dialects of the same field name rather than assuming one reader works on both.

A row written through `board-row-set-json.py --json detail=@file` can store that object as a
PRETTY-PRINTED STRING in `tasks.jsonl` too, so `.detail.decision` / `.detail.candidate_sha` read
`null` on a write that landed perfectly — and `null` beside a passing exit code and a rewritten
`updated_at` reads exactly like a dropped field. Probe the type before believing the null, and
project through a tolerant accessor in every readback:

```bash
jq -r 'select(.id=="<ID>") | .detail | type' <board>            # "object" or "string"
jq -c 'select(.id=="<ID>") | (.detail | if type=="string" then fromjson else . end) | {decision, candidate_sha}'
```

Rows written by different writers on the same board legitimately disagree on this shape; a
reader that assumes one will report the other's fields as missing on every pass. When a
readback nulls a key you just wrote, re-read with the accessor before re-running the writer — the
second write would double the field or restamp the row for nothing.

The payload itself should carry the
sweep id, pass label, candidate SHA, census, exact-SHA run ids, per-leg status (including
UNVERIFIED legs and why), and the ordering decision.

**`validate` warnings are pre-existing board state.** Legacy shapes (events with no id,
non-numeric ids, duplicated legacy ids) print as `[warn]` while the run still ends
`RESULT: OK (N warning(s))`. Compare the warning count before and after your write; do not
report inherited warnings as something the pass introduced.

The comparison that survives a shared or dirty checkout is a PRISTINE BASELINE: create a
second detached worktree at the base SHA (`git worktree add --detach <scratch>/<lane>-base
<base-sha>`), run `validate` there, and compare the exact `(errors, warnings)` PAIR with your
carrier's. Identical pairs — `455 errors / 589 warnings` on both — prove the carrier added
zero, which is the sentence the report needs; "fewer warnings than before" instead invites the
reader to wonder what the pass silently repaired. Reap the baseline worktree afterwards so the
next pass does not validate against a stale tree.

On a long-lived board `validate` can also end `RESULT: FAIL (N error(s))` on inherited event-id
ordering errors that predate the pass. That FAIL is not your commit gate and not your regression:
the gate is the evidence audit — `python3 scripts/board-evidence-audit.py --check` must exit 0 and
print `0 new since baseline`. Quote both numbers so an inherited FAIL is not read as damage and a
new unverifiable completion is not waved through.

## A stale lane checkout: re-apply the writer calls, do not merge the JSONL

Writer calls are cheap and idempotent; a JSONL merge is neither. When the lane checkout is behind
the remote board while carrying your own writer output, do not pull across the two board files:
discard the generated paths (`git checkout -- <board>/tasks.jsonl <board>/events.jsonl`),
fast-forward (`git merge --ff-only origin/master`), then re-run the same `update`/`create`
commands on the new tip and read the rows back before staging. Only the writer's output is
discarded — files written outside the board, including an artifact under a directory policy
ignores, stay on disk through the ff-merge; confirm with `ls` rather than assuming the checkout
removed them.

**A board-only diff guards as `DEGRADED PASS` by design** (`skips: go_build/go_lint/go_tests
= No Go files staged`). Quote that, plus the hosted run on the carrier, as the receipt —
do not reach for a hook bypass on a guard that behaved correctly.

**A stale count inside the owning row's TITLE is corrected in the event, not by rewriting
the row — unless the TITLE's PREMISE is wrong. Before binding a refresh, validate the exact
writer syntax and payload contract once; a refused flag combination is not evidence that the
row changed, and repeated retries with guessed flags only consume the tick.** When the row's acceptance criteria, reasoning and foreman_note already carry the
live measurement, rewrite nothing mid-tick: the title's words are a prior pass's snapshot,
rewriting an active P1 title churns a row another lane may be dispatching, and the event is
where the correction belongs as long as it names which words are stale. Rewrite it when the
title names the wrong GATE or the wrong FIX: that is what a dispatcher reads first, and a
foreman given a stale premise implements a different change than the one required. The wrong
RELEASE LINE is the same class: a patch title (`vX.Y.(Z+1)`) on a row whose own acceptance
criteria require a minor bump makes a title-only reader cut the wrong tag, and a published tag
is expensive to retract. A version retarget is not done until title, note, acceptance criteria
and `updated_at` all agree — the note and criteria are the surfaces a retarget reaches first and
the title the one it forgets. Before closing a sweep, re-read the row and assert the version in
the title equals the version its ACs name. In that
case update the title to the measured premise AND append the correction to `foreman_note`
in the same call so the row is self-consistent wherever a reader enters it. Correcting a
number the row merely repeats is an event; correcting what the row ASSERTS is a title edit.

A count quoted in a row you are composing is your own measurement, not inherited state:
derive it from the certified range in the same step that builds the payload
(`git rev-list --count <tag>..<sha>`) and never transcribe a total from an earlier pass's
note or report. A freshly filed row that repeats a stale total hands a dispatcher a wrong
premise about scope, and the correction then costs a second write to a row that was
avoidable in the first place.

## A board that refuses to load is not a board that is broken

One malformed record — an EVENT-shaped object appended to `tasks.jsonl`, carrying a numeric
id and event keys — makes every `boardctl` verb refuse that directory until the read verbs
are given `--skip-bad-lines`. The symptom is exit 1 with no rows or an error naming the
offending line; do not conclude the board is corrupt, and do not repair it from a
verify-only lane.

- Read with `--skip-bad-lines`; the WRITE verbs do not accept it. Flag sets differ per verb,
  so probe `--help` or a scratch board copy instead of guessing — a rejected flag proves
  nothing about the board and costs a round trip.
- Count state with a tolerant reader over the file (skip unparsable lines explicitly) and
  report the tuple `N complete / N pending / N blocked / 1 malformed`, naming the line
  number and the malformed record's id. A total that accounts for the bad line is
  auditable; a bare "N complete" is not.
- Attribute the bad line before ascribing it to your write: `git log -S` / `git blame` on
  that line, or a check of the commit that introduced it. It almost always predates the
  pass, which makes it an inherited defect to file as its own row — never a reason to skip
  the tick's real measurement or to hand-edit the board.

## The selector can starve the actionable row

`next` breaks equal-priority ties by PHYSICAL ROW ORDER — the order ids appear in
`tasks.jsonl`, not priority, not age, not dispatchability — while `ready` filters rows on a
worker field a parked row never sets. A row that cannot be executed in this repository
(fix surface in another repo, owner-gated) can therefore sit above the release blocker and
win every P1 tie: the blocker is re-measured each pass and dispatched never.

Prove the mechanism without touching the live board:

```bash
S=$(mktemp -d); mkdir -p $S/board; cp <board>/tasks.jsonl <board>/events.jsonl $S/board/
<bin> next -C $S                                        # baseline pick
<bin> update -C $S <parked-id> --deferred true --defer-reason "<why it cannot run here>"
<bin> next -C $S                                        # pick flips to the actionable row
```

A pick that flips on that one flag proves the tie-break, not the calendar, is starving the
row. File the selector defect as its own row (acceptance: the parked row is skipped or
ordered last, plus a unit test that fails on the old ordering) and leave the cross-repo row's
status alone — flipping it makes owner decisions dispatchable.

`--acceptance-criteria "$(cat <file>)"` is the safe form for long multi-line criteria:
command substitution of a FILE survives (2 KB+ multi-line criteria land intact and read back
byte-equal), while a literal `$(...)` written into the text is substituted away.

## No `tags:` trigger means a tag is untested

If the workflow triggers only on `push: branches:[main]` and `pull_request`, pushing a tag runs nothing, and pushing a `wt/*` branch runs nothing either — which is exactly why a completed worker branch looks "CI-less" while the same tree on `main` is green. Before the first release either add the tag trigger or dispatch explicitly (`gh workflow run ci.yml --ref vX.Y.Z`) and wait for that run before publishing anything.

## A directory-wide board commit deletes evidence it never saw

A writer that stages the whole directory (`git add -- <board-dir>/`) from a checkout whose
snapshot lacks a file records that file as a DELETION. The row citing it then carries a
dangling reference while the commit looks like a routine board refresh.

Check every board commit you read or write for unintended deletions before trusting its shape:

```bash
git show --name-status <sha> | grep -E '^D'          # deletions the commit carries
git cat-file -e <tip>:<path> ; echo "exists=$?"      # 0 = present, non-zero = gone
```

Repair on the spot: restore the artifact from the parent commit byte-identically, record its
sha256 in the record, and prove the restored bytes (`git show <tip>:<path> | sha256sum`). Then
file the mechanism as its own row — acceptance should be that the writer refuses unrequested
deletions under the board directory, not merely that the file came back.

## `git add -A` publishes the guard's own state files

A commit-time guard regenerates its own state as a side effect of running — a graph cache
(`<cache>/graph/state.json`) plus lock files — while the project tracks only a manifest and rebuilds
the rest per checkout. `git add -A` in a board/evidence carrier therefore commits files the project
deliberately keeps out of history, and the commit still reads as a routine board refresh.

Stage explicit paths in every carrier — `git add <artifact> <board>/tasks.jsonl <board>/events.jsonl` —
and assert the intended set before pushing:

```bash
git show --name-status --format= HEAD          # only the paths you composed, nothing under cache dirs
grep -n '<cache-dir>' .gitignore               # what the project considers regenerable
```

Unwanted paths already in the commit are repaired with `git rm -r --cached <path>` plus
`--amend`, but a gated surface can decline that command. When it does, do not push and do not
discard the work: leave the commit local, state exactly which paths are in it and the one command
that finishes it, and say the push is held. Shared main carrying files the project untracks is a
worse outcome than an undelivered tick.

## A wrapper that asserts per-id persistence trips on rows it did not write

`scripts/board-write.sh`-style wrappers verify, after the wrapped write, that every id passed
on the command line changed hash; failure is rc=5. Rows you created BEFORE invoking the wrapper
never change during it, so a batch that mixes prior creates with one update aborts the run —
and the abort lands AFTER the commit exists and BEFORE the push.

Pass only the ids the wrapped write itself mutates. When rc=5 arrives, do not re-run the update
(the note is append-only and would double); check `git log -1` and `git status --porcelain`:
a new commit with a clean tree means the write landed locally. Verify the tree by content
(`git show --name-status`, then read the rows back), land the push yourself
(`git push origin HEAD:<branch>`), and prove the rows at the remote (`git show
origin/<branch>:<board> | jq 'select(.id=="<ID>")'`).

Keep reason/AC/note payload files OUTSIDE the repo. A payload written into the board directory
gets swept by the wrapper's directory-wide `git add` and lands as a dotfile commit; stage it in
scratch and pass `--note "$(cat <scratch>/note.txt)"`, then confirm the committed tree carries
no dotfiles under the board dir (`git ls-tree -r --name-only HEAD <board-dir>/ | grep -E '/\.'`).

**A detached carrier worktree cannot host the wrapper's push.** In a worktree created with
`git worktree add --detach`, no branch is checked out and a branch name that already exists in the
repo (`master`, `main`) cannot be created there — `git switch -c master` fails. Run the writer with
`BOARD_WRITE_NO_PUSH=1`, create a uniquely named carrier branch for auditability
(`git switch -c releng/<project>-<hhmm>`), then push the ref explicitly and prove it:

```bash
BOARD_WRITE_NO_PUSH=1 scripts/board-write.sh <id> --note "..."
git switch -c releng/<project>-<hhmm>
git push origin HEAD:master
git ls-remote origin refs/heads/master   # must equal `git rev-parse HEAD` exactly
```

The refspec `HEAD:<branch>` is what publishes from a detached checkout; a bare `git push` has no
upstream and silently does nothing. Verify the rows from the remote tree, then
`git worktree remove --force` — a detached worktree left behind keeps the board paths half-owned
by a checkout no lane will ever update again.

## A re-fired pass whose candidate moved only inside the board

A lane can dispatch the same tick id again after its own pass already committed the artifact.

A carried pass carries BUILD legs by tree identity; it does not carry a CI VERDICT. When the
previous run was red, the failing set from a run at the new tip is new evidence — see
`references/controlled-pair-ci-attribution.md` before restating the old red or the old green.
Two DIFFERENT path sets decide what that second pass must redo — conflating them either
re-runs an hour of builds for nothing or carries a measurement that no longer holds.

**Build-carry set** (does the compiled/tested tree differ?):

```bash
git diff --name-only <old-pass-sha>..<new-tip> | grep -vE '^(\.coding-hermes/|\.gitreins/)' | wc -l
```

Zero means the code tree is the sha the census already ran on and build/vet/selfcheck/package
legs CARRY. `docs/`, `CHANGELOG.md` and `README.md` also leave the compiled tree untouched, so
they ride the same set — but they are squarely inside the **decision set**, which the release
surface is derived from. So on a carried pass:

- Name the carry: both SHAs, the exclusion set used, the empty material path count, and which
  legs carry. A silent restatement of old numbers reads as fresh measurement when it is not.
- Re-derive live every receipt that ANY commit invalidates — hosted run id at the new tip,
  tags (local and remote), release objects, tag-trigger workflows, changelog versioned
  sections, release scripts, board row states. These are seconds each; quoting them is how a
  stale tag count reaches a delivery report.
- Append a `## Pass N` section to the SAME artifact and append ONE audit event. A second
  artifact or a second readiness row for the same tick is the duplicate the board cannot absorb.
- EXCEPT when the rolling row binds that artifact's sha256: an appended `## Pass N` section changes
  the digest, so the row would then name pre-edit bytes and the rebind needed to fix it is exactly
  what a delta pass must not do. In that case the delta is ONE audit event whose payload carries
  pass, decision, candidate, tip, the changed-path set with its empty material count, and the
  gates-carried reason — leave the artifact BYTE-IDENTICAL and say in the event that it was
  deliberately not rewritten because the row binds its digest. One durable record per tick id is
  satisfied by the event; a digest break is not a record, it is a defect.

Refresh the rolling row's note so a reader at the row sees the moved tip, passing the current
status because `update` requires one:

```bash
boardctl -C <board-dir> update <ROW> --status pending \
  --note "PASS 2 (<tick-id>): tip moved to <new-sha> (bookkeeping-only, 0 material paths vs <old-sha>),\
 exact-SHA CI <run> <conclusion>. Re-derived: <surfaces>. DECISION UNCHANGED: <decision>"
```

Never re-attach the evidence triple for a run id already stored on the row — `--evidence-*`
appends, so the same run lands twice and the row reads as two measurements. Verify the write
by shape, not by its status line: `git diff --numstat <board>` is `1 1`, `wc -l < <board>` is
unchanged, and `jq 'select(.id=="<ROW>") | .detail.evidence|length'` still equals its pre-write
value.

## Main advanced with PRODUCT commits after the measurement

A sweep certifies a SHA, then the tip moves with real product paths before the record is
delivered — a sibling lane landed a fix in the same window. Three moves are wrong: re-certifying
the new tip off the old measurement (the compiled tree changed), silently re-basing the row onto
the new SHA (the artifact, its digest and every run id describe the old one), and restarting the
whole sweep inside the tick (it will be superseded again before you finish).

Keep both anchors explicit. `candidate_sha` stays the measured commit with its own run ids; add
`main_advanced_after_measurement {tip, changed_product_paths, run_ids, note}` to the row's detail
and say in the report that the next sweep re-measures `<tip>`:

```bash
git diff --name-only <candidate>..<new-tip> \
  | grep -vE '^(\.coding-hermes/|\.gitreins/|docs/|CHANGELOG|README)'
```

An empty product-path set is the bookkeeping-only case above (measurement carries). A non-empty
set means HEAD is no longer what you certified: classify the advancement, do not bless it. A run
still `in_progress` on the new tip is not evidence in either direction, and a fix that touches the
surface of the failing run is promising, not green.

Interleaved sibling commits also mean `git log origin/main` shows commits you did not author
between your own; assert each record commit individually (`git merge-base --is-ancestor <sha>
origin/main`) instead of reading a linear chain off the log, and cite the artifact commit and the
row-refresh commit separately in the report.

## A duplicated row id blocks every id-addressed writer

Boards accumulate the same id twice when a family is re-swept over old rows. The shipped row helpers (`board-row-set-json.py`, `board-row-reasoning.py`) refuse an ambiguous id outright, so the new pass cannot refresh its target until the file holds exactly one row per id.

Resolve by renaming the SUPERSEDED row, never the canonical one: the newest row keeps the live id and the history a dispatcher reads, while the older duplicate becomes `<ID>-SUPERSEDED-<yyyymmdd>` with `"status": "duplicate"`. Rename by PHYSICAL LINE, not by a global replace on the id string — the live row carries the same id and a file-wide `sed` hits both:

```bash
cp <board> <scratch>/board-before.jsonl
sed -i '<N>s/"id": "<ID>"/"id": "<ID>-SUPERSEDED-<yyyymmdd>"/' <board>
sed -i '<N>s/"status": "[a-z]*"/"status": "duplicate"/' <board>
```

Verify before staging: line count unchanged, `git diff --numstat` equal to the number of fields you rewrote (`2 2` for id+status on one physical line), and every OTHER row byte-identical:

```bash
diff <(sed '<N>d' <scratch>/board-before.jsonl) <(sed '<N>d' <board>) && echo OTHERS-UNCHANGED
git show HEAD:<board> | jq -r 'select(.id|startswith("<ID>")) | "\(.id) \(.status)"'   # exactly two rows, one duplicate
```

Leave the duplicate in place rather than deleting it: the id is cited in older evidence and commit messages, and a deleted row turns those citations into dangling references.

## Hand-writing rows without touching your neighbours

When no sanctioned writer exists for the row edit, the rewrite must be LINE-preserving: parse each
physical line only to identify it, and emit the ORIGINAL bytes for every line that is not a target.

The failure shape is a serializer applied to the whole file — `out.append(json.dumps(obj))` sitting
outside the `if id in TARGETS:` branch re-serializes all N rows (key order, spacing, escaping) and
the diff becomes the entire board even though the content is identical. Detect it before staging:
`git diff --numstat <board>` must read exactly the number of target lines; a diff spanning ids you
never named means the writer, not the content, changed.

Recovery when the whole-file rewrite already landed in an unpushed commit: restore the board from
the pre-write rev (`git checkout <pre-write-rev> -- <board>/tasks.jsonl`) to get pristine rows back,
re-apply the change through the sanctioned writer, then splice only the target line — and require
`git diff --numstat <board>` to equal the target count before staging. Chasing the reformat with a
style-matching serializer reproduces the dialect of each legacy writer and still leaves every
untouched row one diff hunk away from the writer's own output; re-applying is cheaper and provable.

Shape that holds:

```python
lines = path.read_text().splitlines(keepends=True)
out, hit = [], set()
for ln in lines:
    if not ln.strip():
        out.append(ln); continue
    obj = json.loads(ln)
    if obj.get("id") in TARGETS:
        obj["detail"] = NEW_DETAIL[obj["id"]]; hit.add(obj["id"])
        out.append(json.dumps(obj) + "\n")          # ONLY here
    else:
        out.append(ln)                               # verbatim, byte-for-byte
assert hit == TARGETS, hit
```

Guard the write against a concurrent sibling lane: capture `sha256` of the file before reading and
re-check immediately before writing; abort on mismatch instead of clobbering a fresh foreman write.
Keep the pre-write copy as `<name>.before.jsonl` so a bad write is restored ("RESTORED-CLEAN") rather
than patch-chased.

Match the file's JSON dialect for NEW lines (events, appended rows). Compact boards were written
with `separators=(",", ":")`; default `json.dumps` spacing produces a one-line diff per row that
looks like content drift. Prove the dialect before using it: round-trip one untouched line through
your serializer and assert the result equals the original bytes — if it differs, your serializer
style is wrong, not the file.

Verification before staging:

```bash
grep -c '"id": "<ID>"' <board>        # 1 per target, proves no duplication
git diff --numstat <board>            # changed lines == targets written
jq -c . <board> >/dev/null && echo TASKS-VALID
jq -c . <events> >/dev/null && echo EVENTS-VALID
jq -c 'select(.id=="<ID>") | .detail' <board>   # read back the field you wrote
```

For appended events, derive the id from numeric-looking ids only (`grep`-style filter, then max+1)
because the counter is mixed-shape; then confirm the file grew by exactly the number of events.

## A closed row with no `commit_hash` is completion debt

`update --status complete` stores the status but not the code binding, and the validator then warns that the row is complete with no commit. Bind it in a follow-up call — allowed on an already-complete row, and no `--status` is needed:

```bash
FULL=$(git rev-parse <short-sha>)          # never transcribe an abbreviation into the field
boardctl update <ID> --commit-hash "$FULL"
boardctl show <ID> | jq -r '.commit_hash'  # exactly 40 hex chars
```

An abbreviated SHA carried over from your own notes is form-invalid and the warning persists. Resolve the full object id in the same step that binds it, then re-run `validate`: the debt warning drops by one while inherited warnings stay put — a count that does not move means the bind did not land.

**A row-presence grep is only as good as its JSON dialect.** Boards carry both `{"id":"<ID>", ...}` and `{"id": "<ID>", ...}`; a pattern anchored on one reports 0 on the other, and acting on that 0 has started a duplicate `create`. Use a separator-tolerant pattern (`grep -n '"id": ?"<ID>"' <board>`) or `jq 'select(.id=="<ID>")'`, which is dialect-blind — and when a row you just wrote reads absent, suspect the pattern before concluding the write failed.

## Evidence binding

Keep one rolling readiness row per candidate set; refresh in place rather than creating a second readiness row. Use the evidence triple only when its run-id contract is satisfied. Otherwise store hosted CI receipts in the row's supported structured detail and leave completion pending; a hosted run is not a GitReins history directory. File a separate row only for a distinct work item, never merely because HEAD moved.

An artifact whose reproduction recipe points at a scratch worktree dies when that tree is reaped, turning every later audit's `sha256`-and-rerun check into a broken command. Commit the receipts script BESIDE the report (`…/<report>-receipts.sh`), parameterize its root as `W="${1:-$(git rev-parse --show-toplevel)}"`, run it from the worktree root, `diff -q` its output against the copy the artifact's numbers were read from, and cite both the script digest and the output digest inside the artifact. The row still binds the ARTIFACT's sha256 — the script is how a reader re-derives the numbers, not what the row binds.

### Repairing stale digest and premise bindings

1. Read the artifact from the fetched remote tree and hash those exact bytes. Compare each owning row's structured receipt, not only its latest prose. Distinguish an artifact digest from a tree-listing digest even when both are valid 64-character hashes.
2. If the artifact needs factual correction, edit the existing tick artifact in an isolated carrier, publish that evidence commit first, and verify the remote bytes. Preserve historical pass sections but make the current header and explicit supersession unambiguous. A repair is not an excuse to rerun unchanged product gates or mint another readiness row.
3. Prepare the complete row payload from the fetched live row, not a reused scratch filename: corrected title/reasoning/note plus the existing detail object with the authoritative current receipt replaced. Prepend a labelled correction to reasoning and append to the full note; do not replace their histories with a fresh summary. Preserve historical evidence entries and unrelated detail keys. Add at most one new entry per unique `(run_id, timestamp, fingerprint, artifacts)` tuple. Identify superseded bindings explicitly. Put an artifact SHA-256 in an artifact-fingerprint field and an evaluated commit in a commit field; never substitute a 40-character commit SHA for the artifact digest just because both identify evidence.
4. Use `scripts/board-row-set-json.py <board> <id> --json detail=<payload.json> --text title=<title.txt> --text reasoning=<reasoning.txt> --text foreman_note=<note.txt> --write` for structured values the live CLI cannot set. The text file must contain the complete intended note, including preserved history. Do not pass an object through the string-only dotted setter: that stores JSON text instead of an object.
5. Assert unchanged row count, exact target-id set, and one removed/added physical line per target. Compare validator results before/after, then commit the board once. Read the remote artifact and nested receipt back and require the same evidence commit and byte digest in every repaired owner row.
6. Query and wait for the final board carrier's own workflows, then deliver that carrier receipt without another certification commit. Keep the sweep anchor, evidence commit and final carrier distinct; the row must not attempt to contain its own commit SHA.

### Pin the anchors, or every correction buys another carrier

A row repair iterates against a moving target: each board-only commit advances HEAD, so any value the payload derives from HEAD is stale the moment the payload is pushed. Three anchors, three different jobs — name them in the payload instead of letting one stand in for another:

- **gate-verified tip** — the commit the build/vet/test/vuln legs and the hosted runs actually belong to. Fixed until product code moves.
- **audit / evidence commit** — the commit that carried the artifact. This is what `carrier` binds to, with a `carrier_ci_run` that resolves to the same SHA.
- **record-repair commit** — the board-only commit carrying the corrected row. Record it in its own field (`record_repair.commit`), never as the carrier.

A `carrier` written as HEAD beside a run id belonging to an earlier commit looks complete, passes `--numstat` (`1 1`), passes `validate`, and still fails the reviewer's binding probe (`carrier` == the run's `headSha`). Before the first push, walk every SHA interpolated into `title`/`ci_result`/`guard_result`/`foreman_note`/reasoning and confirm the run id printed beside it resolves to that SHA (`gh run list --commit <full-sha>`); prose labels drift silently while the structured fields stay right.

**Assert the stable anchor and the PROPERTY, not a moving total.** A pinned range count (`rev-list --count <tag>..HEAD == N`) is true for exactly one commit and fails the second time the script runs. Pin the census at the gate tip and assert the property that licenses carrying the earlier measurement:

```python
assert n_at_gated_tip == EXPECTED, "census anchor moved"
assert not [p for p in git("diff", "--name-only", GATED_TIP + "..HEAD").splitlines()
            if p and not p.startswith(".coding-hermes/")], "product paths moved past the gated tip"
```

Report the delta as "N bookkeeping commits past the gated tip", computed, not typed.

**Make the rewrite idempotent before the first run.** A repair that appends a labelled pass block must strip any block from a previous run, or a retry nests the narrative twice and the row reads as two measurements:

```python
def strip_block(text, marker):
    i = (text or "").find(marker)
    return (text[:i] if i != -1 else text).rstrip()
```

Derive the `was` side of any correction table from the LIVE row (`old_detail.get(key)`), not from a literal. After the first repair the literal describes a state that no longer exists, so the enumerated audit trail claims fields changed that had already matched — the record then lies in the direction of looking more thorough.

Keep every prior structured record under `detail.history` and append; do not delete the pass you superseded. The history grows by one snapshot per repair, which is the intended cost of an auditable correction.

Scope precondition checks to their phase: assert the fetched starting tip before writing evidence, then assert the published evidence commit before repairing rows. Do not reuse an unconditional `origin/main == starting_tip` assertion after your own successful evidence push, because the expected ref has deliberately advanced.

## `append-audit-event.py` payload shape

The script refuses a payload that carries `type` and no `event_type`: `REFUSED: payload needs task_id and event_type`. Build the JSON with `event_type` (e.g. `audit`), `task_id`, `actor`, `id: 0`, and `detail`; the script assigns the real id and timestamp. The `--marker` CLI flag alone does not provide the dedup key — the marker must also appear INSIDE the payload (`marker` at top level and in `detail`), otherwise a re-fire of the same tick appends a second identical event. Verify with the marker grep count (`grep -c <marker> events.jsonl` == 1) plus `jq -e . events.jsonl` for line validity, and confirm the append is 1 insertion / 0 deletions.

**Use the shipped script before hand-rolling an appender.** A bespoke appender re-introduces the mixed-shape id trap (`max(int(r["id"]))` dies on legacy rows with no id and on string ids — skip anything that is not an int) and the dialect trap (match the file's `separators=(",",":")`), both of which the packaged writer already handles. Hand-roll only when the payload contract genuinely does not fit.

**When you do hand-roll it, derive the dedupe key from the payload value you are about to write.** A skip key copied as a literal (`(tick, "evidence_correction")`) beside a payload whose `type` you later rename (`correction_withdrawal`) makes the re-run skip the corrected write and report success — the correction silently never lands. Keep one variable, used for both the write and the key:

```python
type_ = payload["type"]
if any(r.get("detail", {}).get("tick") == TICK and r.get("detail", {}).get("type") == type_ for r in rows):
    print(f"skip: {TICK}/{type_} already present"); continue
```

After any rename, grep the persisted file for the NEW type string (`grep -c '"type": "<new-type>"' events.jsonl` == 1) rather than trusting the appender's own success line: the skip path prints nothing distinguishing and exits 0, which is indistinguishable from a landed write in every other respect.

## Main advances after your board write is already committed

A lane that commits its board write and then finds `origin/main` moved has a conflict `git rebase`
resolves WRONG by default: both sides appended lines, the clash is presented as a line edit, and the
resolution either drops your events or ships an id the sibling lane already used.

This is the ONE-SIDED case: one lane's own append against an upstream that took the ids. When two
board histories genuinely diverged (a stale long-lived branch plus the live board), use the union
recipe in `foreman-board-state-reconciliation` (`references/diverged-stream-board-merge.md`) — a
delta merge of your own commit under-counts what a real union has to preserve.

Decide replay vs merge first, and default to replay. Discard the generated paths, ff, re-run the same
`create`/`update` calls (see "A stale lane checkout" above) — cheap, idempotent, no ids to invent.
Merge only when the write cannot be replayed: hand-appended notes, rows whose ids your own commit
messages already cite, or a doc+board commit stack you would have to rebuild from scratch.

Then merge as a SET DIFFERENCE, never as a line merge — BASE = the commit your board write was based
on, THEIRS = the new upstream tip, MINE = your commit:

- Emit THEIRS' lines byte-verbatim FIRST, preserving their order.
- Then emit only the objects in MINE that are absent from BASE (match on the object, not the line).
- Renumber event ids past `max(numeric ids in THEIRS)`; never reuse one the sibling took.
- `events.jsonl` usually opens with a header object carrying no `id`, and the counter is mixed-shape.
  `json.loads(ln)["id"]` dies on the header and on string ids: use `.get("id")` plus an
  `isinstance(i, int)` filter.

Renumbering invalidates your own commit MESSAGE, which now cites ids that belong to the sibling
lane. `git commit --amend -F <scratch>/msg.txt` in the same breath, or the history advertises an
event that is not in the tree.

A guard-regenerated tracked artifact (a graph/index file the commit hook rewrites) dirties the tree
on every commit and enters the rebase as an unrelated conflict. Park it first:
`git stash push -m '<lane> guard artifact' -- <path>`, then rebase and leave it stashed.

Gate the push on `git merge-base --is-ancestor origin/main HEAD` and repeat the merge cycle on a
second advance — a board is an append-only ledger, so force-pushing it is never the answer.

To correct a NUMBER already baked into an unpushed artifact commit, do not stack a "correct the
count" commit on top of it: `git commit --fixup <sha>`, then
`GIT_SEQUENCE_EDITOR=true GIT_EDITOR=true git rebase -i --autosquash <base>`. One carrier per pass,
and the artifact's diff stays one coherent edit.

Ordering rule that prevents the whole class: publish the artifact commit FIRST, hash the pushed blob,
then file the row that binds that digest. A row filed before the artifact's last edit binds
pre-edit bytes by construction; when the order was already violated, the correction is an audit
EVENT carrying both digests, not a rewrite of the row.

## Markdown edits trip the format guard before the secrets guard

A table-row edit in an evidence artifact fails Tier-1 with `prettier format check failed` before it ever reaches gitleaks. Run the repo's own `./node_modules/.bin/prettier --write <file>` and re-stage; do not reach for `core.hooksPath=/dev/null` unless the built guard log proves the failure is pre-existing and unrelated. Prettier re-aligns whole table blocks, so re-check that the semantic content (run ids, SHAs) survived, and recompute the artifact digest afterwards — alignment changes the digest even when the prose is identical.

## A 201 write followed by a failed read is not a failed write

A DuckBrain `POST /api/memories` returning `201` and then a 4xx from the readback probe means the write landed and only the probe shape was wrong. Re-POSTing creates a second active record under the same key. Before retrying, count active records for that key; if a duplicate exists, tombstone the extra one via the MCP `forget` tool (`DELETE /api/memories/<id>` returns 404) and re-count until exactly one active record remains. Write the record with the project's established namespace (`wojons-mythos`), not the project short name, and use the lane's own key family (`/project/<project>/releng/<tick>`).

**The MCP `remember` wrapper wants an attribute object, not a prose blob.** A `content`-only call is refused outright — `tool_call to '<tool>' is missing required argument(s): attributes` — and repeating it burns the tick. Supply `attributes` (the structured facts a later pass will query: candidate, carrier commit, evaluated run id, row, decision, guard), plus `key`, `namespace`, `domain`, `author`, and `embedding_text` carrying the narrative. Write the record ONCE: a second call under the same key on the same tick leaves a superseded stub beside the full record, and a `recall` that returns one of them does not tell you which a future reader will get. Confirm with `recall` on the exact key and treat the returned body as the stored record, ignoring the write ack.

**An attribute you got wrong is corrected beside the record, never rewritten into it.** Ledger
records are append-only, so a fabricated value — typically a SHA whose prefix you read and whose
suffix you typed — stays readable forever. Write a second record under
`<the-same-key-path>-correction` whose attributes carry `correction_of` (the original key),
`<field>_true` with the value expanded in the same step (`git rev-parse <short>`),
`error`, and `scope`. State in `scope` what is NOT changing and that it was independently
verified — otherwise the correction reads as a retraction of the whole pass. Then check whether
anything committed cites the bad value: an artifact citing the short prefix is still TRUE and no
carrier has to move, which is the sentence the delivery needs. Do not silently restate the
corrected value in a new full record under the same key; two narratives for one pass is the
failure this rule exists to prevent.
