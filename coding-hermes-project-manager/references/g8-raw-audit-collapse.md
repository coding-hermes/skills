# G8 deep dive — raw-line audit and duplicate-id collapse

Depth for the G8 gate in SKILL.md. Read when the audit reports duplicate ids, validate errors, or before any collapse.

## Why RAW lines, never a keep-last view

Every reader (foreman, board loader, PM scan) resolves the board by keep-LAST, so a duplicate-id board looks perfect through that lens — the extra lines are invisible. A dedupe claim computed through the loader is tautological: by construction the id collapses to one row. `boardctl` also refuses ambiguous ids on write (`task appears on multiple lines (355 and 370)`), so duplicate lines silently block row closures — fixed rows stay re-pickable, which is how a 'fixed' row respawns as work. Compute every claim on the raw file.

## The collapse procedure (append-log board)

- Keep the LAST line per id — that is the line every reader treats as live — and drop the earlier ones, byte-preserving every kept line.
- **Keep-OLDEST vs keep-LAST, and WHY a G7 fold is an IN-PLACE EDIT on a per-row JSONL board.** G7's fold says *keep the oldest canonical*; the board's readers resolve keep-LAST, and `boardctl validate` errors on ANY id appearing on more than one line. So on a JSONL board where each id exists exactly once, appending a new superseding line under the SAME id is WRONG — it manufactures a duplicate-id validate FAIL that silently blocks every later closure of that row. Fold those boards by rewriting the losing row IN PLACE: set `status='complete'`, add `superseded_by=<canonical id>`, append the fold reason + evidence to `reasoning`, keep the original title/detail. An append-style superseding line is only correct on boards that legitimately carry the same id on multiple lines (rotating-cycle-slot boards) — and even there, keep the LAST occurrence, since that is the line every reader resolves; anything that deletes or rewrites earlier lines must keep LAST or the reader resolves the row you meant to retire. Snapshot the board to /tmp before the fold; if the first attempt produces validate errors, restore the snapshot and redo — never patch on top of a half-folded board. Verify every fold with BOTH `boardctl validate` (error-count delta) and the G8 raw-line audit (`unique_ids == lines`).
- Handle tasks.jsonl and events.jsonl together: write to temp files, validate the board, then swap in both files atomically. On failure, restore originals.
- Never re-serialize the whole file: a line-touching rewrite that changes untouched lines makes `git diff --numstat` disagree with the row count you edited, which is the signature auditors use.
- **If the fold is correct but the diff still rewrites most of the file, the cause is key-order/whitespace re-encoding of untouched rows, not the fold.** The failure shape: `git diff --numstat` shows ~1 changed line per row (81/78 on an 88-row board) while only 2 rows were edited — a `json.dumps` round-trip of the whole board re-encodes every untouched row's key order/spacing/escapes. Restore the snapshot and rewrite each line with its ORIGINAL byte text, `json.dumps`-re-encoding ONLY the rows actually edited. Confirm minimality with a per-id SEMANTIC diff (parse both trees, compare parsed objects by id): the changed-row set must be exactly the intended edit set, with row count and order unchanged — that assert, plus numstat back to the edited-row count, is the verification line.
- Re-parse and assert `unique_ids == lines` before committing.

## Distinct findings that reuse one ID

A duplicate ID is not automatically a stale shadow. If two copies are both open but their titles/remediation differ, preserve both findings: on a one-line-per-ID board, re-identify the later distinct row in place with the next unused ID in the board's existing series, preserve its evidence, and add a provenance note explaining the G8 repair. Do not drop it, mark it `duplicate`, or append another copy under the same ID; those choices either erase dispatchable work or keep the board invalid. Re-run the raw audit and `boardctl validate`, and report task-file errors separately from pre-existing `events.jsonl` ordering errors.

## Duplicate-id collapse is safe ONLY on terminal dup sets

Judge the duplicate CLASS, not the id count:
- Last line per duplicated id is `complete` (or otherwise terminal) and carries the close verdict (merge hash, artifact, verified-on-merged-result): the earlier lines are un-superseded stale states (often reverting to `pending`) every reader ignores — collapse them; the verdicts live entirely on the kept lines.
- Duplicated ids still genuinely OPEN (all copies pending/in_progress): do NOT collapse first — that deletes the foreman's pickable work. UNLESS both lines are the SAME finding (a sibling lane's enriched rewrite of the original: same title subject, later `updated_at`, the sibling's evidence note attached) — then the second line is evidence, not a second task, and keeping LAST preserves the pickable row while clearing the duplicate-id validate error. Distinguish by diffing the two lines: a rewrite carries the original's fields plus new ones (a lane-specific `*_note`); two distinct tasks carry different remediation text.

## Prove landed work before trusting any line

Every merge hash a close-note cites must pass `git merge-base --is-ancestor <hash> <default>` in the target repo, and remote parity must be clean. Resolve the default branch FIRST (`git symbolic-ref --short refs/remotes/origin/HEAD`) and never hardcode EITHER name — a hardcoded wrong name fails with 'unknown revision', or a bare `origin/master` alias can silently resolve and report NOT-ancestor, reading as a false 'fix not merged' verdict on a fix that landed fine. Read `git symbolic-ref` in the same command as the containment test and substitute its output.

