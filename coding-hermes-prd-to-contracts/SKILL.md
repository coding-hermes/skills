---
name: coding-hermes-prd-to-contracts
description: Use when rebuilding a failed system or kicking off a greenfield project — owner-interview PRD with multi-round agent-panel consensus, then specs/contracts by the same panel.
version: 1.0.0
author: Bane + Hermes
metadata:
  hermes:
    tags: [coding-hermes, prd, panels, consensus, specs, process]
---

# coding-hermes-prd-to-contracts

The proven process for taking a system from "it failed / it doesn't exist"
to "signed PRD + verified contract set" using panels of full Hermes agent
sessions. Distilled from the DAGger rebuild (2026-09-10/11): interview →
destination plans → salvage verdicts → PRD → 3-round consensus → specs phase.
Use it as the playbook for any project kickoff or rebuild.

## Why panels of full sessions (not subagents)

- A **full Hermes session** (`hermes chat -q "$(cat brief.txt)" -m <model>
  --provider <p> --ignore-rules -Q`) has tools, memory of the repo, and budget
  to actually investigate — subagent fan-outs die at the leaf timeout and
  produce thin drafts.
- **Diverse models catch different things.** Across 3 PRD rounds, five models
  converged on every load-bearing decision and diverged productively on
  details (the strictest auditor found 12 defects; the visionary rewrote
  whole sections; the process judge caught a self-contradicting example).
- The coordinator (you) is a **merge editor, not an author**: adopt judges'
  exact replacement wording verbatim. Paraphrasing 30 fragments reintroduces
  contradictions — v1.1's merge created 4 conflicts the judges caught in
  round 2. Verbatim adoption in v1.2/v1.3 converged to 5/5.

## Phase 0 — Ground truth before any panel

Before asking agents anything, establish receipts:
- What the owner actually asked for, quoted with source IDs (chat message IDs,
  state.db rows). Owner quotes outrank every spec.
