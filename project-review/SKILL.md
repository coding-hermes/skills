---
name: project-review
description: 'Use when asked to explore, test, and report on a project — hands-on clone/build/run/compare review, delivered as one self-contained HTML verdict.'
version: 1.0.0
author: carterlasalle
license: MIT
metadata:
  hermes:
    label: carter
    source: https://github.com/carterlasalle/scc
    tags: [review, verification, html-report, third-party, evidence, 検証]
    related_skills: [frontend-design, impeccable, find-skills]
    requires_external:
      - frontend-design
      - impeccable (install: npx skills add pbakaus/impeccable@impeccable)
      - find-skills
    attribution: >
      Collected by the owner and labelled "carter"; the username came from the scc
      project as instructed (carterlasalle). VERIFIED 2026-09-26: the identical skill
      text also appears in 5throck/ai-workspace-standards (AGPL-3.0) including
      .hermes/.agents/.claude variants, and this skill is NOT present in
      carterlasalle's public repos. Treat the label as the owner's filing bucket, not
      as a verified authorship claim — resolve before republishing.
---

# Project Review — hands-on third-party review with HTML verdict

When the user shares a repo or project link and wants it explored, tried out,
compared, and judged, do all four for real: the deliverable is a working
test pass backed by actual tool output, plus a single self-contained HTML
report. Never review from docs alone when the project can be built.

## Related skills

Load these; they are part of the method, not decoration:

- **frontend-design** — the report is a designed artifact. Follow its
  two-pass flow (design plan with tokens/type/layout/signature, then build)
  and its Read-mode guidance: structure for comprehension, hero as thesis.
- **impeccable** (pbakaus/impeccable — install via `npx skills add
  pbakaus/impeccable@impeccable` when missing; never skip the skill and
  fake its rigor) — run `impeccable context --target <report>`, roll
  `concept-seed` for replacement visual worlds, record the direction
  contract, re-read `craft-floor.md` immediately before any UI edit, run
  `detect --json` once finished and fix what is mechanical. Code-led unless
  the harness has image generation; state the substitution when the full
  ceremony (decision pages, finish-reviewer spawn) doesn't fit the session.
- **find-skills** — when the review names a capability the harness lacks
  (a design skill, a protocol reference), search for and install it instead
  of proceeding without it.

## Concepts (standing corrections — do not relearn these)

- **Forward-ready.** Establish who the report is for before writing. A
  report the user will forward to the builder gets a cover note addressed
  to them (TO / FROM / RE routing block), honest effort visible on every
  page, and an offer to re-run on request. A private log gets neither.
  Ask when unknown rather than guessing.
- **Composition, not camps.** When two tools win in non-overlapping scopes
  (e.g. in-process bus vs networked broker), recommend the composition
  with its bridge — which layer each owns, what the bridge agent holds —
  never a winner.
- **When/why, not just what.** Every comparison and every usage fit is
  framed as when the reader would reach for it and why, ranked. A table
  without a take is unfinished.
- **The reviewer's scorecard.** Score adjacent tools reviewed statically
  (9/10 inside scope, 0/10 outside it), and attach an evidence note
  whenever a side was verified from source/artifacts rather than live
  exercise — including why (e.g. live exercise would burn real tokens).
- **Absence is evidence only after a grep.** 'No A2A support' means a
  tree-wide search returned nothing. Same for idempotency keys,
  expiry-notify paths, frame auth.
- **Label every number by method.** Measured (port + backend + sample),
  default (config/handler cite), or projection (labeled as such — a small
  probe is never presented as a soak).
- **Docs are a hypothesis; code is the verdict.** Read the docs first —
  they tell you what to probe — but never assert a docs claim until the
  handler, the wire, or the run confirms it. Docs can lie (stale flags,
  aspirational features, copied examples); code never lies. When docs and
  code disagree, the disagreement itself is a finding: quote both.
  The rare inverse — docs that confess their own gaps — is the strongest
  trust signal a project can send; say so when you find it.
- **Install, don't skip.** If the user names a skill the harness lacks,
  install it (skills CLI, global-first, local fallback) and follow it.
  Producing the artifact without the named method is failure.

## Procedure

1. **Clone and read.** Clone into a fresh scratch dir (`/tmp/<name>-review` —
   clone fresh rather than deleting an existing checkout). Read the README,
   quickstart/tester guide, and architecture docs; note the claimed features
   and the project's own happy-path commands.
2. **Build via the project's front door.** Prefer its Makefile/build script;
   fall back to Docker only if native build fails. Record build time, artifact
   size, and any linter/vet signal.
3. **Run on a scratch port and prove liveness.** Pick a high scratch port,
   confirm it is free first (`ss` check — never measure against someone
   else's server), start the server with `background=true` (a foreground
   command with `&` is rejected — background it, then health-check in a
   follow-up call), and assert `/health` answers from the process just
   started. Pair the start with the project's stop mechanism (pidfile,
   `make stop`) so cleanup is one command.