Run `boardctl validate` before AND after the collapse and quote the `[error]` count delta (pre: 17 duplicate-id errors; post: OK) — that delta is the collapse's verification line.

## When a losing row is not itself fixed, do not invent an out-of-vocabulary
terminal status such as `superseded`: validator errors make the board
unpickable and status-gated readers disagree about backlog. Preserve a valid
open status (normally `pending`), add `superseded_by` and a
`superseded_note`, and annotate the winning row when the fresh count differs
(name the evidence source and `generated_at`). Use `complete` only when the
losing finding is independently resolved, not merely replaced by a newer
re-detection.

The terminal gate must accept `done` — and normalize it in the same pass

A keep-last safety gate that allowlists only (`complete`, `failed`) ABORTS on a valid close written with `status: done` (a boardctl read-alias that appears in the wild on foreman closes). Include `done` in the terminal allowlist, and — because `done` is also a validate WARNING (canonicalize) — normalize the kept line `done -> complete` in the SAME RMW pass, before the `unique_ids == lines` re-parse assert, so the post-write audit reads the normalized file. Gating BEFORE the rename but normalizing after it splits one edit into two board writes.

## The reverse-shadow class: terminal copies early, pending LAST

When a duplicate set's LAST line is NOT the close-verdict line (the foreman later re-appended the id as a plain `pending` re-statement, or a superseded copy carries the verdict on an earlier line), blind keep-last erases the verdict and blind keep-oldest erases the pickable row. Clear the duplicate-id error WITHOUT deleting any copy: preserve every losing line in place by RE-IDENTIFYING it (`id: <canonical>-SUP-N`, N per extra copy), set `status='complete'`, add `superseded_by=<canonical id>`, and a neutral foreman_note ('G8 structural duplicate retained as terminal superseded record; canonical last occurrence remains authoritative; no product resolution implied') — the last occurrence keeps the canonical id and stays the row every reader resolves. Use this when ANY copy in the set carries close metadata (commit_hash, worker_summary) you cannot prove is duplicated onto the kept line; when the kept line provably carries the full verdict, plain shadow-drop is still correct and cheaper. Either way expect `git diff --numstat` = one modified line per re-id'd copy + one append per gated row, and verify with boardctl (errors → 0) plus `unique_ids == lines`.

## The stale-shadow class: pending first line vs terminal last line

The commonest duplicate set is a stale shadow: an early `pending` line for an id whose LAST line is a terminal close carrying the verdict (commit hash / release note). Drop the FIRST line, keep the last — the kept line is what every reader resolves. Verify the class before dropping: the last line must carry a close verdict (commit_hash or an explicit RESOLVED/fix note in the title/reasoning); a terminal status with no verdict is still keep-last (the reader resolves it), but the shadow drop is unproven — name the verdict in the commit message. Post-collapse expect `git diff --numstat` = one modified line per normalized row + pure deletions for shadows (e.g. `1 4` for 3 dropped shadows + 1 normalized line).

## Backup-and-retry mechanics

Copy the board to a /tmp backup BEFORE the first script run (`cp tasks.jsonl /tmp/<lane>-<tick>-tasks.jsonl.bak`); after a failed run, restore with that copy AND delete the board's `.tmp` sibling before retrying — a leftover partial `.tmp` from the aborted pass is mistaken for fresh output on the next run. If a script ABORTs mid-cascade (safety gate fired on the third id), the first two drops are already staged in the temp file but never renamed — the on-disk board is untouched; no partial collapse ever exists on the rename-atomic pattern.

## Derive collapse-script indices from what the script computes

The G8 audit prints 1-based line numbers; a Python helper enumerates 0-based. Copying the printed number into a hard-coded index assert fails the script on its first run. Compute the duplicate indices inside the script, assert against exactly what it computed, and derive the drop index from that same variable.

## A duplicate-id signal a settled re-audit contradicts is a torn read

Sibling lanes append and rewrite board files in place; a count taken between their write passes can see a row twice or a partial line. Re-run the raw audit and grep the id count on the file as it now stands before chasing the ghost — but never delete or weaken the assert that flagged it: the assert is what proves which reading was the torn one.

## Decompose a validate FAIL per file before collapsing

A sibling pretty-printed state file (e.g. `board.jsonl` beside `tasks.jsonl`, rewritten by the foreman each tick) can trip `boardctl validate` with a bare `EOF` error — that FAIL is not a row problem and does not block a clean collapse. Split `[error]` counts by file first (`validate | grep -o '^\[error\] [a-z]*\.jsonl' | sort | uniq -c`) and judge only the canonical row file; leave foreman-owned state files untouched. Verify the collapse with `git diff --numstat` (pure deletions: 0 added) plus a per-row semantic-identity assert against the source keep-last lines — a keep-last collapse on a fully-complete board needs no vocab pass: the invalid-status lines were all early copies and die with their duplicates.
