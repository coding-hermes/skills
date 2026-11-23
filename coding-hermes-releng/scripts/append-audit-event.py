# Append exactly one audit event to a JSONL board event log, assertion-hardened.
#
# Usage:
#   python3 append-audit-event.py <events.jsonl> <payload.json> [--write]
#        [--marker TEXT] [--force]
#
# payload.json: ONE JSON object = the event you want appended. `detail` may be a
#   dict (it is serialized to a compact JSON STRING, the shape JSONL boards
#   store) or already a string. `id` and `timestamp` are always overwritten:
#   id = max numeric id + 1, timestamp = now UTC. Leave them as 0 / __TS__
#   placeholders in the file you hand in.
#
# Dry run by default (prints the planned line and the assertions it would make);
# pass --write to persist. Exit 0 = done, 2 = refused (nothing written).
#
# --marker TEXT makes the append IDEMPOTENT: if TEXT already appears anywhere in
#   the log the tool refuses, which is what stops a re-fired tick from stacking a
#   duplicate audit event on the same row. --force overrides. Pass the tick ID or
#   another string unique to this pass.
#
# Why this exists: board CLIs commonly expose a row-create/update verb but no
# event verb, and the event log is the file a later audit actually reads. Hand
# appending drifts (string vs dict detail, re-used ids, a second copy of the same
# event); this asserts every one of those invariants instead.
import argparse
import datetime
import json
import pathlib
import sys


def collect_ids(lines):
    max_id = 0
    seen = set()
    for raw in lines:
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        v = rec.get("id")
        if isinstance(v, bool):
            continue
        if isinstance(v, int):
            seen.add(v)
            max_id = max(max_id, v)
        elif isinstance(v, str) and v.isdigit():
            seen.add(int(v))
            max_id = max(max_id, int(v))
    return max_id, seen


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("events_jsonl")
    ap.add_argument("payload_json")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--marker", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    path = pathlib.Path(args.events_jsonl)
    raw = path.read_text(encoding="utf-8").splitlines()
    before = len(raw)

    ev = json.loads(pathlib.Path(args.payload_json).read_text(encoding="utf-8"))
    if not isinstance(ev, dict):
        print("REFUSED: payload must be a single JSON object", file=sys.stderr)
        return 2
    if not ev.get("task_id") or not ev.get("event_type"):
        print("REFUSED: payload needs task_id and event_type", file=sys.stderr)
        return 2

    if args.marker and not args.force:
        hits = sum(1 for line in raw if args.marker in line)
        if hits:
            print(
                f"REFUSED: marker {args.marker!r} already present ({hits} line(s)); "
                "pass --force to append anyway",
                file=sys.stderr,
            )
            return 2

    max_id, seen = collect_ids(raw)
    ev["id"] = max_id + 1
    ev["timestamp"] = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    # Boards store detail as a STRING; a dict here silently breaks every
    # selector that greps the log as text.
    if isinstance(ev.get("detail"), dict):
        ev["detail"] = json.dumps(ev["detail"], separators=(",", ":"), sort_keys=False)

    line = json.dumps(ev, separators=(",", ":"), sort_keys=False)
    if "\n" in line:
        print("REFUSED: serialized event contains a newline", file=sys.stderr)
        return 2

    # --marker is BOTH the idempotency probe and a post-write "appears exactly
    # once" assertion, so it must live INSIDE the payload (e.g. detail.marker).
    # Without this guard, a payload that omits it appends fine and then dies on
    # the post-write assert: a nonzero exit for a durable write.
    if args.marker and args.marker not in line:
        print(
            f"REFUSED: marker {args.marker!r} is not present in the payload. Embed "
            "it in the event (e.g. \"marker\": \"...\" inside detail) so the "
            "post-write assertion can find it, or drop --marker.",
            file=sys.stderr,
        )
        return 2

    if not args.write:
        print(f"log lines: {before} -> {before + 1}")
        print(f"new id: {ev['id']} (max was {max_id}, unique={ev['id'] not in seen})")
        print(f"task_id: {ev['task_id']}  event_type: {ev['event_type']}")
        print(f"detail: {'string' if isinstance(ev['detail'], str) else type(ev['detail']).__name__}")
        print(f"line: {line[:300]}{'...' if len(line) > 300 else ''}")
        print("DRY RUN: pass --write to append")
        return 0

    unparseable = sum(1 for l in raw if l.strip() and not _parses(l))
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    after = path.read_text(encoding="utf-8").splitlines()
    last = json.loads(after[-1])
    assert len(after) == before + 1, f"line count {len(after)} != {before + 1}"
    assert last["id"] == ev["id"], "appended id does not match planned id"
    assert last.get("task_id") == ev["task_id"], "appended task_id drifted"
    if args.marker:
        hits_before = sum(1 for l in raw if args.marker in l)
        hits = sum(1 for l in after if args.marker in l)
        assert hits == hits_before + 1, (
            f"marker appears {hits} times after write (expected {hits_before + 1})"
        )
    print(
        f"APPENDED id={ev['id']} ts={ev['timestamp']} task={ev['task_id']} "
        f"lines {before}->{len(after)}"
        + (f" marker_once=true" if args.marker else "")
        + (f" pre_existing_unparseable={unparseable}" if unparseable else "")
    )
    return 0


def _parses(raw):
    try:
        json.loads(raw)
        return True
    except json.JSONDecodeError:
        return False


if __name__ == "__main__":
    sys.exit(main())
