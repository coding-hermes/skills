#!/usr/bin/env python3
"""count_goconst_by_package.py — per-package goconst counts from a golangci-lint JSON dump.

Canonical next-slice-order counter for LINT-DEBT-001-style goconst paydowns
(hivemind-work + any Go repo with a golangci-lint v2 goconst debt slice).

Usage (after the canonical three-flag repo-wide dump):
  golangci-lint run --no-config --default=none --enable-only=goconst \
    --max-issues-per-linter=0 --max-same-issues=0 --uniq-by-line=false \
    --output.json.path=/tmp/goconst_repo.json ./...
  ~/.hermes/venvs/board/bin/python3 count_goconst_by_package.py /tmp/goconst_repo.json

Classifies issues by repo top-level dir (pkg/, internal/, cmd/, tests/<sub>,
scripts/, web/, migrations/) so tests/ and scripts/ counts never hide in an
unknown bucket — hivemind tick 223's first naive counter (pkg/internal/cmd/
test/web prefixes only) left 191 tests/ + scripts/ issues classified as '?';
a second-pass classifier exposed tests/report 66, tests/regression 37,
tests/security 32, scripts/generate-openapi 6. This script does both passes
in one. Sorted descending; pkg slices are prioritized over tests/ when
choosing the next slice.

Stdlib only (json/collections) — runs under the board venv python
(~/.hermes/venvs/board), no duckdb/numpy needed.

Optional second arg = linter name to count (default goconst), so the same
script serves noctx/errcheck/gosec counting during CI-sim sweeps.
"""
import collections
import json
import sys

TOP_DIRS = ("pkg", "internal", "cmd", "tests", "test", "scripts", "web", "migrations")


def classify(path: str) -> str:
    parts = path.split("/")
    for i, p in enumerate(parts):
        if p in TOP_DIRS:
            sub = parts[i + 1] if i + 1 < len(parts) else ""
            if p == "tests" and sub:
                return f"tests/{sub}"
            return f"{p}/{sub}" if sub else p
    # repo-root file (e.g. main.go) — key by its own name
    return parts[-1] if parts else "?"


def main() -> None:
    if len(sys.argv) not in (2, 3):
        print(f"usage: {sys.argv[0]} <golangci-json-dump> [linter]", file=sys.stderr)
        sys.exit(2)
    linter = sys.argv[2] if len(sys.argv) == 3 else "goconst"
    with open(sys.argv[1]) as f:
        data = json.load(f)
    counts = collections.Counter()
    for issue in data.get("Issues", []):
        if issue.get("FromLinter") == linter:
            counts[classify(issue.get("Pos", {}).get("Filename", "?"))] += 1
    for pkg, n in counts.most_common():
        print(f"{n:5d}  {pkg}")
    print(f"TOTAL: {sum(counts.values())}")


if __name__ == "__main__":
    main()
