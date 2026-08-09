#!/usr/bin/env python3
"""Read-only probe: verify board.db (DuckDB cache) is in sync with the tracked JSONL mirror.

Usage:
  ~/.hermes/venvs/board/bin/python3 board-db-sync-probe.py [REPO_ROOT]   (default: cwd)

Needs a python with duckdb (system python3 usually lacks it — use the board venv).
Works for any coding-hermes project using the DuckDB v2.1 board at
.coding-hermes/board/ (board.db + board.jsonl/events.jsonl/tasks.jsonl/fixtures.jsonl).

Checks db-vs-JSONL for: board header (last_tick, ticks_total, ticks_idle, last_commit),
events count + max(id), tasks count, fixtures count. Prints PASS/FAIL per table.

WHY (proven TotalStack tick #83/#84):
  JSONL-direct ticks do NOT touch board.db (gitignored cache). After a few such ticks
  board.db lags the tracked JSONL, and running the canonical update script against the
  stale db clobbers the tracked mirror (replaces the newest event, under-counts the
  header). The tracked JSONL is the AUTHORITY; board.db is a rebuildable cache.

DECISION:
  PASS  -> board.db is synced; safe to run the canonical duckdb update script.
  FAIL  -> db is stale: do NOT run the canonical script. Either (a) rebuild board.db
           from the corrected JSONL (DELETE events + re-insert with explicit ids,
           DELETE board + INSERT header row, round-trip verify), or (b) use the
           JSONL-direct update path instead. Never mix blindly.
"""
import json
import os
import sys


def main() -> int:
    repo = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    base = os.path.join(repo, ".coding-hermes", "board")
    db = os.path.join(base, "board.db")
    if not os.path.isdir(base):
        print(f"FAIL: no board dir at {base}")
        return 1

    import duckdb

    con = duckdb.connect(db, read_only=True)
    db_hdr = con.execute(
        "SELECT last_tick, ticks_total, ticks_idle, last_commit FROM board"
    ).fetchone()
    db_ev = con.execute("SELECT COUNT(*), MAX(id) FROM events").fetchone()
    db_tk = con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    db_fx = con.execute("SELECT COUNT(*) FROM fixtures").fetchone()[0]

    def _load_header(path: str) -> dict:
        """Parse board.jsonl header tolerating BOTH single-line NDJSON and
        pretty-printed (multi-line) JSON. Pretty-printed headers were committed
        by some ticks (TotalStack #91) via json.dump(indent=...) — a bare
        readline()+loads() crashes on them (JSONDecodeError line 2 col 1),
        which made the probe useless right when the db/JSONL sync check
        mattered most (#92)."""
        with open(path) as f:
            text = f.read()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
        # multi-line doc: whole file is one JSON object
        return json.loads(text)

    jhdr = _load_header(os.path.join(base, "board.jsonl"))
    with open(os.path.join(base, "events.jsonl")) as f:
        j_evs = [json.loads(l) for l in f if l.strip()]
    with open(os.path.join(base, "tasks.jsonl")) as f:
        j_tk = sum(1 for l in f if l.strip())
    with open(os.path.join(base, "fixtures.jsonl")) as f:
        j_fx = sum(1 for l in f if l.strip())

    hdr_keys = ["last_tick", "ticks_total", "ticks_idle", "last_commit"]
    hdr_ok = all(str(dh) == str(jhdr[k]) for dh, k in zip(db_hdr, hdr_keys))
    ev_ok = db_ev[0] == len(j_evs) and db_ev[1] == max(e["id"] for e in j_evs)
    tk_ok = db_tk == j_tk
    fx_ok = db_fx == j_fx

    print("DB   header:", dict(zip(hdr_keys, [str(v) for v in db_hdr])))
    print("JSON header:", {k: jhdr[k] for k in hdr_keys})
    print(f"DB events count/maxid: {db_ev} | JSON: {len(j_evs)}/{max(e['id'] for e in j_evs)}")
    print(f"DB tasks/fixtures: {db_tk}/{db_fx} | JSON: {j_tk}/{j_fx}")
    for name, ok in [("header", hdr_ok), ("events", ev_ok), ("tasks", tk_ok), ("fixtures", fx_ok)]:
        print(f"  {name}: {'PASS' if ok else 'FAIL'}")
    if hdr_ok and ev_ok and tk_ok and fx_ok:
        print("SYNC: PASS — safe to run the canonical duckdb update script")
        return 0
    print("SYNC: FAIL — board.db is stale vs tracked JSONL; rebuild from JSONL or use JSONL-direct update")
    return 1


if __name__ == "__main__":
    sys.exit(main())
