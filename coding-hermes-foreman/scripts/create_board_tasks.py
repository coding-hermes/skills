#!/usr/bin/env python3
"""Create one or more tasks on a JSONL-tracked DuckDB foreman board in one shot.

Appends task rows to tasks.jsonl (tracked git mirror), inserts them into
board.db (gitignored live store, best-effort), and appends task_created
events to events.jsonl + board.db with explicit max-id sequence.

Usage (cron-safe: no python3 -c, no heredocs, no pipes):
  uv run --with duckdb python3 create_board_tasks.py REPO TICK_NUMBER TASKS_JSON [--reason '...']

  REPO          absolute path to the project repo
  TICK_NUMBER   tick number creating the tasks (stamped on events)
  TASKS_JSON    path to a JSON file: array of task dicts with fields
                id, title, priority, complexity, primary_model,
                primary_provider, reasoning, capability_tags, foreman_note
                (all other schema fields default sensibly)
  --reason      short source string for the task_created event detail
                (default: "foreman")

Event ids = MAX(id)+1 across events.jsonl (JSONL is the id authority).
Tasks whose ids already exist in tasks.jsonl are skipped (idempotent).
Ordering per board convention: task rows BEFORE the task_created events.

Proven: ring-runner tick 47 (2026-08-03) — RR-COV-01 + RR-GOV-01 created
from the idle deeper pass (Bane directive 2026-08 #1).
"""
import argparse
import json
from datetime import datetime


def load_rows(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def max_event_id(path):
    mid = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if e.get("id", 0) > mid:
                mid = e["id"]
    return mid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("tick_number", type=int)
    ap.add_argument("tasks_json")
    ap.add_argument("--reason", default="foreman")
    args = ap.parse_args()

    board = f"{args.repo.rstrip('/')}/.coding-hermes/board"
    tasks_path = f"{board}/tasks.jsonl"
    events_path = f"{board}/events.jsonl"
    db_path = f"{board}/board.db"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    with open(args.tasks_json) as f:
        new_tasks = json.load(f)

    existing_ids = {t["id"] for t in load_rows(tasks_path)}
    added = []
    for t in new_tasks:
        if t["id"] in existing_ids:
            print(f"skip existing {t['id']}")
            continue
        row = {
            "status": "pending",
            "blocks": None,
            "fallback_model": None,
            "fallback_provider": None,
            "worker_status": "pending",
            "dispatched_at": None,
            "completed_at": None,
            "attempts": 0,
            "exit_code": None,
            "commit_hash": None,
            "files_changed": None,
            "lines_added": 0,
            "lines_removed": 0,
            "guard_result": None,
            "ci_result": None,
            "worker_summary": None,
            "blocked_reason": None,
            "review_notes": None,
            "created_at": now,
            "updated_at": now,
            **t,
        }
        added.append(row)

    with open(tasks_path, "a") as f:
        for t in added:
            f.write(json.dumps(t, default=str, separators=(",", ":")) + "\n")
    print(f"tasks.jsonl: appended {len(added)} rows")

    next_id = max_event_id(events_path)
    events = []
    for t in added:
        next_id += 1
        events.append({
            "id": next_id,
            "timestamp": now,
            "event_type": "task_created",
            "task_id": t["id"],
            "actor": "foreman",
            "detail": json.dumps({"source": args.reason, "tick": args.tick_number}),
            "tick_number": args.tick_number,
        })
    with open(events_path, "a") as f:
        for ev in events:
            f.write(json.dumps(ev, default=str, separators=(",", ":")) + "\n")
    print(f"events.jsonl: appended {len(events)} task_created events")

    try:
        import duckdb
        con = duckdb.connect(db_path)
        cols = list(added[0].keys()) if added else []
        for t in added:
            con.execute(
                f"INSERT OR REPLACE INTO tasks ({','.join(cols)}) VALUES ({','.join(['?'] * len(cols))})",
                [t[c] for c in cols],
            )
        for ev in events:
            con.execute(
                "INSERT INTO events (id, timestamp, event_type, task_id, actor, detail, tick_number) "
                "VALUES (?,?,?,?,?,?,?)",
                [ev["id"], ev["timestamp"], ev["event_type"], ev["task_id"], ev["actor"], ev["detail"], ev["tick_number"]],
            )
        con.close()
        print("board.db: tasks + events inserted")
    except Exception as exc:
        print(f"WARN: board.db insert skipped ({exc}) - JSONL mirror has the rows; re-sync later")

    print("done")


if __name__ == "__main__":
    main()
