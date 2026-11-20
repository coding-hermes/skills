#!/usr/bin/env python3
"""board_parity_id_diff.py — diagnose a parity DIVERGENCE between events.jsonl and board.db.

Usage: python3 board_parity_id_diff.py <board-dir>   (default: .coding-hermes/board)
Needs duckdb: invoke via ~/.hermes/venvs/board/bin/python3.

Prints: id counts per store, jsonl-only ids, db-only ids, max ids, and a VERDICT.

Mixed event-id shapes (DF-CRIER-513): fleet boards carry ints next to legacy
"evt-..." string ids, pure-digit strings and null ids — on BOTH stores. The DIFF
stays a raw id-SET comparison (a non-numeric id is a real id and must still show
up in the only-* listings), but every ordering/arithmetic step (sorted(), max())
runs over the NUMERIC candidates only, so a mixed set can never raise TypeError.

Verdict meanings (per idle-cheap-audit-ladder parity doctrine):
- "benign jsonl-superset stable gap": jsonl-only ids present, NO db-only ids, max ids
  EQUAL. Append stays safe (next event = MAX+1, no collision); record the gap set as a
  baseline in the event detail and do NOT repair mid-tick.
  NOTE: the gap set can include RECENT ids — consensus tick #257 (2026-08-18) found id
  235 (= tick #254's event, 4 ticks old) jsonl-only alongside migration-era ids 12-16,
  still benign because later ids (236, 237) landed in BOTH stores (gap not growing) and
  max-id matched. Diagnose by the criteria, not by gap age.
- Anything else (db-only ids, OR max-id mismatch, OR a growing gap) = REAL desync —
  stop, diagnose the append script / mirror sync before appending.
"""
import json
import sys

import duckdb


def numeric_ids(ids):
    """The subset of *ids* usable as an event-id bound, as ints.

    Numeric candidates are ints (bools excluded - True is an int in Python) and
    strings that are pure ASCII digit strings. Nulls and non-numeric string ids
    ("evt-7") are ignored here; they stay in the parity DIFF, they just cannot be
    ordered.
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


def main() -> int:
    board_dir = sys.argv[1] if len(sys.argv) > 1 else ".coding-hermes/board"
    jsonl_path = f"{board_dir}/events.jsonl"
    db_path = f"{board_dir}/board.db"

    jsonl_ids = set()
    for line in open(jsonl_path):
        line = line.strip()
        if not line:
            continue
        try:
            jsonl_ids.add(json.loads(line)["id"])
        except Exception:
            pass

    con = duckdb.connect(db_path, read_only=True)
    db_ids = set(r[0] for r in con.execute("SELECT id FROM events").fetchall())
    con.close()

    only_jsonl = sorted(jsonl_ids - db_ids, key=id_sort_key)
    only_db = sorted(db_ids - jsonl_ids, key=id_sort_key)
    max_jsonl = max_numeric(jsonl_ids)
    max_db = max_numeric(db_ids)
    print(f"jsonl ids: {len(jsonl_ids)}  db ids: {len(db_ids)}")
    print(f"jsonl-only ids: {only_jsonl}")
    print(f"db-only ids: {only_db}")
    print(f"max jsonl: {max_jsonl if max_jsonl is not None else 'EMPTY'}  "
          f"max db: {max_db if max_db is not None else 'EMPTY'}")
    if max_jsonl is not None:
        print(f"next jsonl id (max numeric + 1): {max_jsonl + 1}")
    if only_jsonl and not only_db and max_jsonl == max_db:
        print("VERDICT: benign jsonl-superset stable gap — append safe (MAX+1), record baseline, do not repair")
    else:
        print("VERDICT: REAL DESYNC — diagnose before appending")
    return 0


if __name__ == "__main__":
    sys.exit(main())
