---
name: boardctl
description: >-
  Use when reading, writing, or validating coding-hermes JSONL foreman
  boards — boardctl CLI (list/show/create/update/event/header/validate/stats).
  The JSONL files ARE the board; board.db/parquet retired 2026-09-03.
version: 1.1.0
author: Bane + Hermes
metadata:
  hermes:
    tags: [coding-hermes, board, jsonl, cli]
---

# boardctl — JSONL foreman board CLI

github.com/coding-hermes/boardctl — Go CLI over the canonical board store
(`tasks.jsonl` + `events.jsonl` + `board.jsonl` header + `fixtures.jsonl`).

**Doctrine (2026-09-03): the JSONL files ARE the board.** `board.db` and
`*.parquet` caches were retired fleet-wide — never create, query, or re-sync
them. No parity probes, no resync scripts, no cache-lag heuristics.

## Install

```bash
go install github.com/coding-hermes/boardctl/cmd/boardctl@latest
# or a static binary from releases (linux/darwin/windows/freebsd)
```

## Commands

```bash
boardctl -C <repo-or-board-dir> list [--status pending] [--priority P1] [--json] [--all]
boardctl -C <repo> show <TASK-ID> [--events]
boardctl -C <repo> create --id FEAT-1 --title "..." [--priority P2] [--complexity 3] \
    [--depends-on A,B] [--reasoning "..."] [--capability-tags go,net] \
    [--worktree PATH] [--branch NAME] [--session ID (repeatable)]
boardctl -C <repo> update <TASK-ID> --status complete [--commit-hash SHA] \
    [--guard PASS|FAIL|SKIP] [--ci GREEN|RED|SKIP] [--summary "..."] [--note "..."] \
    [--worktree PATH] [--branch NAME] [--session ID (repeatable)]
boardctl -C <repo> event --type audit [--task-id ID] [--tick N] \
    [--detail @file.json | --detail-text '...']
boardctl -C <repo> header [--json] [--set-ticks-total N] [--set-ticks-idle N] [--set-last-commit SHA]
boardctl -C <repo> validate
boardctl -C <repo> stats [--json] [--all]
```

`-C` resolves: repo root → `.coding-hermes` → the board dir itself.
Exit codes: 0 ok · 1 validation failure · 2 usage/board-not-found.

## Behaviors that matter

- **Style-preserving writes** — appended/updated rows match the board's
  detected JSON style (sorted vs insertion-order keys, compact vs spaced),
  so git diffs stay minimal.
- **Append-only events** — `event`/`update`/`create` compute the new event id
  as MAX(id)+1 across events.jsonl; duplicate task ids are rejected with a
  typed error.
- **Topology A+B** — auto-detects legacy boards where the header is line 1 of
  tasks.jsonl.
- **Legacy tolerance** — `validate` warns (not errors) on string/event-less
  legacy event ids and duplicate legacy ids.
- **Fixtures** — `list` hides fixture rows (ids in fixtures.jsonl) unless
  `--all`; `stats` same via `--all`.

## Row fields: `worktree`, `branch`, `sessions`

A task row carries WHERE the work happened and WHICH agent run did it, so the board — not a
dispatcher's memory — is the record:

- **`worktree`** — the absolute path of the git worktree the task was built in. Omitted when the work
  happened in the repo's main checkout.
- **`branch`** — that worktree's git branch (e.g. `wt/CHT-031`). Omitted when the work landed on the
  main branch directly.
- **`sessions`** — a JSON **array** of Hermes session-id strings: every session that actually worked
  the row. This is the audit trail from a board row to the agent run(s) that produced it.

Write them with `--worktree` / `--branch` / `--session` (repeat `--session` for more than one).
Semantics: an ABSENT flag leaves the field untouched; passing `--session` **sets** the list (replace,
not append); a row with none of them simply omits all three keys.

Conventions:

- A dispatcher that sends a worker into a worktree records `worktree` + `branch` on the row, and adds
  its own session id to `sessions` when it closes the row — so a later reader can
  `git -C <worktree> log` the exact tree the row describes.
- These fields are **data, not gate input**: no admission, cooldown or dependency decision reads
  them. They exist for audit, reconciliation and worktree reaping. A `worktree` path whose branch has
  since been merged and deleted is expected — the row is the survivor.

## Python equivalents (fleet scripts)

The foreman skill's scripts still work for tick housekeeping and remain the
cron-safe path inside ticks: `append_board_event.py`,
`append_board_task_completed.py`, `update_board_task_notes.py`,
`create_board_tasks.py` (all plain python3, no duckdb). Prefer `boardctl`
for interactive/one-off reads and validation.

## Pitfalls

- **`create` cannot bootstrap an empty board** — it mirrors the task schema
  and JSON style from an existing row; on an empty `tasks.jsonl` it errors
  with "no row to mirror the schema from". Seed one task row by hand (or via
  `create_board_tasks.py`) when initializing a brand-new board.
- **`update` requires the task to already exist** — there is no upsert; use
  `create` first.
- `show <id>` prints pretty JSON by default (no `--json` flag exists).
- `event --detail-text` values are stored base64-encoded in the `detail`
  field of events.jsonl — decode before diffing details.
- Never write `board.db`/`*.parquet` — the JSONL is the whole store.
- `tasks.jsonl` rewrites preserve line order; only the target row changes.
- Legacy boards may carry STRING ids/counters — boardctl int-coerces on read.
- On superproject boards (board dir in a parent repo), the tick # lives in
  board history, not repo HEAD — don't gate on `git log -1` alone.
