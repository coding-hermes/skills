# Task Format Guidelines

## Required Fields
Every task row in the board must include:
- `id`: Unique identifier in GAP-### format
- `title`: Clear, concise description of the work
- `status`: One of pending, in_progress, completed, verified, stale
- `priority`: P0-P5 scale
- `complexity`: Estimated effort (1-5 scale)
- `depends_on`: Array of task ID strings that must be completed before this task can start
- `blocks`: Array of task ID strings that are blocked by this task
- `primary_model`: Primary model to use (optional)
- `primary_provider`: Primary provider (optional)
- `fallback_model`: Fallback model (optional)
- `fallback_provider`: Fallback provider (optional)
- `reasoning`: Brief explanation of why this task is needed
- `capability_tags`: Array of capability tags (e.g., ++testing, ++api)
- `worker_status`: Current worker state (pending, dispatched, in_progress, complete)
- `dispatched_at`: Timestamp when task was dispatched
- `completed_at`: Timestamp when task was completed
- `attempts`: Number of attempts made
- `exit_code`: Exit code from execution
- `commit_hash`: Git commit hash when completed
- `files_changed`: Number of files changed
- `lines_added`: Lines of code added
- `lines_removed`: Lines of code removed
- `guard_result`: Result from gitreins guard (PASS/FAIL/SKIP)
- `ci_result`: Result from CI (GREEN/RED/SKIP)
- `worker_summary`: Summary from worker
- `foreman_note`: Notes from foreman
- `blocked_reason`: Reason if blocked
- `review_notes`: Notes from review
- `created_at`: Timestamp when task was created
- `updated_at`: Timestamp when task was last updated
- `blocked_since`: Timestamp when task was blocked

## Dependencies Format
The `depends_on` field must be a JSON array of strings, each string being a task ID.
Example: `[\"GAP-001\", \"GAP-002\"]`

If there are no dependencies, use an empty array: `[]`

Never leave the field empty or null.

## Observable Pass Criteria
Each task must include observable pass criteria in the title or description that answers:
- What does "fixed" look like?
- How will we verify it actually landed?
- What command or test will prove the fix?

This is what you'll verify in the next cycle.

## ID Generation

Derive the id prefix and next number from the BOARD, never from memory of what this lane filed last cycle (other writers advance the sequence between ticks):

1. Read the board's dominant id prefix from the ids actually present (`grep -o '"[A-Z-]*GAP-[0-9]*"' <board> | sort -u | tail` shows e.g. `C-GAP-###`, `QA-<PROJ>-###`, bare `GAP-###`). Match the family your new row belongs to; do not assume bare `GAP-###` — most project boards carry project-prefixed ids and a bare-GAP id can collide with a different family's sequence.
2. Compute max over ALL ids matching that exact prefix pattern (regex the numeric part; tolerate suffixed ids like `TR-046b` by matching `PREFIX-\d+` and taking max over matches). Format `PREFIX-{max+1:03d}`.
3. Pre-check the candidate: `grep -c '"<CANDIDATE-ID>"' <board>` must be 0 BEFORE appending. Numbering gaps exist on real boards (ids 043/044 can be taken while the highest id is 042), so 'max+1 seems free' is not a proof.
4. After appending, `grep -c '"<CANDIDATE-ID>"' <board>` must be exactly 1. Two hits means the append script ran twice or another writer took the id mid-cycle: remove ONLY your own line (identify it by `source`/`created_at`, never by id alone — the colliding row is usually a pre-existing complete one) via an atomic temp→re-parse→rename rewrite, re-derive the next free id, and refile. Verify the final board parses with zero duplicate ids before reporting row counts.

Never invent the next id from the last number you remember writing — collisions convert a clean append into a mid-cycle repair and can silently orphan the pre-existing row's identity.

## Co-author Trailer
Every commit MUST include `Co-authored-by: the identity in `CODING_HERMES_CO_AUTHOR``
Never use `git commit --no-verify` to bypass a blocked commit.

## Manual ledger stamping below the reconciler's age threshold

When a prior-cycle item's board row is COMPLETE and the fix is verified (commit is an ancestor of HEAD via `git merge-base --is-ancestor`, and the fix artifact is present on the live tree), stamp the ledger item `verified` directly — the reconciler's `--apply` only touches items above its age threshold, so a young complete row would otherwise sit `added` forever. Always `cp` the ledger to /tmp first, edit with jq (filter over `.items[]`, select on BOTH `id` and `project`), validate the result parses as one JSON document before `mv` over the original, then read the item back to confirm. Never stamp `verified` without the containment check — the board's `complete` alone is the foreman's claim, not evidence.
