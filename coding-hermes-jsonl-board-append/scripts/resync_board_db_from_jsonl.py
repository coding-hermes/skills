#!/usr/bin/env python3
"""Resync board.db (events + tasks) from JSONL — for headerless JSONL-canonical boards.

Why: on headerless boards (no board.jsonl; header lives only in board.db's `board`
table) append_board_task_completed.py crashes at the board.jsonl read AFTER landing
its events.jsonl + tasks.jsonl writes, so its duckdb sync (events insert + tasks
UPDATE) NEVER runs. board.db then lags tasks.jsonl (missing status flips, missing
rows). This script wipes events + tasks in board.db and re-inserts them from the
JSONL files (source of truth), preserving the board header row untouched.

Usage:
  ~/.hermes/venvs/board/bin/python3 resync_board_db_from_jsonl.py <board-dir>
  # or with the venv on PATH: PATH=~/.hermes/venvs/board/bin:$PATH python3 ...

Run AFTER all appends of the tick (per-task appends, dispatch event, final audit),
BEFORE the parity probe. Then verify:
  board_jsonl_parity_probe.py <board-dir>   # expect MATCH (counts + max id)
"""
import json
import sys

import duckdb

BOARD = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else ".coding-hermes/board"
con = duckdb.connect(f"{BOARD}/board.db")

# --- events: fixed schema columns from schema.sql ---
events = []
with open(f"{BOARD}/events.jsonl") as f:
    for line in f:
        line = line.strip()
        if line:
            events.append(json.loads(line))
con.execute("DELETE FROM events")
con.executemany(
    "INSERT INTO events (id, timestamp, event_type, task_id, actor, detail, tick_number) VALUES (?,?,?,?,?,?,?)",
    [
        (
            e["id"],
            e["timestamp"],
            e["event_type"],
            e.get("task_id"),
            e.get("actor"),
            e["detail"],
            e.get("tick_number"),
        )
        for e in events
    ],
)
print(f"events resynced: {len(events)}")

# --- tasks: columns from the live schema; 'None' string -> NULL; JSON arrays pass through ---
tasks = []
with open(f"{BOARD}/tasks.jsonl") as f:
    for line in f:
        line = line.strip()
        if line:
            tasks.append(json.loads(line))
cols = [r[0] for r in con.execute("DESCRIBE tasks").fetchall()]
con.execute("DELETE FROM tasks")
for t in tasks:
    vals = [None if v is None or v == "None" else v for v in (t.get(c) for c in cols)]
    placeholders = ",".join(["?"] * len(cols))
    con.execute(f"INSERT INTO tasks ({','.join(cols)}) VALUES ({placeholders})", vals)
print(f"tasks resynced: {len(tasks)}")

print("header:", con.execute("SELECT project, namespace, ticks_total, ticks_idle, last_commit FROM board").fetchall())
print("status:", con.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall())
con.close()
print("RESYNC DONE — verify with board_jsonl_parity_probe.py <board-dir>")
