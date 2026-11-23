---
name: spec-rating
description: Use when rating or authoring a system spec for completeness.
version: 1.0.0
author: <project>
metadata:
  hermes:
    tags: [spec, review, architecture, prd, rating]
    related_skills: [coding-hermes-nasa-spec, vision-brief-prd, auger-spec-surgery]
---

# Spec Rating — skill set, not a single skill

**When to use:** rating a spec for completeness, WRITING a spec with workhorse
models (the primary use — see process-workhorse-guide.md), reviewing a PRD
before it becomes specs, or deciding what sections a design doc is missing.

**Start with the routing table:** `process-file-routing.md` maps a project
shape (small web app, CLI, daemon, mobile, embedded, pipeline, distributed) to
its minimum file set, and maps intent signals to the files they imply. Rung 2
of the ladder is a lookup, not a judgment — use the table, then write the skip
list with a reason per family.

**The core idea:** workhorse models (cheap, fast) are poor planners but good
answerers. This skill set converts that: 89 resource files, each a question
ladder for one technology or lifecycle domain. A workhorse model walks the
ladders, answers every question (from the operator, the codebase, or a
decision record), and the written answers ARE the spec. The same files then
serve as the rating rubric: a second agent verifies the spec domain-by-domain
against the same checklists.

**Scope (the owner's framing):** this is the ENTIRE software development
lifecycle turned into specifications — not just the implementation, but
everything around it: the project's manifesto, its repository layout (and
how layout changes per language), its testing methodology, its CI/CD and
release process, its dependencies and third-party integrations, cost,
compliance, operations. A workhorse model that follows the set can take a
small-to-medium intent from a human and turn it into a complete project.

This skill rates how complete a system spec is, and tells an author what a
complete spec must contain. The SKILL.md carries the PROCESS; the actual
knowledge lives in `references/` — one file per technology or domain. An
agent working a spec loads only the resource files that match the system
being written or rated.

## The file contract (what every resource file must carry)

The workhorse loop's only mechanism is "answer every question, one at a time". That
is executable only when the file HAS a question list, so every file in `references/`
carries the same three sections, in this order:

1. `## What a complete spec documents` — the artefact list for this domain.
2. `## The questions it must answer` — a NUMBERED list (Q1…Qn), one answer line
   each. Rewrite assertions as interrogatives; a bullet a model can restate is not
   a question, and a file without this section degrades the run into prose
   generation that looks finished.
3. `## FAIL checks` — predicates a rater can adjudicate from the spec TEXT alone:
   a count, a bound, a named artefact, or a stated number. Never "fast",
   "appropriate", "copy-pasted", "sensible": a rater cannot decide those, so the
   check either always passes or invites an invented finding.

Optional fourth line per file: **Load also:** the sibling files this domain implies.
A file that no other file cites is reachable only from the index, so a model that
loads it and nothing else produces a spec that satisfies that file and contradicts
the system.

**Mandatory artefacts need a specimen.** When a file declares a table, a branch
table with an ELSE row, an error envelope, a pipeline or a filled rating as
required, the set must contain one worked instance of it somewhere reachable from
the index — otherwise nothing can be pattern-matched, each run invents a shape, and
the rater compares an invention against prose.

## The process (every spec passes through these stages)

1. **Core idea** — one paragraph: what it is, who it serves, what change it makes.
2. **PRD** — problem, users, jobs-to-be-done, success metrics, constraints,
   non-goals. (Pair with `vision-brief-prd` for the deliverable format.)
3. **Flows** — every user journey and machine journey, start to finish, with
   the happy path AND the failure path drawn.
4. **Data traffic patterns** — what moves, how much, how often, latency
   budgets, who reads and who writes each datum.
5. **Machines required** — the runtime inventory: processes, nodes, gateways,
   schedulers, third-party dependencies. One line per machine: what it owns.
6. **Network protocols** — per interface: protocol, port, auth, versioning,
   error envelope. (See `references/protocols-*.md`.)
7. **Storage** — per store: engine choice, schema, the queries and indexes
   that must be supported, consistency model, retention. (See
   `references/storage-*.md`.)
8. **Caching** — per cache: what it holds, invalidation, failure behavior.
   (See `references/caching-*.md`.)
9. **Failure handling** — per machine and per dependency: what breaks, what
   the user sees, what recovers automatically, what pages a human.
10. **Rating** — score the spec against the loaded resource files. A spec is
    only rated for the domains it claims; the rating lists per-domain verdicts
    COMPLETE / PARTIAL / ABSENT and names the missing artifacts.

## How to rate

- Identify the system type first (mobile app, embedded system, Linux kernel,
  web service, CLI, distributed system) and load its platform file plus every
  resource file the flows imply.
