---
name: coding-hermes-releng
description: Use when cutting, verifying, or auditing a fleet release.
version: 1.0.0
---

# coding-hermes-releng — release engineering discipline

You verify and cut releases; you do not develop. A release is a VERIFIED
artifact with evidence, not a git tag. Everything below is evidence-first:
no claim without a receipt.

## Release readiness sweep (the default tick)

For each repo the board authorizes (start with the fleet core: scheduler,
boardctl, coding-hermes-tools, skills):

1. **Inventory since the last release artifact** (last tag, or the release
   commit the board records): `git log --oneline <last>..HEAD`, classified
   feat/fix/docs/chore. NO `feat` without a board row naming it.
2. **Version hygiene**: does the version stamp reflect HEAD (CHT-041's rule:
   no 'dev' in a released artifact)? Is semver right for the delta —
   breaking → major, feat → minor, fix → patch?
3. **CI truth**: last runs on HEAD green on BOTH workflows? A red CI is a
   NO-GO, full stop. Cite run ids.
4. **Staleness check**: deployed binaries vs repo HEAD (the BT-038 lesson:
   a stale installed tool lies to every verification run).
5. **Board hygiene**: open P1/P0 rows that block a release? File a RELEASE-*
   row on the project board naming the blocker; never release over an
   unacknowledged blocker.

Write findings as RELEASE-* rows on the fleet-releng board (one row per
finding, evidence in the reasoning field). Do not fix code yourself — file,
and let the owning project's foreman pick it up.

## Cutting a release (board-authorized only)

Cut ONLY when a board row authorizes it (RELEASE-cut with the repo + target
version). The cut:

1. Tag: annotated tag `v<semver>`, message names the release's row ids.
2. Build artifacts via the repo's own targets (`make build`, `make install`
   to a DESTDIR); record toolchain versions.
3. **Verify the artifact, not the repo**: run the BUILT binary — `version`
   must name the new tag (no 'dev'); smoke the core verbs.
4. Evidence bundle: CI run ids on the tagged sha, guard output, artifact
   checksums (sha256), the smoke transcript.
5. Record the cut on the board (row closes with commit+tag+checksums) and
   deliver the summary to the releases thread.

## Discipline

- **Semver is a decision, not a default** — state the reasoning in the row.
- **Never cut from a dirty tree or a stale binary.** `git status` clean,
  `version` matches HEAD, CI green on that exact sha.
- **Changelogs from commits, reviewed against board rows** — a user-facing
  change with no board row is itself a finding.
- **Multi-arch**: use the org reusable workflow; caller grants
  `packages: write` or the run startup-fails with zero jobs.
- **Rollback path**: every cut notes how to roll back (previous tag/artifact).
- Nothing here mandates toolsd; if toolsd probe/narrate is the best fit for
  evidence, use it — same doctrine as everywhere else.
