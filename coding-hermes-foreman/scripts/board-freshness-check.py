#!/usr/bin/env python3
"""Enter-tick board freshness check for parquet-only DuckDB boards.

Usage: ~/.hermes/venvs/board/bin/python3 board-freshness-check.py <repo>

Prints the live board.db header (last_tick, ticks_total, ticks_idle,
last_commit) vs git HEAD and a FRESH/STALE verdict.

STALE means the PRIOR tick skipped its phase-2 post-commit header UPDATE
(the recurring miss documented in rabbit-hole-foreman-ops.md — re-hit at
ticks #100/#102/#103/#107/#111, ~50% miss rate). Re-sync with
scheduler-phase2-last-commit.py <board.db> <new-hash>, or let the next
append's --set last_commit=<pre-commit HEAD> self-correct (which still
leaves the header one commit behind until phase-2 runs).

Caveat: the git-TRACKED board.parquet header is stale BY DESIGN
(tracked-stale, tick #91) — this script reads live board.db instead, so a
one-commit lag here is REAL drift, not the known-good parquet state.
"""
import subprocess
import sys

import duckdb


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: board-freshness-check.py <repo>")
        return 2
    repo = sys.argv[1]
    board_db = repo.rstrip("/") + "/.coding-hermes/board/board.db"
    try:
        con = duckdb.connect(board_db, read_only=True)
        row = con.execute(
            "SELECT last_tick, ticks_total, ticks_idle, last_commit FROM board"
        ).fetchone()
    except Exception as e:  # noqa: BLE001
        print(f"board read failed (is this a parquet-only DuckDB board?): {e}")
        return 1
    print(f"board header (last_tick, ticks_total, ticks_idle, last_commit): {row}")
    head = subprocess.run(
        ["git", "-C", repo, "log", "-1", "--format=%h"],
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()
    print(f"git HEAD: {head}")
    if row is not None and row[3] == head:
        print("FRESH")
        return 0
    print("STALE (prior tick skipped phase-2 post-commit UPDATE — re-sync with scheduler-phase2-last-commit.py or self-correct via next append --set last_commit)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
