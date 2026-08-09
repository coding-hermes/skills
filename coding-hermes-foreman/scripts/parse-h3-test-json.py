#!/usr/bin/env python3
"""Parse h3-test --json output files (H3 E2E tick verification).

Usage: python3 parse-h3-test-json.py /tmp/e2e_91.json [/tmp/e2e_92.json ...]

Handles files with a trailing '<LANG>_EXIT=N' marker line appended by the
spawning shell wrapper (stripped before JSON parsing). Prints pass counts,
failed test names, latency percentiles (the _ms-suffixed keys), and the
stable category breakdown (7/8/6/7/10/5 = 43 across all SDKs).
"""
import json
import sys
import collections

MARKERS = ("GO_EXIT", "PY_EXIT", "TS_EXIT", "EXIT")
LAT_KEYS = ("min_ms", "p50_ms", "p90_ms", "p95_ms", "p99_ms", "max_ms", "mean_ms")


def parse(path):
    raw = open(path).read()
    lines = [l for l in raw.strip().splitlines() if not l.startswith(MARKERS)]
    data = json.loads("\n".join(lines))
    lat = data.get("latency", {})
    cats = collections.Counter(r.get("category") or "?" for r in data.get("results", []))
    failed = [r.get("name") for r in data.get("results", []) if not r.get("passed")]
    print(f"== {path} ==")
    print(f"  passed={data.get('passed')}/{data.get('total')} failed={failed}")
    if isinstance(lat, dict) and lat:
        print("  latency:", {k: lat[k] for k in LAT_KEYS if k in lat})
    if cats:
        print("  categories:", dict(cats))
    for k in ("duration_ms", "duration_s", "elapsed_ms"):
        if k in data:
            print(f"  {k}={data[k]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for p in sys.argv[1:]:
        try:
            parse(p)
        except Exception as e:
            print(f"== {p}: PARSE ERROR {e} ==")
