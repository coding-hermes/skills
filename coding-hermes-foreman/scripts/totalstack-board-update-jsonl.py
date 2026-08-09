#!/usr/bin/env python3
"""TotalStack foreman board update — JSONL-direct variant (proven tick #82).

Usage:
  python3 totalstack-board-update-jsonl.py <TICK> <PRE_TICK_HEAD> \
      [--detail "event detail"] [--no-idle]

Alternative to scripts/totalstack-board-update.py when board.db consistency is NOT
needed: writes directly to the TRACKED JSONL mirror (events.jsonl append + board.jsonl
header rewrite) with SYSTEM python3 — no duckdb venv, no COPY syntax, no parquet.
Produces the same minimal 2-file diff (board.jsonl + events.jsonl, 2 insertions/1
deletion, zero reorder churn — proven tick #82, first-try).

⚠️ Does NOT touch board.db (gitignored cache). Use the canonical duckdb script instead
if a later tick must read the new event/tick from board.db. ⚠️ Not idempotent: if the
script fails midway or you re-run it, the header double-bumps and a duplicate event is
appended — reset first by restoring board.jsonl from `git checkout` (events.jsonl append
can be trimmed by removing the last line) before re-running.

Steps:
  1. Append one event row to events.jsonl (id = max(id)+1, tick_number = TICK)
  2. Rewrite board.jsonl header: last_tick/updated_at = now, ticks_total+1,
     ticks_idle+1 (skip with --no-idle), last_commit = PRE_TICK_HEAD
     (one-behind-HEAD is the CORRECT steady state, not a lag)
  3. Print the new header + event id for verification
"""
import argparse
import datetime
import json
import os
import sys

BOARD = '~/totalstack/.coding-hermes/board'
EVENTS = os.path.join(BOARD, 'events.jsonl')
HEADER = os.path.join(BOARD, 'board.jsonl')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('tick', type=int, help='tick number, e.g. 82')
    ap.add_argument('pre_tick_head', help='current git HEAD before this tick\'s commit')
    ap.add_argument('--detail', default='tick update (see board events)',
                    help='event detail string (gate results, corrections, etc.)')
    ap.add_argument('--no-idle', action='store_true', help='do not increment ticks_idle')
    args = ap.parse_args()

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(EVENTS) as f:
        events = [json.loads(l) for l in f if l.strip()]
    next_id = max((e.get('id') or 0) for e in events) + 1
    event = {
        "id": next_id,
        "timestamp": now,
        "event_type": "audit",
        "task_id": None,
        "actor": "foreman",
        "detail": args.detail,
        "tick_number": args.tick,
    }
    with open(EVENTS, 'a') as f:
        f.write(json.dumps(event) + '\n')

    with open(HEADER) as f:
        hdr = json.load(f)
    hdr['last_tick'] = now
    hdr['ticks_total'] = hdr.get('ticks_total', 0) + 1
    if not args.no_idle:
        hdr['ticks_idle'] = hdr.get('ticks_idle', 0) + 1
    hdr['last_commit'] = args.pre_tick_head
    hdr['updated_at'] = now
    with open(HEADER, 'w') as f:
        json.dump(hdr, f)
        f.write('\n')

    print(f"event id={next_id} tick={args.tick} appended")
    print(f"header: ticks_total={hdr['ticks_total']} ticks_idle={hdr['ticks_idle']} "
          f"last_commit={hdr['last_commit']} last_tick={hdr['last_tick']}")
    print("then: git add .coding-hermes/board/board.jsonl .coding-hermes/board/events.jsonl "
          "&& git commit -F <msg file> (Co-authored-by trailer)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
