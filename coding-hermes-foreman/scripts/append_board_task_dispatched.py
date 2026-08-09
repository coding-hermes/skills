#!/usr/bin/env python3
"""Append a task_dispatched event to a JSONL-tracked DuckDB v2.1 board + update the tasks row.

For JSONL-tracked boards (.coding-hermes/board/ with events.jsonl / tasks.jsonl / board.jsonl).
append_board_task_completed.py is COMPLETION-ONLY (requires a commit hash, flips the row to
complete) — use THIS script for the dispatch moment (worker spawned, still in flight).
Verified shape: dexdat-core tick #138 (event id 15).

Usage:
  python3 append_board_task_dispatched.py REPO TASK_ID TICK_NUMBER MODEL PROVIDER PID

Conventions:
- event id: MAX(id)+1 across events.jsonl (authoritative — never reuse).
- event shape: {"id", "timestamp", "event_type": "task_dispatched", "task_id",
  "actor": "foreman", "detail": <JSON-ENCODED STRING, not an object>, "tick_number"}.
  detail must be json.dumps(...) of the payload — prior dispatch events store the whole
  dict as a string, and readers json.loads it.
- tasks.jsonl row: worker_status -> "dispatched", dispatched_at = now, attempts += 1.
- Does NOT bump ticks_total: dispatch-only ticks don't bump the header; the COMPLETING
  tick does (via append_board_task_completed.py). See dexdat-core tick #137: 135 -> 137.
- Does NOT touch board.db (JSONL is the source of truth; the completion script does the
  best-effort duckdb sync).
- stdlib-only (json, datetime) — system python3 works; no duckdb needed.

After running, commit with explicit files (never the dir; board.db is gitignored):
  git add -f .coding-hermes/board/events.jsonl .coding-hermes/board/tasks.jsonl
"""
import argparse
import datetime
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", help="absolute path to the repo (board at <repo>/.coding-hermes/board/)")
    ap.add_argument("task_id")
    ap.add_argument("tick", type=int)
    ap.add_argument("model")
    ap.add_argument("provider")
    ap.add_argument("pid", type=int)
    args = ap.parse_args()

    bdir = f"{args.repo.rstrip('/')}/.coding-hermes/board"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.000000")

    with open(f"{bdir}/events.jsonl") as f:
        events = [json.loads(l) for l in f if l.strip()]
    nid = max(e["id"] for e in events) + 1

    detail = json.dumps({
        "model": args.model,
        "provider": args.provider,
        "pid": args.pid,
        "task": args.task_id,
        "tick": args.tick,
    })

    event = {
        "id": nid,
        "timestamp": now,
        "event_type": "task_dispatched",
        "task_id": args.task_id,
        "actor": "foreman",
        "detail": detail,
        "tick_number": args.tick,
    }

    with open(f"{bdir}/events.jsonl", "a") as f:
        f.write(json.dumps(event, separators=(",", ":")) + "\n")

    with open(f"{bdir}/tasks.jsonl") as f:
        tasks = [json.loads(l) for l in f if l.strip()]
    for t in tasks:
        if t["id"] == args.task_id:
            t["worker_status"] = "dispatched"
            t["dispatched_at"] = now
            t["attempts"] = int(t.get("attempts") or 0) + 1
    with open(f"{bdir}/tasks.jsonl", "w") as f:
        for t in tasks:
            f.write(json.dumps(t, separators=(",", ":")) + "\n")

    print(f"event id={nid} appended; tasks.jsonl {args.task_id} worker_status=dispatched attempts="
          f"{[t['attempts'] for t in tasks if t['id'] == args.task_id][0]}")


if __name__ == "__main__":
    main()
