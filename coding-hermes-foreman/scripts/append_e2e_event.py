#!/usr/bin/env python3
"""Append an e2e_verified event (task_id set) to a board-v2 JSONL board + best-effort board.db insert.

WHY: append_board_event.py hardcodes event_type="audit"/task_id=None, so E2E fixture
ticks need a FIRST event carrying the task id (e.g. E2E-001) logged before the audit event.

USAGE:
  uv run --with duckdb python3 scripts/append_e2e_event.py <repo_path> <tick> <detail.json> [task_id]

  - repo_path: absolute path to the project repo (board at .coding-hermes/board/)
  - tick:      tick number (int)
  - detail.json: path to a JSON file with the event detail object (write via write_file, no shell quoting)
  - task_id:   default "E2E-001"

MECHANICS (proven crier ticks 72-102):
  - events.jsonl is the AUTHORITATIVE git-tracked store; board.db is a best-effort mirror.
  - new id = MAX(existing id)+1 — json.loads per line tolerates BOTH "id": 87 and "id":87 forms.
  - board.db is a DUCKDB file despite the .db extension: plain INSERT INTO via the duckdb
    module, NEVER sqlite3 ("file is not a database"), NEVER INSERT OR REPLACE
    (events table has no PK constraint -> Binder Error).
  - Order: run this FIRST, then the one-shot append_board_event.py for the audit event
    (it auto-picks the next id). Then verify JSONL max id == board.db max id via
    read_duckdb_board.py. If the JSONL line appended but the DB insert failed, backfill
    with a small script that plain-INSERTs the LAST events.jsonl line — do NOT re-append.
"""
import json
import sys
import datetime
import os

if len(sys.argv) < 4:
    print(__doc__)
    sys.exit(1)

repo = sys.argv[1]
tick = int(sys.argv[2])
detail_path = sys.argv[3]
task_id = sys.argv[4] if len(sys.argv) > 4 else "E2E-001"

board = os.path.join(repo, ".coding-hermes", "board")
events_path = os.path.join(board, "events.jsonl")
db_path = os.path.join(board, "board.db")

with open(events_path) as f:
    lines = [l for l in f.read().splitlines() if l.strip()]
ids = [json.loads(l)["id"] for l in lines]
new_id = max(ids) + 1
print(f"max existing id: {max(ids)}, new id: {new_id}")

detail = json.load(open(detail_path))
event = {
    "id": new_id,
    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
    "event_type": "e2e_verified",
    "task_id": task_id,
    "actor": "foreman",
    "detail": json.dumps(detail, ensure_ascii=False),
    "tick_number": tick,
}
with open(events_path, "a") as f:
    f.write(json.dumps(event, ensure_ascii=False) + "\n")
print("JSONL appended, id", new_id)

try:
    import duckdb
    con = duckdb.connect(db_path)
    con.execute(
        "INSERT INTO events (id, timestamp, event_type, task_id, actor, detail, tick_number) VALUES (?,?,?,?,?,?,?)",
        [event["id"], event["timestamp"], event["event_type"], event["task_id"], event["actor"], event["detail"], event["tick_number"]],
    )
    con.close()
    print("board.db insert ok")
except Exception as e:
    print("board.db insert skipped/failed:", e)
