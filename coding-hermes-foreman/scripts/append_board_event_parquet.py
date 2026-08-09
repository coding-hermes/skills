#!/usr/bin/env python3
"""Append a foreman audit event to a PARQUET-tracked DuckDB board in one shot.

For boards whose git-tracked representation is parquet (events.parquet,
tasks.parquet, schema.sql — NO events.jsonl / board.jsonl mirror). Check the
tracked set FIRST: `git ls-files .coding-hermes/board/` (proven: terminal-jail
tick #73, muster tick 82, gitreins-poc tick 98). Do NOT use
`scripts/append_board_event.py` on these repos — it is JSONL-only and
hard-fails with FileNotFoundError: .../events.jsonl.

Usage (cron-safe: no python3 -c, no heredocs, no curl pipes):
  # 1. write the detail object to a file (write_file, avoids shell quoting)
  # 2. run — the board venv python works and avoids a uv network fetch in cron mode
  #    (proven: terminal-jail tick #78): ~/.hermes/venvs/board/bin/python3 append_board_event_parquet.py ...
  #    The uv form below also works when no duckdb env is already present:
  uv run --with duckdb python3 append_board_event_parquet.py REPO TICK_NUMBER DETAIL_JSON \
      [--ts 'YYYY-MM-DD HH:MM:SS.mmmmmm'] \
      [--export-tasks] \
      [--set last_commit=abc123] [--set ticks_idle=27]

  REPO           absolute path to the project repo
  TICK_NUMBER    the tick number for this audit event
  DETAIL_JSON    path to a JSON file holding the event `detail` object
  --ts           event timestamp; defaults to naive-UTC now
  --export-tasks also COPY tasks -> tasks.parquet (only when task rows changed)
  --set          repeatable KEY=VALUE pairs merged into the board header row
                 (allowed keys: ticks_total, ticks_idle, last_commit, cooldown_s,
                 service_port, service_url, health_endpoint, git_branch, git_remote).
                 ticks_total/ticks_idle default to +1 increments when not given.

Pipeline (per references/duckdb-board-parquet-tracked-set.md):
  1. Repair NULL-id rows (safe no-op when all ids explicit; qualified-UPDATE
     form avoids DuckDB Binder 'Ambiguous reference to column name id').
  2. INSERT event with explicit id = MAX(id)+1 (never trust auto-increment;
     ref duckdb-board-events-id-sequence.md).
  3. UPDATE board header row (project name read from the table — varies by
     repo: 'Terminal-Jail', 'Muster', ... — never hardcode).
  4. COPY events -> events.parquet; tasks -> tasks.parquet only with
     --export-tasks. Never export board/fixtures (untracked noise: commit them
     and you pollute the mirror, leave them and git status stays dirty).

Afterwards: `git add` only the changed parquet files (binary size deltas),
commit with the Co-authored-by trailer, push. The Tier-2 auditor's 'No
supported source files found' warning is informational for parquet commits
(proven: terminal-jail tick #73 commit 34a9473).

Proven: terminal-jail tick #73 (2026-08-02) — event id 42, header ticks_total
73 / ticks_idle 27 / last_commit set, one commit + push, CI green.
"""
import argparse
import json
from datetime import datetime, timezone

ALLOWED_HEADER_KEYS = {
    "ticks_total", "ticks_idle", "last_commit", "cooldown_s",
    "service_port", "service_url", "health_endpoint", "git_branch", "git_remote",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("tick_number", type=int)
    ap.add_argument("detail_json")
    ap.add_argument("--ts", default=None, help="timestamp, default naive-UTC now")
    ap.add_argument("--export-tasks", action="store_true",
                    help="also COPY tasks to tasks.parquet (task rows changed)")
    ap.add_argument("--set", action="append", default=[], help="KEY=VALUE header updates")
    args = ap.parse_args()

    board = f"{args.repo.rstrip('/')}/.coding-hermes/board"
    db = f"{board}/board.db"

    ts = args.ts or datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S.000000")

    with open(args.detail_json) as f:
        detail = json.load(f)
    detail_json = json.dumps(detail, ensure_ascii=False)

    import duckdb
    con = duckdb.connect(db)

    # 1. repair NULL-id rows — qualified form avoids DuckDB Binder ambiguity;
    #    no-op when all ids are explicit (safe to keep).
    con.execute("""
        UPDATE events SET id = (SELECT COALESCE(MAX(events.id),0) + sub.rn FROM events) FROM (
            SELECT id AS sid, row_number() OVER (ORDER BY tick_number, timestamp) AS rn
            FROM events WHERE id IS NULL
        ) sub WHERE events.id IS NULL
    """)

    # 2. insert event with explicit MAX(id)+1
    max_id = con.execute("SELECT COALESCE(MAX(id),0) FROM events").fetchone()[0]
    next_id = max_id + 1
    con.execute(
        "INSERT INTO events (id, timestamp, event_type, task_id, actor, detail, tick_number) "
        "VALUES (?, ?, 'audit', NULL, 'foreman', ?, ?)",
        [next_id, ts, detail_json, args.tick_number],
    )
    print(f"inserted event id={next_id} tick={args.tick_number}")

    # 3. header update — read project name from the table (varies by repo)
    row = con.execute(
        "SELECT project, ticks_total, ticks_idle FROM board LIMIT 1"
    ).fetchone()
    project, ticks_total, ticks_idle = row
    overrides = {}
    for kv in args.set:
        k, _, v = kv.partition("=")
        if not k or k not in ALLOWED_HEADER_KEYS:
            print(f"WARN: skipping --set {kv} (unknown key)")
            continue
        overrides[k] = int(v) if (v.isdigit() and k in ("ticks_total", "ticks_idle", "cooldown_s")) else v
    if "ticks_total" not in overrides:
        overrides["ticks_total"] = ticks_total + 1
    if "ticks_idle" not in overrides:
        overrides["ticks_idle"] = ticks_idle + 1
    for k, v in overrides.items():
        con.execute(f"UPDATE board SET {k} = ? WHERE project = ?", [v, project])
    con.execute("UPDATE board SET last_tick = ?, updated_at = ? WHERE project = ?", [ts, ts, project])

    # 4. copy ONLY tracked tables to parquet
    con.execute(f"COPY events TO '{board}/events.parquet' (FORMAT PARQUET)")
    print("events.parquet exported")
    if args.export_tasks:
        con.execute(f"COPY tasks TO '{board}/tasks.parquet' (FORMAT PARQUET)")
        print("tasks.parquet exported")

    hdr = con.execute(
        "SELECT project, ticks_total, ticks_idle, last_commit, last_tick FROM board"
    ).fetchone()
    print("board header:", hdr)
    con.close()


if __name__ == "__main__":
    main()
