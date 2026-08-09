#!/usr/bin/env python3
"""Update task-row fields on a DuckDB foreman board in BOTH artifacts.

append_board_event.py only covers audit EVENTS (events.jsonl + board.db
events table + board.jsonl header). Task-row updates — fixture
foreman_note/worker_summary refreshes, status flips, commit_hash backfills —
need a dual write:

  1. .coding-hermes/board/tasks.jsonl   <- git-tracked mirror (what gets committed)
  2. .coding-hermes/board/board.db      <- live read source (next tick reads THIS)

Update one without the other: the commit shows nothing (DB-only) or the next
tick reads stale notes (JSONL-only). Proven: scheduler tick #213 (2026-08-02).

Usage (cron-safe: no python3 -c, no heredocs):
  uv run --with duckdb python3 update_board_task_notes.py REPO TASK_ID FIELD=VALUE [FIELD=VALUE...] [--ts 'YYYY-MM-DD HH:MM:SS']

  REPO      absolute path to the project repo
  TASK_ID   task id, e.g. E2E-001
  FIELD=VALUE  repeatable; always include foreman_note for fixture refreshes
  --ts      updated_at value; defaults to now

Verifies the row exists in BOTH stores (non-zero exit + ERROR if missing in
either). tasks.jsonl full rewrite is fine — only events.jsonl is append-only.
"""
import argparse
import json
import sys
from datetime import datetime

import duckdb


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("task_id")
    ap.add_argument("fields", nargs="+", help="FIELD=VALUE pairs")
    ap.add_argument("--ts", default=None)
    args = ap.parse_args()

    board = f"{args.repo.rstrip('/')}/.coding-hermes/board"
    ts = args.ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    updates = {"updated_at": ts}
    for fv in args.fields:
        k, _, v = fv.partition("=")
        if not k:
            print(f"WARN: skipping malformed {fv}")
            continue
        updates[k] = v

    # 1) JSONL mirror (git-tracked)
    rows = []
    with open(f"{board}/tasks.jsonl") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    found = False
    for r in rows:
        if r["id"] == args.task_id:
            r.update(updates)
            found = True
    if not found:
        print(f"ERROR: task {args.task_id} not found in tasks.jsonl")
        sys.exit(1)
    with open(f"{board}/tasks.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"tasks.jsonl updated {args.task_id}: {sorted(updates)}")

    # 2) Live DuckDB store
    con = duckdb.connect(f"{board}/board.db")
    cur = con.execute("SELECT id FROM tasks WHERE id = ?", [args.task_id])
    if cur.fetchone() is None:
        print(
            f"ERROR: task {args.task_id} not in board.db — JSONL updated but DB "
            "missing; re-run migrate-board-to-duckdb.py export"
        )
        con.close()
        sys.exit(1)
    sets = ", ".join(f"{k} = ?" for k in updates)
    con.execute(
        f"UPDATE tasks SET {sets} WHERE id = ?",
        [*updates.values(), args.task_id],
    )
    con.close()
    print("board.db tasks updated")


if __name__ == "__main__":
    main()
