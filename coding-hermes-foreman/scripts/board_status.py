#!/usr/bin/env python3
"""DuckDB board-v2 status read — counts by status, meta row, last events.

Usage: python3 board_status.py [board_dir]
Defaults: board_dir=.coding-hermes/board  (run from repo root)

Why this script exists: the board consistency gate is run every tick, and the
schema has two traps discovered by trial and error:
- The meta table is named `board`, NOT `board_meta`.
- The `board` meta row is POSITIONAL, not key/value: (name, project_type,
  home_id, last_tick, ticks_total, ticks_idle, cooldown, ..., last_commit,
  updated_at). The 5th field is ticks_total, the 9th-ish is last_commit.
- tasks columns: id, title, status, priority, complexity, depends_on, blocks,
  primary_model, primary_provider, fallback_model, fallback_provider,
  reasoning, capability_tags, worker_status, dispatched_at, completed_at,
  attempts, exit_code, commit_hash, files_changed, lines_added, lines_removed,
  guard_result, ci_result, worker_summary, foreman_note, blocked_reason,
  review_notes, created_at, updated_at, blocked_since.
  No `task` or `name` column — id is the task ID (e.g. UI-09).
- Maintenance-tick discipline: when no status changed, do NOT re-export
  parquet / advance ticks_total (single-write discipline, T116/T120/T132
  precedent). Only write when a task changed status or a real event happened.
"""
import duckdb, os, sys

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.coding-hermes/board'
    con = duckdb.connect(os.path.join(root, 'board.db'), read_only=True)
    print('tables:', con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall())
    print('status counts:', con.execute(
        "SELECT status, count(*) FROM tasks GROUP BY status ORDER BY 1").fetchall())
    print('in_progress:', con.execute(
        "SELECT id, title FROM tasks WHERE status='in_progress'").fetchall())
    try:
        print('meta:', con.execute("SELECT * FROM board LIMIT 5").fetchall())
    except Exception as e:
        print('meta read err:', e)
    print('last events:', con.execute(
        "SELECT id, event_type, task_id, tick_number FROM events ORDER BY id DESC LIMIT 5").fetchall())

if __name__ == '__main__':
    main()
