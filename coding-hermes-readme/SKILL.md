---
name: coding-hermes-readme
description: Use when auditing a project's README for staleness and accuracy, or when a weekly README-health lane runs. Files findings as rows for the owning foreman; never edits the README itself.
version: 1.0.0
metadata:
  hermes:
    tags: [coding-hermes, docs, readme, audit, weekly, foreman]
    related_skills:
      - coding-hermes-docs
      - coding-hermes-foreman
      - coding-hermes-jsonl-board-append
      - coding-hermes-releng
---

# coding-hermes-readme — README health

You audit the README; you do not rewrite it. **A README that is wrong is worse than no
README**, because it is believed. Your output is findings as board rows for the owning
project's foreman, with evidence sufficient that a worker can fix it without re-deriving
your work.

The target standard: **no project's README is more than a week out of date.** That is the
whole point of running weekly — a monthly cadence guarantees a month of lies.

## The weekly sweep

Run in the project repo, on a clean tree. Read the README top to bottom, then work these
checks in order. Every check either passes or produces a row; there are no notes.

1. **Freshness — what changed since the README last moved?**
   - `git log -1 --format=%ad --date=short -- README.md` (does the README predate the last release/tag and the last board closed-row wave)
   - For changes since then, ask of each: *does the README now say something untrue?* A new flag, a renamed verb, a moved directory, a changed config key, a new required env var — each is a candidate finding.
   - A README **older than the last tagged release** is a finding on its own.

2. **Truth — do the documented commands still work?**
   - Every fenced command block that claims output must be **executed**, and its promised output compared. A documented command that no longer runs, or whose output no longer matches, is the highest-severity class here.
   - Prefer the repo's own docs-check target if it has one (`make docs-check` and friends); if it does not, that absence is itself a finding worth filing.
   - Do not paste a command's output as evidence without running that exact command.

3. **Install path — can a stranger start from zero?**
   - Prerequisites, toolchain versions, and the install command must be present and current. A prerequisite that is implicitly satisfied on the maintainer's machine and not stated is the most common real-world failure.
   - If the README's install path differs from what CI or the release process actually does, file it.

4. **Structure — the reader's questions, in order.**
   - What is this? · Why would I use it? · How do I build it? · How do I run it? · How do I test it? · How do I install/deploy it? · What are the limits and known gaps?
   - A missing section is a finding. State which question goes unanswered, not "docs are thin".

5. **Drift — links, badges, and claims that point at nothing.**
   - CI badges and links resolving to the right repo and workflow; image/link targets that still exist; version numbers matching the shipped version; any prose naming a file, flag or endpoint that no longer exists.

## What you file

One row per finding, on the **owning project's board** — never a prose report, never a
patch to the README.

```
id:      README-<n>
title:   one sentence naming the defect, not the symptom
type:    accuracy | freshness | install-path | structure | drift
severity: P1 if the README actively misleads a new user, else P2
evidence: the exact command you ran  ->  the exact output you saw
         and README.md:<line> for a claim that is now false
fix:     what the corrected text must say, in one line
```

Sizing rule: **a row is done when a worker who never read your tick can execute it.** If
your row requires reading your reasoning to act on, it is not a row, it is a note — and
notes do not get executed.

## Discipline

- **Never edit the README in this lane.** You file; the foreman dispatches; the worker edits. An audit that silently fixes what it finds produces no record that the defect class exists, and the same drift returns next week.
- **A claim you cannot execute is a finding, not an opinion.** If you could not run it, say so in the row rather than asserting it is wrong.
- **Absence is a finding.** A README with no install section is not "fine, it's obvious" — state the missing question.
- **Do not file style preferences.** Prose taste, ordering within a section, and word choice are not defects. Misleading, missing, stale, or broken are.
- **One week.** If the README is accurate and current, file nothing. Then say so — a lane that always finds something is not measuring anything.
- **Report the gap, not the grade.** Say which checks failed, with evidence. Do not editorialize about documentation culture in the repo.

## Failure modes to hunt by name

- **The command that only works on the author's machine** — undocumented prerequisite, an uncommitted config, a PATH entry from a dotfile.
- **The badge that points at the old repo** after a rename or an org move: it still renders, which is exactly why nobody notices.
- **The example that was true two versions ago** and has never been re-run because nothing executes it.
- **The README describing the roadmap** while the code does something else; the reader believes the roadmap.
- **The quiet deletion**: a feature or flag removed from code and left documented.
