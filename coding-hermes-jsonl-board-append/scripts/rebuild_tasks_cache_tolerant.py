#!/usr/bin/env python3
"""Tolerant tasks-table cache rebuild for JSONL-canonical boards.

Usage: python3 rebuild_tasks_cache_tolerant.py <board-dir>

Rebuilds ONLY the tasks table in board.db from tasks.jsonl, tolerating
legacy row shapes that kill the stock scripts:
- ints/strings in VARCHAR[] columns (depends_on/blocks/capability_tags/files_changed)
- JSON-typed columns (detected via information_schema; string/int values
  json.dumps()-wrapped before INSERT)
- rows missing optional fields (all gets default to None)

Events table: use the stock rebuild_board_caches.py for events (it rebuilds
events fine and only dies on tasks) or resync_board_db_from_jsonl.py; this
script leaves events untouched.

Verified: hermes-canopy tick 410 (2026-08-25) — 199/199 tasks rows inserted
after rebuild_board_caches.py died with ConversionException (INTEGER ->
VARCHAR[]) and resync_board_db_from_jsonl.py died with KeyError 'timestamp'
(after wiping the events table — always re-run the full rebuild after that).
Full write-up: references/tolerant-tasks-cache-rebuild.md in this skill.

Parity verification after: board_jsonl_parity_probe.py <board-dir> (in the
coding-hermes-foreman skill scripts dir) must print MATCH.
"""
import json
import sys
import duckdb

COLS = [
    'id', 'title', 'status', 'priority', 'complexity', 'depends_on', 'blocks',
    'primary_model', 'primary_provider', 'fallback_model', 'fallback_provider',
    'reasoning', 'capability_tags', 'worker_status', 'model_used', 'provider_used',
    'dispatched_at', 'completed_at', 'attempts', 'exit_code', 'api_calls',
    'commit_hash', 'files_changed', 'lines_added', 'lines_removed', 'guard_result',
    'ci_result', 'worker_summary', 'foreman_note', 'blocked_reason', 'review_notes',
    'created_at', 'updated_at', 'blocked_since',
]
LIST_COLS = {'depends_on', 'blocks', 'capability_tags', 'files_changed'}


def lst(v):
    """Coerce any value to a VARCHAR[]-compatible list or None."""
    if v is None:
        return None
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def main():
    if len(sys.argv) != 2:
        print(f'usage: {sys.argv[0]} <board-dir>')
        return 2
    board = sys.argv[1].rstrip('/')
    con = duckdb.connect(board + '/board.db')

    # JSON-typed columns vary per board — always detect, never hardcode.
    json_cols = {
        r[0] for r in con.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='tasks' AND data_type='JSON'"
        ).fetchall()
    }
    print('JSON-typed columns:', sorted(json_cols))

    rows = [json.loads(l) for l in open(board + '/tasks.jsonl') if l.strip()]
    con.execute('DELETE FROM tasks')
    sql = ('INSERT INTO tasks (' + ','.join(COLS) + ') VALUES ('
           + ','.join(['?'] * len(COLS)) + ')')
    n = 0
    for r in rows:
        try:
            vals = []
            for c in COLS:
                v = r.get(c)
                if c in LIST_COLS:
                    v = lst(v)
                elif c in json_cols and v is not None and isinstance(v, (str, int, float)):
                    v = json.dumps(v)
                vals.append(v)
            con.execute(sql, tuple(vals))
            n += 1
        except Exception as e:
            print('SKIP', r.get('id'), '->', str(e)[:90])
    print(f'inserted {n} of {len(rows)}')
    print('tasks in db:', con.execute('SELECT count(*) FROM tasks').fetchone()[0])


if __name__ == '__main__':
    main()
