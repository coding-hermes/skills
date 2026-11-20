#!/usr/bin/env python3
"""Classify a board parity DIVERGENCE by diffing events.jsonl ids vs board.db ids.

Usage: ~/.hermes/venvs/board/bin/python3 board_jsonl_id_diff.py <BOARD_DIR>

Why: board_jsonl_parity_probe.py prints only row counts + max id and exits 1 on
DIVERGENCE. When it diverges, this script shows WHICH ids differ and classifies
the gap so the tick can decide append-vs-repair without re-deriving the diff:

  MATCH            - stores agree, nothing to do
  BENIGN-SUPERSET  - jsonl is a strict superset of db WITH matching max id =
                     stable migration-era gap (jsonl-only old ids), append safe
                     (new event id = MAX+1, no collision); record the gap set in
                     the board event, do NOT repair mid-tick
  DIVERGENCE       - real desync (db-only ids, max-id mismatch, or a GROWING
                     gap vs the recorded baseline) - do NOT append; diagnose

Mixed event-id shapes (DF-CRIER-513): fleet boards carry ints next to legacy
"evt-..." string ids, pure-digit strings and null ids. The DIFF stays a raw id-SET
comparison (a non-numeric id is a real id and must still show up in the only-*
listings), but every ordering/arithmetic step runs over the NUMERIC candidates
only, so `sorted()`/`max()` can never raise TypeError on a mixed set.

Proven: consensus tick #270 (2026-08-19) — BENIGN-SUPERSET, jsonl-only ids
[12, 13, 14, 15, 16, 235, 241, 242] = same stable set as the prior tick noted.
"""
import json
import sys

import duckdb


def numeric_ids(ids):
    """The subset of *ids* usable as an event-id bound, as ints.

    Numeric candidates are ints (bools excluded - True is an int in Python) and
    strings that are pure ASCII digit strings, so a legacy "9" still bounds the
    sequence. Nulls and non-numeric string ids ("evt-7") are ignored here; they
    stay in the parity DIFF, they just cannot be ordered.
    """
    out = []
    for value in ids:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            out.append(value)
        elif isinstance(value, str) and value.isascii() and value.isdigit():
            out.append(int(value))
    return out


def id_sort_key(value):
    """sorted() key that tolerates mixed id shapes: numeric ids first, then strings."""
    if isinstance(value, bool):
        return (1, 0, str(value))
    if isinstance(value, int):
        return (0, value, "")
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return (0, int(value), "")
    return (1, 0, "" if value is None else str(value))


def max_numeric(ids):
    """Largest numeric id, or None when the store holds no numeric id at all."""
    return max(numeric_ids(ids), default=None)


board_dir = sys.argv[1] if len(sys.argv) > 1 else "."

jsonl_ids = set()
with open(f"{board_dir}/events.jsonl") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            jsonl_ids.add(json.loads(line)["id"])
        except Exception:
            pass  # malformed/legacy line - skip id extraction

con = duckdb.connect(f"{board_dir}/board.db", read_only=True)
db_ids = {r[0] for r in con.execute("SELECT id FROM events ORDER BY id").fetchall()}
con.close()

only_jsonl = sorted(jsonl_ids - db_ids, key=id_sort_key)
only_db = sorted(db_ids - jsonl_ids, key=id_sort_key)
max_jsonl = max_numeric(jsonl_ids)
max_db = max_numeric(db_ids)
print(f"jsonl ids: {len(jsonl_ids)} distinct, max {max_jsonl if max_jsonl is not None else 'EMPTY'}")
print(f"db ids:    {len(db_ids)} distinct, max {max_db if max_db is not None else 'EMPTY'}")
print(f"jsonl-only ids: {only_jsonl}")
print(f"db-only ids:    {only_db}")
if max_jsonl is not None:
    print(f"next jsonl event id (max numeric + 1): {max_jsonl + 1}")
if jsonl_ids == db_ids:
    verdict = "MATCH"
elif jsonl_ids > db_ids and max_jsonl == max_db:
    verdict = "BENIGN-SUPERSET (append safe: event id = MAX+1, no collision)"
else:
    verdict = "DIVERGENCE (real desync - do NOT append; diagnose/repair first)"
print(verdict)
