#!/usr/bin/env python3
"""One-shot tick append for JSONL-canonical foreman boards that STILL HAVE a
board.jsonl header file (canopy-style: header lives in board.jsonl, not only in
board.db). Extends append_event_no_header.py for boards whose tracked set is
events.jsonl + tasks.jsonl + board.jsonl (+ fixtures.jsonl/schema.sql).

Also updates TASK ROWS in tasks.jsonl (dict.update preserves key order -> minimal
diff: existing keys keep position, new keys append at end). Untouched lines are
written back byte-identical.

Usage: copy to /tmp/<tickprefix>_append.py, edit the CONFIG block, then
  source ~/.hermes/venvs/board/bin/activate && python3 /tmp/<tickprefix>_append.py
"""
import json
from datetime import datetime, timezone

# --- CONFIG: edit per project/tick ---
BOARD = "~/<repo>/.coding-hermes/board"
TICK = 304
NAMESPACE = "home"                      # from board.jsonl header 'namespace'
TICKS_TOTAL = 304                       # prior total + 1
TICKS_IDLE = 0                          # productive: prior value (don't fight it)
LAST_COMMIT = "<sha of last WORK commit>"  # header last_commit LAGS one tick:
                                          # = last non-board commit (work commit),
                                          # NOT the board commit you're about to make
TASKS_UPDATES = {                       # task_id -> fields to set (omit for event-only)
    "TASK-01": {
        "status": "complete",
        "worker_status": "complete",
        "exit_code": 0,
        "guard_result": "PASS",
        "commit_hash": "<work commit sha or None for board-only ops tasks>",
        "completed_at": None,           # filled with TS below
        "updated_at": None,
        "foreman_note": "summary of verification",
    },
}
EVENT_SUMMARY = "Tick NNN — one-line summary of what was delivered + gates."
# --- END CONFIG ---

TS = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000")
# ⚠️ Match the BOARD's committed escape style: raw-UTF-8 (ensure_ascii=False) vs
# escaped \uXXXX (True). Check the last committed events.jsonl line first.

# ---------- 1. tasks.jsonl row updates ----------
TASKS = f"{BOARD}/tasks.jsonl"
if TASKS_UPDATES:
    with open(TASKS) as f:
        lines = f.readlines()
    out, updated = [], []
    for line in lines:
        s = line.strip()
        if not s:
            out.append(line)
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            out.append(line)
            continue
        if row.get("id") in TASKS_UPDATES:
            fields = dict(TASKS_UPDATES[row["id"]])
            fields["completed_at"] = fields.get("completed_at") or TS
            fields["updated_at"] = TS
            row.update(fields)
            updated.append(row["id"])
        out.append(json.dumps(row, ensure_ascii=False) + "\n")
    with open(TASKS, "w") as f:
        f.writelines(out)
    print(f"tasks.jsonl updated: {updated}")

# ---------- 2. events.jsonl append (next id from JSONL, never DB) ----------
EVENTS = f"{BOARD}/events.jsonl"
max_id = 0
with open(EVENTS) as f:
    for line in f:
        s = line.strip()
        if not s:
            continue
        try:
            e = json.loads(s)
            if e.get("id", 0) > max_id:
                max_id = e["id"]
        except json.JSONDecodeError:
            pass
next_id = max_id + 1
detail_obj = {"tick": TICK, "summary": EVENT_SUMMARY}
inner = {"event_type": "audit", "task_id": None, "actor": "foreman", "detail": detail_obj}
event = {
    "id": next_id,
    "timestamp": TS,
    "event_type": "audit",
    "task_id": None,
    "actor": "foreman",
    "detail": json.dumps(inner, ensure_ascii=False),
    "tick_number": TICK,
}
with open(EVENTS, "a") as f:
    f.write(json.dumps(event, ensure_ascii=False) + "\n")
print(f"events.jsonl appended id={next_id} tick={TICK}")

# ---------- 3. board.jsonl header (file, not just DB) ----------
HEADER = f"{BOARD}/board.jsonl"
with open(HEADER) as f:
    hdr = json.loads(f.readline())
hdr["last_tick"] = TS
hdr["ticks_total"] = TICKS_TOTAL
hdr["ticks_idle"] = TICKS_IDLE
hdr["last_commit"] = LAST_COMMIT
hdr["updated_at"] = TS
with open(HEADER, "w") as f:
    f.write(json.dumps(hdr, ensure_ascii=False) + "\n")
print(f"board.jsonl header: ticks_total={TICKS_TOTAL} ticks_idle={TICKS_IDLE} last_commit={LAST_COMMIT}")

# ---------- 4. board.db cache (untracked, rebuildable) ----------
import duckdb

con = duckdb.connect(f"{BOARD}/board.db")
con.execute(
    "INSERT INTO events (id, timestamp, event_type, task_id, actor, detail, tick_number) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)",
    [next_id, TS, "audit", None, "foreman", json.dumps(inner, ensure_ascii=False), TICK],
)
con.execute(
    "UPDATE board SET last_tick=?, updated_at=?, ticks_total=?, ticks_idle=?, last_commit=? "
    "WHERE namespace=?",
    [TS, TS, TICKS_TOTAL, TICKS_IDLE, LAST_COMMIT, NAMESPACE],
)
print("board.db cache synced")
con.close()
print("DONE — verify with jq (see SKILL.md), commit the 3 tracked files, push")
