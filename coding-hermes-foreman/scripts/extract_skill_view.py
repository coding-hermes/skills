#!/usr/bin/env python3
"""Extract skill bodies from skill_view persisted-output JSON wrappers.

skill_view results >~100KB get persisted to /tmp/hermes-results/call_*.txt as a
JSON object with the SKILL.md body in the `content` field (one giant escaped
line). This script extracts each input to a named .md file in a per-tick
scratch dir.

Usage:
  python3 extract_skill_view.py /tmp/hermes-results/call_00_xxx.txt /tmp/hermes-results/call_01_xxx.txt \
      -o /tmp/<tickprefix>-skills -n foreman cron

  -n names must match input count (default: call_00 -> skill0.md, ...)
  -o defaults to /tmp/<first-input-basename>-extracted

Why this exists: hand-written extraction scripts kept landing in the
sibling-shared /tmp/hermes-results/ dir (duckbrain #285, hermes-dagger #62,
helios #166) and drew sibling-modification warnings. This is the reusable,
scanner-safe form: write it to the skill's scripts/ dir, invoke with plain
python3 — no -c flag, no pipes, no heredoc.
"""
import argparse
import json
import os
import sys


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("inputs", nargs="+", help="call_*.txt files from /tmp/hermes-results/")
    ap.add_argument("-o", "--outdir", default=None)
    ap.add_argument("-n", "--names", nargs="*", default=None)
    args = ap.parse_args()

    if args.names and len(args.names) != len(args.inputs):
        sys.exit(
            "error: -n count (%d) != input count (%d)" % (len(args.names), len(args.inputs))
        )
    if args.outdir:
        outdir = args.outdir
    else:
        outdir = "/tmp/" + os.path.basename(os.path.dirname(args.inputs[0])) + "-extracted"
    os.makedirs(outdir, exist_ok=True)

    for i, f in enumerate(args.inputs):
        with open(f) as fh:
            data = json.load(fh)
        name = (args.names[i] if args.names else "skill%d" % i) + ".md"
        out = os.path.join(outdir, name)
        with open(out, "w") as fh:
            fh.write(data["content"])
        print("%s -> %s (%d chars)" % (os.path.basename(f), out, len(data["content"])))


if __name__ == "__main__":
    main()
