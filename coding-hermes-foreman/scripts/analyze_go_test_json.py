#!/usr/bin/env python3
"""Analyze `go test -json` output: per-package wall times + slowest top-level
tests. Filters subtest names (contain '/') so parent tests aren't double-counted
— the sum of ALL test events overstates wall time badly (canopy T190: 246s sum
vs 190s package wall).

Usage:
  go test -short -p 1 -count=1 -timeout 300s -json ./... > /tmp/sweep.json
  python3 analyze_go_test_json.py /tmp/sweep.json

Prints: per-package elapsed (desc), then top-level tests >= 2s per package.
Exit 0 always (parse-only)."""
import json
import sys

if len(sys.argv) < 2:
    print("usage: analyze_go_test_json.py <go-test-json-file>")
    sys.exit(1)

path = sys.argv[1]
pkgs = {}
tests = {}
fails = []
for line in open(path):
    try:
        d = json.loads(line)
    except Exception:
        continue
    if d.get('Action') in ('pass', 'fail', 'skip') and d.get('Test'):
        p = d['Package'].split('/')[-1]
        if '/' not in d['Test']:  # top-level only
            tests.setdefault(p, []).append((d.get('Elapsed', 0), d['Test'], d.get('Action')))
        if d.get('Action') == 'fail':
            fails.append(d['Test'])
    elif d.get('Action') == 'pass' and d.get('Package') and not d.get('Test'):
        pkgs[d['Package'].split('/')[-1]] = d.get('Elapsed', 0)

print("=== package wall times ===")
for p, e in sorted(pkgs.items(), key=lambda x: -x[1]):
    print(f"{e:8.1f}s  {p}")

print("\n=== top-level tests >= 2s ===")
for p, ts in sorted(tests.items()):
    for e, t, a in sorted(ts, key=lambda x: -x[0]):
        if e >= 2.0:
            print(f"{e:8.1f}s  {a:4s} {t}  [{p}]")

if fails:
    print("\n=== FAILED TESTS ===")
    for f in fails:
        print(" ", f)
