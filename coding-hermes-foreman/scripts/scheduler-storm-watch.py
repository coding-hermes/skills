#!/usr/bin/env python3
"""Scheduler storm-watch probe — coding-hermes-scheduler foreman ticks.

Queries the LIVE daemon DB (~/.hermes/coding-hermes/scheduler.db) for:
  - duplicate concurrent running ticks per project (INFRA-003 runningSet proof)
  - total running ticks
  - last-24h outcome distribution
  - most recent ticks for this project (confirms the current tick is running)

The repo-root scheduler.db is a 0-byte placeholder — never query that one.
Run with the board venv: ~/.hermes/venvs/board/bin/python3 <this-file>
Proven: tick #202 (2026-08-02). No sqlite3 CLI on the host; stdlib module only.
"""
import sqlite3

conn = sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
cur = conn.cursor()

cur.execute("SELECT project_name, COUNT(*) c FROM ticks WHERE status='running' GROUP BY project_name HAVING c>1")
dups = cur.fetchall()
print("DUPLICATE RUNNING TICKS:", dups if dups else "0 rows (clean)")

cur.execute("SELECT COUNT(*) FROM ticks WHERE status='running'")
print("TOTAL RUNNING:", cur.fetchone()[0])

cur.execute("SELECT outcome, COUNT(*) FROM ticks WHERE spawned_at > datetime('now','-24 hours') GROUP BY outcome")
print("LAST 24H OUTCOMES:", cur.fetchall())

cur.execute("SELECT id, project_name, status, outcome, spawned_at FROM ticks WHERE project_name='coding-hermes-scheduler' ORDER BY id DESC LIMIT 3")
for row in cur.fetchall():
    print("MY TICKS:", row)

conn.close()
