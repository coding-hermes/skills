#!/usr/bin/env python3
"""goconst_preflight_overlap.py — pick the cleanest package for a goconst debt slice.

For each candidate package, dumps the goconst issue set and the other-linter issue set
(noctx/errcheck/gosec/unused/unparam/gocyclo/gocritic/staticcheck/ineffassign/whitespace/
misspell) and reports the LINE OVERLAP between them.

WHAT IT CAN TELL YOU:
  - High flagged-line overlap  -> package will surface co-located debt under CI
    `only-new-issues` -> NOT a clean slice candidate (or needs a debt-class slice first).
  - Zero overlap              -> good sign, BUT SEE THE BLIND SPOT below.

⚠ BLIND SPOT (proven hivemind tick 214): the goconstfix rewriter replaces EVERY
occurrence of a flagged string across the package, not just the goconst-flagged lines
(527 rewrites from 99 flagged issues in pkg/database). Other-linter issues on
REPLACEMENT lines that were never goconst-flagged also become "new" under CI.
The JSON dump only contains flagged lines, so this script CANNOT see that debt.
The reliable gate remains the post-rewrite run:
    golangci-lint run --new-from-rev=origin/main --max-issues-per-linter=0 --max-same-issues=0 ./<pkg>/...
Budget for a uniform co-located class (e.g. 20+ noctx on touched lines) even at 0 overlap.

USAGE:
    python3 goconst_preflight_overlap.py [repo-root] [pkg...]
    python3 goconst_preflight_overlap.py ~/hivemind-work pkg/database pkg/alerts
    (defaults: repo-root = cwd, pkgs = pkg/database pkg/alerts)
"""
import collections
import json
import subprocess
import sys

GOLANGCI = "~/go/bin/golangci-lint"
OTHER_LINTERS = ["noctx", "errcheck", "gosec", "unused", "unparam", "gocyclo",
                 "gocritic", "staticcheck", "ineffassign", "whitespace", "misspell"]


def dump(repo_root, pkg, tag, linters):
    out = "/tmp/goconst_preflight_%s_%s.json" % (pkg.replace("/", "_"), tag)
    cmd = [GOLANGCI, "run", "--no-config", "--default=none",
           "--max-issues-per-linter=0", "--max-same-issues=0", "--uniq-by-line=false",
           "--output.json.path=" + out]
    # NOTE: --enable-only is REQUIRED here. Bare --enable=goconst (without --no-config)
    # still applies the repo .golangci.yml enable list (tick 214 saw gosec/noctx leak in).
    cmd += ["--enable-only=" + ",".join(linters)]
    cmd += [pkg + "/..."]
    r = subprocess.run(cmd, capture_output=True, cwd=repo_root, timeout=540)
    if r.returncode not in (0, 1):  # 1 = issues found (normal); other = tool failure
        print("  !! golangci-lint failed for %s (%s): rc=%d" % (pkg, tag, r.returncode))
        print("  stderr:", r.stderr.decode()[:300])
        return None
    try:
        with open(out) as f:
            return json.load(f)
    except Exception as e:
        print("  !! cannot read dump for %s (%s): %s" % (pkg, tag, e))
        return None


def main():
    args = sys.argv[1:]
    repo_root = args[0] if args else "."
    pkgs = args[1:] if len(args) > 1 else ["pkg/database", "pkg/alerts"]

    for pkg in pkgs:
        g = dump(repo_root, pkg, "goconst", ["goconst"])
        if g is None:
            continue
        goconst_lines = {}
        for i in g["Issues"]:
            goconst_lines.setdefault((i["Pos"]["Filename"], i["Pos"]["Line"]), []).append(i["Text"])

        o = dump(repo_root, pkg, "others", OTHER_LINTERS)
        if o is None:
            continue
        other_lines = collections.defaultdict(list)
        for i in o["Issues"]:
            other_lines[(i["Pos"]["Filename"], i["Pos"]["Line"])].append(i["FromLinter"])

        overlap = {k: v for k, v in other_lines.items() if k in goconst_lines}
        print("=== %s: %d goconst issues / %d lines; %d other-linter issues / %d lines; "
              "FLAGGED-LINE OVERLAP %d lines ===" % (
                  pkg, len(g["Issues"]), len(goconst_lines),
                  len(o["Issues"]), len(other_lines), len(overlap)))
        if overlap:
            for (fname, line), lints in sorted(overlap.items())[:20]:
                print("    OVERLAP %s:%d %s" % (fname.split("/")[-1], line,
                                                ",".join(sorted(set(lints)))))
        print("    ⚠ blind spot: rewriter touches ALL occurrence lines, not just flagged "
              "ones — 0 overlap does NOT guarantee clean. Gate post-rewrite with "
              "--new-from-rev=origin/main.")


if __name__ == "__main__":
    main()
