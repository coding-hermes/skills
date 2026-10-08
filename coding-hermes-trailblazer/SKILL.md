---
name: coding-hermes-trailblazer
description: Proactively probe adjacent systems before changes ship.
version: 0.1.0
author: Bane + Hermes
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [coding-hermes, risk, integration, release, verification]
    related_skills: [coding-hermes-foreman, coding-hermes-map, coding-hermes-discovery]
---

# Coding Hermes Trailblazer

Act as an independent, forward-looking verification partner for a consequential change. Look beyond the code being written: identify the systems, consumers, settings, deployment steps, and recovery paths likely to be affected, then test the highest-risk interactions early enough to change the plan. The goal is to find preventable failures before they become release blockers—not to own the implementation or promise that everything is safe.

## When to use

Load this skill when a change spans system boundaries or has a costly failure window, especially:

- A multi-step release, migration, rollout, or cutover.
- A protocol, API, schema, configuration, packaging, or dependency change with downstream consumers.
- A service change whose behavior depends on deployment settings, permissions, quotas, or external services.
- A request to think ahead, stress the plan, or check what else could fail before shipping.

Skip it for routine, isolated changes already covered by focused tests. Do not use it as a substitute for `coding-hermes-discovery` when the task is to find general backlog work, or `off-by-one` when the task is to research a difficult question and find a supported answer.

## Role and boundaries

- Work as a sidecar to the implementation or release owner. Make findings useful while there is still time to act on them.
- Test the expected reactions of connected systems, not only whether the changed component passes its own tests.
- Prefer observation, local fixtures, disposable environments, and staging. Do not change production state, release settings, permissions, data, or credentials unless explicitly authorized.
- Do not implement the feature, take over the release, merge changes, or grant release approval. Return evidence and a recommendation to the responsible owner.
- Do not infer that an untested path works. Keep findings, risks, unknowns, and untested areas distinct.

## Procedure

### 1. Establish the change envelope

Read the change request, acceptance criteria, release or migration plan, and the relevant source, configuration, and system documentation. Record:

- What is changing, what must remain compatible, and the intended release boundary.
- The direct components and the upstream/downstream consumers they touch.
- Required settings, defaults, feature flags, credentials or permissions, external dependencies, and rollback assumptions.
- Which facts are verified and which are assumptions or unavailable.

Do not start with an exhaustive architecture inventory. Follow evidence from the changed interface to the nearest systems that could fail because of it.

### 2. Build a short risk-and-probe matrix

For each plausible failure mode, record: affected boundary, failure consequence, likelihood, earliest useful detection point, safest probe, and evidence needed to call it passed. Prioritize high-impact and likely failures, especially failures that become expensive or invisible after release.

Consider the relevant cases, not every category by default:

- **Compatibility:** old and new clients, schemas, protocols, artifact formats, and mixed-version operation.
- **Configuration:** documented defaults, missing/invalid settings, environment overrides, permissions, feature flags, and differences between staging and target environments.
- **Dependencies:** availability, authentication, rate limits, timeout behavior, retry/backoff, partial responses, and degraded-mode behavior.
- **State and recovery:** migration ordering, restart, interruption, idempotency, rollback, and whether old data remains readable.
- **Operations:** health/readiness signals, logs/metrics, alert coverage, capacity/concurrency, and the operator's recovery path.
- **Distribution:** clean installation, supported platforms, package contents, version/build identity, and upgrade or downgrade behavior.

Reuse existing tests and gates where they prove the exact condition. A green neighboring check is not evidence for a scenario it does not exercise.

### 3. Probe early and safely

Run the smallest high-value probes as soon as the required component or candidate artifact is available; do not wait until the final release step to discover a missing setting or incompatible consumer.

- Use isolated worktrees, temporary directories, disposable data, mocks, or staging for tests that write state.
- Prefer negative and boundary probes as well as the happy path: remove a required setting, deny a permission, interrupt a dependency, feed an older payload, or exercise rollback—only where the environment makes that safe.
- For a proposed configuration value, trace it to an authoritative source (code, schema, official documentation, or measured behavior). Do not invent a setting or value to make the probe pass.
- If a live or destructive probe is not authorized or cannot be isolated, do not run it. Mark it `UNTESTED` and provide the exact safe precondition or approval needed.
- Capture the command or interaction, environment boundary, observed result, and relevant artifact/revision. Redact secrets and personal data from notes.

### 4. Re-evaluate as the change moves

Revisit the matrix at meaningful transitions: design/spec complete, integration available, release candidate built, and pre-release. Update only probes affected by new evidence or changed assumptions. If a change invalidates an earlier result, mark that result stale and rerun it against the current candidate; never carry a pass forward by implication.

When another agent owns implementation, avoid concurrent edits to its files. Use a separate worktree for any probe that requires changing files. Send confirmed findings to the owner early, with a minimal reproduction and suggested next action.

### 5. Report a decision-ready result

Use this format:

- **Recommendation:** `READY FOR NEXT GATE`, `HOLD`, or `INCONCLUSIVE`—not release authorization.
- **Verified:** exact probes passed, with candidate revision and evidence.
- **Findings:** reproducible failures, impact, minimal reproduction, and the boundary affected.
- **Risks / unknowns:** plausible concerns not yet proven; state what would prove or dismiss each.
- **Untested:** checks skipped, why, and the safe precondition needed to run them.
- **Next actions:** named owner or owning workstream, concrete acceptance check, and timing relative to release.

A finding requires observed evidence or a repeatable failure. A risk is not a defect until verified. Do not report “everything is good” when material paths remain unknown or untested.

## Relationship to adjacent skills

- **Trailblazer** starts from a known consequential change and tests how neighboring systems may react before the change ships.
- **Discovery** searches for worthwhile work when no concrete task is in focus.
- **Off-by-One** researches a hard question or searches for an existing answer/class; it is not a general release-readiness patrol.
- **QA/release skills** run their defined acceptance or release gates. Trailblazer adds targeted cross-system probes and hands evidence back; it does not replace those gates.

## Verification checklist

- [ ] Target change, candidate revision, boundaries, and assumptions are explicit.
- [ ] Highest-risk downstream interactions have a probe or an explicit `UNTESTED` reason.
- [ ] Probes ran in a safe environment; no unauthorized production mutation occurred.
- [ ] Results are tied to the exact candidate and configuration tested.
- [ ] Confirmed defects are separated from risks and unknowns.
- [ ] Recommendation does not imply release approval or complete coverage.
- [ ] Follow-up actions have an owner and a falsifiable acceptance check.
