#!/usr/bin/env python3
"""manifest_check.py — normative skills manifest: drift gate.

Every skill directory MUST have a manifest entry; every manifest entry MUST have
a SKILL.md. Dispatch class must be one of: always, trigger, route-only, owner.

Usage:
  python3 scripts/manifest_check.py            # check (exit 1 on drift)
  python3 scripts/manifest_check.py --write    # regenerate manifest from the tree
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "skills-manifest.json"
CLASSES = {"always", "trigger", "route-only", "owner"}


def tree():
    return sorted(d.name for d in ROOT.iterdir() if (d / "SKILL.md").exists() and d.is_dir())


def load():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {}


def write(manifest):
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {MANIFEST.name}: {len(manifest)} entries")


def main():
    dirs = tree()
    manifest = load()
    if "--write" in sys.argv:
        for name in dirs:
            e = manifest.get(name, {})
            manifest[name] = {
                "dispatch": e.get("dispatch", "trigger"),
                "layer": e.get("layer", ""),
                "owner": e.get("owner", "coding-hermes"),
            }
        write(manifest)
        return 0

    fails = []
    for name in dirs:
        if name not in manifest:
            fails.append(f"skill '{name}' missing from {MANIFEST.name}")
    for name, e in manifest.items():
        if not (ROOT / name / "SKILL.md").exists():
            fails.append(f"manifest entry '{name}' has no SKILL.md")
        if e.get("dispatch") not in CLASSES:
            fails.append(f"manifest entry '{name}' dispatch '{e.get('dispatch')}' not in {sorted(CLASSES)}")
    for f in fails:
        print(f"FAIL  {f}")
    print(f"{len(dirs)} skills, {len(manifest)} manifest entries: {len(fails)} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
