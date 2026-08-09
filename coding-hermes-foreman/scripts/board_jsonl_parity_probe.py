#!/usr/bin/env python3
"""Board parity probe for DuckDB v2.1 JSONL-tracked boards (events.jsonl vs board.db).

Every idle/light tick on a JSONL-tracked board (git ls-files shows
events.jsonl/board.jsonl/tasks.jsonl tracked, board.db untracked) should verify
the JSONL mirror and the DuckDB cache agree before appending a new event.
Previously each tick re-derived this probe in /tmp (board events cited a
phantom "board_parity_probe.py"). Use this canonical script instead.

Reads board.db READ-ONLY via the duckdb module (the board venv has it:
~/.hermes/venvs/board/bin/python3) with a sqlite3 fallback. Prints both row
counts + max event ids and exits 0 on MATCH, 1 on DIVERGENCE.

Usage:
  ~/.hermes/venvs/board/bin/python3 board_jsonl_parity_probe.py [BOARD_DIR]

Example (ring-runner tick 67):
  ~/.hermes/venvs/board/bin/python3 board_jsonl_parity_probe.py \
    ~/ring-runner/.coding-hermes/board
  -> engine: duckdb | jsonl rows: 108 max id: 113 | db rows: 108 max id: 113 |
     parity: MATCH

Notes:
- "Known gaps" (event ids present in neither store, e.g. old tracked-markdown
  rows that never migrated) are expected, NOT divergence — both stores agree,
  that's the parity that matters.
- board.db is a local query cache; events.jsonl + board.jsonl are the
  git-tracked current-state source (see references/board-db-lag-jsonl-authority.md).
  A DIVERGENCE means the append script failed mid-write (stray events.jsonl
  line) — trim `head -n -1` and re-append, per references/board-jsonl-mirror-str-int-pitfall.md.
"""
import json
import os
import sys


def main() -> int:
    board = sys.argv[1] if len(sys.argv) > 1 else '.coding-hermes/board'
    events_path = os.path.join(board, 'events.jsonl')

    with open(events_path) as f:
        jsonl_ids = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                jsonl_ids.append(json.loads(line).get('id'))
            except Exception:
                pass

    engine = None
    db_rows = db_max = None
    try:
        import duckdb
        con = duckdb.connect(os.path.join(board, 'board.db'), read_only=True)
        db_rows = con.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        db_max = con.execute('SELECT MAX(id) FROM events').fetchone()[0]
        con.close()
        engine = 'duckdb'
    except Exception as e1:
        try:
            import sqlite3
            con = sqlite3.connect(os.path.join(board, 'board.db'))
            db_rows = con.execute('SELECT COUNT(*) FROM events').fetchone()[0]
            db_max = con.execute('SELECT MAX(id) FROM events').fetchone()[0]
            con.close()
            engine = 'sqlite'
        except Exception as e2:
            print('PARITY PROBE ERROR duckdb:', e1)
            print('PARITY PROBE ERROR sqlite:', e2)
            return 1

    jmax = max(jsonl_ids) if jsonl_ids else None
    print('engine:', engine)
    print('jsonl rows:', len(jsonl_ids), 'max id:', jmax)
    print('db rows:', db_rows, 'max id:', db_max)
    match = len(jsonl_ids) == db_rows and jmax == db_max
    print('parity:', 'MATCH' if match else 'DIVERGENCE')
    return 0 if match else 1


if __name__ == '__main__':
    sys.exit(main())
