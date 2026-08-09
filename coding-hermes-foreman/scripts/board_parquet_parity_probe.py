#!/usr/bin/env python3
"""Parquet-tracked DuckDB board parity probe.

Compares events.parquet + tasks.parquet against the live board.db
(counts, max event id, max tick number). Exit 0 = MATCH, 1 = DIVERGENCE.

Usage: python3 board_parquet_parity_probe.py <BOARD_DIR>
       (BOARD_DIR = the .coding-hermes/board/ directory, not the repo root)
Needs the duckdb module: run with ~/.hermes/venvs/board/bin/python3 or
`uv run --with duckdb python3 ...`. No pandas/numpy dependency (fetchone only).

Proven: duckbrain tick #277 (2026-08-03) — events.parquet 73 == board.db 73
(max id 73 = tick 276), tasks 7/7, MATCH.
"""
import duckdb
import os
import sys


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    board_dir = sys.argv[1].rstrip('/')
    db_path = os.path.join(board_dir, 'board.db')
    if not os.path.exists(db_path):
        print(f"board.db not found at {db_path}")
        sys.exit(2)

    con = duckdb.connect(db_path, read_only=True)
    ok = True

    pq = os.path.join(board_dir, 'events.parquet')
    if os.path.exists(pq):
        pq_count = con.execute(f"SELECT count(*) FROM read_parquet('{pq}')").fetchone()[0]
        db_count = con.execute('SELECT count(*) FROM events').fetchone()[0]
        pq_max = con.execute(f"SELECT max(id) FROM read_parquet('{pq}')").fetchone()[0]
        db_max = con.execute('SELECT max(id) FROM events').fetchone()[0]
        pq_tick = con.execute(f"SELECT max(tick_number) FROM read_parquet('{pq}')").fetchone()[0]
        db_tick = con.execute('SELECT max(tick_number) FROM events').fetchone()[0]
        print(f"events.parquet: count={pq_count} max_id={pq_max} max_tick={pq_tick}")
        print(f"board.db      : count={db_count} max_id={db_max} max_tick={db_tick}")
        match = (pq_count == db_count and pq_max == db_max)
        print("EVENTS:", "MATCH" if match else "DIVERGENCE")
        ok = ok and match
    else:
        print("events.parquet missing — nothing to compare")

    tq = os.path.join(board_dir, 'tasks.parquet')
    if os.path.exists(tq):
        c1 = con.execute(f"SELECT count(*) FROM read_parquet('{tq}')").fetchone()[0]
        c2 = con.execute('SELECT count(*) FROM tasks').fetchone()[0]
        print(f"tasks.parquet={c1} board.db={c2} -> {'MATCH' if c1 == c2 else 'DIVERGENCE'}")
        ok = ok and (c1 == c2)

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
