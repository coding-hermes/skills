---
name: coding-hermes-nasa-spec
description: "Full design spec method: Rumsfeld, flows, contracts, quorum."
version: 1.1.0
author: totalwindupflightsystems
license: MIT
category: software-development
metadata:
  hermes:
    tags: [specs, design, rumsfeld, decomposition, contracts, quorum, traceability]
    related_skills: [nasa-handbook, rumsfeld-matrix, coding-hermes-specs, coding-hermes-quorum, exhaustive-specification]
---

# 仕様 NASA Spec — from four quadrants to a signed contract

A design-spec method that turns one vague intent into a numbered, traceable,
worker-ready spec set, and then puts it in front of a judging panel before any
code exists.

It is the **substance** half of the pair whose **form** half is the
`nasa-handbook` skill:

- **`nasa-handbook`** — the LOOK. Apollo Operations Handbook page: running head,
  numbered paragraphs, Leroy-lettered drawings, performance tables,
  NOTE/CAUTION/WARNING, Flight Data File checklist card, dated footer, PDF render.
  Credit for that visual/print system belongs to that skill; this one does not
  re-implement, fork, or restyle it.
- **`rumsfeld-matrix`** — the quadrant method this skill runs in Phase 1.
- **`coding-hermes-specs`** — the implementation-spec standard a module/submodule
  contract must satisfy once it is dispatched.
- **`coding-hermes-quorum`** — the panel that decides whether the spec is
  implementable at all.

Use all four together. This skill is a **companion to the NASA skill, not a
replacement**: keep `nasa-handbook` for the document and its render loop, and
change only the process that produces the facts it prints.

## Two invariants that keep the pair honest

1. **Facts flow one way.** Facts are gathered by THIS skill's process — read the
   code, run the tool, probe the service, read the decision record — and land in
   `_facts.md` with a source and a timestamp. The rendered page is never a data
   source. A number that exists only in a PDF or a figure caption is an
   unverified claim wearing a uniform.
2. **Render is a projection, not a derivation.** Restyling the page — new
   template, different figure, A4 to Letter, reordered sections — must not change
   a single normative statement. Re-render from the same spec files. If a fact
   changes, change `_facts.md`, then the spec, then re-render. Never edit the
   page and back-propagate.

Corollary, and the practical reason this rule exists: **run the substance round
before the visual round.** Re-drawing a truthful page is a cheap render cycle;
re-deriving the truth from a pretty page is impossible.

## The pipeline

```
0 frame ─ 1 Rumsfeld ─ 2 facts ledger ─ 3 overview ─ 4 flows ─ 5 modules
   ─ 6 submodules ─ 7 contracts ─ 8 cross-cutting ─ 9 traceability+checker
   ─ 10 quorum rounds ─ 11 dispatch briefs ─ 12 render (nasa-handbook)
```

Each phase writes a FILE. Chat prose, a DuckBrain entry, or a memory note is not
an artifact and does not satisfy a phase. Nothing downstream starts until the
upstream file exists on disk.

---

## Phase 0 — Frame the domain

Write `specs/00-frame.md` in three or four sentences:

- what system, for whom, in what environment;
- the **one idea** the whole document exists to convey, in one sentence;
- who reads this (worker / judge / operator) and what each of them must be able
  to do after reading it;
