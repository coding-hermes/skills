#!/usr/bin/env python3
"""Diff board.db against the tracked parquet for a coding-hermes v2 board.

Usage:
  ~/.hermes/venvs/board/bin/python3 board-db-parquet-diff.py <board-dir>

Run BEFORE append_board_event_parquet.py. A stale board.db (lags the
tracked parquet after a sibling/PM export) will otherwise clobber the
git-tracked parquet with an incomplete task/event set on --export-tasks.

Exit codes: 0 = in sync, 1 = divergence (report printed), 2 = usage/setup.

Events are matched by (task_id, event_type, tick_number, timestamp) — NOT
by id, because ids can be renumbered by divergent exports (proven: warpfs
tick 65, GAP creates at parquet ids 22-24 vs board.db audits at ids 22-24).
"""
import duckdb
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: board-db-parquet-diff.py <board-dir>")
        return 2
    bd = sys.argv[1]
    db_path = os.path.join(bd, "board.db")
    tasks_pq = os.path.join(bd, "tasks.parquet")
    events_pq = os.path.join(bd, "events.parquet")
    for f in (db_path, tasks_pq, events_pq):
        if not os.path.exists(f):
            print(f"MISSING {f}")
            return 2

    con = duckdb.connect(db_path, read_only=True)
    pq = duckdb.connect()
    issues: list[str] = []

    # --- tasks ---
    db_tasks = set(r[0] for r in con.execute("SELECT id FROM tasks").fetchall())
    pq_tasks = set(
        r[0] for r in pq.execute("SELECT id FROM read_parquet(?)", [tasks_pq]).fetchall()
    )
    if db_tasks != pq_tasks:
        issues.append(
            f"TASKS diverge: board.db-only={sorted(db_tasks - pq_tasks)} "
            f"parquet-only={sorted(pq_tasks - db_tasks)}"
        )

    # --- events: count/max ---
    db_ev = con.execute(
        "SELECT COUNT(*), COALESCE(MAX(id),0) FROM events"
    ).fetchone()
    pq_ev = pq.execute(
        "SELECT COUNT(*), COALESCE(MAX(id),0) FROM read_parquet(?)", [events_pq]
    ).fetchone()
    if db_ev != pq_ev:
        issues.append(f"EVENTS count/max diverge: board.db={db_ev} parquet={pq_ev}")

    # --- events: content match (id-agnostic) ---
    db_events = set(
        tuple(r)
        for r in con.execute(
            "SELECT task_id, event_type, tick_number, CAST(timestamp AS VARCHAR) "
            "FROM events"
        ).fetchall()
    )
    pq_events = set(
        tuple(r)
        for r in pq.execute(
            "SELECT task_id, event_type, tick_number, CAST(timestamp AS VARCHAR) "
            "FROM read_parquet(?)",
            [events_pq],
        ).fetchall()
    )
    only_pq = pq_events - db_events
    only_db = db_events - pq_events
    if only_pq:
        issues.append(f"EVENTS in parquet missing from board.db: {sorted(only_pq)}")
    if only_db:
        issues.append(f"EVENTS in board.db missing from parquet: {sorted(only_db)}")

    con.close()
    pq.close()

    if issues:
        print("\n".join(issues))
        return 1
    print("board.db and tracked parquet in sync (tasks + events).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