4. **Exercise the core loop live.** Follow the project's own quickstart:
   register/auth, one happy-path round-trip, one negative test (bad auth /
   missing credential), and a small latency sample. Capture the real terminal
   output verbatim for `<pre>` blocks — transcripts, not paraphrases. When the report will make scaling claims, run a
  bounded load probe on a second scratch port (register ~100 agents, fire
  a few hundred requests, report msgs/s and what broke) — one small real
  number beats a large projected one, and anything beyond the probe stays
  labeled projection.
5. **Map the surface.** Enumerate real routes (OpenAPI `paths` keys or the
   route table — never the marketing list); record source vs test file
   counts and a vet-class signal (`go vet`, typecheck, lint); list what
   was deliberately NOT exercised, by name. Verify negative claims ('no
   A2A support', 'no idempotency keys') with a tree-wide search before
   asserting them — an absence never grepped for is an impression.
6. **Compare against incumbents.** One table: the project vs the 3–5 tools a
   practitioner would actually pick instead, on the dimensions that matter
   for the job (ops weight, auth model, durability, maturity). One-line take
   saying when to pick it and when to pick the incumbent. When the user names
   one of their own adjacent tools for comparison, verify it from the local
   install first (installed version, binary strings, local state) and the
   upstream source tree — aggregator wikis truncate and lag; the artifact on
   disk is the claim that counts. When both tools win in non-overlapping
   scopes, recommend the composition with its bridge, not either/or.
7. **Deep dive (agent-messaging targets, or on request).** For anything that
   moves messages between agents, add all five lenses:
   (a) **Wiring & protocols** — enumerate every hook-in door (MCP tools by
   name, raw HTTP/WS surface, skill files, SDKs); grep the tree for A2A /
   ACP / AgentCard support and report presence AND absence; document how
   agents discover the bus and when each lane is the right one.
   (b) **Push vs poll** — per lane, verified in code: which lanes push
   (WS subscribe, mesh frames, webhook POST + retry/backoff policy) and
   which only answer polls (inbox retrieve params: a wait/block param
   existing or not; MCP polling comments). Name the gap when the durable
   lane can't wake sleepers.
   (c) **Scale probe** — run a bounded load pass (e.g. register ~100 agents,
   deliver ~500 messages, report wall time and msgs/s) on a scratch port;
   record rate caps, lease/batch/TTL defaults from config + handler code;
   name what breaks toward 1000 (single process, connection fanout,
   namespaces/tenants, presence honesty). Never present a small probe as a
   soak — label projections as projections.
   (d) **Task ownership** — how claims work (lease+ack, visibility-timeout
   family) and the verified edge gaps: idempotency keys (grep), silent
   TTL-expiry drops (grep for expiry-notify paths), transfer/reassign,
   priority lanes, DLQ.
   (e) **Incident observability** — inventory what the bus exposes
   (audit trail or its absence, metrics, status, failure receipts, guard
   verdict surfacing) and map it against a named real incident's kill
   chain: what would have been attributed, blocked, detected, missed.
   Research the incident from primary sources (never from memory), and
   say plainly when the answer is 'attributed afterward, not detected
   during'.
8. **Improvements from prior art.** Ranked add/change list, each item
   tracing to a verified finding or a named precedent. Research the
   adjacent ideas for real (WAMP/crossbar, A2A, MCP Tasks/notifications,
   XMPP presence, Celery visibility timeouts, Temporal, Matrix, NATS
   JetStream) — cite what to steal, not vibes.
9. **Good/bad from evidence.** Good = strengths actually verified live.
   Bad = rough edges actually hit, plus documented caveats that change the
   adoption decision. Quote the error or output, not the impression.
10. **Usage: concrete where/how.** Ranked fits with a sentence each on how it
   would be deployed, plus what to verify or harden before trusting it.
11. **Design, then write the HTML report, then clean up.** Load
   frontend-design (plus any installed polish/critique skill) and follow
   it — the report is a designed artifact, not a filled template. Single
   self-contained file, inline CSS, sections: what-it-is · live output
   (real transcripts in `<pre>`) · comparison · [agent-messaging targets:
   wiring · push-vs-poll · scale+ownership · incident-observability ·
   improvements] · good · bad · usage ·
   verdict. Validate markup parses clean, then audit the render
   mechanically rather than by eye (overflow, contrast math, font-load
   state — see references/verify-render.md); screenshot with headless
   chrome directly when the harnessed browser capture hangs — infinite CSS
   animation keeps it from settling. Send via `MEDIA:<path>`, then stop scratch servers and confirm the port is free.

## Rules

- Report only output actually observed; label anything untested as
  not-exercised. A passing test suite elsewhere is not evidence here.
- Match the evidence method to its cost: when live exercise would spend real
  money (LLM-driven paths) or need a second party (federation, org-to-org),
  verify statically from source and installed artifacts and label the
  evidence level in the report — never burn budget to prove transport.
- A guessed endpoint or flag that fails is a finding about discoverability,
  not a failure of the run — record the wrong guess and the right shape.
- Pin the exact commit tested in the report footer with toolchain, date, and
  port so the verdict is reproducible.
- When a full redesign must replace the report file and the writer refuses
a stale overwrite, write the new version to a sibling path and move it
over — never rebuild the file piecemeal to dodge the guard.
- Template starter shell: `templates/review-report.html` — copy and fill,
  keep the section order, including the cover-note block when forward-ready.
