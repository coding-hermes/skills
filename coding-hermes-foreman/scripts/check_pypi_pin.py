#!/usr/bin/env python3
"""Check whether a PyPI package's LATEST release exact-pins a dependency.

Reusable probe for blocked dep-pin tasks (gitreins-poc GR-099 pattern): a task
wants dep>=X but the latest parent release exact-pins dep==Y where Y < X, making
the pin impossible until the parent bumps. Fetches live PyPI JSON METADATA via
urllib only — cron-safe (no curl|python3 pipe, no inline python -c).

Usage:
  check_pypi_pin.py <pkg> <dep-prefix> [--min-version X]

Examples:
  check_pypi_pin.py pydantic pydantic-core --min-version 2.47.0
    -> prints "STILL-BLOCKED", exit 1   (latest pydantic exact-pins core==2.46.4)
    -> prints "UNBLOCKED",    exit 0    (some pin allows >=2.47.0)

Exit code makes it scriptable: 0 = unblocked (dispatch/close the task), 1 =
still blocked (leave task blocked, do NOT re-create — fabrication cycle).
"""
import argparse
import json
import sys
import urllib.request


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-foreman-dep-pin-check"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pkg", help="PyPI package name (e.g. pydantic)")
    ap.add_argument("dep", help="dependency name prefix (e.g. pydantic-core)")
    ap.add_argument("--min-version", help="required minimum version, e.g. 2.47.0")
    args = ap.parse_args()

    info = json.loads(fetch(f"https://pypi.org/pypi/{args.pkg}/json"))["info"]
    ver = info["version"]
    requires_dist = info.get("requires_dist") or []
    pins = [d for d in requires_dist if args.dep in d]
    print(f"{args.pkg} latest: {ver}")
    print(f"requires_dist {args.dep} pins: {pins}")

    dep_info = json.loads(fetch(f"https://pypi.org/pypi/{args.dep}/json"))["info"]
    print(f"{args.dep} latest: {dep_info['version']}")

    if args.min_version:
        ok = any(f">={args.min_version}" in d for d in pins)
    else:
        ok = not any("==" in d for d in pins)
    print("RESULT:", "UNBLOCKED" if ok else "STILL-BLOCKED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
