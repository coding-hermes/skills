#!/usr/bin/env python3
"""Audit all local SKILL.md files for valid YAML frontmatter.

A skill whose frontmatter no longer parses silently becomes unavailable:
skill_view returns "Skill '<name>' is not supported on this platform" — a
misleading error that looks like a platform issue but is a YAML parse failure.
The skill stays invisible until fixed, silently degrading dependent agents.

Proven: coding-hermes-foreman was dead for weeks this way (corrupted
support_files entries in the frontmatter block) before detection 2026-07-25.

Usage:
    python3 audit-skill-frontmatter.py [base_dir]
    # default base_dir = ~/.hermes/skills

Exit code: 0 = all valid, 1 = at least one broken.
"""
import os
import sys
import yaml


def check_file(path: str) -> tuple[bool, str]:
    """Return (ok, detail) for one SKILL.md file."""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---"):
            return False, "does not start with ---"
        parts = content.split("---", 2)
        if len(parts) < 3:
            return False, "no closing --- found"
        yaml.safe_load(parts[1])
        return True, "OK"
    except Exception as e:  # YAML parse error, IO error, etc.
        return False, f"{type(e).__name__}: {e}"


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.hermes/skills")
    broken: list[tuple[str, str]] = []
    ok_count = 0
    for root, _dirs, files in os.walk(base):
        if "SKILL.md" in files:
            path = os.path.join(root, "SKILL.md")
            ok, detail = check_file(path)
            if ok:
                ok_count += 1
            else:
                broken.append((path, detail))
                print(f"BROKEN: {path}  ({detail})")
    print(f"\n{ok_count} valid, {len(broken)} broken")
    if broken:
        # Print just the frontmatter of broken files for quick diagnosis
        for path, _detail in broken:
            print(f"\n--- {path} ---")
            with open(path, encoding="utf-8") as f:
                head = f.read(1200)
            print(head)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
