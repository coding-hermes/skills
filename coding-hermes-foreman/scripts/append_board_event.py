#!/usr/bin/env python3
"""Append a foreman audit event to a DuckDB foreman board in ONE shot.

Keeps the three board artifacts in sync (the tracked JSONL mirror is
authoritative; board.db is the live gitignored read source):

  1. .coding-hermes/board/events.jsonl   <- appended (tracked in git)
  2. .coding-hermes/board/board.db       <- INSERT into events table (gitignored)
  3. .coding-hermes/board/board.jsonl    <- header merge (ticks_total/ticks_idle/last_commit)

Usage (cron-safe: no python3 -c, no heredocs, no curl pipes):
  # 1. write the detail object to a file (write_file, avoids shell quoting)
  # 2. run:
  uv run --with duckdb python3 append_board_event.py REPO TICK_NUMBER DETAIL_JSON \
      [--ts 'YYYY-MM-DD HH:MM:SS.mmmmmm'] \
      [--set last_commit=abc123] [--set ticks_idle=10] [--set ticks_total=34]

  REPO         absolute path to the project repo
  TICK_NUMBER  the tick number for this audit event
  DETAIL_JSON  path to a JSON file holding the event `detail` object
  --ts         event timestamp; defaults to now
  --set        repeatable KEY=VALUE pairs merged into the board.jsonl header
               (e.g. last_commit=<pre-tick HEAD>, ticks_total, ticks_idle)

Event id is computed as MAX(id)+1 across events.jsonl (explicit sequence per
duckdb-board-events-id-sequence.md — never trust auto-increment; ids are the
sync key between DB and mirror).

The DuckDB INSERT is best-effort: if a live sibling foreman holds the write
handle and the insert locks, the JSONL mirror (tracked artifact) is still
updated and the DB can be re-synced next tick. Verify sync afterwards with
`python3 ~/.hermes/skills/coding-hermes-foreman/scripts/read_duckdb_board.py REPO 1`
(⚠️ the read script is NOT executable — direct invocation without the
`python3` prefix fails with `Permission denied`; proven: bunker tick #159).

Proven: ring-runner tick 34 (2026-08-02) — DB + JSONL tails matched exactly
(max id 78 = tick 34) after one run.
"""
import argparse
import json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("tick_number", type=int)
    ap.add_argument("detail_json")
    ap.add_argument("--ts", default=None, help="timestamp, default now")
    ap.add_argument("--set", action="append", default=[], help="KEY=VALUE header updates")
    args = ap.parse_args()

    board = f"{args.repo.rstrip('/')}/.coding-hermes/board"
    events = f"{board}/events.jsonl"
    header = f"{board}/board.jsonl"
    db = f"{board}/board.db"

    ts = args.ts
    if ts is None:
        from datetime import datetime

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.000000")

    with open(args.detail_json) as f:
        detail = json.load(f)
    detail_json = json.dumps(detail, ensure_ascii=False)

    # explicit id sequence: MAX(id)+1 across JSONL (source of truth)
    max_id = 0
    with open(events) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if e.get("id", 0) > max_id:
                    max_id = e["id"]
            except json.JSONDecodeError:
                print(f"WARN: skipping malformed events.jsonl line: {line[:80]}")
    next_id = max_id + 1

    event = {
        "id": next_id,
        "timestamp": ts,
        "event_type": "audit",
        "task_id": None,
        "actor": "foreman",
        "detail": detail_json,
        "tick_number": args.tick_number,
    }
    with open(events, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"events.jsonl appended id={next_id} tick={args.tick_number}")

    # best-effort DuckDB insert (lock-safe vs live sibling)
    try:
        import duckdb

        con = duckdb.connect(db)
        con.execute(
            "INSERT INTO events (id, timestamp, event_type, task_id, actor, detail, tick_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [next_id, ts, "audit", None, "foreman", detail_json, args.tick_number],
        )
        con.close()
        print("board.db inserted")
    except Exception as exc:  # ImportError or file-lock contention
        print(f"WARN: board.db insert skipped ({exc}) — JSONL mirror already has the event; re-sync later")

    # header merge
    with open(header) as f:
        hdr = json.load(f)
    hdr["last_tick"] = ts
    hdr["updated_at"] = ts
    for kv in args.set:
        k, _, v = kv.partition("=")
        if not k:
            print(f"WARN: skipping malformed --set {kv}")
            continue
        if v.isdigit():
            v = int(v)
        hdr[k] = v
    with open(header, "w") as f:
        json.dump(hdr, f, default=str)
        f.write("\n")
    print("board.jsonl header updated")


if __name__ == "__main__":
    main()
