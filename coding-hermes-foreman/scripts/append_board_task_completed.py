#!/usr/bin/env python3
"""Append a task_completed event + audit summary + tasks-row update + header bump to a JSONL foreman board.

JSONL is the canonical store - board.db was retired 2026-09-03 (fleet
doctrine: no db cache file; the JSONL files ARE the board). Plain python3,
no duckdb needed.

Usage:
  python3 append_board_task_completed.py REPO TASK_ID TICK_NUMBER COMMIT_HASH \
      --summary "tick 137 - TASK complete (commit, +N/-M). ..." \
      [--guard PASS] [--ci PASS] [--judge "PASS verdict abc (n/n criteria)"] \
      [--note "foreman_note for the tasks row"] \
      [--commit "chore(board): close TASK_ID (tick N)"]

Conventions (verified dexdat-core tick #137):
- event ids: MAX(id)+1 across events.jsonl (authoritative tick numbering), computed
  over NUMERIC candidate ids only (ints, and pure-digit strings such as "42").
  Fleet boards carry mixed id shapes - the real crier events.jsonl holds plain ints
  alongside string ids and null ids - so a bare max() over every row raised
  TypeError before a single event was written and killed every closeout (DF-CRIER-511).
  Non-numeric and missing ids are ignored; a board with no numeric id at all starts
  at 1. Existing lines are never renumbered, reordered or rewritten.
- events appended: task_completed (detail JSON: commit/guard/judge/tick) then audit (tick summary).
- tasks.jsonl row: status/worker_status -> complete, completed_at=now, commit_hash, guard_result, ci_result, foreman_note.
- board.jsonl header: ticks_total = the COMPLETING tick number (dispatch-only ticks do NOT bump), last_commit, last_tick, updated_at, ticks_idle=0.

STAGED BY DEFAULT (DF-CRIER-510). Writing the files is not a close: the close is
the COMMIT. This script therefore stages exactly the board files it wrote
(events.jsonl, tasks.jsonl, board.jsonl) with `git add -f`, so the caller's commit
cannot under-stage the completion event line. Outside a git repo it prints a
NOTICE and skips staging instead of failing.

  --commit "message"  additionally commits those exact paths (pathspec commit), so
                      write+commit is atomic and cannot be split by a caller that
                      forgets the event file. Existing callers that omit the flag
                      keep the old contract: write + stage, caller commits.

  `git add -f` is deliberate: some boards keep .coding-hermes/ ignored-but-tracked
  (that is why the documented recipe always force-added board.db-era files), and a
  single ignored path poisons a multi-path `git add` so NOTHING is staged. All three
  paths here are ones this script just wrote, so forcing them is safe.

  Defect closed: crier commit be35c5a7 (2026-11-19) closed DF-CRIER-509 in
  tasks.jsonl but left event id 1795041048590000012 UNCOMMITTED in the working
  tree for ~24h - every reader of main:<board> saw a closed row with no event.

  NEVER re-run this script to "retry" a commit: it appends DUPLICATE events. If
  --commit fails, the files are already written and staged - commit by hand:
    git -C <repo>/.coding-hermes/board commit -m "..." -- events.jsonl tasks.jsonl board.jsonl
"""
import argparse
import datetime
import json
import os
import subprocess

BOARD_FILES = ("events.jsonl", "tasks.jsonl", "board.jsonl")


def numeric_event_ids(events):
    """Yield the event ids that can be ordered against a new int id.

    Numeric candidates are ints (bools excluded - True is an int in Python) and
    strings that are pure ASCII digit strings, so a legacy "9" still bounds the
    sequence. Nulls, id-less rows and non-numeric string ids ("evt-3") are ignored.
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

    Staging-only unless commit_message is given, so every existing caller keeps its
    behaviour and only gains the guarantee that the event line is staged. A git
    failure is reported, never raised: the JSONL writes already happened and
    aborting would invite a re-run, which appends duplicate events.
    Returns 0 on success or skip, 1 only when a requested --commit did not land.
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
    ap.add_argument("commit", help="task commit hash")
    ap.add_argument("--summary", required=True, help="audit event summary text")
    ap.add_argument("--guard", default="PASS")
    ap.add_argument("--ci", default=None)
    ap.add_argument("--judge", default="")
    ap.add_argument("--note", default="", help="foreman_note for the tasks.jsonl row")
    ap.add_argument("--commit", "--commit-message", dest="commit_message", default=None,
                    help="also git-commit the three board files with this message "
                         "(atomic close; omit to only write + stage)")
    args = ap.parse_args()

    bdir = f"{args.repo.rstrip('/')}/.coding-hermes/board"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.000000")

    with open(f"{bdir}/events.jsonl") as f:
        events = [json.loads(l) for l in f if l.strip()]
    nid = next_event_id(events)
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
    return stage_board_files(bdir, BOARD_FILES, args.commit_message)


if __name__ == "__main__":
    raise SystemExit(main())
