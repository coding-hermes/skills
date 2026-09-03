#!/usr/bin/env python3
"""Backfill events missing from board.db (untracked cache) from events.jsonl (canonical).

Usage: python3 backfill_events_db_from_jsonl.py <board_dir>
       (run with the board venv: source ~/.hermes/venvs/board/bin/activate)

Inserts JSONL event rows whose id is absent from the board.db events table,
using the exact schema columns (id, timestamp, event_type, task_id, actor,
detail, tick_number). Prints the inserted ids; then run the parity probe:

    python3 ~/.hermes/skills/coding-hermes-foreman/scripts/board_jsonl_parity_probe.py <board_dir>
    # expect: parity: MATCH

Proven: deepseek-dashboard tick 177 (2026-08-19) — rows 187-189 backfilled after
appenders continued the DB sequence from 186 while JSONL was 3 rows ahead.
"""
import json
import sys
import duckdb

if len(sys.argv) != 2:
    sys.exit(__doc__)

board = sys.argv[1].rstrip("/")
db = duckdb.connect(f"{board}/board.db")
have = {r[0] for r in db.execute("SELECT id FROM events").fetchall()}
want = []
with open(f"{board}/events.jsonl") as f:
    for line in f:
        e = json.loads(line)
        if e["id"] not in have:
            want.append(e)
print("rows to insert:", [e["id"] for e in want])
for e in want:
    db.execute(
        "INSERT INTO events (id, timestamp, event_type, task_id, actor, detail, tick_number) VALUES (?,?,?,?,?,?,?)",
        (e["id"], e.get("timestamp"), e.get("event_type"), e.get("task_id"),
         e.get("actor"), e.get("detail"), e.get("tick_number")),
    )
db.close()
print("done — run the parity probe to confirm MATCH")
