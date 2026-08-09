#!/usr/bin/env python3
"""Sync the JSONL mirror after append_board_event_parquet.py on parquet-tracked boards.

append_board_event_parquet.py writes board.db + exports events.parquet/tasks.parquet
but does NOT touch events.jsonl / board.jsonl. On parquet-tracked boards the JSONL
files are gitignored yet remain the READ authority (board.db lags — ref:
board-db-lag-jsonl-authority.md), and fleet convention keeps them in sync: the
tick event appears in events.jsonl even though only parquet is committed.

Run this AFTER append_board_event_parquet.py so all three artifacts agree
(board.db, parquet exports, JSONL mirror):

  python3 sync_board_jsonl_mirror.py REPO TICK_NUMBER DETAIL_JSON [--set last_commit=abc123]

  REPO           absolute path to the project repo
  TICK_NUMBER    tick number of the event just appended
  DETAIL_JSON    path to the SAME detail JSON file used for the parquet append
  --set          KEY=VALUE header overrides (last_commit, ticks_total, ticks_idle)

Behavior:
  1. appends the event to events.jsonl with id = MAX(id)+1 (keeps ids aligned with
     the parquet append — run the parquet script FIRST, pass the same detail file)
  2. rewrites the board.jsonl header row: last_tick/updated_at = now,
     ticks_total/ticks_idle = +1 each (unless overridden with --set), last_commit
     passed through only when --set explicitly (header last_commit lags one tick
     by convention — set it to the PREVIOUS tick's commit sha)

Stdlib-only (json + datetime) — no duckdb needed, cron-safe (no -c, no pipes).
Proven: warpfs tick 54 (2026-08-03) — manual one-shot replaced by this script.
"""
import argparse
import json
from datetime import datetime, timezone


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("tick_number", type=int)
    ap.add_argument("detail_json")
    ap.add_argument("--set", action="append", default=[])
    args = ap.parse_args()

    board = f"{args.repo.rstrip('/')}/.coding-hermes/board"
    now = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S.%f")

    with open(args.detail_json) as f:
        detail = json.load(f)
    detail_json = json.dumps(detail, ensure_ascii=False)

    overrides = {}
    for kv in args.set:
        k, _, v = kv.partition("=")
        if k:
            overrides[k] = int(v) if v.isdigit() else v

    # 1. append event to events.jsonl (id = max+1, matches the parquet insert)
    ev_path = f"{board}/events.jsonl"
    with open(ev_path) as f:
        lines = [l for l in f if l.strip()]
    ids = [int(json.loads(l)["id"]) for l in lines]
    next_id = max(ids) + 1
    event = {
        "id": next_id,
        "timestamp": now,
        "event_type": "audit",
        "task_id": None,
        "actor": "foreman",
        "detail": detail_json,
        "tick_number": args.tick_number,
    }
    with open(ev_path, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(f"events.jsonl appended id={next_id} (now {len(lines)+1} events)")

    # 2. rewrite board.jsonl header row
    # ⚠️ header is multi-line pretty-printed JSON, NOT line-per-record (proven
    #    sdk-go tick #90) — read the WHOLE file, never just the first line.
    hdr_path = f"{board}/board.jsonl"
    with open(hdr_path) as f:
        hdr = json.loads(f.read())
    hdr["last_tick"] = now
    hdr["updated_at"] = now
    hdr["ticks_total"] = overrides.get("ticks_total", int(hdr.get("ticks_total", 0)) + 1)
    hdr["ticks_idle"] = overrides.get("ticks_idle", int(hdr.get("ticks_idle", 0)) + 1)
    if "last_commit" in overrides:
        hdr["last_commit"] = overrides["last_commit"]
    with open(hdr_path, "w") as f:
        f.write(json.dumps(hdr, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("board.jsonl header:", json.dumps(
        {k: hdr[k] for k in ("ticks_total", "ticks_idle", "last_commit", "last_tick")}))


if __name__ == "__main__":
    main()
