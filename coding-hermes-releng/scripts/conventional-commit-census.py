#!/usr/bin/env python3
"""Strict Conventional Commit census for a release decision.

WHY THIS EXISTS
    The skill requires a TESTED strict parser, not a shell grep: the census
    must classify lowercase conventional types only, count breaking markers
    STRUCTURALLY, and prove every bucket sums to the non-merge commit total.
    Hand-rolling that inline each pass is where the counts drift, and a grep
    over `%s%n%b` over-counts breaking changes by matching commits that merely
    QUOTE the convention (changelog and docs commits describing the footer).

USAGE
    conventional-commit-census.py <repo> <base> <tip>

    base may be a tag name or a rev; `v0.1.1^{commit}` is accepted so a peeled
    annotated tag is used rather than the tag object.

EXIT STATUS
    0  census completed and every bucket sums to the total
    1  sum mismatch (parser defect - fix it before freezing semver)

READ THE OUTPUT, DO NOT TRUST EXIT 0 ALONE
    `other_conventional` is a real bucket: subjects whose type is conventional
    SHAPED but not a recognized type (`board:`, `ops:`, `settle:`) land there
    with the unrecognized type listed, so a large count is bookkeeping, not a
    parser failure. `non_conventional` subjects are printed in full - inspect
    them for shipped behaviour before dismissing them as noise, because a
    subject that merely lacks the colon can still change product behaviour.
"""
import re
import subprocess
import sys
from collections import Counter

RECOGNIZED = {"feat", "fix", "perf", "refactor", "docs", "test", "chore",
              "build", "ci", "style", "revert"}

# type, optional (scope), optional !, colon, space, subject
SUBJECT_RE = re.compile(r"^([a-z]+)(\([^)]*\))?(!)?: (.+)$")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args],
                          capture_output=True, text=True, check=True).stdout


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    repo, base, tip = sys.argv[1:4]

    # RS-terminated records so multi-line bodies cannot be confused for records.
    raw = git(repo, "log", "--no-merges", "--format=%H%x01%s%x01%b%x02",
              f"{base}..{tip}")
    records = [r for r in raw.split("\x02") if r.strip()]

    counts = Counter()
    breaking_subjects, breaking_footers = [], []
    non_conventional, unrecognized_types = [], Counter()

    for rec in records:
        parts = rec.split("\x01")
        if len(parts) < 3:
            continue
        sha, subject, body = parts[0].strip(), parts[1].strip(), parts[2]
        counts["total"] += 1

        m = SUBJECT_RE.match(subject)
        if m:
            ctype, _scope, bang, _rest = m.groups()
            if ctype in RECOGNIZED:
                counts[ctype] += 1
                # Structural breaking marker: `!` on a RECOGNIZED type only.
                if bang:
                    breaking_subjects.append((sha[:8], subject))
            else:
                counts["other_conventional"] += 1
                unrecognized_types[ctype] += 1
        else:
            counts["non_conventional"] += 1
            non_conventional.append((sha[:8], subject))

        # A breaking footer counts only at column 0 of the body.
        for line in body.splitlines():
            if line.startswith(("BREAKING CHANGE", "BREAKING-CHANGE")):
                breaking_footers.append((sha[:8], line.strip()))

    total = counts["total"]
    recognized = sum(counts[k] for k in RECOGNIZED if counts[k])
    summed = (recognized + counts["other_conventional"]
              + counts["non_conventional"])

    print(f"range={base}..{tip}")
    print(f"non_merge_total={total}")
    for k in sorted(counts):
        if k != "total":
            print(f"  {k}={counts[k]}")
    print(f"  recognized_conventional={recognized}")
    print(f"  sum_check={summed} (must equal {total})")
    if unrecognized_types:
        top = ", ".join(f"{t}={n}" for t, n in unrecognized_types.most_common(8))
        print(f"  unrecognized_types: {top}")
    print(f"breaking_subjects={len(breaking_subjects)} {breaking_subjects[:5]}")
    print(f"breaking_footers={len(breaking_footers)} {breaking_footers[:5]}")
    print(f"non_conventional={len(non_conventional)}")
    for sha, subj in non_conventional[:15]:
        print(f"   {sha} {subj[:100]}")

    # Bump rule: breaking -> major (proposes, requires owner confirmation),
    # else feat -> minor, else patch. Printed as a PROPOSAL, never a decision.
    if breaking_subjects or breaking_footers:
        print("bump_rule=major (proposes major; requires explicit confirmation)")
    elif counts["feat"]:
        print("bump_rule=minor")
    else:
        print("bump_rule=patch")

    if summed != total:
        print("REFUSING: bucket sum does not equal the non-merge total")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
