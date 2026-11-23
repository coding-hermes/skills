#!/usr/bin/env python3
"""Surgically rewrite the `reasoning` field of ONE board row.

`boardctl update` has no --reasoning flag, so a rationale that still quotes a
superseded candidate SHA, a refuted blocker, or a stale CI run cannot be
corrected through the writer. A note appended beneath it does NOT correct it:
readers and the next pass take `reasoning` first.

This edits exactly one physical line: JSON-load each line, mutate the loaded
dict (insertion order is preserved, so the row's key order survives), re-dump
only the matching line, and leave every other byte of the file untouched. It
refuses unless exactly one row carries the id.

Usage:
    board-row-reasoning.py <tasks.jsonl> <row-id> <text-file>

Verify afterwards (the board may be marked `-diff` in .gitattributes, so a
plain `git diff` shows a binary blob and proves nothing):

    git diff --text --numstat -- <tasks.jsonl>
    git diff --text -U0 -- <tasks.jsonl> | grep -c '^-[^-]'
    wc -l < <tasks.jsonl>

An update is +K/-K with the line count UNCHANGED and one row per touched id.
"""
import json
import sys


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    board, row_id, text_file = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(text_file, "r", encoding="utf-8") as fh:
        new_reasoning = fh.read()

    with open(board, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    hits = 0
    out = []
    for line in lines:
        if not line.strip():
            out.append(line)
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            out.append(line)
            continue
        if isinstance(obj, dict) and obj.get("id") == row_id:
            hits += 1
            obj["reasoning"] = new_reasoning
            out.append(json.dumps(obj, ensure_ascii=False) + "\n")
        else:
            out.append(line)

    if hits != 1:
        print(f"REFUSED: {row_id} matched {hits} rows (want exactly 1)", file=sys.stderr)
        return 2

    with open(board, "w", encoding="utf-8") as fh:
        fh.writelines(out)
    print(f"rewrote reasoning for {row_id} ({len(new_reasoning)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
