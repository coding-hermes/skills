#!/usr/bin/env python3
"""Append an e2e_verified event (task_id set) to a board-v2 JSONL board.

(board.db retired 2026-09-03 — JSONL-only doctrine; this script now writes events.jsonl only.)

WHY: append_board_event.py hardcodes event_type="audit"/task_id=None, so E2E fixture
ticks need a FIRST event carrying the task id (e.g. E2E-001) logged before the audit event.

USAGE:
  python3 scripts/append_e2e_event.py <repo_path> <tick> <detail.json> [task_id]

  - repo_path: absolute path to the project repo (board at .coding-hermes/board/)
  - tick:      tick number (int)
  - detail.json: path to a JSON file with the event detail object (write via write_file, no shell quoting)
  - task_id:   default "E2E-001"

MECHANICS (proven crier ticks 72-102):
  - events.jsonl is the AUTHORITATIVE git-tracked store.
  - new id = MAX(existing id)+1 — json.loads per line tolerates BOTH "id": 87 and "id":87 forms.
  - Order: run this FIRST, then the one-shot append_board_event.py for the audit event
    (it auto-picks the next id), and the JSONL max id must equal the last event id.

STAGED BY DEFAULT (DF-CRIER-510): after writing, the script `git add -f`s events.jsonl
so a caller commit cannot leave the e2e event behind. Outside a git repo it prints a
NOTICE and skips staging instead of failing; a git failure is reported, never raised
(the write already happened and re-running would append a duplicate event).
"""
import fcntl
import json
import sys
import datetime
import os
import subprocess

BOARD_FILES = ("events.jsonl",)

BOARD_LOCK_FILE = ".lock"


def acquire_board_write_lock(board):
    """QA-GITREINS-16: exclusive advisory flock on <board>/.lock - the SAME
    sidecar lock file boardctl's write guard uses (coding-hermes-boardctl
    internal/board/lock.go, boardLockFileName = ".lock") - held across the
    id-derivation read and the append so a concurrent writer cannot slip an
    event in between and get its id reused (the 2026-11-15 60789922
    duplicate-id signature). Advisory: protects only writers that acquire
    it; flock releases on process death."""
    f = open(os.path.join(board, BOARD_LOCK_FILE), "a+")
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    return f


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


if len(sys.argv) < 4:
    print(__doc__)
    sys.exit(1)

repo = sys.argv[1]
tick = int(sys.argv[2])
detail_path = sys.argv[3]
task_id = sys.argv[4] if len(sys.argv) > 4 else "E2E-001"

board = os.path.join(repo, ".coding-hermes", "board")
events_path = os.path.join(board, "events.jsonl")

lockf = acquire_board_write_lock(board)
try:
    with open(events_path) as f:
        lines = [l for l in f.read().splitlines() if l.strip()]
    ids = [json.loads(l)["id"] for l in lines]
    new_id = max(ids) + 1
    print(f"max existing id: {max(ids)}, new id: {new_id}")

    detail = json.load(open(detail_path))
    event = {
        "id": new_id,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "event_type": "e2e_verified",
        "task_id": task_id,
        "actor": "foreman",
        "detail": json.dumps(detail, ensure_ascii=False),
        "tick_number": tick,
    }
    with open(events_path, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
finally:
    lockf.close()  # releases the flock; no stale lock survives a crash
print("JSONL appended, id", new_id)
sys.exit(stage_board_files(board, BOARD_FILES))
