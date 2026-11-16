#!/usr/bin/env python3
"""style_check.py — mechanical writing-rules enforcement for coding-hermes skills.

FAIL tier (exit 1): frontmatter validity — every SKILL.md must be discoverable.
WARN tier (printed): body style — size budget, changelog drift, empty sections.

Usage: python3 scripts/style_check.py [--root DIR] [--strict]
  --strict  promote WARN to FAIL (used by release sweeps, not routine guard)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAILS, WARNS = [], []
BASELINE = Path(__file__).resolve().parent / "style-baseline.json"


def fail(skill, msg):
    line = f"{skill}: {msg}"
    if BASELINE.exists() and line in BASELINE.read_text().splitlines():
        WARNS.append(f"BASELINE {line}")  # pre-existing debt: ratcheted, not blocking
    else:
        FAILS.append(line)

REQUIRED_FM = ["name", "description", "version", "author", "metadata"]
DESC_TRIGGER = re.compile(r"^\s*(Use when|Use before|Use after|Use when running|Fleet-level|The |How )")


def warn(skill, msg):
    WARNS.append(f"{skill}: {msg}")


def check_skill(p: Path, root: Path):
    skill = str(p.relative_to(root))
    text = p.read_text(errors="replace")
    if not text.startswith("---"):
        fail(skill, "no frontmatter block")
        return
    try:
        end = text.index("\n---", 3)
    except ValueError:
        fail(skill, "frontmatter not terminated")
        return
    fm = text[3:end]
    body = text[end + 4:]

    # FAIL tier: required keys
    for key in REQUIRED_FM:
        if not re.search(rf"^{re.escape(key)}:", fm, re.M):
            fail(skill, f"frontmatter missing '{key}'")
    m = re.search(r"^name:\s*(\S+)", fm, re.M)
    if m and m.group(1) != p.parent.name:
        fail(skill, f"frontmatter name '{m.group(1)}' != directory '{p.parent.name}'")
    m = re.search(r"^description:\s*(>-|>|\|)?\s*\n?\s*(.{0,80})", fm, re.M | re.S)
    if m:
        desc_text = m.group(0).split("description:", 1)[1]
        desc_text = re.sub(r"^\s*(>-|>|\|)\s*$", "", desc_text, flags=re.M)
        desc_text = re.sub(r"^\s+", "", desc_text)
        if not DESC_TRIGGER.match(desc_text):
            warn(skill, "description is not trigger-style ('Use when …') — dispatch reads it")
    # version bump check: semver shape
    if not re.search(r"^version:\s*\d+\.\d+\.\d+", fm, re.M):
        fail(skill, "version is not semver")

    # WARN tier: body style
    lines = body.count("\n") + 1
    if lines > 700:
        warn(skill, f"{lines} lines — over the 700-line size budget, split into references/")
    if not body.lstrip().startswith("# "):
        fail(skill, "body does not open with an H1 title")
    if re.search(r"\bTODO\b|\bFIXME\b", body):
        warn(skill, "TODO/FIXME left in doctrine")
    # folded description style (warn when inline, i.e. NOT a >- / | block)
    if re.search(r"^description:\s+\S", fm, re.M) and not re.search(r"^description:\s*(>|>-|\|)", fm, re.M):
        warn(skill, "description should be a folded block (>-), not inline")
    # non-ascii CJK outside allowed title lines is a warn (mode-skill titles exempt)
    cjk = [ln for ln in body.splitlines() if re.search(r"[\u4e00-\u9fff]", ln) and not ln.startswith("#")]
    if cjk:
        warn(skill, f"non-ASCII CJK in body ({len(cjk)} line(s)) — English/ASCII rule")

    for refdir in ["references"]:
        if (p.parent / refdir).exists() and not list((p.parent / refdir).glob("*.md")):
            warn(skill, f"{refdir}/ exists but is empty")


def main():
    root = ROOT
    strict = "--strict" in sys.argv
    if "--root" in sys.argv:
        root = Path(sys.argv[sys.argv.index("--root") + 1]).resolve()
    skills = sorted(d for d in root.iterdir() if (d / "SKILL.md").exists() and d.is_dir())
    if not skills:
        print("no skills found — wrong root?")
        return 1
    for d in skills:
        check_skill(d / "SKILL.md", root)

    for w in WARNS:
        print(f"WARN  {w}")
    for f in FAILS:
        print(f"FAIL  {f}")
    print(f"\n{len(skills)} skills checked: {len(FAILS)} FAIL, {len(WARNS)} WARN")
    if FAILS or (strict and WARNS):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
