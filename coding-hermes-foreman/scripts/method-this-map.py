#!/usr/bin/env python3
"""Per-method this./purity map for barrel-split targets (mythos QUALITY-LF-0NN series).

Usage: python3 method-this-map.py <file.ts>

Prints each method's line range and its this. references so the foreman can
classify pure vs stateful BEFORE writing the worker prompt (the pre-dispatch
structural map that drives first-try splits). Pure methods (zero this. refs,
not test-called) extract as standalone fns; test-called methods keep public
delegators on the class (LF-037 rule).

🪤 Handles generic methods (executeWithRecovery<T>) that naive `name(` regexes
miss — without the (\s*<[^>]+>)? group the map silently drops generic methods
and the prompt under-specifies the target (hit tick #139, LF-042).
"""
import re
import sys

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

lines = open(sys.argv[1]).read().split("\n")

method_re = re.compile(
    r"^\s{2}(?:private |public |protected |static |async )*(?:async )?"
    r"[a-zA-Z_][a-zA-Z0-9_]*(\s*<[^>]+>)?\("
)
methods = []  # (name, start_line_1idx)
for i, l in enumerate(lines, 1):
    if method_re.match(l) and not l.strip().startswith("//"):
        name = l.strip().split("(")[0].split()[-1].split("<")[0]
        methods.append([name, i])

if not methods:
    print("No methods found (check indentation/exports — this expects class bodies).")
    sys.exit(0)

for idx, (name, start) in enumerate(methods):
    end = methods[idx + 1][1] - 1 if idx + 1 < len(methods) else len(lines)
    body = lines[start - 1 : end]
    hits = [(i + start, l.strip()[:100]) for i, l in enumerate(body) if "this." in l]
    print(f"== {name} (L{start}-{end}, {end-start+1}L) this.refs={len(hits)}")
    for ln, txt in hits:
        print(f"    L{ln}: {txt}")
print("\n== total lines:", len(lines))
