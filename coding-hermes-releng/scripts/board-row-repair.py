#!/usr/bin/env python3
"""Assertion-hardened single-line repair of a JSONL foreman board row.

WHY THIS EXISTS
    `boardctl update` owns only the flags it exposes (title, priority, status,
    note, worker_*, evidence flags). `reasoning` and the primary `detail.*`
    keys have NO flag at all, so a stale candidate / blocker / decision can
    only be fixed by rewriting one physical line of tasks.jsonl.

    The shell recipe (grep -n, head -n, sed -n) is a TRAP: an unmatched grep
    leaves LINE empty, `head -n -1` then degenerates and `sed -n "p"` prints
    EVERY line, so the transform rewrites the whole board while the line-count
    assertion still passes. This script locates the row by PARSED id, not by
    text, and refuses on anything ambiguous.

USAGE
    # dry run (default): prints the changed keys and exits without writing
    board-row-repair.py <tasks.jsonl> <row-id> --set reasoning=@/tmp/new-reasoning.txt

    # apply
    board-row-repair.py <tasks.jsonl> <row-id> \
        --set reasoning=@/tmp/new-reasoning.txt \
        --set title='corrected title' \
        --evidence-run-id <tick-or-run-id> \
        --evidence-fingerprint <sha256> \
        --evidence-artifact <path> \
        --ts 2026-01-01T00:00:00Z \
        --write

    `--set k=@path` reads the value from a file so long prose never has to
    survive shell quoting (backticks, $, quotes all pass through intact).
    Dotted keys are supported: `--set detail.candidate_head=<sha>`.
    Array elements are supported with a trailing `[-1]`, which is how a row's
    newest evidence entry gets re-bound after the artifact is re-hashed:
    `--set 'detail.evidence[-1].tree_fp=<sha256>' --set 'detail.evidence[-1].ts=<iso>'`
    (quote the brackets in the shell).

WHAT IT GUARANTEES (all assertions run BEFORE the write)
    * exactly one line parses to the requested id
    * every non-target line is byte-identical after the transform
    * the line count is unchanged
    * the target line still parses and still carries the same id
    * compact separators + original key insertion order are preserved, so the
      diff is one line and field ownership stays readable
    * the trailing newline is preserved (handling it naively is how the
      "non-target lines changed" self-check produces a false failure)

    detail.fingerprint is writer-derived and not reproducible: leave it alone
    and bind fresh evidence through detail.evidence[-1].tree_fp.
"""

import argparse
import json
import os
import sys


def load_lines(path):
    text = open(path, encoding="utf-8").read()
    trailing_newline = text.endswith("\n")
    lines = text.split("\n")
    if trailing_newline:
        lines = lines[:-1]
    return lines, trailing_newline


def parse_value(raw):
    if raw.startswith("@"):
        return open(raw[1:], encoding="utf-8").read()
    return raw


def set_dotted(row, dotted, value):
    """Set a dotted path; a segment written `<key>[-1]` addresses the list's last element.

    `detail.evidence[-1].tree_fp` is the documented way to re-bind a row's newest
    evidence entry after the evidence artifact is re-hashed. A dict-only walk
    would replace the whole evidence list with a dict and destroy the record, so
    the array form has to resolve here. Refuse anything that would create a
    list out of nothing: an empty or missing list is an operator mistake, not a
    shape to invent.
    """
    parts = dotted.split(".")
    if parts[-1].endswith("[-1]"):
        sys.exit("ABORT: %r ends on a list element with no field to set" % dotted)
    node = row
    for key in parts[:-1]:
        if key.endswith("[-1]"):
            name = key[: -len("[-1]")]
            seq = node.get(name)
            if not isinstance(seq, list) or not seq:
                sys.exit("ABORT: %r does not address a non-empty list" % key)
            node = seq[-1]
            continue
        nxt = node.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            node[key] = nxt
        node = nxt
    node[parts[-1]] = value


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("board")
    ap.add_argument("row_id")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--evidence-run-id")
    ap.add_argument("--evidence-fingerprint")
    ap.add_argument("--evidence-artifact", action="append", default=[])
    ap.add_argument("--ts", default=None)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    lines, trailing = load_lines(args.board)

    hits = []
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            if json.loads(line).get("id") == args.row_id:
                hits.append(idx)
        except json.JSONDecodeError:
            continue

    if len(hits) != 1:
        sys.exit(
            "ABORT: expected exactly 1 line with id %r, found %d. "
            "Duplicate ids need the duplicate resolved first; zero ids means the "
            "row is not in this board." % (args.row_id, len(hits))
        )

    target_idx = hits[0]
    original = lines[target_idx]
    row = json.loads(original)
    before_keys = list(row.keys())

    for assignment in args.set:
        if "=" not in assignment:
            sys.exit("ABORT: --set expects KEY=VALUE, got %r" % assignment)
        key, _, raw = assignment.partition("=")
        set_dotted(row, key.strip(), parse_value(raw))

    if args.evidence_run_id or args.evidence_fingerprint or args.evidence_artifact:
        if not (args.evidence_run_id and args.evidence_fingerprint):
            sys.exit(
                "ABORT: an evidence entry needs BOTH --evidence-run-id and "
                "--evidence-fingerprint (a half-bound entry is worse than none)"
            )
        entry = {
            "run_id": args.evidence_run_id,
            "tree_fp": args.evidence_fingerprint,
            "ts": args.ts or "",
            "artifacts": list(args.evidence_artifact),
        }
        row.setdefault("detail", {}).setdefault("evidence", []).append(entry)

    if list(row.keys()) != before_keys:
        # Appending detail/evidence is expected to ADD keys only when the row had
        # none. A reordered key set means the serializer changed shape.
        sys.exit(
            "ABORT: top-level key order changed (%r -> %r). Refusing to rewrite "
            "a row whose shape moved." % (before_keys, list(row.keys()))
        )

    new_line = json.dumps(row, separators=(",", ":"), ensure_ascii=False)
    if json.loads(new_line).get("id") != args.row_id:
        sys.exit("ABORT: reserialized row lost its id")

    out = list(lines)
    out[target_idx] = new_line

    if len(out) != len(lines):
        sys.exit("ABORT: line count changed")
    for idx, (old, new) in enumerate(zip(lines, out)):
        if idx != target_idx and old != new:
            sys.exit("ABORT: non-target line %d changed" % (idx + 1))
    if out[target_idx] == original:
        print("NO-OP: row already carries these values; nothing written")
        return 0

    changed = sorted(
        k for k in set(before_keys) | set(row.keys()) if json.loads(original).get(k) != row.get(k)
    )
    print("row %s at line %d/%d" % (args.row_id, target_idx + 1, len(lines)))
    print("changed keys: %s" % ", ".join(changed))

    if not args.write:
        print("DRY RUN: pass --write to apply")
        return 0

    tmp = args.board + ".tmp-repair"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write("\n".join(out) + ("\n" if trailing else ""))
    os.replace(tmp, args.board)
    print("WROTE %s" % args.board)
    print("next: boardctl -C <board-dir> validate, then diff -U0 to confirm one hunk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
