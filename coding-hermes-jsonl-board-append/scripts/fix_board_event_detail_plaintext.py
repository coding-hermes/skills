#!/usr/bin/env python3
"""Fix double-escaped event detail rows written by append_board_event.py.

append_board_event.py does `detail = json.load(detail_file)` then
`detail_json = json.dumps(detail)`, so a detail file holding a JSON string
literal ("Tick N ...") lands in the event row with an EXTRA literal quote
layer: `"detail": "\"Tick N ...\""`. Boards whose committed convention is
PLAIN-TEXT detail (totalstack #109, proven #168 2026-08-10) need the row
de-escaped in BOTH stores (events.jsonl authoritative + board.db cache) so
parity probes stay green.

Usage:
  python3 fix_board_event_detail_plaintext.py <repo> [event_id]

  repo      absolute path to the project repo
  event_id  optional; omit to scan ALL events (de-escapes every row whose
            detail is a quoted JSON string — safe: plain-text rows untouched)

Only rows where detail starts AND ends with `"` and json.loads(detail)
succeeds are rewritten (the json.dumps-of-a-string signature). Rows are
re-dumped with the same compact separators + ensure_ascii=False style the
appender uses; ASCII-only detail text avoids escape-style churn.
"""
import json
import sys

repo = sys.argv[1]
event_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
board = f"{repo.rstrip('/')}/.coding-hermes/board"
events_path = f"{board}/events.jsonl"
db_path = f"{board}/board.db"

with open(events_path) as f:
    lines = f.readlines()

changed = []
for i, line in enumerate(lines):
    line = line.strip()
    if not line:
        continue
    ev = json.loads(line)
    if event_id is not None and ev.get("id") != event_id:
        continue
    d = ev.get("detail")
    if isinstance(d, str) and d.startswith('"') and d.endswith('"'):
        try:
            unescaped = json.loads(d)
        except json.JSONDecodeError:
            continue
        if isinstance(unescaped, str) and unescaped != d:
            ev["detail"] = unescaped
            lines[i] = json.dumps(ev, ensure_ascii=False, separators=(",", ":")) + "\n"
            changed.append(ev["id"])

if not changed:
    print(f"NO CHANGE: no double-escaped detail rows {'for id ' + str(event_id) if event_id else ''}")
    sys.exit(0)

with open(events_path, "w") as f:
    f.writelines(lines)
print(f"events.jsonl de-escaped ids: {changed}")

# re-sync board.db cache (same rows, same strings — parity must match)
try:
    import duckdb
except ImportError:
    print("WARN: duckdb not available — board.db cache NOT synced; run with `uv run --with duckdb`")
    sys.exit(0)

con = duckdb.connect(db_path)
for eid in changed:
    target = None
    with open(events_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            if ev.get("id") == eid:
                target = ev["detail"]
                break
    con.execute("UPDATE events SET detail = ? WHERE id = ?", [target, eid])
con.close()
print(f"board.db synced ids: {changed}")
