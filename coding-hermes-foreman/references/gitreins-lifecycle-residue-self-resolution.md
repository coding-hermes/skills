# GitReins lifecycle residue — self-resolution ladder

## When to use
The ownership barrier fires on `.gitreins/tasks.yaml` (or another GitReins lifecycle
file) that THIS tick's or the PRIOR tick's own `task complete` / guard run produced.
Measured loop (2026-11-09, crier-foreman): the foreman's 12:54 closeout ran
`task complete` at 14:06, which flipped `INGRESS-CRIER-001` to `complete` AFTER the
closeout commit — so the next two ticks each read ~2.5M input tokens (~$0.25 each),
hit the unattributed dirty tree, selected zero rows, and ended `dry_run no_changes`.
Every successful closeout was poisoning the next tick.

## CHEAP BLOCKED EXIT (cost law, Bane 2026-11-11)
A tick that will end dry/blocked must NOT pay a full evidence ceremony for a class
the fleet has already named. The measured burn: every barrier tick spent 2–4M input
tokens re-deriving the SAME three dirty paths (porcelain ×2, blocked-receipt build,
validator, markern probes) — ~46M tokens in one 24-tick window. Rules:

1. **First turn decides the shape**: read board pending count + porcelain + the
   previous tick's outcome ONCE. If the residue matches a class already named in a
   prior tick/unblock report (gitreins flip, board overlay, orphaned marker), take
   the ladder arm in ≤6 tool calls and end the tick. No second porcelain capture,
   no receipt builder, no validator for a known class.
2. **The full blocked-receipt ceremony is for FIRST-OF-CLASS or unattributable
   residue only** — where the evidence genuinely needs preserving.
4. **A dry tick's budget is one board read + one status read + one disposition.**
   If you have made more than ~10 tool calls and have not settled, dispatched, or
   escalated, end the tick with what you have — a repeat of the same evidence at
   2M tokens is the burn, not the diligence.
5. **ORIG_HEAD is a ROUTINE merge artifact, never barrier material (measured
   2026-11-12: a bare .git/ORIG_HEAD blocked two crier-foreman ticks for ~2.5h).**
   Git writes ORIG_HEAD on EVERY merge/rebase — the foreman's own successful
   wave closeouts re-create it, so treating it as residue is a perpetual
   settle-recreate cycle: settle it, next merge re-creates it, next tick blocks
   again. Same for FETCH_HEAD. Before a bare ref marker can count as a barrier,
   attribute it: if ORIG_HEAD points at an ancestor of (or an earlier tip on)
   the current branch's history, it is the pointer backup of a completed merge —
   ignore it and select work. Only a marker whose target is NOT reachable from
   any ref (truly orphaned operation state: REBASE_HEAD with rebase dirs,
   MERGE_HEAD mid-merge, CHERRY_PICK_HEAD) is real residue — and even then the
   ladder is attribute → settle → continue, not blocked-receipt.
6. **Timestamp discipline when attributing residue: tick ids are UTC, git
   committer dates are local.** Convert before concluding anything ran 'hours
   ago' — measured miss: 10:48 -05:00 commits read as 10:48 UTC and made a
   45-minute-old in-flight wave look hours stale.
4. **File the recurring cost, not just the instance**: a barrier class seen on ≥3
   ticks of one lane gets a board row naming the structural fix (per ladder rule 6),
   so the ceremony retires instead of re-arming every cadence window.


## The ladder — attribute, dispose, RESUME (never end dry on known residue)

1. **Capture** the full porcelain and the exact diff of the lifecycle file.
2. **Attribute by content, not suspicion.** A dirty `.gitreins/tasks.yaml` whose diff
   is exactly a status flip (`in_progress -> complete`) plus a `completed_at` bump on
   a row the prior tick just closed — matching the `task complete` call's timestamp —
   is SELF-PRODUCED residue. The producer is the gitreins CLI the prior closeout ran;
   there is no live writer to wait for.
3. **Dispose by committing it, not preserving it.** The state change is correct
   bookkeeping (the task IS complete). Commit it as a chore with the attribution in
   the message, push, re-capture porcelain, and CONTINUE the same tick's selection
   phase. Do not end the tick `dry_run` on residue you just attributed as your own
   fleet's bookkeeping.
4. **Restore-and-continue is the wrong disposal** for a status flip that matches a
   verdict you rely on: the lifecycle file is the durable record that the row closed.
   Commit, never checkout/restore.
5. **Only foreign residue stays a barrier**: a diff touching a DIFFERENT task id than
   the row this lane just closed, fields you cannot account for, or a live
   evaluator/guard process still running (check `.gitreins/history/` timestamps and
   `/proc` cwd census first) → blocked-receipt workflow as written.
6. **Structural fix owed in the tick report:** every time this ladder fires, the
   report names the underlying defect — the closeout path should commit its lifecycle
   state change in the SAME pass it closes the row — and files/updates the board row
   for it, so the product fix lands instead of the ladder recurring forever.
7. **Composite residue (board rows + lifecycle + git markers from the lane's own
   recent review/closeout sessions) is attributed per path in ONE pass** — row id ↔
   session ↔ mtime — then committed together as one settle commit; only true
   unknowns stay orphaned. Mixed provenance alone does not make residue foreign:
   measured 2026-11-10 crier-foreman, five consecutive dry ticks (13:45–14:29,
   ~16M tokens) preserving a mix its own review tick had produced. If a path's
   producer cannot be bound after the one pass, use the blocked-receipt workflow
   for THAT path only and select work with the rest of the tree.

## Orphaned git operation markers are residue too — verify, then remove

A bare `.git/REBASE_HEAD` (or `MERGE_HEAD`, `CHERRY_PICK_HEAD`) with NO corresponding
`rebase-merge`/`rebase-apply` directory and NO live rebase process is an orphaned
marker, and the pre-flight treats it as an operation barrier on a CLEAN porcelain —
so a clean tree can still wedge every tick. Resolve it in this order:

1. Prove orphanhood: the operation directories are absent, a process census finds no
   live rebase, and the porcelain is clean.
2. Prove the marked commit is superseded: it exists, its content is already landed on
   the canonical remote (`git show origin/main:<path>` for the files it carried), and
   nothing references it as a handle.
3. Remove the marker file only after both proofs, then re-capture porcelain and
   CONTINUE selection. Do not preserve a stale marker across ticks: unlike a
   lifecycle record, an orphaned marker is a pointer to state that no longer exists,
   and preserving it preserves the wedge (measured: two dry ticks on a clean tree
   until the marker was removed by hand).

If the marked commit is NOT superseded, that is a real interrupted operation —
finish or abort it properly instead of deleting the marker.

## Guard against the sibling class
A dirty tree from a FOREMAN TICK's own board commit is not residue: verify the
committed tree (`git show origin/main:<board>`) carries the row state, then treat the
working-tree copy as stale and reconcile. When in doubt, the committed tree is the
truth; the working tree is a draft.
