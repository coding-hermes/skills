#!/usr/bin/env python3
"""DuckDB board tick-update helper (coding-hermes fleet, board v2.1).

Inserts an audit event (explicit MAX(id)+1), optionally updates task
foreman_note columns, then exports tasks/events/fixtures/board to JSONL
(the git-tracked mirror post-INFRA-013). Run with the board venv python
(~/.hermes/venvs/board/bin/python3) — stdlib + duckdb only, no yaml needed.

Usage:
  duckdb-board-audit-event.py --db <board.db> --tick N --detail <detail.json> \
      [--notes <notes.json>] [--event-type audit] [--actor foreman]

  --db      path to .coding-hermes/board/board.db (board dir is derived from it)
  --tick    tick number (goes into the events.tick_number column)
  --detail  JSON file: the event detail object (stored as the detail column)
  --notes   optional JSON map {task_id: new_foreman_note} to update task rows

Flow (proven scheduler tick #212, 2026-08-02):
  1. Repair NULL-id event rows (assign MAX(id)+1 in tick_number order) —
     id-less INSERTs silently write NULL-id rows (no DEFAULT nextval in DuckDB)
  2. Insert event with explicit id = MAX(id)+1, naive-UTC timestamp string
  3. Apply foreman_note updates (fixture notes like E2E-001 / NEVER-DONE)
  4. COPY each table to <board_dir>/<table>.jsonl (FORMAT JSONL), abs paths
  5. Verify round-trip via read_json_auto counts

Post-run steps (foreman's job): git add the JSONL files (plain `git add` works —
they're negated in .gitignore), commit with Co-authored-by trailer, push, then
Phase 2: UPDATE board SET last_commit='<new hash>', updated_at=<naive-UTC> — DB-only,
no second commit.
"""
import argparse
import datetime
import json
import os
import duckdb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True, help='path to .coding-hermes/board/board.db')
    ap.add_argument('--tick', type=int, required=True)
    ap.add_argument('--detail', required=True, help='JSON file: event detail object')
    ap.add_argument('--notes', default=None, help='JSON file: {task_id: foreman_note}')
    ap.add_argument('--event-type', default='audit')
    ap.add_argument('--actor', default='foreman')
    args = ap.parse_args()

    board_dir = os.path.dirname(os.path.abspath(args.db))
    detail = json.load(open(args.detail))
    notes = json.load(open(args.notes)) if args.notes else {}
    now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    con = duckdb.connect(args.db, read_only=False)

    # 1. repair NULL-id rows before inserting
    null_rows = con.execute(
        "SELECT id, tick_number FROM events WHERE id IS NULL ORDER BY tick_number"
    ).fetchall()
    if null_rows:
        max_id = con.execute("SELECT COALESCE(MAX(id),0) FROM events").fetchone()[0]
        for (_rid, tno) in null_rows:
            max_id += 1
            con.execute(
                "UPDATE events SET id = ? WHERE tick_number = ? AND id IS NULL",
                [max_id, tno],
            )
        print(f"Repaired {len(null_rows)} NULL-id rows")

    # 2. insert event with explicit id
    max_id = con.execute("SELECT COALESCE(MAX(id),0) FROM events").fetchone()[0]
    new_id = max_id + 1
    con.execute(
        "INSERT INTO events (id, event_type, task_id, actor, detail, tick_number, timestamp) "
        "VALUES (?,?,?,?,?,?,?)",
        [new_id, args.event_type, None, args.actor, json.dumps(detail), args.tick, str(now_utc)],
    )
    print(f"Inserted event id={new_id} tick={args.tick}")

    # 3. foreman_note updates
    for tid, note in notes.items():
        con.execute("UPDATE tasks SET foreman_note = ? WHERE id = ?", [note, tid])
        print(f"Updated note: {tid}")

    # 4. export JSONL (absolute paths — relative paths pollute the board cache)
    for tbl in ['tasks', 'events', 'fixtures', 'board']:
        con.execute(f"COPY {tbl} TO ? (FORMAT JSONL)", [os.path.join(board_dir, f'{tbl}.jsonl')])
        cnt = con.execute(
            "SELECT count(*) FROM read_json_auto(?)",
            [os.path.join(board_dir, f'{tbl}.jsonl')],
        ).fetchone()[0]
        print(f"Exported {tbl}.jsonl: {cnt} rows")

    con.close()
    print("Board update complete")


if __name__ == '__main__':
    main()
