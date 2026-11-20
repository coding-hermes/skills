#!/usr/bin/env python3
"""Append a foreman audit event to a JSONL foreman board in ONE shot.

JSONL is the canonical store - board.db was retired 2026-09-03 (fleet
doctrine: no db cache file; the JSONL files ARE the board). Writes:

  1. .coding-hermes/board/events.jsonl   <- appended (tracked in git)
  2. .coding-hermes/board/board.jsonl    <- header merge (ticks_total/ticks_idle/last_commit)

Usage (cron-safe: no python3 -c, no heredocs, no curl pipes):
  # 1. write the detail object to a file (write_file, avoids shell quoting)
  # 2. run:
  python3 append_board_event.py REPO TICK_NUMBER DETAIL_JSON \
      [--ts 'YYYY-MM-DD HH:MM:SS.mmmmmm'] \
      [--set last_commit=abc123] [--set ticks_idle=10] [--set ticks_total=34]

  REPO         absolute path to the project repo
  TICK_NUMBER  the tick number for this audit event
  DETAIL_JSON  path to a JSON file holding the event `detail` object
  --ts         event timestamp; defaults to now
  --set        repeatable KEY=VALUE pairs merged into the board.jsonl header
               (e.g. last_commit=<pre-tick HEAD>, ticks_total, ticks_idle)

Event id is computed as MAX(id)+1 across events.jsonl (explicit sequence -
never trust implicit ordering). Read status with boardctl
(github.com/coding-hermes/boardctl) or jq on the JSONL files.

STAGED BY DEFAULT (DF-CRIER-510): after writing, the script `git add -f`s exactly
the files it wrote (events.jsonl, board.jsonl) so a caller commit cannot leave the
audit event behind. Outside a git repo it prints a NOTICE and skips staging instead
of failing; a git failure is reported, never raised (the writes already happened and
re-running would append a duplicate event).

Proven: ring-runner tick 34 (2026-08-02).
"""
import argparse
import json
import os
import subprocess

BOARD_FILES = ("events.jsonl", "board.jsonl")


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


def main() -> int:
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
                eid = e.get("id", 0)
                if isinstance(eid, str):
                    eid = int(eid) if eid.isdigit() else 0
                if eid > max_id:
                    max_id = eid
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
    return stage_board_files(board, BOARD_FILES)


if __name__ == "__main__":
    raise SystemExit(main())
