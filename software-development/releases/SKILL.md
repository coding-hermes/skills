---
name: releases
description: Decide when to cut, what ships, and when deps move.
version: 2.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [release, semver, dependencies, scheduler, ci, gh]
    related_skills: [git-release, dependency-audit-closeout, release-readiness-gate]
---

# Releases — Release Engineering Lane

## When to Use

Use when a `release-engineer` / `<project>-releng` scheduler tick is spawned, or when asked whether a release is due, what belongs in one, or when to move dependencies. You are the release **decision maker**, not a readiness reporter: the job is to decide, act, and record why.

## 0. Authority charter — what you decide alone, what you never decide alone

You hold **standing authorization** to cut patch and minor releases whenever §4's criteria are met. No owner prompt, board row, or scheduler dispatch is needed to begin a cut that follows this skill. Waiting for permission this charter already grants is a failure mode: it turns the lane into a reporter that re-files "hold — blocked on owner" rows and releases nothing, which is exactly the state §4 exists to prevent.

Decide alone:

- whether a release is due and which bump (patch/minor) per §4;
- what belongs in the release and how it is described (§5);
- when to move patch/minor dependencies (§6);
- filing RELEASE-* rows, cutting the tag, publishing the Release object.

Never decide alone — file a row, **notify the owner in chat**, and stop:

- a **major** bump, or any release carrying a breaking change;
- publishing to a distribution channel, registry, or namespace never published to before;
- irreversible acts outside the repo: deleting or force-moving tags, unpublishing/yanking artifacts, rotating signing keys.

An owner message naming a version, or saying "release it", is a *confirmation*, never a precondition. Its absence is not a blocker.

## 1. Resolve the target before touching release state

If the triggering thread does not name a project or repository, ask in the delivery thread which project to release and stop. Before asking, use only already-resolved delivery metadata needed to address the reply; do not query scheduler state to infer a project. Do not inspect the stand-in lane checkout, its local board, scheduler state, repository files, remotes, tags, CI, or release tooling while the target is unresolved: the lane path is a carrier hint, not repository identity, and its contents may belong to an unrelated project. Resume discovery only after the delivery thread identifies the target. Send the clarification through the supported messaging CLI/API using the exact resolved platform, chat, and thread, and treat a sender’s success line as transport evidence only; verify the outbound message by readback when the platform exposes it, otherwise report delivery as UNVERIFIED.

Resolve and assert identity before fetches, tests, tags, or release tooling. Use the repository named by the triggering thread or lane prompt; never use the scheduler workdir as a discovery heuristic. Keep this preflight read-only and low-noise until identity passes:

```bash
git -C <candidate> rev-parse --show-toplevel
git -C <candidate> remote -v
git -C <candidate> remote get-url origin
```

The resolved root and GitHub `origin` must match the named target. A lane checkout may be an unrelated repository, a nested worktree, a bare pointer, or a shared parent checkout; a surprising remote is a stop condition, not a hint to reinterpret the target. If the scheduler's canonical `local:/path` repository path is absent, treat the target as unresolved: do not probe the supplied carrier, search nearby directories, or reinterpret a parent checkout. Ask in the resolved delivery thread for the canonical repository/path and stop the sweep. Do not run `git status`, release checks, or broad file searches in an unresolved lane checkout: shared parent trees can expose unrelated residue and create misleading evidence. Once the target is resolved, use its path explicitly for every subsequent command.

Fetch tags, verify the default-branch tip, and record cleanliness and divergence:

```bash
git -C <repo> fetch origin --tags --quiet
git -C <repo> status --short
git -C <repo> rev-parse origin/main
git -C <repo> rev-list --left-right --count HEAD...origin/main
git -C <repo> tag --sort=-v:refname | head -5
git -C <repo> ls-remote origin refs/heads/main
```

Cross-check the branch SHA through the hosting provider API as well as `git ls-remote`. If the two provider views disagree, classify the candidate as UNVERIFIED and stop release decisions; preserve both SHAs and do not choose one for convenience. A board-only carrier must be re-anchored and rechecked through both views before any final report or mutation.

