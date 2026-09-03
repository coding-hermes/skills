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

Proven: consensus tick #270 (2026-08-19) — BENIGN-SUPERSET, jsonl-only ids
[12, 13, 14, 15, 16, 235, 241, 242] = same stable set as the prior tick noted.
"""
import json
import sys

import duckdb

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

only_jsonl = sorted(jsonl_ids - db_ids)
only_db = sorted(db_ids - jsonl_ids)
print(f"jsonl ids: {len(jsonl_ids)} distinct, max {max(jsonl_ids)}")
print(f"db ids:    {len(db_ids)} distinct, max {max(db_ids)}")
print(f"jsonl-only ids: {only_jsonl}")
print(f"db-only ids:    {only_db}")
if jsonl_ids == db_ids:
    verdict = "MATCH"
elif jsonl_ids > db_ids and max(jsonl_ids) == max(db_ids):
    verdict = "BENIGN-SUPERSET (append safe: event id = MAX+1, no collision)"
else:
    verdict = "DIVERGENCE (real desync - do NOT append; diagnose/repair first)"
print(verdict)
