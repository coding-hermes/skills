#!/usr/bin/env python3
"""Regression fixtures for spec_coverage.py — run after ANY parser change.

    python3 scripts/test_spec_coverage.py [-v]

Three obligations, in the order the SKILL.md demands them:

1. fixtures/good/      must exit 0 under --strict (the gate can PASS at all)
2. fixtures/bad/       must exit 1 AND emit one named error per broken rule
                       (the gate fires for EACH rule, not just some)
3. ../templates/       must exit 1 (an unfilled template set is not a spec)

Why this file exists: the first version of the checker counted `test:`/`check:`
anywhere in a requirement row, so prose like "(see check: above)" satisfied the
gate and an unverifiable requirement passed. A gate nobody has watched fail is
a decoration; this script is the watching.

Exit 0 = all obligations met. Exit 1 = a rule is missing, dead, or misfiring.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKER = HERE / "spec_coverage.py"
FIXTURES = HERE / "fixtures"
TEMPLATES = HERE.parent / "templates"

# (label, fragments that must all appear on the SAME error line)
# Line numbers shift whenever a fixture gains a row, so match the id + message,
# never the path:line prefix.
BAD_EXPECTATIONS: list[tuple[str, tuple[str, ...]]] = [
    ("duplicate declaration id", ("duplicate id MOD-01",)),
    ("module names an unknown flow", ("MOD-03", "names unknown FLOW-99")),
    ("flow without trigger", ("FLOW-01", "has no `trigger:` line")),
    ("flow without exit", ("FLOW-02", "has no `exit:` line")),
    ("contract names an unknown consumer", ("CT-01", "names unknown MOD-77")),
    ("zero assertions", ("R-901", "has 0 assertions")),
    ("two assertions", ("R-902", "has 2 assertions")),
    ("missing evidence", ("R-903", "has no `fact: FACT-nn`")),
    ("dangling fact", ("R-904", "cites missing FACT-99")),
    (
        "prose assertion outside the column",
        ("R-905", "names an assertion outside the assertion column"),
    ),
    ("prose assertion target", ("R-906", "assertion target", "is not runnable")),
    ("wrong column count", ("R-907", "has 4 columns")),
    ("module only in the statement", ("R-908", "has no `module: MOD-nn` in its attach column")),
    ("requirement names an unknown module", ("R-909", "names unknown MOD-77")),
    ("duplicate requirement id", ("duplicate id R-910",)),
]

GOOD_EXPECTATIONS: list[tuple[str, tuple[str, ...]]] = [
    ("no errors and no warnings", ("PASS  0 error(s), 0 warning(s)",))
]

TEMPLATE_EXPECTATIONS: list[tuple[str, tuple[str, ...]]] = [
    ("unfilled template: dangling contract reference", ("CT-01", "names unknown MOD-02")),
    ("unfilled template: duplicate placeholder id", ("duplicate id R-001",)),
]


def run(path: Path, *flags: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(CHECKER), str(path), *flags],
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def check_case(
    label: str,
    path: Path,
    flags: tuple[str, ...],
    want_rc: int,
    expectations: list[tuple[str, tuple[str, ...]]],
    verbose: bool,
) -> list[str]:
    failures: list[str] = []
    if not path.is_dir():
        return [f"{label}: fixture directory missing: {path}"]

    rc, out = run(path, *flags)
    if rc != want_rc:
        failures.append(f"{label}: exit {rc}, expected {want_rc}")
    lines = out.splitlines()
    for name, fragments in expectations:
        if not any(all(fragment in line for fragment in fragments) for line in lines):
            failures.append(f"{label}: rule not enforced — {name} (wanted one line with {fragments})")
    if verbose:
        print(f"--- {label} (exit {rc}) ---\n{out}\n")
    return failures


def main(argv: list[str]) -> int:
    verbose = "-v" in argv or "--verbose" in argv
    failures: list[str] = []

    failures += check_case(
        "good fixture", FIXTURES / "good", ("--strict",), 0, GOOD_EXPECTATIONS, verbose
    )
    failures += check_case("bad fixture", FIXTURES / "bad", (), 1, BAD_EXPECTATIONS, verbose)
    failures += check_case(
        "unfilled templates", TEMPLATES, (), 1, TEMPLATE_EXPECTATIONS, verbose
    )

    if failures:
        print(f"FAIL  {len(failures)} obligation(s) not met")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    rules = len(BAD_EXPECTATIONS) + len(GOOD_EXPECTATIONS) + len(TEMPLATE_EXPECTATIONS)
    print(
        f"PASS  {rules} obligations: good exits 0 --strict, "
        f"{len(BAD_EXPECTATIONS)} broken rules each fire, unfilled templates still fail"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
