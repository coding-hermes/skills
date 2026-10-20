# Board Status Vocabulary

The board validator (`boardctl validate`) accepts ONLY these status values: `blocked`, `complete`, `failed`, `in_progress`, `pending`, `review`.

## Closing a `failed` row the PM re-verified (host-file caveat)

A foreman `failed` verdict can be a SCOPE artifact, not a broken fix: the row's acceptance
lives in a file outside the repo (e.g. a `~/.hermes/scripts/` hourly script), so the worker
correctly reports 'no tracked implementation surface' while the fix itself is present on the
host. Before treating `failed` as a live defect: (1) verify the row's acceptance criteria
against the ACTUAL artifact with a real command (grep the cited behavior, diff against any
pre-fix backup); (2) if the criteria are met, flip the row to `complete` — never leave it
`failed` — with a `foreman_note` that names the untracked-file reason for the original
failure and the evidence lines, clears `blocked_reason`/`worker_status`, and records any
backup path. A failed row left standing re-reads as open work in every later census and
lures a re-dispatch that can only fail the same way.

## Read Aliases (display only, never write these)

- `open` -> `pending`
- `done` -> `complete`
- `todo` -> `pending`
- `completed` -> `complete`
- `in-progress` / `inprogress` -> `in_progress`
- `reopen` / `reopened` -> `pending`
- `verified` -> `complete` (display alias only — NOT a canon write value)

## The `verified` Trap

`verified` is NOT a canon status. It is a read alias that maps to `complete` for display, but writing `status: "verified"` into tasks.jsonl FAILS boardctl validation and blocks the commit.

When the PM verifies a fix landed:
1. Set `status: "complete"` (the canon form)
2. Record verification evidence in `review_notes` as a list entry prefixed with the date, e.g. `["PM VERIFIED 2026-09-29: fix landed in commit abc1234"]`
3. Or use a dedicated verification field if the row schema supports it

Never use `verified` as the status value itself — it will fail the commit gate.

## Why This Matters

The PM cycle marks items as verified after checking that fixes actually landed in code. The natural instinct is to write `status: "verified"` to distinguish PM-verified completions from worker-reported completions. But the board schema has no `verified` status — only the six canon values above. The distinction belongs in `review_notes` or a verification field, not in the status enum.
