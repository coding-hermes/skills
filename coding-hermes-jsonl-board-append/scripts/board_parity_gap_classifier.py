#!/usr/bin/env python3
"""Classify a JSONL-board parity DIVERGENCE: benign permanent-gap vs real desync.

Usage: python3 board_parity_gap_classifier.py <board_dir>
(run under the board venv: ~/.hermes/venvs/board/bin/python3, or
`uv run --with duckdb python3` — the script imports duckdb)

Reads events.jsonl (the authoritative tracked store) + the board.db events table,
diffs event ids, and prints the missing set WITH tick numbers so the signature is
classifiable at a glance.

Classification:
- All missing ids HISTORICAL (older ticks) + max id EQUAL in both stores
  -> benign permanent-gap signature: JSONL authoritative, the append script's
  id = MAX(jsonl)+1 keeps new events landing in BOTH stores, the ledger keeps a
  permanent gap. Record the signature in the event's `parity` field; NEVER
  hand-patch board.db; NEVER flag as corruption (scheduler #279 doctrine).
- RECENT ids missing in board.db while JSONL has them -> the append path broke
  (real desync) -> repair warranted.
- Extra ids in db (superset) -> someone wrote board.db directly -> investigate.

Proven: speclang tick #177 (jsonl 46 / db 30, missing ids 12-35 = ticks 155-171
era, max id 46 both -> benign; lockstep since #172).
"""
import json
import sys

try:
    import duckdb
except ImportError:
    print("ERROR: duckdb not available — run under the board venv "
          "(~/.hermes/venvs/board/bin/python3) or `uv run --with duckdb python3`")
    sys.exit(2)

if len(sys.argv) != 2:
    print(f"usage: {sys.argv[0]} <board_dir>   # e.g. .coding-hermes/board")
    sys.exit(2)

board = sys.argv[1].rstrip("/")
try:
    with open(f"{board}/events.jsonl") as f:
        rows = [json.loads(line) for line in f if line.strip()]
except FileNotFoundError:
    print(f"ERROR: {board}/events.jsonl not found (board dir arg? not repo root)")
    sys.exit(2)

jsonl_ids = [r["id"] for r in rows]
con = duckdb.connect(f"{board}/board.db", read_only=True)
try:
    db_ids = [r[0] for r in con.execute("SELECT id FROM events ORDER BY id").fetchall()]
except Exception as e:  # noqa: BLE001 — non-board-schema board.db (pg_views flavor)
    print(f"NOTE: board.db events table unreadable ({e}) — JSONL-only board, no parity possible")
    db_ids = []
finally:
    con.close()

missing = sorted(set(jsonl_ids) - set(db_ids))
extra = sorted(set(db_ids) - set(jsonl_ids))
by_id = {r["id"]: r for r in rows}
max_j = max(jsonl_ids) if jsonl_ids else 0
max_d = max(db_ids) if db_ids else 0

print(f"jsonl ids: {len(jsonl_ids)}  db ids: {len(db_ids)}  max jsonl: {max_j}  max db: {max_d}")
if missing:
    print(f"MISSING in db ({len(missing)}):")
    for i in missing:
        r = by_id[i]
        print(f"  id={i} tick={r.get('tick_number')} type={r.get('event_type')} ts={r.get('timestamp')}")
if extra:
    print(f"EXTRA in db (not in jsonl): {extra}")

if not missing and not extra:
    print("CLASSIFICATION: MATCH — no gaps")
elif extra:
    print("CLASSIFICATION: DB SUPERSET — someone wrote board.db directly; investigate before appending")
elif max_d == max_j and all(i <= max_j - 10 for i in missing):
    print("CLASSIFICATION: benign permanent-gap signature (all missing ids historical, "
          "max id equal in both stores) — JSONL authoritative, no repair; record the "
          "signature in the event's parity field")
else:
    print("CLASSIFICATION: REAL DESYNC — recent ids missing in board.db (append path "
          "broke) — repair warranted")
