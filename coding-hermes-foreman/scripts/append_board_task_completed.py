#!/usr/bin/env python3
"""Append a task_completed event + audit summary + tasks-row update + header bump to a JSONL foreman board.

JSONL is the canonical store - board.db was retired 2026-09-03 (fleet
doctrine: no db cache file; the JSONL files ARE the board). Plain python3,
no duckdb needed.

Usage:
  python3 append_board_task_completed.py REPO TASK_ID TICK_NUMBER COMMIT_HASH \
      --summary "tick 137 - TASK complete (commit, +N/-M). ..." \
      [--guard PASS] [--ci PASS] [--judge "PASS verdict abc (n/n criteria)"] \
      [--note "foreman_note for the tasks row"]

Conventions (verified dexdat-core tick #137):
- event ids: MAX(id)+1 across events.jsonl (authoritative tick numbering).
- events appended: task_completed (detail JSON: commit/guard/judge/tick) then audit (tick summary).
- tasks.jsonl row: status/worker_status -> complete, completed_at=now, commit_hash, guard_result, ci_result, foreman_note.
- board.jsonl header: ticks_total = the COMPLETING tick number (dispatch-only ticks do NOT bump), last_commit, last_tick, updated_at, ticks_idle=0.

After running, commit with explicit files (never the whole dir):
  git add .coding-hermes/board/events.jsonl .coding-hermes/board/tasks.jsonl .coding-hermes/board/board.jsonl
"""
import argparse
import datetime
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", help="absolute path to the repo (board at <repo>/.coding-hermes/board/)")
    ap.add_argument("task_id")
    ap.add_argument("tick", type=int)
    ap.add_argument("commit", help="task commit hash")
    ap.add_argument("--summary", required=True, help="audit event summary text")
    ap.add_argument("--guard", default="PASS")
    ap.add_argument("--ci", default=None)
    ap.add_argument("--judge", default="")
    ap.add_argument("--note", default="", help="foreman_note for the tasks.jsonl row")
    args = ap.parse_args()

    bdir = f"{args.repo.rstrip('/')}/.coding-hermes/board"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.000000")

    with open(f"{bdir}/events.jsonl") as f:
        events = [json.loads(l) for l in f if l.strip()]
    nid = max(e["id"] for e in events) + 1
    new_events = [
        {"id": nid, "timestamp": now, "event_type": "task_completed", "task_id": args.task_id,
         "actor": "foreman", "detail": json.dumps({"commit": args.commit, "guard": args.guard, "judge": args.judge, "tick": args.tick}),
         "tick_number": args.tick},
        {"id": nid + 1, "timestamp": now, "event_type": "audit", "task_id": None, "actor": "foreman",
         "detail": json.dumps({"tick": args.tick, "summary": args.summary}), "tick_number": args.tick},
    ]
    with open(f"{bdir}/events.jsonl", "a") as f:
        for e in new_events:
            f.write(json.dumps(e, separators=(",", ":")) + "\n")

    tk_path = f"{bdir}/tasks.jsonl"
    with open(tk_path) as f:
        tasks = [json.loads(l) for l in f if l.strip()]
    row = next((t for t in tasks if t["id"] == args.task_id), None)
    if row is None:
        print(f"WARN: task {args.task_id} not found in tasks.jsonl; row not updated")
    else:
        row["status"] = "complete"
        row["worker_status"] = "complete"
        row["completed_at"] = now
        row["updated_at"] = now
        row["commit_hash"] = args.commit
        row["guard_result"] = args.guard
        if args.ci:
            row["ci_result"] = args.ci
        if args.note:
            row["foreman_note"] = args.note
        with open(tk_path, "w") as f:
            for t in tasks:
                f.write(json.dumps(t, separators=(",", ":")) + "\n")

    hd_path = f"{bdir}/board.jsonl"
    with open(hd_path) as f:
        hdr = json.load(f)
    hdr["last_tick"] = now
    hdr["ticks_total"] = args.tick
    hdr["ticks_idle"] = 0
    hdr["last_commit"] = args.commit
    hdr["updated_at"] = now
    with open(hd_path, "w") as f:
        json.dump(hdr, f, default=str)
        f.write("\n")

    print(f"OK: events [{nid},{nid + 1}] tick {args.tick} commit {args.commit} task {args.task_id}")


if __name__ == "__main__":
    main()