If the checkout is dirty, diverged, or not the named repository, create a new clean detached worktree from the resolved target's `origin/main`. Prefer a unique directory and the VCS worktree mechanism so `.git` metadata and release tooling remain available. Verify that the directory was actually created, that `git -C <clean-repo> rev-parse HEAD` equals the recorded release SHA, and that its root plus remote match the resolved target before running any checks; a path typo, inherited parent remote, or failed `cd` must not be mistaken for a failed build or gate.

```bash
REMOTE_SHA=$(git -C <repo> rev-parse origin/main)
CLEAN_REPO=$(mktemp -d "${TMPDIR:-/tmp}/release-worktree.XXXXXX")
git -C <repo> worktree add --detach "$CLEAN_REPO" "$REMOTE_SHA"
```

Never reclaim a possibly shared path with `rm -rf`, and never combine destructive cleanup with clone/worktree creation. If the clean worktree operation is blocked or unavailable, use a new non-existing temporary directory and a read-only clone of the verified remote SHA; if that also fails, stop. Do not substitute a dirty scheduler checkout, a feature branch, or a nearby project tree. Run every release check and build from the exact clean candidate that would be tagged, and label any selftest from another tree as non-authoritative evidence.

## 2. Gather evidence in release order

Use the newest semantic tag from `git tag --sort=-v:refname`. If none exists, evaluate the initial-release case explicitly as `v0.1.0`; do not use an empty `..HEAD` range or invent a baseline.

Release notes must be derived from board rows and verified commits, never memory. An open or in-progress board row is not a completed release claim.

Then gather:

1. Git history since the last tag. Categorize conventional prefixes: `feat` → feature, `fix` → bug fix, `perf` → performance/behavior change, `chore`/`docs`/`refactor`/`test` → non-material. Search full commit bodies for `BREAKING CHANGE:` and `type!:`; do not inspect subjects only. Count commits touching shipped source separately from board/docs-only commits: a board-only commit is not material and must not inflate the release.

2. Hosted CI, deriving `ORG/REPO` from the verified GitHub remote, never the folder name:

```bash
gh run list --repo "$ORG_REPO" --limit 20 --json status,conclusion,displayTitle,headBranch,headSha,createdAt,url
gh workflow list --repo "$ORG_REPO"
gh run list --repo "$ORG_REPO" --commit "$RELEASE_SHA" --limit 20 --json status,conclusion,headSha,url
```

A green local test or GitReins result never substitutes for hosted CI. No workflows, no run for the exact release SHA, pending, cancelled, or failed CI is UNVERIFIED/BLOCKED. Inspect the exact failed job's steps/logs before summarizing the cause; a failed job with executed steps is a real release gate, not a generic runner caveat. Never release on it without an explicit override naming the exception.

3. GitReins verdicts. Run the repository's configured guard with the installed syntax, commonly:

```bash
gitreins guard --full --scope working-tree --json
```

Read the structured result and bind it to the clean worktree SHA. Inspect changed-file count, skipped steps, degraded status, and the scanners that actually ran; a top-level pass on an unchanged tree can be a bounded or degraded receipt rather than comprehensive release evidence. Only a fresh non-degraded pass for the exact tree is green evidence; degraded/skipped checks must remain visible and require separately executed gates. Search repository-local verdicts and task records for the commits in the release range. Missing verdicts are unverified.

4. Dogfood/QA. Read the project's dogfood evidence and distinguish `PASS` from `UNVERIFIED`, vacuous no-test-path, `N/A`, and launch/setup `FAIL`. A clean collect step does not turn failed or empty test cells green. Missing or vacuous coverage is an evidence gap.

5. Previous-release artifact reality. Check what the last release actually shipped: asset names, sizes, whether they install, whether the CLI they document exists. A Release object with zero assets, or with artifacts missing their entry point, is a broken release — auditing it is a standing part of this sweep, and fixing it belongs in the release you are about to cut.

