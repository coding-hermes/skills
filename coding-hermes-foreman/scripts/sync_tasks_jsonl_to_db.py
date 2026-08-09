#!/usr/bin/env python3
"""sync_tasks_jsonl_to_db.py — heal board.db tasks table from tasks.jsonl.

JSONL is the git-tracked source of truth; board.db is a local cache that can
lag. Symptom: `update_board_task_notes.py` exits
`ERROR: task X not in board.db` — the row exists in tasks.jsonl but the DB
cache missed it (create_board_tasks.py skips the DB insert on
`Binder Error: no UNIQUE/PRIMARY KEY constraints`, so rows created that way
are JSONL-only from birth).

Inserts missing rows, updates changed fields on existing rows.
JSON-typed DuckDB columns (worker_summary, guard_result, ...) are
json.dumps-encoded — raw strings die
`ConversionException: Malformed JSON at byte 0`.

Usage (cron-safe — run with the board venv python, never bare python3):
  <board-venv>/bin/python3 sync_tasks_jsonl_to_db.py /path/to/repo

Proven: bunker tick #216 — GAP-003/004/005 rows JSONL-only; 4 inserted,
10 updated, board.db healed.
"""
import json
import sys
import duckdb

if len(sys.argv) != 2:
    print("usage: sync_tasks_jsonl_to_db.py <repo>")
    sys.exit(2)

board = f"{sys.argv[1].rstrip('/')}/.coding-hermes/board"

with open(f"{board}/tasks.jsonl") as f:
    rows = [json.loads(l) for l in f if l.strip()]

con = duckdb.connect(f"{board}/board.db")
cols = [r[0] for r in con.execute("DESCRIBE tasks").fetchall()]
json_cols = {r[0] for r in con.execute("DESCRIBE tasks").fetchall() if r[1] == "JSON"}

existing = {r[0] for r in con.execute("SELECT id FROM tasks").fetchall()}
print(f"DB has {len(existing)} tasks; JSONL has {len(rows)}")


def enc(col, v):
    if v is None:
        return None
    return json.dumps(v) if col in json_cols else v


inserted = 0
updated = 0
for r in rows:
    tid = r["id"]
    if tid not in existing:
        keys = [c for c in cols if c in r]
        vals = [enc(c, r[c]) for c in keys]
        con.execute(
            f"INSERT INTO tasks ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(keys))})",
            vals,
        )
        inserted += 1
    else:
        sets = []
        vals = []
        for c in cols:
            if c in r and c != "id":
                sets.append(f"{c} = ?")
                vals.append(enc(c, r[c]))
        if sets:
            con.execute(
                f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?",
                vals + [tid],
            )
            updated += 1

con.close()
print(f"inserted={inserted} updated={updated}")
