#!/usr/bin/env python3
"""Update task-row fields on a JSONL foreman board.

append_board_event.py only covers audit EVENTS (events.jsonl + board.jsonl
header). Task-row updates - foreman_note/worker_summary refreshes, status
flips, commit_hash backfills - go to the single canonical store:

  1. .coding-hermes/board/tasks.jsonl   <- git-tracked canonical (board.db retired 2026-09-03)

Usage (cron-safe: no python3 -c, no heredocs):
  python3 update_board_task_notes.py REPO TASK_ID FIELD=VALUE [FIELD=VALUE...] [--ts 'YYYY-MM-DD HH:MM:SS']

  REPO      absolute path to the project repo
  TASK_ID   task id, e.g. E2E-001
  FIELD=VALUE  repeatable; always include foreman_note for fixture refreshes
  --ts      updated_at value; defaults to now

Verifies the row exists (non-zero exit + ERROR if missing).
tasks.jsonl full rewrite is fine - only events.jsonl is append-only.

STAGED BY DEFAULT (DF-CRIER-510): after a successful rewrite the script `git add -f`s
tasks.jsonl so a caller commit cannot leave the row update behind. Outside a git repo
it prints a NOTICE and skips staging instead of failing; a git failure is reported,
never raised (the write already happened).
"""
import argparse
import fcntl
import json
import os
import subprocess
import sys
from datetime import datetime

BOARD_FILES = ("tasks.jsonl",)

BOARD_LOCK_FILE = ".lock"


def acquire_board_write_lock(bdir):
    """QA-GITREINS-16: exclusive advisory flock on <bdir>/.lock - the SAME
    sidecar lock file boardctl's write guard uses (coding-hermes-boardctl
    internal/board/lock.go, boardLockFileName = ".lock") - held from BEFORE
    the tasks.jsonl re-read until AFTER the rewrite (and the staging, which
    publishes the written bytes). This script is a READ-MODIFY-WRITE-ALL
    writer: a stale snapshot plus the full rewrite is exactly the
    2026-11-15 60789922 board damage (RELEASE-025 row deleted, RELEASE-023
    reverted). Advisory: protects only writers that acquire it; flock
    releases on process death."""
    f = open(os.path.join(bdir, BOARD_LOCK_FILE), "a+")
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    return f


def board_line_count(path):
    with open(path) as f:
        return sum(1 for line in f if line.strip())


def refuse_drift(path, snapshot):
    """QA-GITREINS-16 drift refusal: exit 2, write nothing, when the caller's
    pre-lock snapshot no longer matches disk - another writer moved the board
    and a rewrite from the stale view would silently revert their rows."""
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
    aborting would invite a re-run that could duplicate the update.
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
        print("ERROR: the board files ARE written and staged. Do NOT re-run this script - "
              "commit manually:")
        print(f"  git -C {bdir} commit -m {json.dumps(commit_message)} -- {' '.join(names)}")
        return 1
    print(f"OK: committed {', '.join(names)}: {commit_message}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("task_id")
    ap.add_argument("fields", nargs="+", help="FIELD=VALUE pairs")
    ap.add_argument("--ts", default=None)
    ap.add_argument("--snapshot-tasks-lines", type=int, default=None,
                    help="line count of tasks.jsonl read by the caller BEFORE this "
                         "invocation; mismatch under the write lock refuses with exit 2")
    args = ap.parse_args()

    board = f"{args.repo.rstrip('/')}/.coding-hermes/board"
    ts = args.ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    updates = {"updated_at": ts}
    for fv in args.fields:
        k, _, v = fv.partition("=")
        if not k:
            print(f"WARN: skipping malformed {fv}")
            continue
        updates[k] = v

    lock = acquire_board_write_lock(board)
    try:
        if refuse_drift(f"{board}/tasks.jsonl", args.snapshot_tasks_lines):
            return 2

        rows = []
        with open(f"{board}/tasks.jsonl") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        found = False
        for r in rows:
            if r["id"] == args.task_id:
                r.update(updates)
                found = True
        if not found:
            print(f"ERROR: task {args.task_id} not found in tasks.jsonl")
            sys.exit(1)
        with open(f"{board}/tasks.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"tasks.jsonl updated {args.task_id}: {sorted(updates)}")
        return stage_board_files(board, BOARD_FILES)
    finally:
        lock.close()  # releases the flock; no stale lock survives a crash


if __name__ == "__main__":
    raise SystemExit(main())