6. Public posture, when required: visibility, license, secret scanning, push protection, branch protection, and tracked-secret scan. Query supported repository fields first, then use the REST API for `security_and_analysis` and branch protection; classify a successful `404 Branch not protected` as an unprotected-branch finding, not as an API outage. Report each as PASS, FAIL, or UNVERIFIED. Review tracked localhost/private-network endpoints as a posture finding when the project claims public readiness; classify intentional loopback runtime probes separately from leaked deployment endpoints.

## 3. Semver classification

| Evidence since last tag | Bump |
|---|---|
| only `fix`/`chore`/`docs`/`refactor`/`test` | patch |
| at least one `feat`, or behavior-changing `perf` | minor |
| `BREAKING CHANGE:`, `!` after type, or 0.x → 1.x | major — owner confirmation required (§0) |
| red/absent/unverified hosted CI or failing evidence gate | release blocked — fix the gate; never file a hold row instead |

For an initial untagged repository, `v0.1.0` is executable only when a version stamp, changelog, and artifact strategy exist or are created in the same cut. If the repository also lacks a version stamp, changelog, release precedent, release tooling, and an evidenced artifact strategy, stop at readiness reporting. A reachable GitHub remote alone is not a release contract.

## 4. Decision 1 — is a release due?

Evaluate in order; stop at the first rule that fires.

| # | Condition | Decision |
|---|---|---|
| 1 | Security advisory affecting a runtime dependency or shipped code | **Release now** — patch (minor if the fix changes behavior). Do not wait for cadence. |
| 2 | Open P0 blocker in the target, or exact-SHA CI red/absent | **No release.** Fix the blocker or the gate. A release blocked on a repo-owned defect is this lane's work item. |
| 3 | Zero material commits since the last tag | **Not due.** Report in one line and stop. |
| 4 | ≥1 `feat` since the last tag, gates green | **Minor release due.** Cut it. |
| 5 | ≥1 material `fix` since the last tag, gates green | **Patch release due.** Cut it. |
| 6 | ≥14 days since the last release and ≥5 material commits accumulated | **Release due** at the highest applicable bump — cadence floor, so a long tail of small fixes cannot starve users. |
| 7 | Otherwise (under 14 days, only trivial accumulated change) | **Not due.** One line: count so far, and the trigger that will fire next. |

Hard invariants, whatever the table says:

- exact-SHA hosted CI green;
- version stamp equals the tag being cut;
- the tag does not already exist locally or remotely;
- clean tree at the cut SHA;
- the previous release's artifact gaps are either fixed by this cut or carried forward explicitly in the notes.

If an invariant fails, the answer is **fix the invariant now** — not "hold and wait for the owner".

## 5. Decision 2 — what belongs in a release

A release is a point on the default branch, not a curated subset.

- **Included automatically:** every commit reachable from the cut SHA since the last tag. Do not cherry-pick selectively, and do not hold completed work back for a future version: unreleased fixes are the most expensive kind of debt.
- **Excluded from the release notes** (not from the release): board/harness bookkeeping, merge commits, generated churn, version-bump noise. Say so — "board/harness bookkeeping commits are not listed" — so the counts stay honest.
- **Must be present before tagging:** version stamp at the release version; a CHANGELOG section for that version with its date; docs naming the version updated; dependency lock refresh if §6 says one is due.
- **Never in an auto-cut:** a breaking change (that is a major, §0), a dependency major bump, or an unreviewed large refactor.
- **Security hotfix path:** when a released version needs an urgent fix, cut the patch from the released tag rather than from main, so users get the fix without main's unreleased surface. Record which path was used.

Publish the artifact set the project's tooling defines. If the repo has release tooling (`.github/workflows/release.yml`, goreleaser, Makefile targets, `scripts/release*`), the tooling is authoritative — use it, do not reimplement it by hand. If the tooling is broken, that breakage is the release blocker to fix, not a reason to hop to a manual path and declare victory: a manual publish is a documented workaround that must come with a filed row against the tooling, carrying acceptance criteria.