- what breaks if the spec is wrong (this is the quorum's stakes paragraph later);
- explicit scope boundary: what this spec set does NOT cover.

No design, no architecture, no diagram. Frame only.

## Phase 1 — Rumsfeld matrix, before any design

Load `rumsfeld-matrix` and populate all four quadrants. The point is not a
taxonomy exercise: **each quadrant has a mandatory downstream sink.** A quadrant
whose contents go nowhere was decoration.

| Quadrant | What belongs | Mandatory sink |
|---|---|---|
| Known knowns | verified facts: code read, tool output, probe, decision record | a row in `_facts.md` with HOW it was measured |
| Known unknowns | questions you can articulate but cannot answer | open-question register: owner, resolution path, deadline, blocking yes/no |
| Unknown unknowns | blind spots found with the techniques below | either a measurement task that converts it to a fact, or a design decision plus its falsifier |
| Unknown knowns | constraints the operator already holds: memory, prior decisions, implied norms, past failures | an explicit normative statement, or a stated non-goal |

Unknown-unknown techniques (use at least four, name which):

- **Assumption inversion** — take each known known, ask "what if this is wrong",
  follow the cascade to a design consequence.
- **Cross-domain analogy** — find the structurally identical system elsewhere and
  import its documented failure mode.
- **Scale extremes** — 0, 1, 10x, 100x the expected load/size/time; what breaks
  first and what does it look like.
- **Second-order effects** — if it succeeds completely, what else changes; if it
  fails silently, who notices and when.
- **Paradigm challenge** — is this the right problem, or is the framing the blind
  spot.
- **Day-one state** — the system before anyone has written the first row: what
  does every derived state, cache, counter, and dashboard show then.
- **Unexpressible failure** — if the store/event/log cannot record "failed", every
  downstream count lies. Ask early; it changes the schema.
- **Adversary view** — the actor who benefits from the system doing the wrong
  thing correctly.

Hard rules:

- No quadrant may be empty. An empty quadrant is a finding — write why it is thin
  rather than pretending it is clean.
- A named unknown-unknown that cannot be resolved becomes a RISK with a named
  probe that would reveal it, not a vague worry.
- Every unknown-known cites where it came from (memory key, decision record, prior
  spec). "Probably" is not a citation.
- Re-read the matrix at Phase 10: the quorum brief quotes it, and anything that
  materialized mid-design is promoted into `_facts.md`.

## Phase 2 — Facts ledger

`specs/_facts.md` is the spine of the document. One row per fact:

```
| id | claim | how measured (command / path / store) | measured at | confidence |
| FACT-12 | terminal sandbox caps a worker at 4 GiB | `systemd-analyze cat-config` on the worker scope | 2026-11-05T09:10Z | measured |
```

Confidence classes: `measured`, `read-from-code`, `told-by-operator`,
`assumed`. An `assumed` fact can never back a normative statement — convert it or
mark the statement as a spike.

Grep every number the document will print. When documentation and code disagree,
code wins and the discrepancy is itself a fact. This ledger is what lets a judge
grade a claim instead of a vibe, and it is what a re-render re-prints unchanged.

## Phase 3 — Overview

`specs/00-overview.md`:

1. Purpose and the one idea (from Phase 0).
2. Actors — every human, service, and agent that touches the system, plus which
   of them can be untrusted.
3. Boundary — inside vs outside; what crosses the boundary and in which direction.
4. Invariants — statements that must always hold (these become `check:`
   requirements later).
5. Non-goals — explicit, drawn from the matrix; each with the reason it is out.
6. Constraints — fixed by environment, cost, platform, or owner decision.
7. Success criteria — observable, with a measurement.
8. **Surface inventory** — every entry point, derived from the live system, not
   from memory: CLI verbs (`--help`), HTTP routes (router table or `ss` + probe),
   cron/timer jobs (unit list), UI screens, events/webhooks subscribed, files
   dropped. Each row: surface → where it is declared → flow it belongs to.

The surface inventory is the anchor for flow completeness. A flow set derived
from imagination always misses a route; a flow set derived from a route table
misses nothing without saying so.

## Phase 4 — Flows

One file per flow: `specs/flows/FLOW-01-<slug>.md`.

Each flow carries, in this order:

- **id and name** (`### FLOW-01 — Mint a session token`)
- `trigger:` what starts it (request, cron fire, operator command, event)
- `exit:` what the caller observes when it is done (response shape, side effect,
  state change) — the observable end, not "success"
- actors and preconditions
- numbered steps; **every step names the module that executes it**
- per-step branches and error paths, with the caller-visible result of each
- state transitions (which entity moves from which state to which)
- data read / data written, by contract id
- timing, limits, retries, timeouts, idempotency behaviour
- the diagram (sequence or timeline) — in the markdown file as mermaid, and later
  in the handbook as a figure

Completeness rule: **every surface in the inventory maps to exactly one flow, or
is listed out-of-scope with a reason.** Keep that mapping table in the overview;
no checker can infer it for you.

Every flow must contain the happy path, at least one failure path, the
duplicate/concurrent case (same request twice, two callers at once), and the
empty/day-one case.

## Phase 5 — Modules per flow

A module exists because a flow step needed it. One file per module:
`specs/modules/MOD-03-<slug>.md`.

```
### MOD-03 — Token broker
flow: FLOW-01
owns: token rows, rotation schedule
does-not-own: authentication of the caller, rate limits
inputs: actor id, requested scope, TTL
outputs: signed token, refresh handle
collaborators: MOD-05 (store), MOD-07 (policy)
failure modes: store down → fail closed; clock skew → reject; replayed handle → 409
invariants upheld: never issues a token without a policy decision
concurrency: single writer per token id, optimistic version check
config: TOKEN_TTL_SECONDS (int, default 3600, >0)
observability: counter token_minted_total, counter token_rejected_total{reason}
```

Rules:

- A flow step that names no module is a hole. A module named by no flow is a
  component nobody asked for — the checker flags it as an orphan.
- **Every piece of state has exactly one writer module.** Shared writes are a
  design defect to resolve now, not a footnote for the implementer.
- "Does not own" is mandatory: it is what stops two modules from each
  half-implementing the same rule.
- Failure modes are per dependency, with the direction of failure (fail closed /
  open / degraded) stated.

## Phase 5b — the field contract every module section must satisfy

A module section is a claim with its evidence attached, in a fixed order — not prose about a
component. The full field contract, with the failure each field prevents, is
`references/module-section-fields.md`. Five of those fields carry the most weight and are
editable-in by the owner, so they are non-negotiable:

| field | rule |
|---|---|
| dependencies + library contracts | three tables — runtime (version, required location, **how absence is DETECTED**), library (the call or field relied on, never "uses X"), service (peer, direction, transport, payload, compatibility, **both sides' file and function**) |
| verification | a command a stranger can run, the expected output, the date and the revision. A check that cannot fail is decoration; a check that last passed three revisions ago is `UNVERIFIED` |
| why it matters | not what it does — what breaks if it is absent, and what breaks if it LIES |
| metrics | type, labels, the question it answers, where scraped. **Emits none → write "none" and carry the section as RED.** An unobservable module on the critical path is a finding, not a blank |
| log lines | every operator-visible line verbatim, plus its kind: **descriptive** (reports that something happened) or **evidentiary** (can be cited as proof). A line that says so is not proof it is so |

Status vocabulary is `VERIFIED` / `UNVERIFIED` / `FAILING`. There is no "done" and there is no
blank: an empty required field IS the finding, rendered RED. A document that renders every
section comfortably full is a document that stopped measuring.

## Phase 6 — Submodules

Recurse one level, and only as deep as the testable unit. One file per
submodule, or a section inside the module file:

```
#### SUB-03.2 — Signature verifier
module: MOD-03
contract: verify(token string, key KeySet) (Claims, error)
pre: token non-empty, key set loaded
post: claims returned only when signature and expiry both valid
errors: ErrExpired, ErrBadSignature, ErrUnknownKid
side effects: none
ordering/idempotency: pure, safe to call concurrently
test: TestVerifyExpiredRejects
```

A module with no submodules declares `leaf: yes` and the reason it needs no
further decomposition (checked, so silence is not an option).

## Phase 7 — Contracts

Four contract classes, one template each. A contract is not a description; it is
what a caller is allowed to rely on and what a producer is forbidden to break.

1. **Module contract** — exact signatures and types, pre/post-conditions, typed
   errors, idempotency, ordering, concurrency guarantees.
2. **Service/API contract** — route table, request/response schema with a
   COMPLETE inline example, status codes, error catalog, auth per route, rate
   limits, timeouts, pagination, versioning, deprecation policy.
3. **Data contract** — DDL with constraints and indexes, ownership (writer),
   retention, migration path, what is forbidden to mutate in place.
4. **Config and event contracts** — env names, types, defaults, validation
   rules; event schema, delivery semantics (at-least-once / exactly-once),
   ordering key, versioning.

Ground every external surface in the tool's own `--help` or a live probe. A
surface you have not measured is a SPIKE — write it as a spike with the named
unknown, not as a plausible-looking endpoint. Invented third-party APIs fail at
implementation time, which is the one failure the spec exists to prevent.

**Contract matrix** (in `specs/contracts/_matrix.md`): producer → consumer →
contract id → breaking-change policy. Every contract has at least one producer
and one consumer; the checker enforces it, because a contract nobody consumes is
either dead weight or a missing module.

## Phase 8 — The everything-else register

A spec that stops at flows and modules is a diagram, not a design. Under
`specs/cross-cutting/`, one file each — every item a numbered requirement, not a
paragraph of good intentions:

- **errors and recovery** — the catalog, who retries, who gives up, what the user
  sees, what is recorded.
- **security and trust boundaries** — authn/authz per surface, secret storage and
  rotation, injection surface at each boundary, what is logged and what must
  never be logged.
- **observability** — metrics, log fields, traces, alerts; and for each alert its
  ARMED state and who it wakes.
- **performance and capacity** — budgets with numbers, the measurement that
  proves them, the worst-case real row (not a toy profile).
- **durability** — backup, restore, and the restore that was actually tested.
- **operations** — deploy, rollback, day-one bootstrap from nothing, runbooks,
  teardown.
- **data lifecycle** — retention, deletion, export, migration and compatibility
  windows.
- **testing** — unit, integration, e2e, chaos, and what each level is forbidden
  from mocking (the twin rule: a smoke test that mocks the transport proves the
  mock).
- **acceptance criteria** — the R-table (Phase 9).

## Phase 9 — Numbering, traceability, and the coverage gate

One ID space for the whole set: `FACT-nn`, `FLOW-nn`, `MOD-nn`, `SUB-nn.d`,
`CT-nn`, `R-nnn`. IDs are declared once, in a heading. Numbering is GLOBAL to the
set — two files claiming `MOD-03` is the defect that survives every grep and
fails every judge.

Requirements live in a table whose shape IS the contract with the judge:

```
| id | statement | attaches to | assertion | evidence |
| R-014 | the broker must reject an expired token with 401 | module: MOD-03 | test: TestVerifyExpiredRejects | fact: FACT-12 |
```

Rules:

- **one R per normative statement**, `must` = something fails without it;
- **exactly one assertion** per R, and it lives in the ASSERTION COLUMN (4th
  cell): `test:` for behaviour, `check:` for a prohibition or a prose claim
  (a grep, a schema lint, a rendered-page check). Prose elsewhere in the row
  does not count — a row whose statement says "(see check: above)" while the
  assertion column is empty is a hole, and the checker now says so. The target
  must be runnable: an identifier or path (`TestExpiredRejects`,
  `scripts/lint_board.sh`), never a phrase (`test: it rejects expired tokens`);
- **the row is exactly five columns.** Four columns (a missing cell) or six (an
  unescaped `|`) shift the columns silently, so the checker refuses the row
  rather than guessing which cell was meant;
- **evidence is mandatory**: `fact: FACT-nn` or `decision: <where recorded>`,
  in the evidence column;
- the coverage table maps R → module → flow → test, and the spec's own highest R
  number is parsed back, so a renumber cannot leave phantom statements passing.

Before every quorum round and after every fix, run:

```bash
python3 scripts/spec_coverage.py specs/
```

The checker enforces: unique ids; every module names a real flow; every submodule
names a real module; every contract has a resolving producer and consumer; every
requirement attaches to a real module in its attach column, carries exactly one
runnable assertion in its assertion column, and a fact or decision in its
evidence column; every flow declares `trigger:` and `exit:`. It warns on facts
nobody cites, flows with no modules, modules with no submodule and no `leaf:`,
and flows no contract touches. Exit 1 on errors; `--strict` makes warnings
errors too.

**Prove the gate FIRES before trusting a PASS.** A checker that parses nothing
reports zero violations, and a parser that silently ignores an unknown metadata
key downgrades a real defect to a warning. The fixtures ship beside the script,
and one command proves all three obligations:

```bash
python3 scripts/test_spec_coverage.py      # 18 obligations; exits 1 on any miss
```

`scripts/fixtures/good/` must exit 0 under `--strict`; `scripts/fixtures/bad/`
carries one deliberately broken row per rule (duplicate decl id, unresolved
flow/module/contract reference, missing `trigger:`/`exit:`, zero and two
assertions, missing evidence, dangling fact, prose assertion in the wrong
column, prose assertion target, four-column row, duplicate R id) and the score
must name each one; `templates/` must still fail, because an unfilled template
is not a spec. Run it after ANY parser change — the first version counted
`test:`/`check:` anywhere in the row, so a statement containing "check:" passed
with no assertion at all, and only the mutation test caught it.

## Phase 10 — Quorum: the panel decides

A spec that will drive other agents is not done when it is written; it is done
when independent families fail to break it. Run `coding-hermes-quorum`:

1. **Freeze the version.** Stamp the spec set with a date/commit and point every
   seat at file paths. A seat reviewing a moving target produces a round about
   the weather.
2. **Brief = claim checklist**, built from the spec: FACT claims with an expected
   value and a grade (CONFIRMED / CONTRADICTED), and a separately LABELLED
   inference block (the highest-yield target — the coordinator's own causal
   reasoning is thinnest there). Template: `templates/quorum-brief.md`.
3. **Verify seats live.** Resolve lanes against the live registry, probe each one,
   and prove identity from `session_model_usage` — a labelled model is not a
   served model. Report the panel as fewer families rather than quoting a lineup
   that did not serve.
4. **3-5 families, every judge works the whole checklist**; diversity supplies
   different error emphasis, never a division of labour.
5. **Two rounds.** Round 2 is two jobs: *Job A* — quote the text that now carries
   each merged fix and return FIXED / PARTIAL / NOT-FIXED; *Job B* — attack the
   surfaces the fixes created. A fix is a new design and fails in its own ways.
6. **Merge is the commit layer.** Every CONTRADICTED is a lead: re-verify at the
   primary source before acting. Fix by REGENERATION (re-derive the tables from
   the code, delete claims no command reproduces), not by patching prose. After
   every fix, grep for the new string AND for the old one — a find/replace that
   matches nothing exits 0 and changes nothing.
7. **End with a measurement.** A prose round grades what the design PROMISES, not
   what it DELIVERS. Name the effect the design claims, measure it, and if the
   gate fails, ship the feature default-off and record the negative result — a
   panel-approved design that fails its own gate is still a failed design.

Below quorum, nothing happened: if diversity collapsed or independence was
shared, say the round never convened.

## Phase 11 — Dispatch: a spec is not work

Convert each capability into one worker brief (see `coding-hermes-specs`) with:
goal, files to touch, numbered acceptance criteria that are RUNNABLE, gates, the
evidence the closeout must carry, and an explicit out-of-scope list. Then file one
board row per brief whose `acceptance_criteria` is the concatenation of those
checks.

A deviation recorded only in a commit message or a closeout summary is how a
spec section quietly stops existing: the same day, write the missing section into
the NEXT row's scope and name which row supersedes it.

## Phase 12 — Render with `nasa-handbook`

Only now, and only as that skill prescribes: its template, its fonts, its
`render.sh` fit loop, its `check.py`, its 300 dpi tile review. Do not fork the
renderer, the geometry rules, or the critique-triage rules here — this skill owns
what the page SAYS, the handbook skill owns how it LOOKS.

Mapping from spec artifact to handbook block:

| Spec artifact | Handbook block |
|---|---|
| overview purpose + one idea | intro paragraph (3 lines) |
| actors + surface inventory | hero general-arrangement figure |
| a single flow | sequence/timeline figure, one numbered paragraph per step |
| module tree + collaborators | block diagram with callouts |
| contracts (limits, rates, sizes, timeouts) | performance data table, units on every value |
| error catalog | NOTE / CAUTION / WARNING (WARNING reserved for destructive or irreversible) |
| invariants | underlined mechanism paragraph |
| acceptance criteria R-table | Flight Data File checklist card |
| facts ledger stamps | dated footer plus "data as of" in figure captions |

Two handbook rules that this method depends on, restated because they are the
handoff points:

- **A snapshot is not a state.** Anything with a count in it is a dated
  measurement; caption it with the measurement date, or say what is required
  instead of claiming what is installed.
- **A correction is set-wide.** When a fact changes, grep every sheet for the
  contradicted phrase, the component name and its neighbours before re-rendering.
  A set that argues with itself is worse than no set.

## Deliverable bundle

```
specs/
  _index.md            # what exists, status, dependency order
  _rumsfeld.md         # four quadrants + sinks
  _facts.md            # the ledger
  00-frame.md  00-overview.md
  flows/        FLOW-nn-*.md
  modules/      MOD-nn-*.md
  contracts/    CT-nn-*.md + _matrix.md
  cross-cutting/*.md
  _coverage.md         # R → module → test, and the surface → flow map
  _quorum/             # briefs, verdicts, merge ledger
  <name>-handbook.pdf  # rendered last, from the approved spec
```

The handover is the directory plus the coverage report, not a chat message.

## Pitfalls learned by doing this

- **Prose in memory is not a spec.** A 200-word entry in a memory system cannot
  produce correct code; the worker invents types, DDL, errors, and wiring.
- **If a worker can build two different things from one statement, the statement
  is wrong.** That is the only quality test that matters.
- **A module with no flow is a component nobody asked for; a flow step with no
  module is a hole.** Run the checker instead of trusting your memory of the tree.
- **"Read the README" is not a measurement.** When docs and code disagree, code
  wins and the disagreement becomes a fact.
- **Numbering is global.** Duplicates pass a local grep and fail a judge; the
  handbook set has the same rule for section and figure codes.
- **Do not let the visual round set priorities.** A pretty figure can make a
  missing invariant feel covered; the quorum grades the statements.
- **A quorum on a moving target wastes a round.** Freeze the version, stamp it,
  and re-derive any state claims after the last seat lands.
- **A fix that greps only the new string is half a fix.** Grep for the corrected
  text and confirm the old text is gone — observing the new text is the proof,
  and the exit code is not.
- **Never arm an implementation loop on a FAIL round.** A spec that fails review
  teaches the loop to implement its errors faithfully.
- **A gate that matches prose is not a gate.** Counting `test:`/`check:` anywhere
  in a requirement row let a statement containing "(see check: above)" pass with
  an empty assertion column — the requirement looked verified and pointed at
  nothing. Parse the CELL, not the line; require a runnable target; and keep a
  fixture that reproduces the hole so the fix cannot be reverted quietly.
- **A template that teaches a shape the gate rejects is a defect, not an
  example.** The shipped coverage template printed `| FACT-01 |` in the evidence
  column while the checker demands `fact: FACT-01`; every spec written from it
  would fail its own gate. Run the checker on the templates after editing them.

## Quick start

```bash
mkdir -p specs/{flows,modules,contracts,cross-cutting,_quorum}
cp <skill>/templates/*.md specs/            # frame, rumsfeld, facts, overview, flow, module, contract
# ... write phases 0-9 ...
python3 <skill>/scripts/spec_coverage.py specs/          # must exit 0
# ... quorum round 1 with <skill>/templates/quorum-brief.md ...
sh <nasa-handbook>/scripts/render.sh <out>/<name>.html   # render only after approval
```

Support files:

- `templates/00-frame.md`, `templates/_rumsfeld.md`, `templates/_facts.md`,
  `templates/_coverage.md`
- `templates/00-overview.md`, `templates/flow.md`, `templates/module.md`,
  `templates/contract.md`
- `templates/quorum-brief.md`
- `references/spec-to-page-mapping.md` — deeper spec → handbook block mapping,
  including which spec section supplies which paragraph, figure, table, and notice
- `references/module-section-fields.md` — the field contract a module section must satisfy
  (dependencies and library contracts, verification, metrics, log lines, failure modes) and
  why an empty field is RED rather than incomplete
- `scripts/spec_coverage.py` — the structural gate described in Phase 9
- `scripts/test_spec_coverage.py` — the gate's own regression suite (good must
  pass `--strict`, every bad-fixture rule must fire, unfilled templates must
  fail); run it after any parser change
- `scripts/fixtures/good/`, `scripts/fixtures/bad/` — the two fixture spec sets
  the suite scores

