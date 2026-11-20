#!/usr/bin/env python3
"""Classify a JSONL-board parity DIVERGENCE: benign permanent-gap vs real desync.

Usage: python3 board_parity_gap_classifier.py <board_dir>
(run under the board venv: ~/.hermes/venvs/board/bin/python3, or
`uv run --with duckdb python3` — the script imports duckdb)

Reads events.jsonl (the authoritative tracked store) + the board.db events table,
diffs event ids, and prints the missing set WITH tick numbers so the signature is
classifiable at a glance.

Mixed event-id shapes (DF-CRIER-513): fleet boards carry ints next to legacy
"evt-..." string ids, pure-digit strings, null ids and rows with no id at all. The
DIFF stays a raw id-SET comparison (a non-numeric id is a real id and is listed),
while every ordering/arithmetic step (sorted(), max(), the "older than max-10"
age test) runs over the NUMERIC candidates only, so a mixed board can never raise
TypeError/KeyError here.

Classification:
- All missing ids HISTORICAL (older ticks) + max id EQUAL in both stores
  -> benign permanent-gap signature: JSONL authoritative, the append script's
  id = MAX(jsonl)+1 keeps new events landing in BOTH stores, the ledger keeps a
  permanent gap. Record the signature in the event's `parity` field; NEVER
  hand-patch board.db; NEVER flag as corruption (scheduler #279 doctrine).
  Non-numeric missing ids ("evt-7", null) are named in a NOTE: they carry no tick
  ordering, so they are neither proof of age nor of a recent break.
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


def is_numeric_id(value):
    """True when *value* can act as an event-id bound (bools are not ids)."""
    if isinstance(value, bool):
        return False
    return isinstance(value, int) or (isinstance(value, str) and value.isascii() and value.isdigit())


def numeric_ids(ids):
    """The subset of *ids* usable as an event-id bound, as ints.

    Numeric candidates are ints (bools excluded - True is an int in Python) and
    strings that are pure ASCII digit strings. Nulls and non-numeric string ids
    ("evt-7") stay in the parity DIFF, they just cannot be ordered.
    """
    return [int(value) for value in ids if is_numeric_id(value)]


def id_sort_key(value):
    """sorted() key that tolerates mixed id shapes: numeric ids first, then strings."""
    if isinstance(value, bool):
        return (1, 0, str(value))
    if isinstance(value, int):
        return (0, value, "")
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return (0, int(value), "")
    return (1, 0, "" if value is None else str(value))


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

# Rows may be dicts without an "id" key or non-dict garbage: keep them, id None.
jsonl_ids = [r.get("id") if isinstance(r, dict) else None for r in rows]
con = duckdb.connect(f"{board}/board.db", read_only=True)
try:
    db_ids = [r[0] for r in con.execute("SELECT id FROM events ORDER BY id").fetchall()]
except Exception as e:  # noqa: BLE001 — non-board-schema board.db (pg_views flavor)
    print(f"NOTE: board.db events table unreadable ({e}) — JSONL-only board, no parity possible")
    db_ids = []
finally:
    con.close()

missing = sorted(set(jsonl_ids) - set(db_ids), key=id_sort_key)
extra = sorted(set(db_ids) - set(jsonl_ids), key=id_sort_key)
by_id = {r.get("id"): r for r in rows if isinstance(r, dict)}
max_j = max(numeric_ids(jsonl_ids), default=0)
max_d = max(numeric_ids(db_ids), default=0)
missing_numeric = numeric_ids(missing)
missing_non_numeric = [i for i in missing if not is_numeric_id(i)]

print(f"jsonl ids: {len(jsonl_ids)}  db ids: {len(db_ids)}  max jsonl: {max_j}  max db: {max_d}")
if missing:
    print(f"MISSING in db ({len(missing)}):")
    for i in missing:
        r = by_id.get(i) or {}
        print(f"  id={i} tick={r.get('tick_number')} type={r.get('event_type')} ts={r.get('timestamp')}")
if extra:
    print(f"EXTRA in db (not in jsonl): {extra}")
if missing_non_numeric:
    print(f"NOTE: non-numeric missing ids {missing_non_numeric} carry no tick ordering — "
          "listed in the diff but excluded from the max/age arithmetic")

if not missing and not extra:
    print("CLASSIFICATION: MATCH — no gaps")
elif extra:
    print("CLASSIFICATION: DB SUPERSET — someone wrote board.db directly; investigate before appending")
elif max_d == max_j and all(i <= max_j - 10 for i in missing_numeric):
    print("CLASSIFICATION: benign permanent-gap signature (all missing ids historical, "
          "max id equal in both stores) — JSONL authoritative, no repair; record the "
          "signature in the event's parity field")
else:
    print("CLASSIFICATION: REAL DESYNC — recent ids missing in board.db (append path "
          "broke) — repair warranted")
