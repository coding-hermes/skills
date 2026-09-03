---
name: evidence-backed-reporting
description: >-
  Use for evidence-backed reports: run first, write second. Every number in a
  report is a placeholder until a real execution produces it — no un-executed
  claims in a commit.
version: 1.0.0
category: reporting
---

# Evidence-Backed Reporting

A report whose value IS its evidence (dogfood field reports, verification
records, point-in-time audit docs, PASS-criteria closure notes, benchmark
writeups) is only as good as the runs behind it. The failure mode this skill
exists to prevent: drafting claims of runs that were never executed, then
committing them — **fabrication by accident, not by intent**.

## When to use

- Writing a dogfood / field report that records a verification run
- Closing a task with a foreman note or worker summary that cites numbers
- Producing any doc where a judge, auditor, or reviewer will check claims
  against the repo, CI, or live systems
- Writing PASS criteria evidence into board rows, tick reports, or PRDs

## Core rules

1. **Run first, write second.** Capture real command output, then write the
   report from it. The report template can be drafted before the run, but
   every number in it is a placeholder until the run produces it.
2. **No un-executed claims in a commit.** If a draft was written before the
   run (or a claim was extrapolated), patch in the ACTUAL output before
   committing. A committed report carrying un-executed claims is fabrication
   even if the claims later turn out true — a judge can and will catch it.
3. **Self-check before commit.** Re-read the report and cross-check every
   figure against executed output: exit codes, durations, counts, URLs,
   version strings. Grep for numbers you cannot back.
4. **Cite exact commands and outputs.** Give the command, the rc, and the
   key output lines — not prose summaries. This is what makes the evidence
   independently checkable.
5. **Never edit historical records in place.** A post-fix field report is a
   NEW dated file; the historical failing report stays byte-identical.
   Auditors prove "unchanged" claims with `git diff <commit> -- <file>` and
   expect an empty diff. Appending a retroactive banner to the old file is
   the anti-pattern this class was created to replace.
6. **Two-language / multi-path claims need two runs.** If you claim "both
   Go and Python scaffolds pass", you must have run both. One run backs one
   claim; do not let a successful first run inflate coverage of the second.

## Verification checklist

- [ ] Every command in the report was executed in this session (or is
      explicitly labeled as a reproduction instruction, not a claim)
- [ ] Exit codes and durations match captured output
- [ ] Historical files touched by this class of work are byte-identical
      (`git diff --stat` on them = 0 lines)
- [ ] Numbers a reviewer could grep (44/44, 0.37s, p50) exist verbatim in
      the executed output
- [ ] Cross-report consistency: the same metric appears identically in
      every place it's mentioned (stat card = section text = table)

## References

- `references/field-report-case.md` — proven case: a drafted report claimed
  a second run that hadn't executed; caught in self-review, fixed by
  actually running it before commit, then independently verified by a judge
  (including the git-diff-unchanged check on the historical file).
- `references/deep-audit-pattern.md` — multi-judge adversarial audit pattern
  with evidence-cited paper output (generalizes the same run-first rule to
  large audits).
