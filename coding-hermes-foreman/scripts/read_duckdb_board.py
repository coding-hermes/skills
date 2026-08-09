#!/usr/bin/env python3
"""Read latest events from a migrated DuckDB foreman board (read-only).

Usage: uv run --with duckdb python3 read_duckdb_board.py <repo-path> [limit]

Bare `python3 <script>` fails with ModuleNotFoundError on hosts where the
system interpreter lacks duckdb — wrap with `uv run --with duckdb`
(cron-safe; see references/duckdb-board-cron-query.md) or use the pre-built
board venv `~/.hermes/venvs/board/bin/python` (the only local python with
duckdb; the project's own .venv lacks it — proven: muster tick 85). Proven:
h3-shim tick #172, muster tick 85.

⚠️ Pass the REPO path, NOT the board.db path. The script appends
`.coding-hermes/board/board.db` itself — passing the .db file yields a
confusing `IO Error: Cannot open file "...board.db/.coding-hermes/board/board.db": Not a directory`.
Fix: `read_duckdb_board.py <repo-path>` (proven: ring-runner tick 38, 2026-08-02).

Safe against a live sibling foreman: read_only=True avoids file-lock
contention on board.db (a live foreman holds a write handle). Cron-safe
(no python3 -c — run the file directly).
"""
import duckdb, sys

repo = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3
db = f"{repo.rstrip('/')}/.coding-hermes/board/board.db"
con = duckdb.connect(db, read_only=True)
tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
print("tables:", tables)
if "events" in tables:
    print("event cols:", [c[0] for c in con.execute("DESCRIBE events").fetchall()])
    rows = con.execute(f"SELECT * FROM events ORDER BY rowid DESC LIMIT {limit}").fetchall()
    for r in rows:
        print(r)
con.close()
