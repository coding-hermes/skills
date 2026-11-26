#!/usr/bin/env python3
"""Append a task_dispatched event to a JSONL-tracked DuckDB v2.1 board + update the tasks row.

For JSONL-tracked boards (.coding-hermes/board/ with events.jsonl / tasks.jsonl / board.jsonl).
append_board_task_completed.py is COMPLETION-ONLY (requires a commit hash, flips the row to
complete) — use THIS script for the dispatch moment (worker spawned, still in flight).
Verified shape: dexdat-core tick #138 (event id 15).

Usage:
  python3 append_board_task_dispatched.py REPO TASK_ID TICK_NUMBER MODEL PROVIDER PID

Conventions:
- event id: MAX(id)+1 across events.jsonl (authoritative — never reuse), computed over
  NUMERIC candidate ids only (ints, and pure-digit strings such as "42"). Fleet boards
  carry mixed id shapes — the real crier events.jsonl holds plain ints alongside string
  ids and null ids — so a bare max() over every row raised TypeError before a single
  event was written and killed every dispatch append (DF-CRIER-512, the same class
  DF-CRIER-511 fixed in append_board_task_completed.py). Non-numeric and missing ids are
  ignored; a board with no numeric id at all starts at 1. Existing lines are never
  renumbered, reordered or rewritten. The helpers are replicated (not imported from the
  sibling script) because this file is deployed on its own in several places.
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
import fcntl
import json
import os
import subprocess

BOARD_FILES = ("events.jsonl", "tasks.jsonl")

BOARD_LOCK_FILE = ".lock"


def acquire_board_write_lock(bdir):
    """QA-GITREINS-16: exclusive advisory flock on <bdir>/.lock - the SAME
    sidecar lock file boardctl's write guard uses (coding-hermes-boardctl
    internal/board/lock.go, boardLockFileName = ".lock") - held from BEFORE
    the first board read until AFTER the last write. Advisory: protects only
    writers that acquire it; flock releases on process death."""
    f = open(os.path.join(bdir, BOARD_LOCK_FILE), "a+")
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    return f


def board_line_count(path):
    with open(path) as f:
        return sum(1 for line in f if line.strip())


def refuse_drift(path, snapshot):
    """QA-GITREINS-16 drift refusal: exit 2, write nothing, when the caller's
    pre-lock snapshot no longer matches disk (another writer moved the board;
    writing back from a stale view is the 2026-11-15 60789922 failure)."""
    current = board_line_count(path)
    if snapshot is not None and current != snapshot:
        print(f"DRIFT REFUSED: {path} has {current} lines but the caller "
              f"snapshot says {snapshot} - another writer moved the board "
              f"during this invocation; re-read the board and retry")
        return True
    return False


def numeric_event_ids(events):
    """Yield the event ids that can be ordered against a new int id.

    Numeric candidates are ints (bools excluded - True is an int in Python) and
    strings that are pure ASCII digit strings, so a legacy "9" still bounds the
    sequence. Nulls, id-less rows and non-numeric string ids ("evt-3") are ignored.
    Mirrors append_board_task_completed.py (DF-CRIER-511) - keep the two in step.
    """
    for e in events:
        if not isinstance(e, dict):
            continue
        value = e.get("id")
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            yield value
        elif isinstance(value, str) and value.isascii() and value.isdigit():
            yield int(value)


def next_event_id(events):
    """Next event id as an int: max(numeric candidates) + 1, or 1 when there are none."""
    return max(numeric_event_ids(events), default=0) + 1


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
    ap.add_argument("--snapshot-tasks-lines", type=int, default=None,
                    help="line count of tasks.jsonl read by the caller BEFORE this "
                         "invocation; mismatch under the write lock refuses with exit 2")
    ap.add_argument("--snapshot-events-lines", type=int, default=None,
                    help="line count of events.jsonl read by the caller BEFORE this "
                         "invocation; mismatch under the write lock refuses with exit 2")
    args = ap.parse_args()

    bdir = f"{args.repo.rstrip('/')}/.coding-hermes/board"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.000000")

    lock = acquire_board_write_lock(bdir)
    try:
        if refuse_drift(f"{bdir}/tasks.jsonl", args.snapshot_tasks_lines):
            return 2
        if refuse_drift(f"{bdir}/events.jsonl", args.snapshot_events_lines):
            return 2

        with open(f"{bdir}/events.jsonl") as f:
            events = [json.loads(l) for l in f if l.strip()]
        nid = next_event_id(events)

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
    finally:
        lock.close()  # releases the flock; no stale lock survives a crash


if __name__ == "__main__":
    raise SystemExit(main())
