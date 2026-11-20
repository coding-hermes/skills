#!/usr/bin/env python3
"""Manual JSONL board append — NO appender script, NO duckdb (JSONL-canonical boards).

Proven first-try clean: consensus tick #243 (2026-08-17). Use when a board's
tracked truth is events.jsonl + board.jsonl (header) and you want the whole
write in one script: MAX+1 event append + single-line compact header rewrite +
verification. Idempotent enough to re-run safely (MAX+1 recomputed each run).

EDIT THESE:
  REPO   = absolute repo path (scheduler sessions redirect HOME — no ~)
  TICK_N = the tick number (matches events tick_number + header ticks_total)
  EVENT_TYPE = board convention ("idle" for consensus idle ticks; the stock
               appender hardcodes "audit" — do not use it here)
  DETAIL = the tick's detail dict (compact keys; see board's prior events for
           the exact key set — consensus: tick/type/verdict/work/scheduler/
           gitreins/unpushed/last_commit/build/deps/ci/off_by_one/duckbrain/
           siblings)
"""
import json, datetime


def next_event_id(lines):
    """Next event id: max over NUMERIC ids only, +1 (1 when the board has none).

    Fleet boards carry mixed id shapes - plain ints next to legacy "evt-..." string
    ids and null ids - so the previous bare max() over int() of every row's id raised
    TypeError on a string row (and KeyError on an id-less row) before anything was
    appended. Ints and pure-digit strings ("42") bound the sequence; nulls, id-less
    and non-numeric rows are ignored. Same contract as the DF-CRIER-511 helpers in
    coding-hermes-foreman/scripts/append_board_task_completed.py, inlined because
    templates are copy/pasted into /tmp, not imported.
    """
    best = 0
    for line in lines:
        try:
            value = json.loads(line).get("id")
        except (ValueError, AttributeError):
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            best = max(best, value)
        elif isinstance(value, str) and value.isascii() and value.isdigit():
            best = max(best, int(value))
    return best + 1


BOARD_DIR = "<REPO>/.coding-hermes/board"   # e.g. ~/consensus/.coding-hermes/board
TICK_N = 0                                  # e.g. 243
EVENT_TYPE = "idle"                         # consensus convention for idle ticks

DETAIL = {
    "tick": TICK_N,
    "type": "idle",
    # ... full detail dict here (see board's prior events for the key set) ...
}

events_path = f"{BOARD_DIR}/events.jsonl"
header_path = f"{BOARD_DIR}/board.jsonl"

now = datetime.datetime.now()
ts = now.strftime("%Y-%m-%d %H:%M:%S") + ".000000"

# --- events append (compact ensure_ascii line; MAX+1 id over numeric ids only) ---
with open(events_path, "r", encoding="utf-8") as f:
    lines = f.readlines()
new_id = next_event_id(lines)
event = {
    "id": new_id,
    "timestamp": ts,
    "event_type": EVENT_TYPE,
    "task_id": None,
    "actor": "foreman",
    "detail": json.dumps(DETAIL, ensure_ascii=True, separators=(",", ":")),
    "tick_number": TICK_N,
}
with open(events_path, "a", encoding="utf-8") as f:
    f.write(json.dumps(event, ensure_ascii=True, separators=(",", ":")) + "\n")

# --- header rewrite: SINGLE-LINE compact JSON (json.dumps default separators),
#     or the diff churns all lines (proven consensus #159). Keep last_commit =
#     pre-tick HEAD (board commit always lands AFTER this write). ---
header = json.load(open(header_path, encoding="utf-8"))
header["last_tick"] = ts
header["ticks_total"] = TICK_N
header["ticks_idle"] = header.get("ticks_idle", 0) + (0 if DETAIL.get("type") == "task_completed" else 1)  # adjust per tick type
header["updated_at"] = ts
with open(header_path, "w", encoding="utf-8") as f:
    f.write(json.dumps(header, ensure_ascii=True, separators=(",", ":")) + "\n")

# --- verify (always re-read; a silent no-op write looks successful otherwise) ---
with open(events_path, "r", encoding="utf-8") as f:
    ev = [json.loads(l) for l in f if l.strip()]
hdr = json.load(open(header_path, encoding="utf-8"))
print(f"events: {len(ev)} lines, last id {ev[-1]['id']}, tick_number {ev[-1]['tick_number']}")
print(f"header: ticks_total={hdr['ticks_total']} ticks_idle={hdr['ticks_idle']} last_commit={hdr['last_commit']}")
assert ev[-1]["id"] == new_id, "event id != MAX+1"

# --- commit convention (JSONL era): NORMAL commit, no --no-verify ---
# git add -f <repo>/.coding-hermes/board/board.jsonl <repo>/.coding-hermes/board/events.jsonl
# git commit -m "board: tick #<N> — ..."   # NO Co-authored-by in -m: hook appends exactly 1
# verify: git show --stat HEAD (both files) + git log -1 --format='%B' | grep -c '^Co-authored-by:' == 1
# then PUSH (mandatory per current fleet convention) and `git rev-list --count origin/<branch>..HEAD` == 0.
