#!/usr/bin/env python3
"""Storm-watch probe for scheduler ticks: count running ticks + uniqueness.

Saves the hand-rolled per-tick probe. The /api/v1/ticks GET returns a DICT
wrapper {"ticks": [...]} with GO-STYLE CAPITALIZED field names (Status,
ProjectName, ID) — snake_case keys silently return None for every tick, so a
naive parse reports 0 running and the duplicate check vacuously passes.

Usage (cron-safe — no pipes, no -c flags):
  curl -s -m 10 -o /tmp/sched_ticks.json "http://127.0.0.1:9090/api/v1/ticks?limit=200"
  python3 /tmp/storm-watch.py /tmp/sched_ticks.json

Exit 0 always; prints a one-line verdict + project list. PASS = 0 dups.
Note: the running set is a MOVING WINDOW — two samples ~30s apart can
legitimately differ (a tick completes, another spawns). The check is
per-sample uniqueness, NOT membership stability.
"""
import json
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: storm-watch.py <ticks-json-file>")
        return 1
    with open(sys.argv[1]) as f:
        d = json.load(f)
    ticks = d.get("ticks", []) if isinstance(d, dict) else d
    runs = [t for t in ticks if t.get("Status") == "running"]
    names = [t.get("ProjectName") or "?" for t in runs]
    n, uniq = len(names), len(set(names))
    verdict = "PASS" if n == uniq else "FAIL"
    print(f"storm-watch {verdict}: running={n} unique={uniq} dups={n - uniq}")
    print("projects:", sorted(set(names)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
