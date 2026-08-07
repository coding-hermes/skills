#!/usr/bin/env python3
"""One-shot tick-event append for JSONL-canonical foreman boards WITHOUT board.jsonl.

Boards migrated under JSONL-NORM-001 may keep the header ONLY in board.db's `board`
table. The stock append_board_event.py assumes a board.jsonl header file exists and
crashes (FileNotFoundError) AFTER appending events.jsonl + inserting board.db —
leaving partial state and a non-zero exit. This script does the full append in one
pass: events.jsonl (tracked) -> board.db events (untracked) -> board header UPDATE.

Usage: copy to /tmp/<tickprefix>_append.py, edit the CONFIG block, then
  source ~/.hermes/venvs/board/bin/activate && python3 /tmp/<tickprefix>_append.py
"""
import json
from datetime import datetime, timezone

# --- CONFIG: edit per project/tick ---
BOARD = "~/get-h3/<repo>/.coding-hermes/board"  # <repo>/.coding-hermes/board
DETAIL = "/tmp/<tickprefix>_detail.json"                 # event detail JSON object (write_file it first)
TICK = 84                                                # this tick's number
PRE_HEAD = "<pre-tick HEAD sha>"                         # `git rev-parse HEAD` BEFORE appending
NAMESPACE = "<board-namespace>"                          # board table namespace (NOT display name)
TICKS_TOTAL = 84                                         # prior total + 1
TICKS_IDLE = 1                                           # idle: prior+1; productive: prior (don't fight it)
# --- END CONFIG ---

EVENTS = f"{BOARD}/events.jsonl"
DB = f"{BOARD}/board.db"
TS = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000")

with open(DETAIL) as f:
    detail = json.load(f)
detail_json = json.dumps(detail, ensure_ascii=False)

# next id from JSONL (source of truth) — never from DB auto-increment
max_id = 0
with open(EVENTS) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
            if e.get("id", 0) > max_id:
                max_id = e["id"]
        except json.JSONDecodeError:
            print(f"WARN malformed line: {line[:60]}")
next_id = max_id + 1
print(f"next id: {next_id} (max {max_id})")

event = {
    "id": next_id,
    "timestamp": TS,
    "event_type": "audit",
    "task_id": None,
    "actor": "foreman",
    "detail": detail_json,
    "tick_number": TICK,
}
with open(EVENTS, "a") as f:
    f.write(json.dumps(event, ensure_ascii=False) + "\n")
print(f"events.jsonl appended id={next_id} tick={TICK}")

import duckdb

con = duckdb.connect(DB)
con.execute(
    "INSERT INTO events (id, timestamp, event_type, task_id, actor, detail, tick_number) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)",
    [next_id, TS, "audit", None, "foreman", detail_json, TICK],
)
print("board.db events inserted")
con.execute(
    "UPDATE board SET last_tick=?, updated_at=?, ticks_total=?, ticks_idle=?, last_commit=? "
    "WHERE namespace=?",
    [TS, TS, TICKS_TOTAL, TICKS_IDLE, PRE_HEAD, NAMESPACE],
)
print(f"board header updated: ticks_total={TICKS_TOTAL} ticks_idle={TICKS_IDLE} last_commit={PRE_HEAD}")
print(con.execute("SELECT project, namespace, ticks_total, ticks_idle, last_commit FROM board").fetchall())
con.close()
print("DONE — verify with board_jsonl_parity_probe.py, commit events.jsonl ONLY, push, phase-2 last_commit")