A repository with no release script or release docs is not release-tooling-complete even if a generic GitHub Release can be created. Record that gap; do not let the fallback conceal it.

## 6. Decision 3 — when to update dependencies

Run this on every releng tick and act on the rules. Do not file a permanent "audit dependencies" row that never resolves.

| Finding | Action |
|---|---|
| Advisory affecting a direct or transitive runtime dependency | Update immediately in its own commit, and cut a patch release (§4 rule 1). |
| Patch-level updates available | Batch, and land at release time so each release carries current patches. |
| Minor-level update, changelog shows no breaking change, suite green | Apply at most monthly, as its own commit so it can be reverted alone. |
| Major-level update | **Never automatic.** File a row with migration plan, blast radius, and rollback; owner decides. |
| Dev/test-only dependency | Same ladder, but may ride with a regular release commit. |
| Vendored or pinned dependency | Check the reason before moving it. A pin with no recorded reason is a finding. |

Mechanics — use the project's lockfile, never hand-edit versions:

```bash
# Python (uv)
uv lock --upgrade && uv sync --dev && <test command>
# Python (pip)
pip-audit                                   # advisory scan first
# Node
pnpm outdated && pnpm update && <test command>
# Go
go get -u=patch ./... && go mod tidy && go test ./...
```

Rules that keep dependency work honest:

- One logical dependency change per commit, so a revert is surgical.
- Run the full suite and hosted CI after the change; a lockfile that resolves is not a test pass.
- Record before → after versions in the release notes when the release carries them.
- Never mix a dependency major bump into an unrelated feature release.
- A dependency update that breaks the suite is reverted, not "fixed forward" inside the same release.

## 7. Cut and verify

```bash
git -C <clean-repo> tag -a "v<NEW_VERSION>" -m "Release v<NEW_VERSION>"
git -C <clean-repo> push origin "v<NEW_VERSION>"
gh release create "v<NEW_VERSION>" --repo "$ORG_REPO" --title "v<NEW_VERSION>" --notes-file <notes-file> [artifact ...]
# Pass release assets as positional paths; gh has no --attach option.
```

A tag alone is not a release. Verify every layer, and verify the **shipped artifact**, not just the API response:

```bash
git -C <repo> ls-remote --tags origin
gh release view "v<NEW_VERSION>" --repo "$ORG_REPO" --json tagName,isDraft,isPrerelease,assets
gh run list --repo "$ORG_REPO" --branch "v<NEW_VERSION>" --limit 20 --json status,conclusion,headSha,url
# download the published assets back and prove they work
gh release download "v<NEW_VERSION>" --repo "$ORG_REPO" -D <dir>
(cd <dir> && sha256sum -c SHA256SUMS)
python3 -m venv <fresh> && <fresh>/bin/pip install <dir>/…whl && <fresh>/bin/<cli> --version
```

The shipped verdict requires a remote tag, a published (non-draft, non-prerelease) Release object with the expected assets, assets that verify and install, and green CI on the tag SHA. A tag push that triggers no workflow is not green — investigate the trigger or run the documented local recipe, keeping the tag immutable either way.

**Verify the capability, not the file list.** An installable artifact that lacks its own entry point, or lacks the runtime component its headline feature needs, is a broken release with a passing smoke test. If the notes advertise a capability, prove it from the *installed artifact* before calling the release done.

If an automated publish path fails for a reason outside your control (credential scope, admin-only repo setting), publish through the documented manual path, verify the artifacts, and file the automation defect with acceptance criteria — do not leave the failure undocumented or silently rename it "blocked on owner".

## 8. Escalation — when you cannot decide

A decision you could not make is work, not a waiting state. When §4/§5/§6 hits something §0 withholds (major bump, unreleased breaking change, an admin-scoped setting you cannot change, an unreachable registry):

