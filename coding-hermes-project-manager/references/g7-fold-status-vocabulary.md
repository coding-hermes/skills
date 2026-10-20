# G7 fold losing-row status and boardctl vocabulary

Depth for the G7 fold in SKILL.md. Read before choosing a status for the superseded (losing) row of a content dedupe.

## Check the vocabulary BEFORE the fold, not after

`boardctl validate`'s accepted status set is exactly `{blocked,complete,failed,in_progress,pending,review}` (read aliases: completed/done->complete, in-progress->in_progress, open/reopen/todo->pending). A fold that writes a distinct status outside the set (e.g. `superseded`) is semantically right and still FAILS the whole board with one `[error] status ... not in vocabulary` line per folded row — and a validate FAIL silently blocks every later `boardctl` write on that board, including unrelated row closures. The error only surfaces when someone next runs validate, days later.

So: read the vocabulary from the validate error output (or `boardctl validate --help`) before choosing the losing-row status.

## When the vocabulary HAS a distinct superseded-like status

Use it: `status=<vocab word>`, `superseded_by=<canonical id>`, plus a one-line note naming the decision. Status-gated readers then don't count the row as a resolved fix.

## When it does NOT (the common case)

Fold with `status='complete'` + `superseded_by=<canonical id>` and append a NOT-A-FIX note to the losing row's free-text field (foreman_note/reasoning), e.g.:

    VOCAB-REPAIR <date>: status superseded -> complete (boardctl vocabulary has no superseded);
    this row is NOT a fixed defect — folded by content into <canonical id> via superseded_by;
    do not count as resolved work.

That note is the audit trail: closure-census readers see the caveat inline, and a later validate pass never re-flags the row.

## Verify the fold twice, both green

1. `boardctl validate -C <dir-containing-.coding-hermes>` — quote the `[error]` count delta pre vs post (a fold must never raise it; if it does, restore the /tmp snapshot and redo).
2. The G8 raw-line audit (`g8-board-audit.py <board>/tasks.jsonl`) — `unique_ids == lines` and `bad_lines=0`.
