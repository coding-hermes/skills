#!/usr/bin/env python3
"""Create one or more tasks on a JSONL-tracked DuckDB foreman board in one shot.

Appends task rows to tasks.jsonl (canonical git store) and appends
task_created events to events.jsonl with explicit max-id sequence.
(board.db retired 2026-09-03 — JSONL-only doctrine.)

Usage (cron-safe: no python3 -c, no heredocs, no pipes):
  python3 create_board_tasks.py REPO TICK_NUMBER TASKS_JSON [--reason '...']

  REPO          absolute path to the project repo
  TICK_NUMBER   tick number creating the tasks (stamped on events)
  TASKS_JSON    path to a JSON file: array of task dicts with fields
                id, title, priority, complexity, primary_model,
                primary_provider, reasoning, capability_tags, foreman_note
                (all other schema fields default sensibly)
  --reason      short source string for the task_created event detail
                (default: "foreman")

Event ids = MAX(numeric id)+1 across events.jsonl (JSONL is the id authority;
int ids and legacy pure-digit string ids count, non-numeric/null ids are ignored -
see max_event_id). Tasks whose ids already exist in tasks.jsonl are skipped (idempotent).
Ordering per board convention: task rows BEFORE the task_created events.

Proven: ring-runner tick 47 (2026-08-03) — RR-COV-01 + RR-GOV-01 created
from the idle deeper pass (Bane directive 2026-08 #1).

STAGED BY DEFAULT (DF-CRIER-510): after writing, the script `git add -f`s exactly the
two board files it wrote (tasks.jsonl, events.jsonl) so a caller commit cannot stage the
new rows and leave the matching task_created event behind. Outside a git repo it prints
a NOTICE and skips staging instead of failing; a git failure is reported, never raised
(the writes already happened and re-running would append duplicate events).
"""
import argparse
import fcntl
import json
import os
import subprocess
from datetime import datetime

BOARD_FILES = ("tasks.jsonl", "events.jsonl")

BOARD_LOCK_FILE = ".lock"


def acquire_board_write_lock(bdir):
    """QA-GITREINS-16: exclusive advisory flock on <bdir>/.lock - the SAME
    sidecar lock file boardctl's write guard uses (coding-hermes-boardctl
    internal/board/lock.go, boardLockFileName = ".lock") - held across the
    duplicate-id scan, the event-id derivation and both appends so a
    concurrent writer cannot slip a row/event in between and get its id
    reused. Advisory: protects only writers that acquire it; flock releases
    on process death."""
    f = open(os.path.join(bdir, BOARD_LOCK_FILE), "a+")
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    return f


def board_line_count(path):
    with open(path) as f:
        return sum(1 for line in f if line.strip())


def refuse_drift(path, snapshot):
    """QA-GITREINS-16 drift refusal: exit 2, write nothing, when the caller's
    pre-lock snapshot no longer matches disk."""
    current = board_line_count(path)
    if snapshot is not None and current != snapshot:
        print(f"DRIFT REFUSED: {path} has {current} lines but the caller "
              f"snapshot says {snapshot} - another writer moved the board "
              f"during this invocation; re-read the board and retry")
        return True
    return False


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


def load_rows(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def numeric_event_ids(rows):
    """Yield the event ids that can be ordered against the new int id.

    Numeric candidates are ints (bools excluded - True is an int in Python) and
    strings that are pure ASCII digit strings, so a legacy "9" still bounds the
    sequence. Nulls, id-less rows and non-numeric string ids ("evt-3") are ignored.
    Mirrors append_board_task_completed.py (DF-CRIER-511) and
    append_board_task_dispatched.py (DF-CRIER-512). The helper is duplicated rather
    than imported because every board script in this directory deploys standalone
    (copied into a foreman skill dir / invoked from cron by absolute path) - keep
    the copies in step.
    """
    for e in rows:
        if not isinstance(e, dict):
            continue
        value = e.get("id")
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            yield value
        elif isinstance(value, str) and value.isascii() and value.isdigit():
            yield int(value)


def max_event_id(path):
    """Highest NUMERIC event id in events.jsonl, as an int (0 when there is none).

    Fleet boards carry mixed id shapes - the real crier events.jsonl holds plain
    ints (1795041048590000042) alongside legacy string ids and null ids - so
    comparing every row's id against an int mid raised TypeError and killed every
    task_created append before a single event (or the staging step) ran
    (DF-CRIER-514; same class as DF-CRIER-511/512/513).
    """
    return max(numeric_event_ids(load_rows(path)), default=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("tick_number", type=int)
    ap.add_argument("tasks_json")
    ap.add_argument("--reason", default="foreman")
    ap.add_argument("--snapshot-tasks-lines", type=int, default=None,
                    help="line count of tasks.jsonl read by the caller BEFORE this "
                         "invocation; mismatch under the write lock refuses with exit 2")
    ap.add_argument("--snapshot-events-lines", type=int, default=None,
                    help="line count of events.jsonl read by the caller BEFORE this "
                         "invocation; mismatch under the write lock refuses with exit 2")
    args = ap.parse_args()

    board = f"{args.repo.rstrip('/')}/.coding-hermes/board"
    tasks_path = f"{board}/tasks.jsonl"
    events_path = f"{board}/events.jsonl"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    with open(args.tasks_json) as f:
        new_tasks = json.load(f)

    lock = acquire_board_write_lock(board)
    try:
        if refuse_drift(tasks_path, args.snapshot_tasks_lines):
            return 2
        if refuse_drift(events_path, args.snapshot_events_lines):
            return 2

        existing_ids = {t["id"] for t in load_rows(tasks_path)}
        added = []
        for t in new_tasks:
            if t["id"] in existing_ids:
                print(f"skip existing {t['id']}")
                continue
            row = {
                "status": "pending",
                "blocks": None,
                "fallback_model": None,
                "fallback_provider": None,
                "worker_status": "pending",
                "dispatched_at": None,
                "completed_at": None,
                "attempts": 0,
                "exit_code": None,
                "commit_hash": None,
                "files_changed": None,
                "lines_added": 0,
                "lines_removed": 0,
                "guard_result": None,
                "ci_result": None,
                "worker_summary": None,
                "blocked_reason": None,
                "review_notes": None,
                "created_at": now,
                "updated_at": now,
                **t,
            }
            added.append(row)

        with open(tasks_path, "a") as f:
            for t in added:
                f.write(json.dumps(t, default=str, separators=(",", ":")) + "\n")
        print(f"tasks.jsonl: appended {len(added)} rows")

        next_id = max_event_id(events_path)
        events = []
        for t in added:
            next_id += 1
            events.append({
                "id": next_id,
                "timestamp": now,
                "event_type": "task_created",
                "task_id": t["id"],
                "actor": "foreman",
                "detail": json.dumps({"source": args.reason, "tick": args.tick_number}),
                "tick_number": args.tick_number,
            })
        with open(events_path, "a") as f:
            for ev in events:
                f.write(json.dumps(ev, default=str, separators=(",", ":")) + "\n")
        print(f"events.jsonl: appended {len(events)} task_created events")
        print("done")
        return stage_board_files(board, BOARD_FILES)
    finally:
        lock.close()  # releases the flock; no stale lock survives a crash


if __name__ == "__main__":
    raise SystemExit(main())
