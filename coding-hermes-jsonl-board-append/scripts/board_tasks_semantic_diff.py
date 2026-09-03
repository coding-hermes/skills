#!/usr/bin/env python3
"""Semantic diff of a JSONL board tasks file vs git HEAD.

`update_board_task_notes.py` (and other canonical board writers) REWRITE the
whole tasks.jsonl with their own serializer, so `git diff` shows churn on
EVERY row even when one field changed (proven mafia tick 85: 30/30 rows,
60-line diff for a NEVER-DONE note update). This script proves the churn is
formatting-only: it parses rows HEAD-vs-working-tree and reports which rows
and fields ACTUALLY differ.

Expect exactly ONE row differing (the fixture/task row updated this tick) —
anything else is real drift and should block the commit.

Usage:
    python3 board_tasks_semantic_diff.py [repo_dir] [tasks_relpath]

    repo_dir      git repo root (default: .)
    tasks_relpath board tasks file relative to repo root
                  (default: .coding-hermes/board/tasks.jsonl)

Exit 0 when the row-key sets are equal (structural match); 1 otherwise.
The "rows with any diff: N" line is the human gate: N == 1 = intended update.
"""
import json
import subprocess
import sys

repo = sys.argv[1] if len(sys.argv) > 1 else "."
rel = sys.argv[2] if len(sys.argv) > 2 else ".coding-hermes/board/tasks.jsonl"

head_raw = subprocess.check_output(
    ["git", "-C", repo, "show", f"HEAD:{rel}"], text=True
)
with open(f"{repo}/{rel}") as f:
    new_raw = f.read()


def rows(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        out[r.get("id") or r.get("title", "")[:40]] = r
    return out


h, n = rows(head_raw), rows(new_raw)
print(f"head rows: {len(h)}  new rows: {len(n)}")
print(f"key sets equal: {set(h) == set(n)}")
diffs = 0
for k in h:
    if h[k] != n[k]:
        diffs += 1
        print(f"DIFF row: {k}")
        for f in sorted(set(h[k]) | set(n[k])):
            if h[k].get(f) != n[k].get(f):
                print(f"  field {f}: {str(h[k].get(f))[:80]!r} -> {str(n[k].get(f))[:80]!r}")
print(f"rows with any diff: {diffs}  (1 = only the intended row; more = real drift)")
sys.exit(0 if set(h) == set(n) else 1)
