#!/usr/bin/env python3
"""Read fixture rows from a DuckDB board's fixtures.parquet.

WHY: read_duckdb_board.py (coding-hermes-board skill) throws
`Binder Error: Cannot mix values of type VARCHAR and INTEGER_LITERAL in COALESCE`
on its FIXTURES section for parquet-tracked boards (events+tasks still print fine).
This is the workaround: read fixtures.parquet directly. Proven warpfs ticks 59-60.

USAGE (board venv has duckdb):
  ~/.hermes/venvs/board/bin/python3 read_board_fixtures.py <board-dir>
  e.g. read_board_fixtures.py ~/warpfs/.coding-hermes/board

Fixture rows are usually minimal (id, title, description, active, created_at) —
they gate self-pause (E2E-001 / GITREINS-JUDGE / NEVER-DONE active => 0 real
pending => policy cooldown correct).
"""
import json
import sys

import duckdb

board_dir = sys.argv[1] if len(sys.argv) > 1 else ".coding-hermes/board"
path = f"{board_dir.rstrip('/')}/fixtures.parquet"

con = duckdb.connect()
rows = con.execute(f"SELECT * FROM read_parquet('{path}')").fetchall()
cols = [d[0] for d in con.description]
for r in rows:
    d = dict(zip(cols, r))
    print(json.dumps(d, default=str))
print(f"--- {len(rows)} fixture rows ---")
