#!/usr/bin/env python3
"""Board status probe for DuckDB boards (.coding-hermes/board/board.db).

Cron-safe: run as a FILE, never inline `python3 -c` (blocked in cron mode).
Usage: python3 board_status_query.py [repo-path]   (default: .)

Prints: task status counts, board table row, events count, last 5 events.
This is the quick board-health probe for the 16-gate audit — it answers
"94 complete + 22 pending, 0 in_progress, events 31" without hand-writing
a query. NOTE: board.db is DuckDB, NOT SQLite — sqlite3 on it fails with
"file is not a database".
"""
import os
import sys


def main() -> int:
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    db = os.path.join(repo, ".coding-hermes", "board", "board.db")
    if not os.path.exists(db):
        print("NO BOARD DB at", db)
        return 1
    try:
        import duckdb
    except ImportError:
        print("duckdb module not installed — pip install duckdb")
        return 1
    con = duckdb.connect(db, read_only=True)
    print("tasks by status:", con.execute(
        "SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall())
    print("board row:", con.execute(
        "SELECT * FROM board LIMIT 1").fetchall())
    print("events count:", con.execute(
        "SELECT COUNT(*) FROM events").fetchall())
    print("last 5 events:")
    for r in con.execute(
            "SELECT id, event_type, task_id, tick_number FROM events "
            "ORDER BY id DESC LIMIT 5").fetchall():
        print(" ", r)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
