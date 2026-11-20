#!/usr/bin/env python3
"""Append a task_dispatched event to a JSONL-tracked DuckDB v2.1 board + update the tasks row.

For JSONL-tracked boards (.coding-hermes/board/ with events.jsonl / tasks.jsonl / board.jsonl).
append_board_task_completed.py is COMPLETION-ONLY (requires a commit hash, flips the row to
complete) — use THIS script for the dispatch moment (worker spawned, still in flight).
Verified shape: dexdat-core tick #138 (event id 15).

Usage:
  python3 append_board_task_dispatched.py REPO TASK_ID TICK_NUMBER MODEL PROVIDER PID

Conventions:
- event id: MAX(id)+1 across events.jsonl (authoritative — never reuse).
- event shape: {"id", "timestamp", "event_type": "task_dispatched", "task_id",
  "actor": "foreman", "detail": <JSON-ENCODED STRING, not an object>, "tick_number"}.
  detail must be json.dumps(...) of the payload — prior dispatch events store the whole
  dict as a string, and readers json.loads it.
- tasks.jsonl row: worker_status -> "dispatched", dispatched_at = now, attempts += 1.
- Does NOT bump ticks_total: dispatch-only ticks don't bump the header; the COMPLETING
  tick does (via append_board_task_completed.py). See dexdat-core tick #137: 135 -> 137.
- Does NOT touch board.db (JSONL is the source of truth; the completion script does the
  best-effort duckdb sync).
- stdlib-only (json, datetime) — system python3 works; no duckdb needed.

STAGED BY DEFAULT (DF-CRIER-510): after writing, the script `git add -f`s exactly the
two board files it wrote (events.jsonl, tasks.jsonl), so the caller's commit cannot
under-stage the dispatch event. Outside a git repo it prints a NOTICE and skips
staging instead of failing. A git failure is reported, never raised — the writes
already happened and re-running would append a duplicate event.
"""
import argparse
import datetime
import json
import os
import subprocess

BOARD_FILES = ("events.jsonl", "tasks.jsonl")


def stage_board_files(bdir, files, commit_message=None):
    """git add the board files just written; optionally pathspec-commit them.

    A git failure is reported, never raised: the JSONL writes already happened and
    aborting would invite a re-run, which appends duplicate events.
    Returns 0 on success or skip, 1 only when a requested commit did not land.
    """
    names = [f for f in files if os.path.exists(os.path.join(bdir, f))]
    if not names:
        return 0
    try:
        top = subprocess.run(["git", "-C", bdir, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=60,
                             stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"WARN: git unavailable ({exc}); {len(names)} board file(s) written but NOT staged")
        return 0
    if top.returncode != 0:
        print(f"NOTICE: {bdir} is not inside a git repo; "
              f"{len(names)} board file(s) written but NOT staged")
        return 0

    add = subprocess.run(["git", "-C", bdir, "add", "-f", "--"] + names,
                         capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if add.returncode != 0:
        print(f"WARN: git add failed for board files ({(add.stderr or add.stdout).strip()}); "
              f"files are written but UNSTAGED - commit them manually")
        return 0
    print(f"OK: staged {', '.join(names)} - a caller commit cannot under-stage the board")

    if not commit_message:
        return 0
    com = subprocess.run(["git", "-C", bdir, "commit", "-m", commit_message, "--"] + names,
                         capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if com.returncode != 0:
        print(f"ERROR: git commit failed ({(com.stderr or com.stdout).strip()})")
        print("ERROR: the board files ARE written and staged. Do NOT re-run this script "
              "(it would append duplicate events) - commit manually:")
        print(f"  git -C {bdir} commit -m {json.dumps(commit_message)} -- {' '.join(names)}")
        return 1
    print(f"OK: committed {', '.join(names)}: {commit_message}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", help="absolute path to the repo (board at <repo>/.coding-hermes/board/)")
    ap.add_argument("task_id")
    ap.add_argument("tick", type=int)
    ap.add_argument("model")
    ap.add_argument("provider")
    ap.add_argument("pid", type=int)
    args = ap.parse_args()

    bdir = f"{args.repo.rstrip('/')}/.coding-hermes/board"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.000000")

    with open(f"{bdir}/events.jsonl") as f:
        events = [json.loads(l) for l in f if l.strip()]
    nid = max(e["id"] for e in events) + 1

    detail = json.dumps({
        "model": args.model,
        "provider": args.provider,
        "pid": args.pid,
        "task": args.task_id,
        "tick": args.tick,
    })

    event = {
        "id": nid,
        "timestamp": now,
        "event_type": "task_dispatched",
        "task_id": args.task_id,
        "actor": "foreman",
        "detail": detail,
        "tick_number": args.tick,
    }

    with open(f"{bdir}/events.jsonl", "a") as f:
        f.write(json.dumps(event, separators=(",", ":")) + "\n")

    with open(f"{bdir}/tasks.jsonl") as f:
        tasks = [json.loads(l) for l in f if l.strip()]
    for t in tasks:
        if t["id"] == args.task_id:
            t["worker_status"] = "dispatched"
            t["dispatched_at"] = now
            t["attempts"] = int(t.get("attempts") or 0) + 1
    with open(f"{bdir}/tasks.jsonl", "w") as f:
        for t in tasks:
            f.write(json.dumps(t, separators=(",", ":")) + "\n")

    print(f"event id={nid} appended; tasks.jsonl {args.task_id} worker_status=dispatched attempts="
          f"{[t['attempts'] for t in tasks if t['id'] == args.task_id][0]}")
    return stage_board_files(bdir, BOARD_FILES)


if __name__ == "__main__":
    raise SystemExit(main())
