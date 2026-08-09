#!/usr/bin/env python3
"""Group a golangci-lint v2 JSON issue dump by directory (slice picking) or by file (straggler spotting).

Usage:
  python3 goconst_inventory.py <dump.json> [--files]

Dump must be created with canonical flags so counts match the goconstfix rewriter:
  golangci-lint run --enable-only goconst --max-issues-per-linter=0 \
    --max-same-issues=0 --uniq-by-line=false --output.json.path /tmp/goconst.json ./...

Default groups by package directory (first two path components) -> use for slice
picking (pick a small clean package, avoid ones with heavy co-located debt).
--files groups by full file path -> use after a rewriter pass to spot stragglers
or to see which files carry the remaining issues.

Also prints TOTAL issues — this is the canonical repo-wide count to cite in
commit messages and board notes (never quote prior ticks' numbers; re-measure).
"""
import json
import sys
from collections import Counter


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    by_file = "--files" in sys.argv[2:]
    with open(path) as f:
        data = json.load(f)
    issues = data.get("Issues", [])
    print(f"TOTAL issues: {len(issues)}")
    c: Counter = Counter()
    for i in issues:
        fn = i["Pos"]["Filename"]
        if by_file:
            c[fn] += 1
        else:
            parts = fn.split("/")
            key = "/".join(parts[:2]) if len(parts) >= 2 else parts[0]
            c[key] += 1
    for key, n in c.most_common():
        print(f"{n:5d}  {key}")


if __name__ == "__main__":
    main()
