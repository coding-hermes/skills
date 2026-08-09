#!/usr/bin/env python3
"""TotalStack foreman board update — canonical one-script flow (proven ticks #44-#55).

Usage:
  ~/.hermes/venvs/board/bin/python3 totalstack-board-update.py <TICK> <PRE_TICK_HEAD> \
      [--detail "event detail"] [--no-idle]

One script, one DuckDB connection — never split (proven first-try correct across 10+
corrections). Steps:
  1. Print pre-tick header snapshot (needed for deterministic reset on mid-script failure)
  2. INSERT events row, explicit id = COALESCE(MAX(id),0)+1 (sequence-bypass discipline)
  3. UPDATE board header: last_tick (TIMESTAMP col in this repo — NOT an integer tick
     number), ticks_total+1, ticks_idle+1 (skip with --no-idle for productive ticks),
     last_commit = PRE_TICK_HEAD (the current HEAD; the owning commit gets recorded next
     tick — one-behind-HEAD is the CORRECT steady state, not a lag), updated_at
  4. Export all 4 JSONL via SELECT * — NEVER hand-picked column lists (tick #48: partial
     columns silently truncate the tracked jsonl). ORDER BY id except board (no id column)
  5. Round-trip verify: db count vs file count per table + print last event + header

Pre-flight (mandatory): snapshot the header with a read-only query BEFORE running and
KEEP the output — if the update fails mid-script after the header UPDATE landed, reset
deterministically (never just re-run):
  DELETE FROM events WHERE tick_number = <TICK>;
  UPDATE board SET last_tick=<pre>, ticks_total=<pre>, ticks_idle=<pre>,
    last_commit=<pre>, updated_at=<pre>;
then re-run. After the script: `git diff .coding-hermes/board/` — minimal diff
(board.jsonl + events.jsonl) is normal; long rows replaced by short rows = truncation.
Commit ONLY the changed JSONL files with the Co-authored-by trailer.
"""
import argparse
import datetime
import json
import os
import sys

import duckdb

REPO = '~/totalstack'
DB = os.path.join(REPO, '.coding-hermes/board/board.db')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('tick', type=int, help='tick number, e.g. 55')
    ap.add_argument('pre_tick_head', help='current git HEAD before this tick\'s commit')
    ap.add_argument('--detail', default='tick update (see board events)',
                    help='event detail string (gate results, corrections, etc.)')
    ap.add_argument('--no-idle', action='store_true', help='do not increment ticks_idle')
    args = ap.parse_args()

    now = datetime.datetime.now().replace(microsecond=0)
    con = duckdb.connect(DB)

    # 1. snapshot header (pre-tick) for the record / deterministic reset reference
    hdr = con.execute(
        "SELECT last_tick, ticks_total, ticks_idle, cooldown_s, last_commit, updated_at FROM board"
    ).fetchone()
    print("PRE-TICK HEADER:", dict(zip(
        ['last_tick', 'ticks_total', 'ticks_idle', 'cooldown_s', 'last_commit', 'updated_at'], hdr)))

    # 2. event insert (explicit id discipline)
    next_id = con.execute("SELECT COALESCE(MAX(id),0)+1 FROM events").fetchone()[0]
    con.execute(
        "INSERT INTO events (id, tick_number, event_type, task_id, actor, detail, timestamp) "
        "VALUES (?, ?, 'audit', NULL, 'foreman', ?, ?)",
        [next_id, args.tick, args.detail, now])

    # 3. header update
    idle_delta = 0 if args.no_idle else 1
    con.execute(
        "UPDATE board SET last_tick = ?, ticks_total = ticks_total + 1, "
        "ticks_idle = ticks_idle + ?, last_commit = ?, updated_at = ? WHERE project = 'TotalStack'",
        [now, idle_delta, args.pre_tick_head, now])

    # 4. JSONL exports — SELECT * (full columns), ORDER BY id except board (no id column)
    for t in ['board', 'events', 'tasks', 'fixtures']:
        order = '' if t == 'board' else ' ORDER BY id'
        con.execute(
            f"COPY (SELECT * FROM {t}{order}) TO '{REPO}/.coding-hermes/board/{t}.jsonl' (FORMAT JSON)")

    # 5. round-trip verify
    ok = True
    for t in ['board', 'events', 'tasks', 'fixtures']:
        db_n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        with open(f'{REPO}/.coding-hermes/board/{t}.jsonl') as f:
            rows = [json.loads(l) for l in f if l.strip()]
        match = db_n == len(rows)
        ok = ok and match
        print(f"{t}: db={db_n} file={len(rows)} {'OK' if match else 'MISMATCH'}")
        if t == 'events' and rows:
            print(f"  last event: id={rows[-1].get('id')} tick={rows[-1].get('tick_number')}")
        if t == 'board' and rows:
            print(f"  header: ticks_total={rows[0].get('ticks_total')} "
                  f"ticks_idle={rows[0].get('ticks_idle')} last_commit={rows[0].get('last_commit')}")
    con.close()
    print("OVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
