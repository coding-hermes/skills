#!/usr/bin/env python3
"""Full-state read of a DuckDB foreman board — board header + ALL task rows + fixtures.

Why this exists: `scripts/read_duckdb_board.py` only returns the latest EVENTS.
A sound Step-1 decision (0 real pending vs fixtures-only, E2E next-window,
blocked reasons, NEVER-DONE state) needs the TASKS table rows (foreman_note,
status, blocked_reason) and the FIXTURES table — none of the bundled scripts
dump them. Hand-written queries per tick burn time and risk `python3 -c`
scanner blocks in cron mode.

Usage (cron-safe — run as a FILE, never inline `python3 -c`):
  python3 read_duckdb_board_full.py <repo-path>      # e.g. ~/<project>
  python3 read_duckdb_board_full.py                   # default: .

Prints (all read-only, safe against a live sibling foreman's write handle):
  - board header row        (ticks_total / ticks_idle / last_commit / last_tick)
  - ALL tasks rows          (id, status, title, foreman_note, blocked_reason, commit_hash, ...)
  - fixtures table          (active recurring fixtures — E2E-001, NEVER-DONE, ...)
  - event count + max tick_number + max rowid  (tick numbering ground truth)

Pitfalls honored:
  - Pass the REPO path, NOT the board.db path (script appends
    `.coding-hermes/board/board.db` itself; passing the .db yields
    `IO Error: Cannot open file "...board.db/.coding-hermes/board/board.db"`).
  - read_only=True avoids file-lock contention with a live sibling.
  - board.db is DuckDB, NOT SQLite — `sqlite3` on it fails.

Proven: terminal-jail tick #89 (2026-08-03) — hand-written variant of this
script resolved 0-real-pending + E2E-001 next-window #92-97 + 3 blocked
in one pass.
"""
import os
import sys


def main() -> int:
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    db = os.path.join(repo.rstrip("/"), ".coding-hermes", "board", "board.db")
    if not os.path.exists(db):
        print("NO BOARD DB at", db)
        return 1
    try:
        import duckdb
    except ImportError:
        print("duckdb module not installed — try the board venv: ~/.hermes/venvs/board/bin/python3")
        return 1
    con = duckdb.connect(db, read_only=True)

    print("=== BOARD (header) ===")
    try:
        cols = [c[0] for c in con.execute("DESCRIBE board").fetchall()]
        for r in con.execute("SELECT * FROM board").fetchall():
            print(dict(zip(cols, r)))
    except Exception as e:
        print("ERR:", e)

    print("\n=== TASKS ===")
    try:
        cols = [c[0] for c in con.execute("DESCRIBE tasks").fetchall()]
        rows = con.execute("SELECT * FROM tasks").fetchall()
        for r in rows:
            print(dict(zip(cols, r)))
    except Exception as e:
        print("ERR:", e)

    print("\n=== FIXTURES ===")
    try:
        cols = [c[0] for c in con.execute("DESCRIBE fixtures").fetchall()]
        for r in con.execute("SELECT * FROM fixtures").fetchall():
            print(dict(zip(cols, r)))
    except Exception as e:
        print("ERR:", e)

    print("\n=== EVENTS (count / max tick / max id) ===")
    try:
        print(con.execute("SELECT COUNT(*) FROM events").fetchall())
        print(con.execute("SELECT MAX(tick_number), MAX(rowid) FROM events").fetchall())
    except Exception as e:
        print("ERR:", e)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
