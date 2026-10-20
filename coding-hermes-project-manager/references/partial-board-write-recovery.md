# Partial board-write recovery

Use this when a board CLI reports that a task row was written but its event append failed.

1. Stop. Do not retry `create` or `update`; the task line may already exist.
2. Read the exact task id from `tasks.jsonl` and inspect the event file tail. Confirm whether the task line exists exactly once and whether its corresponding event exists.
3. Snapshot both JSONL files. Repair only the missing event or malformed boundary with the board's byte-preserving atomic procedure; preserve legacy event bytes and do not reserialize the history.
4. Reparse both files line-wise, run the raw G8 audit, and run `boardctl validate`. Treat legacy warnings separately from errors.
5. Assert the task/event pair, then update the ledger once. If the event cannot be repaired safely, leave the task row in place, record the partial state, and escalate rather than creating a duplicate.

Why: board commands can commit the task line before the append-only event write fails, so a nonzero command result does not mean the task was absent.