- Rate each domain on three axes: **decisions stated** (engine/protocol
  chosen and why), **contracts written** (schema/query/error examples that
  a builder can implement from), and **failure paths specified** (what
  happens when this specific thing breaks).
- A domain rates COMPLETE only when all three axes have artifacts a stranger
  could build from without interviewing the author.
- **Verdict definitions feed the author as well as the rater, so state them
  here and in the files the rater loads:** COMPLETE = all three axes present;
  PARTIAL = the decision is stated but a contract or a failure path is missing;
  ABSENT = the domain is never mentioned. Two further rules resolve the
  contradiction between "every rung needs OPEN items" and "a domain needs all
  three axes": an unanswered question CAPS a domain at PARTIAL, and an OPEN
  item the spec names (with an owner and what it blocks) is not a missing axis —
  a domain whose questions are all answered or explicitly OPEN-with-owner can
  still rate COMPLETE. A hidden empty OPEN list is a finding; an honest one is
  not.
- The final rating is the set of per-domain verdicts plus the list of
  domains the spec never mentions. 'The spec doesn't discuss caching' is a
  finding, not a neutral absence.

## Resource index (references/)

**Process (4):** `process-file-routing.md` (signal → files: the project shape
gives the minimum set, signals add files, skipped families get a written
reason — run this BEFORE anything else),
`process-spec-as-memory.md` (THE doctrine: agents have no
informal channel — the spec tree is the total collective memory;
undocumented = nonexistent; every fact owns a file; sessions write their
discoveries into the tree before they end), `process-workhorse-guide.md`
(how workhorse models use this set — read FIRST), `process-prd-to-specs.md`
(idea → PRD → specs ladder)
**System assembly (1):** `system-integration-map.md` — the orchestration
view: the integration inventory (every seam, script, connection with
contract + owner), the ownership matrix (what file owns what), the
whole-system invariants, and the assembly verification (the whole boots
from the spec tree alone; failure drills run at system level — piece
tests passing proves nothing about the assembly)
**SDLC (8):** `sdlc-manifesto.md`, `sdlc-repo-layout.md`,
`sdlc-layout-by-language.md`, `sdlc-module-template.md`,
`sdlc-testing-methodology.md`, `sdlc-cicd.md`, `sdlc-code-review.md`,
`sdlc-intent-to-project.md`
**Flows (2) — deep flow discipline:** `cross-flows.md` (rewritten: the
flow hierarchy — flow/sub-flow/step — the notation with postconditions,
exhaustive branch tables with mandatory ELSE, error flows as first-class
flows with retry/compensation contracts, re-entry and concurrency-in-flow
rules, the completeness checks incl. error-depth parity),
`flows-optimization.md` (the optimization pass: call-count baselines,
serial→parallel, off-critical-path moves, caching/batching at flow level —
each optimization re-stating the invariants it preserves)
**Paradigms (4) — the decisions BENEATH the interfaces:**
`paradigms-concurrency.md` (the concurrency model per component:
threads/event-loop/actors/processes, shared-state discipline),
`paradigms-sync-async.md` (sync default, async must earn its place, the
async-infection boundary), `paradigms-interaction-patterns.md` (individual
vs batch vs stream vs queue vs pub-sub: the decision criteria, per-pattern
failure modes — the HTTP philosophy question generalized),
`paradigms-data-pipeline.md` (batch ETL / streaming / CDC, replay
idempotency, late data)
**Deployment topologies (6) — the SAME spec re-stated per target:**
`deploy-homelab.md` (commodity machines, no HA — recovery story, tested
restores, exposure discipline), `deploy-cloud-managed.md` (AWS/GCP with
budget: managed-service map, multi-AZ/DR geometry, quotas, lock-in and
egress costs, IaC discipline), `deploy-single-vps.md` (the honest small
deploy: per-service resource caps, snapshot-rollback, off-box backups),
`deploy-kubernetes.md` (workload classes, probes, PDBs, storage reality),
`deploy-hybrid-edge.md` (seam availability, sync conflicts, store-and-
forward, per-edge identity), `deploy-onprem-enterprise.md` (customer-run:
air-gapped installs, version-skew promises, their PII in diagnostics),
`deploy-embedded-bundled.md` (the store ships inside the app: migrations
on-device, corruption windows, size budgets)
**Security (2) — beyond the checklist:** `security-lifecycle.md` (how
security work GETS STARTED: threat modeling per surface — STRIDE + abuse
cases + trust levels, accepted-risks signed by an owner, controls verified
by tests, the operate loop feeding abuse cases), `security-supply-chain.md`
(signed artifacts + verified-at-deploy, SBOM, pinned digests, CI credential
blast radius)
**Patterns (2):** `patterns-consistency.md` (saga/outbox/idempotent-
consumer/reconciliation/2PC/CRDT — the consistency pattern per distributed
flow, with the stuck-state answer), `patterns-ui-state.md` (client state
inventory, invalidation rules, optimistic-update rollback, impossible-
state elimination)
**Telemetry pipeline (5) — the whole ops fleet as a spec:**
`telemetry-logs.md` (structured logging standard, collection/transport,
retention tiers per class, PII scrubbing at ingest, the cost governor),
`telemetry-metrics.md` (metric inventory per machine, cardinality control,
downsampling, dashboards-as-code, SLO integration),
`telemetry-tracing.md` (propagation across every hop incl. async, sampling
that keeps errors, the canonical reference trace), `telemetry-audit.md`
(immutable WORM trails, integrity verification, retention/legal-hold, the
consumption loop — an unread audit trail is a liability),
`telemetry-security-monitoring.md` (detection-as-code fed by the threat
model, triage flow with false-positive budgets, MTTD/MTTR, detection
coverage)
**Privacy rules (1) — the regulatory overlay:** `privacy-rules.md`
(regulations compile to requirements: per-regime applicability, data-
subject rights as flows with SLAs, consent records + withdrawal
propagation, breach clocks, transfer mechanisms, ROPA/DPIA artifacts,
the wiring into cross-privacy/thirdparty/telemetry files)
**Platform types (7):** `platform-web-service.md`, `platform-mobile-app.md`,
`platform-embedded.md`, `platform-linux-kernel.md`, `platform-cli.md`,
`platform-daemon.md`, `platform-distributed.md`
**Interfaces (3):** `protocols-http.md`, `protocols-rpc-queue.md`,
`protocols-realtime.md`
**Storage (6):** `storage-sql.md`, `storage-document.md`, `storage-kv.md`,
`storage-search.md`, `storage-object.md`, `storage-embedded.md`
**Caching (3):** `caching-inprocess.md`, `caching-distributed.md`,
`caching-cdn.md`
**Dependencies (3):** `deps-selection.md`, `deps-maintenance.md`,
`deps-vendoring.md`
**Third-party integrations (6):** `thirdparty-apis.md`,
`thirdparty-webhooks.md`, `thirdparty-oauth.md`, `thirdparty-payments.md`,
`thirdparty-messaging.md`, `thirdparty-ml-models.md`
**Cross-cutting (26):** `cross-security.md`, `cross-observability.md`,
`cross-deployment.md`, `cross-testing.md`, `cross-performance.md`,
`cross-compat.md`, `cross-failures.md`, `cross-data-traffic.md`,
`cross-i18n.md`, `cross-accessibility.md`, `cross-machines.md`,
`cross-flows.md`, `cross-cost.md`, `cross-licensing-compliance.md`,
`cross-data-migration.md`, `cross-privacy.md`, `cross-slo.md`,
`cross-capacity.md`, `cross-config.md`, `cross-release.md`,
`cross-developer-experience.md`, `cross-docs.md`, `cross-process.md`,
`cross-rollout.md`, `cross-state-machines.md`, `cross-reporting.md`

