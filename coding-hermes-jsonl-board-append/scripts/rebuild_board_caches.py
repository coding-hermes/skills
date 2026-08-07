#!/usr/bin/env python3
"""Rebuild board.db + parquet caches from the JSONL canonical store (JSONL-NORM-001).

Usage:
  PATH=~/.hermes/venvs/board/bin:$PATH python3 rebuild_board_caches.py <repo-dir>
  e.g. python3 rebuild_board_caches.py ~/get-h3/sdk-typescript

Reads .coding-hermes/board/{events.jsonl,tasks.jsonl} (authoritative, git-tracked),
rebuilds the board.db events/tasks tables, then exports events.parquet/tasks.parquet
(untracked caches). Safe ordering: JSONL rows are loaded into memory and JSON-typed
columns detected BEFORE any DELETE runs, so a mid-loop failure cannot wipe the tables
(h3-sdk-typescript tick #79: DELETE-then-fail left tasks EMPTY).

Known pitfalls handled:
- tasks JSON-typed columns (worker_summary, guard_result, ci_result, review_notes,
  blocked_reason, blocked_since, dispatched_at) need json.dumps() or DuckDB dies
  "ConversionException: Malformed JSON at byte 0".
- complexity may arrive as a string ("low") in JSONL — int-coerced.
- events detail may be a JSON string or object — normalized.
"""
import json
import sys
from pathlib import Path

import duckdb


def load_jsonl(path: Path) -> list:
    rows = []
    for line in path.open():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main() -> int:
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    board = repo / ".coding-hermes" / "board"
    if not (board / "events.jsonl").exists() or not (board / "tasks.jsonl").exists():
        print(f"ERROR: {board} missing events.jsonl/tasks.jsonl — not a JSONL board?")
        return 2

    con = duckdb.connect(str(board / "board.db"))

    # detect JSON-typed columns in tasks BEFORE any DELETE
    json_cols = {
        r[0]
        for r in con.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='tasks' AND data_type='JSON'"
        ).fetchall()
    }
    print(f"JSON-typed task columns: {sorted(json_cols) or 'none'}")

    # --- events ---
    events = load_jsonl(board / "events.jsonl")
    con.execute("DELETE FROM events")
    for e in events:
        detail = e.get("detail")
        if isinstance(detail, (dict, list)):
            detail = json.dumps(detail)
        con.execute(
            "INSERT INTO events (id, timestamp, event_type, task_id, actor, detail, tick_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                e.get("id"),
                e.get("timestamp"),
                e.get("event_type"),
                e.get("task_id"),
                e.get("actor"),
                detail,
                e.get("tick_number"),
            ],
        )
    con.execute(
        f"COPY (SELECT * FROM events) TO '{board / 'events.parquet'}' (FORMAT PARQUET)"
    )

    # --- tasks ---
    tasks = load_jsonl(board / "tasks.jsonl")
    cols = [d[0] for d in con.execute("SELECT * FROM tasks LIMIT 0").description]
    con.execute("DELETE FROM tasks")
    for t in tasks:
        row = []
        for c in cols:
            v = t.get(c)
            if isinstance(v, (dict, list)):
                v = json.dumps(v)
            elif c in json_cols and v is not None:
                v = json.dumps(v)
            elif c == "complexity" and isinstance(v, str):
                try:
                    v = int(v)
                except ValueError:
                    v = None
            row.append(v)
        con.execute(
            f"INSERT INTO tasks ({','.join(cols)}) VALUES ({','.join(['?'] * len(cols))})",
            row,
        )
    con.execute(
        f"COPY (SELECT * FROM tasks) TO '{board / 'tasks.parquet'}' (FORMAT PARQUET)"
    )

    # --- verify: counts + a JSON-column roundtrip (parity probe is count-only) ---
    n_ev = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    n_ts = con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    ok_ev = n_ev == len(events)
    ok_ts = n_ts == len(tasks)
    print(f"events: db={n_ev} jsonl={len(events)} {'MATCH' if ok_ev else 'MISMATCH'}")
    print(f"tasks:  db={n_ts} jsonl={len(tasks)} {'MATCH' if ok_ts else 'MISMATCH'}")
    if json_cols:
        sample = con.execute(
            f"SELECT {sorted(json_cols)[0]} FROM tasks WHERE {sorted(json_cols)[0]} IS NOT NULL LIMIT 1"
        ).fetchone()
        if sample and sample[0]:
            print(f"roundtrip sample {sorted(json_cols)[0]}: {str(sample[0])[:80]}")
    con.close()
    return 0 if (ok_ev and ok_ts) else 1


if __name__ == "__main__":
    sys.exit(main())
