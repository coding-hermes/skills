#!/usr/bin/env python3
"""Phase 2 (post-commit) last_commit sync for DuckDB boards — coding-hermes-foreman ticks.

DB-only: updates the `board` table header row; does NOT re-export JSONL and does NOT
make a second commit (scheduler repo convention — see references/
scheduler-project-e2e-verification.md, item 5 of "Board update flow").

Usage:
  ~/.hermes/venvs/board/bin/python3 scheduler-phase2-last-commit.py <board.db> <new-hash> [project-name]

Args:
  board.db     path to .coding-hermes/board/board.db (DUCKDB, not sqlite)
  new-hash     full or short git hash of the commit just pushed
  project-name optional; defaults to 'Coding Hermes Scheduler'; auto-derives the
  row's project name when the board has EXACTLY ONE row (Rabbit-Hole and other
  single-project boards) — omit the arg and it still targets the right row.
  A wrong-case project arg silently zero-matches (rabbit-hole-foreman-ops:
  'Rabbit-Hole' ≠ 'rabbit-hole'), so derive-don't-guess.

⚠️ DRIVER TRAP (proven tick #224): board.db is DUCKDB — stdlib sqlite3 fails with
"DatabaseError: file is not a database". Run with the board venv's python which has
the duckdb module. sqlite3 is only correct for the LIVE DAEMON db
(~/.hermes/coding-hermes/scheduler.db, storm-watch queries).
"""
import datetime
import sys

import duckdb

DEFAULT_PROJECT = "Coding Hermes Scheduler"


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "usage: scheduler-phase2-last-commit.py <board.db> <new-hash> [project-name]",
            file=sys.stderr,
        )
        return 2
    db = sys.argv[1]
    commit = sys.argv[2]
    explicit_project = sys.argv[3] if len(sys.argv) > 3 else None

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(sep=" ")
    con = duckdb.connect(db)
    try:
        project = explicit_project
        if project is None:
            rows = con.execute("SELECT project FROM board").fetchall()
            if len(rows) == 1:
                project = rows[0][0]
                print(f"auto-derived project name: {project!r}")
            else:
                project = DEFAULT_PROJECT
        con.execute(
            "UPDATE board SET last_commit = ?, updated_at = ? WHERE project = ?",
            [commit, now, project],
        )
        row = con.execute(
            "SELECT project, last_commit, updated_at FROM board WHERE project = ?",
            [project],
        ).fetchone()
        if row is None:
            print(f"WARNING: no board row found for project {project!r}", file=sys.stderr)
            return 1
        print("board row:", row)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