1. File ONE row naming the decision, the evidence, the exact action needed, and its owner.
2. **Notify the owner in chat.** A row that exists only in a JSONL file is not an escalation. One or two sentences, with what you need.
3. Continue with everything that is not blocked.
4. On the next tick, if the state is unchanged, restate the existing row id — never file a duplicate hold row.

Standing rule: a release lane that files "blocked on owner authorization" while §0 already grants that authorization is wrong. Re-read §0 before writing a hold row.

## 9. Record the decision

Every tick leaves one decision record — a board row or audit event — containing:

- target repo, cut SHA, range, newest prior tag;
- material-commit counts by class and the semver classification with its trigger;
- the §4 rule number that fired (or the rule that said not-due);
- gate results with run ids and URLs;
- dependency state: what moved, what was deferred, why;
- the artifact produced (tag, Release URL, verified assets) or the exact blocker and owner.

A tick that produced no decision record did nothing, whatever its transcript says.

## 10. Reconcile same-tick evidence before reporting

If an earlier instance of the same tick already wrote an audit event, read that committed event and compare its candidate SHA, remote tip, CI run IDs, and blocker states with fresh probes. A stale event is not current evidence: do not repeat its SHA or claim its decision as your own. If the state changed, record the correction and delta through the supported board event path; if unchanged, do not append duplicate evidence. Treat a generic append helper's success output as transport only: read back the exact stored event and task row before any second write.

Keep evidence artifacts and board writes in the same owning checkout. Before invoking a writer, assert that the artifact path resolves inside the checkout passed to the writer and that the board files resolve from the same root. If the writer is blocked before execution, leave the row unchanged, preserve the local artifact as explicitly unpublished, and report persistence as UNVERIFIED.

## 11. Report tightly to the delivery thread

| Section | Contents |
|---|---|
| Target | verified org/repo, clean release SHA, range |
| Commits | material feature / fix / non-material counts, breaking count |
| Decision | §4 rule that fired, bump, or explicit not-due reason |
| Build | project tooling used, command result, artifacts |
| CI | exact-SHA status and recent-run summary |
| GitReins/dogfood | fresh verdicts and PASS/UNVERIFIED/FAIL distinctions |
| Dependencies | moved, deferred, blocked (with versions) |
| Public posture | visibility, license, scanning, protection, endpoints |
| Release | tag, Release URL, verified assets, tag-CI verification, or "not created" |

Include the blocker and the command or URL that makes it rerunnable. Never claim a row, release, or gate complete from a commit message alone.

## 12. General pitfalls

- A lane checkout can point at the wrong repository and still pass local tests; verify root plus remote before every release operation, and keep the identity probe read-only until it passes. If the lane prompt already names the target, use that named repository path and do not reinterpret the lane checkout as the target.
- A shared parent checkout can report hundreds of unrelated untracked paths; treat that as lane contamination, not target-repository evidence, and switch to an explicit clean target worktree.
- Create clean release evidence with a unique detached worktree, not a destructive cleanup of a reused path.
- A dirty or diverged checkout can make local evidence describe unpushed residue; use a clean detached worktree at the fetched remote default-branch SHA.
- No hosted workflow or no exact-SHA run is not green CI; local tests and GitReins cannot fill that gap.
- A dogfood collector/cleanup PASS does not prove the test cells ran; inspect each cell for non-empty evidence and explicit status.
- A tag is not a Release object and a Release object is not artifact/CI completeness; verify every release layer separately.
- A repository without project release tooling is not release-tooling-complete; record the gap rather than normalizing it away with a manual `gh release create`.
- Never force-move an existing tag or cut a major without owner confirmation.
- Board bookkeeping can dominate commit counts; always report material vs total so release notes never inherit the inflation.
- Do not treat a stale `superseded_by` row as authority for the version you are cutting — resolve the newest row for that version.
- A published package that installs but ships no executable, or omits the loader its advertised capability needs, is a broken release. Check the artifact, not the manifest.
