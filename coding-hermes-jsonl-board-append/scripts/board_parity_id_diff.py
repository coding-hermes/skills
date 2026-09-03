#!/usr/bin/env python3
"""board_parity_id_diff.py — diagnose a parity DIVERGENCE between events.jsonl and board.db.

Usage: python3 board_parity_id_diff.py <board-dir>   (default: .coding-hermes/board)
Needs duckdb: invoke via ~/.hermes/venvs/board/bin/python3.

Prints: id counts per store, jsonl-only ids, db-only ids, max ids, and a VERDICT.

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

    only_jsonl = sorted(jsonl_ids - db_ids)
    only_db = sorted(db_ids - jsonl_ids)
    print(f"jsonl ids: {len(jsonl_ids)}  db ids: {len(db_ids)}")
    print(f"jsonl-only ids: {only_jsonl}")
    print(f"db-only ids: {only_db}")
    print(f"max jsonl: {max(jsonl_ids) if jsonl_ids else 'EMPTY'}  max db: {max(db_ids) if db_ids else 'EMPTY'}")
    if only_jsonl and not only_db and max(jsonl_ids) == max(db_ids):
        print("VERDICT: benign jsonl-superset stable gap — append safe (MAX+1), record baseline, do not repair")
    else:
        print("VERDICT: REAL DESYNC — diagnose before appending")
    return 0


if __name__ == "__main__":
    sys.exit(main())
