#!/usr/bin/env python3
"""Enter-tick board-state probe for PARQUET-tracked DuckDB boards.

One-shot read of <repo>/.coding-hermes/board/board.db: board header row(s),
tasks (id/status/title), events tail (id/tick_number/event_type/task_id),
and optionally the last event's full detail JSON (--detail) for same-type
shape mirroring before writing your own event.

WHY: the git-tracked parquet exports (events.parquet/tasks.parquet) do NOT
carry the live header (last_commit freshness vs `git log -1 --format='%h'`),
and pure-parquet boards have no events.jsonl/board.jsonl mirror. This is the
enter-tick read the scheduler-idle-light-tick-recipe Step 1 needs, in one
call instead of a hand-written /tmp probe per tick.

Usage (cron-safe — no -c, no pipes, no execute_code):
  ~/.hermes/venvs/board/bin/python3 board-state-probe.py /path/to/repo [--detail]
  # or: ~/gitreins-poc/.venv/bin/python board-state-probe.py ...
  # or: uv run --with duckdb python3 board-state-probe.py ...

REPO is the ABSOLUTE project path (script appends
.coding-hermes/board/board.db). Never pass the board dir itself. Boards
whose header UPDATE filters on `namespace` still show the header fine here
(we print ALL board rows, avoiding namespace guessing).

Proven: terminal-jail tick #123 (2026-08-04) — header last_commit freshness
check, 0-real-pending confirmation, and the last-idle-event detail dump in
one run.
"""
import argparse
import json
import os
import sys


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('repo', help='absolute path to the project repo')
    ap.add_argument('--detail', action='store_true',
                    help='also print the last event detail JSON (pretty)')
    args = ap.parse_args()

    db = os.path.join(args.repo, '.coding-hermes', 'board', 'board.db')
    if not os.path.exists(db):
        sys.exit(f'board.db not found: {db} (JSONL-tracked board? use jq on tasks.jsonl/events.jsonl instead)')

    import duckdb  # interpreter must have duckdb (board venv / gitreins-poc venv / uv --with duckdb)
    con = duckdb.connect(db, read_only=True)

    print('--- BOARD HEADER (all rows) ---')
    cols = [d[0] for d in con.execute('DESCRIBE board').fetchall()]
    for row in con.execute('SELECT * FROM board').fetchall():
        for name, val in zip(cols, row):
            print(f'{name} = {val}')

    print('--- TASKS (id, status, title) ---')
    for r in con.execute('SELECT id, status, title FROM tasks ORDER BY id').fetchall():
        print(r)

    print('--- EVENTS TAIL (id, tick_number, event_type, task_id) ---')
    for r in con.execute('SELECT id, tick_number, event_type, task_id FROM events ORDER BY id DESC LIMIT 6').fetchall():
        print(r)

    if args.detail:
        print('--- LAST EVENT DETAIL ---')
        r = con.execute('SELECT detail FROM events ORDER BY id DESC LIMIT 1').fetchone()
        print(json.dumps(json.loads(r[0]), indent=1))


if __name__ == '__main__':
    main()
