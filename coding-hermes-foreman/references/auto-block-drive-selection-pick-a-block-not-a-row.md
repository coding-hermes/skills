# Block-drive selection — pick a BLOCK, not a row


A tick that picks "the single highest-value pending task" scatters across
unrelated rows and finishes nothing: the same board keeps 180+ pending rows
while blocks sit at 94%, 83% and 81% complete with one row left each. Selection
must be BLOCK-FIRST and the block must be driven to its acceptance.

**Census before selection.** Run
`python3 ~/.hermes/scripts/block_drive.py <workdir> --top 10` (JSON with
`--json`). It groups pending rows into blocks via explicit `blocks` membership,
`depends_on` edges and id family, then ranks blocks that have READY work,
smallest remaining first. The top block is the tick's target — not the
highest-priority row anywhere on the board.

**Drive rules.**

1. One block per tick. Do not switch blocks while the chosen block still has a
   ready (unblocked, unstarted) row: finishing a block beats sampling many.
2. Prefer a block that is nearly complete (fewer pending rows, higher completion
   ratio). A one-row-from-done block that passes its acceptance closes real work
   and removes a standing claim; a fresh five-row block does not.
3. Within the block, dispatch rows in dependency order and verify each one
   against its own acceptance before starting the next. A worker's report is a
   claim; the merged, exercised tree is the fact.
4. A row blocked on an owner decision, credentials, or a live host is a NAMED
   blocker: record it on the row and move to the next ready row *of the same
   block*. Leave the block only when every remaining row is blocked.
5. The block's acceptance gate — not "the row is closed" — ends the block. When
   the last row lands, run the block's end-to-end check on the merged tree and
   record the result on the closing row.
6. Record the block id in the tick's board event, so the next tick resumes the
   same block instead of re-sampling the board.

**Anti-pattern this replaces.** Picking a DOC row, a QA row and a DF row in
three consecutive ticks because each looked "high value" in isolation, while the
three blocks they belonged to each kept a finished-but-unclosed row.

### Fan out inside the block — serial is a loaded-box fallback

A block with five independent rows must not take five ticks. Within the chosen
block, dispatch a WAVE:

```text
slots = min(6, nproc - ceil(loadavg))     # 16 cores, load 21 -> 1 slot -> serial
```

- `slots >= 2` and at least two mutually independent ready rows → one worker per
  row, each in its OWN worktree (`~/.hermes/scripts/worktree.sh new <project>
  <taskid>`), manifest written under `.coding-hermes/waves/` BEFORE dispatch.
- Independence is verified from the rows: no `depends_on` edge between wave
  members, different files, different seam. Co-located edits in one wave buy
  merge conflicts, not speed.
- Verify each worker independently; rework a rejected row in place rather than
  restarting the wave; MERGE SERIALLY behind the gate (zero deletions,
  build/vet/test, push, prove `origin/<branch>..HEAD` is 0) — and see
  *Preserve a judged commit* below before choosing rebase vs merge.
- Repopulate as merges free dependencies, staying in the same block. Budget the
  BLOCK, not the tick: a worker on a measured, test-heavy row runs 30-45 min, so
  a three-row block is a two-stage tick — dispatch the independent pair, merge
  them, then repopulate the third in the same tick rather than waiting idle.
- `slots < 2` → serial, and say in the report that the box was loaded. Serial is
  never the default posture: it is what a saturated host forces.

Never fan out across different blocks in one tick: parallel work without a single
coordinated acceptance target is how a fleet stays busy for weeks and finishes
nothing.

**Scatter check.** `singleton_blocks` in the census output is the measure of
irreducible scatter: rows that share no block, dependency edge or id family.
When that count is high, the board is a pile of one-liners and the fix is to
group related rows under a block goal before dispatching more of them.

### A block's NAME is a union-find root, not an id family

`block_drive.py` unions components on explicit `blocks`, then `depends_on`, then
id family, and prints the component's ROOT — the first-seen member id. One large
component therefore prints under whichever row was seen first, and its pending
count spans families: a board can report `blocks=5` while pending rows from a
dozen prefixes all sit inside one component named after a single unrelated id.

- Never conclude "family X has no block" from grepping the printed block names.
  Read `--json` and inspect membership; take pending/done counts from the JSON
  rather than re-deriving them from the id stems you grepped.
- A component's rank is dominated by `rows_pending`, so the biggest component
  ranks last even when its top rows are small. The ranking names the block; it
does not tell you which row to take.

### Ready is not dispatchable, and a singleton block cannot form a wave

Before confirming a pick, screen the ready rows for EXERCISABILITY. Three shapes
read as ready and are not: an arm that edits the source of a LIVE running
process (a worktree copy changes nothing the daemon executes); an arm whose
verdict needs a live cycle longer than the tick (a clean-machine battery, an
overnight soak); an arm that is an owner ruling. Name each exclusion and its
reason in the wave manifest so the next tick re-proves nothing.

Documented fall-through when the resume block and the top-ranked block cannot be
driven: (1) the resume block, if it has at least one dispatchable row; otherwise
(2) the top DRIVE block; and if that block is a SINGLETON — the WAVE path is
unavailable but a SERIAL wave of one worker still is (SKILL.md DISPATCH DOCTRINE
§7 WAVE FLOOR IS 1 supersedes the older "wave is impossible" reading; a singleton
block is DRIVEN serially, not skipped) — or every ready row fails the
exercisability screen, (3) the highest-ranked block with >= 2 mutually
independent, in-tick-closeable rows. Record the chain
and every exclusion in the manifest's `block_selection_reason`: a deviation from
the ranking that is not written down reads as sampling.

### Preserve a judged commit: merge --no-ff, do not rebase

A row judged at commit X, on a branch cut from an older base, must NOT be
rebased onto the advanced branch: the rebase rewrites X, the verdict's `commit`
no longer names anything on the published branch, and the row's `commit_hash`
becomes an orphan. Merge `--no-ff` instead so X stays an ancestor of the
published branch and the verdict binding holds; confirm the repo already carries
merge commits (`git log --merges --oneline -3`) before introducing the shape.
Rebase remains correct for branches whose commits have NOT been judged yet.