89 resource files (4 process · 1 system assembly · 8 SDLC · 4 paradigms ·
2 flows · 2 security · 2 patterns · 5 telemetry · 1 privacy rules ·
7 platform · 6 deployment
topologies · 3 interfaces · 6 storage · 3 caching · 3 dependencies ·
6 third-party · 26 cross-cutting). A spec states its
deployment TARGETS and re-answers the topology files per target — the same
system on a homelab and on AWS is two different answer sets. Load a file
only when its domain applies to the system
under rating. Add a new file (not prose in this file) when a rating or a
spec-writing run reveals a domain with no resource yet — the set grows with
every system we write.

## Sequencing law (COS: order and effort buy the value)
Not everything needs to exist for v1 — and not every existing file needs
exercising yet. Deciding the order, flow and effort-per-piece to give a
project the most value is the COS's job, not a reflex to build everything:
- **The v1 slice (exercised first)**: process-spec-as-memory +
process-workhorse-guide + process-prd-to-specs + sdlc-module-template +
cross-flows + cross-failures + security-lifecycle + the 2-3 storage/
protocol files the project actually touches. That is enough for a
workhorse model to spec and build a small/medium project.
- **Deferred until a run needs them**: exotic platforms (kernel,
embedded, on-prem enterprise), multi-region, migration-between-
topologies. They exist as checklists; they earn depth when used.
- **Value proof before depth**: the next unit of effort is a REAL run of
the intent→project ladder on one small intent (plus one rating of an
existing spec), and the gaps THAT run reveals outrank any speculative
file in this set.
