#!/usr/bin/env python3
"""Heal board.db tasks table from tasks.jsonl (authoritative) — tolerant of legacy rows.

Why: append_board_task_completed.py / sync_tasks_jsonl_to_db.py can die on
boards whose JSONL carries legacy rows that violate the schema types:
  - complexity as a LIST (crier CR-GAP-014..018: capability_tags stuffed into
    the complexity slot) -> 'Unimplemented type for cast (VARCHAR[] -> TINYINT)'
  - complexity as string 'low' / 'high' (totalstack TS-GAP-019)
  - a DELETE-then-INSERT resync that aborts mid-way leaves the tasks table
    PARTIALLY EMPTY (events table unaffected if resynced separately).

DESCRIBE-driven coercion: numeric cols (int or NOT-NULL default; LIST -> None),
array cols (list, or scalar -> [scalar]), JSON cols (json.dumps), everything
else str/json.dumps. Drops + recreates the tasks table from schema.sql when
the row count diverges from tasks.jsonl.

Usage (board venv python, never bare python3):
  ~/.hermes/venvs/board/bin/python3 heal_tasks_from_jsonl.py <board-dir>
Then run board_jsonl_parity_probe.py <board-dir> (expect parity MATCH).

Proven: crier tick 253 (2026-08-24) — two failed resyncs left 13/79 rows;
heal restored 79, CR-FEAT-021 row complete@6c7600f, parity MATCH.
"""
import json
import sys

import duckdb

BOARD = sys.argv[1].rstrip("/")
con = duckdb.connect(f"{BOARD}/board.db")

rows = [json.loads(l) for l in open(f"{BOARD}/tasks.jsonl") if l.strip()]
desc_rows = con.execute("DESCRIBE tasks").fetchall()
desc = {r[0]: r[1] for r in desc_rows}
numeric_cols = {c for c, t in desc.items() if t.upper() in ("TINYINT", "SMALLINT", "INTEGER", "BIGINT", "UBIGINT", "HUGEINT")}
array_cols = {c for c, t in desc.items() if t.endswith("[]")}
json_cols = {c for c, t in desc.items() if t == "JSON"}
cols = list(desc.keys())


def coerce(col, v):
    if v is None:
        return None
    if col in numeric_cols:
        if isinstance(v, list):
            v = None
        if v is None:
            return 0 if col != "complexity" else 3  # NOT NULL columns need a sane default
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0 if col != "complexity" else 3
    if col in array_cols:
        if isinstance(v, list):
            return v
        return [v]
    if col in json_cols or not isinstance(v, str):
        return json.dumps(v)
    return v


n = con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
print(f"tasks in DB before heal: {n}")
if n != len(rows):
    con.execute("DROP TABLE IF EXISTS tasks")
    ddl = open(f"{BOARD}/schema.sql").read()
    block = ddl[ddl.index("CREATE TABLE IF NOT EXISTS tasks"):]
    block = block[:block.index(");") + 2]
    con.execute(block)

ph = ",".join("?" for _ in cols)
con.executemany(
    f"INSERT INTO tasks ({','.join(cols)}) VALUES ({ph})",
    [[coerce(c, t.get(c)) for c in cols] for t in rows],
)
print(f"tasks healed: {len(rows)} rows")
con.close()
print("DONE — run board_jsonl_parity_probe.py to confirm MATCH")
