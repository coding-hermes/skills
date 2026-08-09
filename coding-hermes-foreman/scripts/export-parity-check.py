#!/usr/bin/env python3
"""Export-parity check for barrel-split refactors (QUALITY-LF series and any TS split).

Deterministic probe: compares the exported symbols of a PRE-SPLIT file
(extracted from git history) against a module barrel's re-exports. Exits 1 on
any missing or extra symbol. Handles the false-diff traps of naive greps:
function-decl parens (`getSyncStatus():`), generics (`queueApiCall<T`), and
single-line `export { x } from "./y.js"` entries.

Usage:
  export-parity-check.py REPO PRE_SPLIT_COMMIT ORIGINAL_FILE BARREL_FILE

Example (mythos tick #120):
  export-parity-check.py ~/wojons-mythos 95c033c2d \
    packages/frontend/src/utils/offline-handler.ts \
    packages/frontend/src/utils/offline-handler/index.ts
"""
import argparse
import re
import subprocess
import sys

# export type ActionType = ... | export interface X { | export const y = | export function f():
PRE_EXPORT_RE = re.compile(
    r"^export\s+(?:type\s+|interface\s+|const\s+|function\s+)?([A-Za-z_]\w*)"
)


def pre_split_exports(repo: str, commit: str, path: str) -> set[str]:
    out = subprocess.run(
        ["git", "-C", repo, "show", f"{commit}:{path}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    names = set()
    for line in out.splitlines():
        m = PRE_EXPORT_RE.match(line)
        if m:
            names.add(m.group(1))
    return names


def barrel_exports(barrel_path: str) -> set[str]:
    text = open(barrel_path).read()
    names = set()
    for block in re.findall(r"export(?:\s+type)?\s*\{([^}]*)\}", text):
        for line in block.split(","):
            line = line.strip()
            if not line:
                continue
            # `x as y` renames: the exported name is y (matches pre-split name)
            name = line.split(" as ", 1)[-1].strip()
            names.add(name.split()[0])
    return names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", help="absolute path to the git repo")
    ap.add_argument("commit", help="pre-split commit (file state BEFORE the refactor)")
    ap.add_argument("original", help="path to the original file, repo-relative")
    ap.add_argument("barrel", help="path to the new index.ts barrel")
    args = ap.parse_args()

    pre = pre_split_exports(args.repo, args.commit, args.original)
    barrel = barrel_exports(args.barrel)
    missing = sorted(pre - barrel)
    extra = sorted(barrel - pre)

    print(f"PRE-SPLIT ({len(pre)}): {sorted(pre)}")
    print(f"BARREL    ({len(barrel)}): {sorted(barrel)}")
    print(f"MISSING:  {missing or 'NONE — parity OK'}")
    print(f"EXTRA:    {extra or 'NONE'}")
    if missing or extra:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS — full export parity")
    return 0


if __name__ == "__main__":
    sys.exit(main())