- What exists on disk vs what was only ever specced ("14 specs, 0 pipelines").
- Failure forensics of the old system with numbers (e.g. "2,218/2,218 runs
  recorded completed, 167/328 briefs never produced a driver log").
- Canonical numbers: if two scans disagree, resolve BEFORE the panel; give
  judges one truth, not a choice.

## Phase 1 — Owner interview → requirements of record

- **Interview, grill, don't assume.** Voice works (local faster-whisper STT);
  batch questions via `clarify` (Bane: 3–5 min to answer — prefer clarify,
  which stays open, over chat ping-pong).
- Record answers as numbered requirements (R1…R22). Numbering gaps (R16) stay
  gaps — never renumber, never invent dispositions for holes.
- Persist immediately to durable memory (DuckBrain namespace + a local
  REQUIREMENTS.md) — the owner said so explicitly: "so we don't lose them."
- When an owner answer contradicts the panel's prior consensus, the owner
  wins; log it as an amendment (e.g. R22 amending R14's architecture), not a
  reinterpretation.
- **Open questions stay visibly open.** If an answer times out 3×, the PRD
  marks it OPEN with a blocking milestone — it does NOT get silently assumed
  (v1 died of silent assumptions; our round-1 judges caught exactly that
  slip in the draft).

## Phase 2 — Destination panel (planning, not verification)

Ask the panel to review what the owner actually wanted (chat logs, specs,
memory) vs what was built (the "slop bucket"), then produce plans to reach
the destination. Key properties:
- Briefs are **file-referenced** (`$(cat prompts/X.txt)`), never inline
  heredocs (approval-gate + parser-size hazards).
- Each judge writes a **detector-marked deliverable** (`PLAN COMPLETE` /
  `VERDICT COMPLETE`) — quiet-mode sessions buffer output, so the marker is
  your completion proof, not process exit.
- Expect crossed filenames and merging surprises: reconcile by content, keep
  both distinct works.

## Phase 3 — Salvage verdict

Before any greenfield enthusiasm: per-component
KEEP / REWORK / DELETE tied to R-items, with the reasoning. Two rules that
held under panel attack:
- Deletion attempts get litigated — a user-directed artifact (our skill
  registry) survived because judges demanded its retention.
- "Rebuild on salvaged chassis, not greenfield, not evolution" was the
  5/5 landing. The keep-list was ~80% of the v1 value at a fraction of mass.

## Phase 4 — PRD by consensus loop

The loop that reached 5/5 in 3 rounds:

1. Coordinator drafts v1.0 from all prior material.
2. **Review round**: per-section APPROVE or CHANGE with EXACT replacement
   text (advice is not a review). Explicit checks: every R-item walked,
   every owner quote honored, "would this have prevented the old failure
   modes?", scope-creep hunt.
3. Merge: **verbatim adoption** of judge wordings; conflicts between judges
   resolved by their own pre-authorized compromises, never the coordinator's
   average (a lowest-common-denominator metric was explicitly rejected).
4. **Verify round**: judges walk their own change list (RESOLVED /
   NOT-RESOLVED) + one fresh pass for merge-introduced contradictions.
5. Repeat until 5/5. Final round is delta-only (approving judges check just
   the edits; dissent may only flag NEW defects).
6. Deliver: HTML PRD (see web-page-delivery `references/prd-format.md`;
   embed mockups base64 for Telegram single-file delivery) + the .md source.

Round data from the reference run: v1.0 → 28 changes; v1.1 merge → 37
residuals (paraphrase tax); v1.2 verbatim → 4 conflicts; v1.3 → 5/5.

### Numeric acceptance criteria

Milestones gate on numbers, with anti-gaming teeth:
- Authoring gate: N reserved briefs × 2 model families, first-shot success ≥
  threshold per family, hard rewrite ceiling, explicit FAIL conditions
  (source-contamination, silent node-drop, nondeterminism = counted failures).
- Migration gate: canary waves, reversible rollback, kill criteria tied to
  baseline metrics (real-dispatch rate; a truthfulness breach or secret leak
  halts unconditionally).
- "Every new hook must delete or simplify something" evolved into: no
  deletion quota, but every change must serve a recorded requirement.

## Phase 5 — Specs & contracts (same panel, multi-round)

Goal per owner: "every edge case, choice, pattern, input, output, ser/deser,
logging, debugging, parallelization, scheduling thought of, accounted for,
all issues mitigated."

1. **Inventory round** (5 judges in parallel): each produces EXISTS (already
   buildable, cited) / NEEDED (the contract catalog: schemas, APIs, error
   taxonomies, concurrency, serialization, logging, debugging, scheduling) /
   WANTED (non-blocking extras) / MISSING (owner decisions with proposed
   defaults). Reconcile into one contract register with owners and a
   dependency-ordered writing plan.
2. **Contract rounds**: draft contracts from the register, then review rounds
   with the same APPROVE/CHANGE-exact-text protocol until consensus per
   contract. Batch independent contracts; single-round small ones.
3. Q-dependent specs wait for owner answers; OPEN items are explicit spec
   states, never assumptions.

## Operational mechanics (the part that silently kills panels)

- Dispatch: `export HOME=<user-home>; hermes chat -q "$(cat brief.txt)" -m
  <model> --provider <provider> --ignore-rules -Q > out.log 2>&1` as separate
  background processes (terminal background=true, notify=true). Registry-
  verified lanes: gpt-6-astra@openai-codex, k3@kimi-for-coding,
  glm-5.3@zai-glm, deepseek-v4-pro@deepseek, qwen3.8-max@opencode-go
  (verify against task-router tables at dispatch time).
- Exit code 0 ≠ done. Check the detector marker in each judge's file; a
  missing marker with a big log = truncated run, re-dispatch or read the log.
- Judges get call budgets (~25–40 tool calls) and "do not modify PRD.md" —
  reviewers never write the artifact under review.
- The coordinator merges only; every merge is a diff the next round checks.
- Delivery law: when the owner asks for a document, the reply carries
  `MEDIA:/abs/path` — they have asked repeatedly; do not make them dig.
- Persist everything to the project workspace dir (`~/<project>-panel/`):
  prompts/, reviews/, plans/, specs/, PRD.md — the next phase's briefs
  reference files, never re-paste content.

## Reference run artifacts

DAGger rebuild, `~/dagger-v2-panel/`: PRD.md (v1.3, 5/5),
REQUIREMENTS.md (R1–R22), prd-review/ (all rounds), plans/, plans-2/,
specs/, DAGGER-PRD.html (delivered), DAGGER-REBUILD-FINAL.html (salvage
report), mockups/. Use as templates for brief structure and merge format.
