#!/usr/bin/env python3
"""Extract skill_view persisted JSON blobs to plain markdown.

Why: skill_view saves large results to /tmp/hermes-results/call_<NN>_*.txt as a
single-line JSON object; read_file/grep on the blob return nothing (empty
content once offset > 1). Extract to .md first, then read that.

Why a committed script instead of a /tmp helper: every foreman tick that loads
big fleet skills re-types this extractor into /tmp with a generic name
(extract.py / extract_skills.py / extract_skill.py), and /tmp is SHARED with
concurrent siblings — the write_file "modified by sibling subagent" warning is
now near-guaranteed on generic names (9 documented violations in 4 days, see
references/skillview-persisted-json-extraction.md). Running THIS file from the
skill dir means no /tmp file exists to collide with.

Usage (cron-safe — no python3 -c, no jq dependency):
  python3 scripts/extract_skill_json.py /tmp/hermes-results/call_00_XXX.txt
      -> writes /tmp/hermes-results/call_00_XXX.md (derived name)
  python3 scripts/extract_skill_json.py in1.txt out1.md in2.txt out2.md ...
      -> explicit output paths (pairs)

Bare input paths derive output by swapping the .txt extension for .md.
Non-skill blobs (delegate_task results, other tool outputs lacking 'content')
are SKIPPED, never raised — the directory holds dozens of sibling files, so
never glob call_0*.txt and never index d['content'] unguarded.
"""
import json
import sys


def extract(in_path, out_path):
    try:
        with open(in_path) as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        print(f"SKIP {in_path}: {e}")
        return False
    content = data.get("content", "")
    if not isinstance(content, str) or not content:
        print(f"SKIP {in_path}: no 'content' key (not a skill_view blob?)")
        return False
    with open(out_path, "w") as f:
        f.write(content)
    print(f"{len(content)} chars -> {out_path}")
    return True


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    args = argv[1:]
    pairs = []
    i = 0
    while i < len(args):
        inp = args[i]
        if i + 1 < len(args) and not args[i + 1].endswith((".txt", ".json")):
            out = args[i + 1]
            i += 2
        else:
            out = inp[:-4] + ".md" if inp.endswith(".txt") else inp + ".md"
            i += 1
        pairs.append((inp, out))
    ok = True
    for inp, out in pairs:
        ok = extract(inp, out) and ok
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
