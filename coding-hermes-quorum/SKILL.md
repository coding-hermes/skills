---
name: coding-hermes-quorum
description: "Use when Bane says quorum — convene judge seats to decide."
version: 3.0.0
author: totalwindupflightsystems
license: MIT
metadata:
  hermes:
    tags: [verification, judges, quorum, multi-agent, decision-review, 定足数]
    related_skills:
      - coding-hermes-bankai
      - coding-hermes-plus-ultra
      - coding-hermes-worker-model
---

# 定足数 QUORUM — The Fixed Number

## 定足数の精神 — The Philosophy of the Fixed Number

**Quorum** is three layers of meaning, all real:

- **Latin: quorum** — the genitive plural of *qui*, "of whom." Medieval England,
  royal commissions of the peace: a commission could name twenty justices, but
  its last line carried the power — *quorum unum esse volumus*, "of whom we
  will [these] to be one." The named few were the **Justices of the Quorum**:
  without one of them present, the rest could not act. The word never meant
  "the whole group." It is the answer to *of whom must at least one be
  present* for the body to be real.
- **Japanese: 定足数 (teisokusū)** — the "fixed sufficing number": 定
  (fixed, settled) + 足 (to suffice) + 数 (number). 定 is the character inside
  決定 (decision), 判定 (verdict), 安定 (stability), 制定 (establishment). A
  meeting below its 定足数 is not a smaller meeting — it is NO meeting.
  Anything it "passes" never happened.
- **Distributed systems** — Raft, Paxos, Cassandra: a cluster commits a write
  only when a quorum of nodes acknowledges. A lone node's write is not a
  minority opinion; it is UNCOMMITTED — and a cluster that accepts it anyway
  has split brain. Quorum is the mechanism that makes many independent
  machines behave as ONE.

**This is the mode:** one reviewer has one blind spot, and one model family's
verdict — however confident — has not met quorum. When Bane says **quorum /
定足数**, Hermes convenes 3-5 **diverse** full Hermes sessions (own process,
full tools, own clock), every judge verifies EVERY claim against one shared
CLAIM CHECKLIST, and the coordinator merges — re-verifying every CONTRADICTED
lead against raw data before anything is ruled. Diversity supplies different
*error-class emphasis*, never a division of labor. Convergence across
independent families is the only thing that counts as the decision existing.
This is review-and-decide for: money gates, specs, architecture redesigns,
post-mortems, "did we repeat the same mistake" audits.

Bankai finishes the battle. Plus Ultra leaves the system better. **The Quorum
decides whether the battle was won at all.**

Not for: quick subtasks (use delegation), single Q&A synthesis (use a
deliberation MCP), or worker coding dispatch (that is a worker, not a judge).

## The Convening Command

**Trigger:** the keyword "quorum" / "定足数" / "convene the quorum" on a
decision, a gate, or a deliverable.

- **Stakes named** → run the round: build the claim-checklist brief, select
  lanes by the process below, fan out, merge.
- **Bare "quorum"** → find the matter awaiting judgment: the artifact staged
  for approval, the gate awaiting sign-off, the deliverable a prior session
  left unmerged. If no matter is live, ask what is being decided — **no brief,
  no round**: convening without a claim checklist produces a debate club, and
  debate is not verdicts.

Proven at fleet scale: the ~81-skill sibling-group rewrite program runs on
this method (coding-hermes-skills-program), as do the fleet's money-gate
audits and PRD red-teams.

## The two modes

**Parallel judge round (3-5 models).** One shared claim-checklist brief, one
session per model, outputs to separate files. Every judge works the full
checklist. Convergence between different model families is the signal —
different families catch different error classes (arithmetic, roster,
official-docs, structural) because of *emphasis*, never because a claim was
assigned to them.

**Deep-review (1 strongest available model).** When the stakes are "what is
STILL wrong / did this repeat past failures", one strong model with a
repeat-offense section finds deeper issues than any parallel round —
especially the coordinator's own recent "fix" reintroducing the banned
failure class. This is the Justice of the Quorum seat: the named one without
whom the rest cannot act when the question is *have we sinned again*.

## What counts as decided (the quorum arithmetic)

- **One family's verdict never meets quorum** — it is a lead, not a ruling.
- **A CONTRADICTED flagged independently by two-plus families has met
  quorum** — especially against the coordinator's own draft. Fix it, then
  verify the fix landed (round 2 lists each merged fix).
- **The coordinator's raw-data re-check is the commit layer.** Judge verdicts
  are proposals; only the coordinator's own verification against the primary
  source commits them.
- **A round that reports zero CONTRADICTED found nothing.** 3-5
  CONTRADICTED per round is the round working.
- **UNRESOLVED is an honest verdict.** Silence is not.

## Model selection — a PROCESS, not a roster

Do not copy model names from any example, including this skill's history.
Diversity is the requirement; specific lanes are disposable instances:

1. **Verify lanes live, never from memory.** Query the model routing registry
   for lanes that exist and authenticate RIGHT NOW. A stale example lane that
   401s converts the round into relaunch noise.
2. **Pick for family diversity, not scoreboards.** 3-5 lanes from >=3 distinct
   model families. The same family twice adds less than a new family once.
3. **One clearly-strongest lane is the deep-review seat** — identified by
   checking the registry, not by habit. If no lane stands out, run the
   parallel round only.
4. **Substitution law.** A lane that flakes mid-round is replaced by another
   lane of a DIFFERENT family — never by "whatever is fastest".
5. **Roles are lenses, not assignments.** "Facts/numbers" or "docs
   contradictions" describe what a given family tends to catch first; every
   judge still receives and works the ENTIRE checklist.

## Transports — two ways to run a judge session

Pick per run; both carry the identical brief and return identical verdict
files. A round may mix transports.

**A. CLI (`hermes chat`) — interactive-adjacent, simple, per-process.**

```bash
hermes chat -q "$(cat /tmp/quorum-brief.txt)" -m <model> --provider <p> \
  --ignore-rules -Q > /tmp/review-j1.txt 2>&1
```

Good for: small rounds, when you want each judge in its own OS process with
its own workspace. Long briefs go in a file referenced by path; huge inline
`-q` strings trip outer command gates and the launch silently never happens.

**B. HTTP gateway (`POST /v1/responses`) — the unattended/batch path.**

The same gateway the scheduler uses for fleet ticks. One long-lived gateway,
N concurrent judge requests, no per-judge process management:

```bash
curl -sS -X POST "$GATEWAY_URL/v1/responses" \
  -H "x-api-key: $GATEWAY_KEY" -H "Content-Type: application/json" \
  -d "$(jq -n --rawfile b /tmp/quorum-brief.txt \
        '{model: $model, input: $b}')"
```

Auth is the `x-api-key` header (Bearer gets 401). Good for: batch rounds,
containerized judges, anything the scheduler would run unattended — the
transport the fleet already trusts for its own ticks. Verify the gateway
resolves the model lane BEFORE fanning out (one probe request per lane; a
stale key kills whole fan-outs — see pitfalls).

Either transport: run judges in parallel (10-25 min), write to separate
output files, and never share state between judges — independence IS the
method. If a judge cannot complete: an unfinished review is a failed review.

## The wave loop — every judge does EVERY stage (owner-corrected)

Seat specialization is the wrong shape for knowledge work: it pools each
stage's quality at a single model's ceiling. The validated pattern runs a
WAVE LOOP where the SAME 5 diverse models each execute EVERY stage — per
wave: every model drafts, every model reviews the other drafts against the
claim checklist, every model verifies its own change list landed — then ONE
merge seat consolidates convergent wordings, applying each model's OWN
wording verbatim and citing which model supplied each fix.

Diversity is preserved ACROSS models; quality is preserved WITHIN each stage
because every stage gets all five models' intelligence.

Rules:
- Stage output count = models x waves, not seats. Name artifacts
  `w<wave>-<stage>-<model>.log` so the wave structure is auditable from the
  filesystem.
- Never let a single model own a stage; a model too weak to draft still
  reviews and verifies that wave.
- Merge is the only single-occupant seat; it invents nothing and attributes
  everything.
- Iteration = wave+1 with the merge conflicts as the round's change list.
- Scale-down keeps the property: fewer models means all-models-do-everything
  with fewer models — NEVER a return to specialist seats.

Pitfall: seat specialization silently reintroduces single-model ceilings. If
the plan names separate architect/scribe/judge agents, the pattern is already
broken — rename the seats to STAGES and assign every model to every stage.

## Brief anatomy (claim checklist, not vibes)

1. **Stakes** — what breaks if the review is wrong; prior failure classes by
   name.
2. **File paths** — "read the actual files, do not review from memory."
3. **Numbered claims grouped by doctrine** — each phrased as a verify-me
   claim with expected value; include the strongest model's repeat-offense
   section: "What in THIS artifact causes the SAME failure classes again?
   (a) credential paths, (b) success-marker string checks, (c) state ladders,
   (d) silent-skip paths, (e) fixes that weaken requirements to fit a lane,
   (f) green-but-did-nothing."
4. **Output format mandated, in order** — verdicts per claim with evidence,
   corrections ranked, new verified facts, top-N fixes ranked. End with the
   truncation detector line (`PANEL REVIEW COMPLETE` — legacy string kept so
   existing parsers keep working).
5. **Deliverable-first budget rule** — verdict sections are MANDATORY; cap
   verification experiments (1 for deep-review, ~3 for judges); an unfinished
   review is a failed review. Research-rich/report-poor sessions are the #1
   round killer.
6. **Pre-run every command the brief prescribes** — judges execute verbatim;
   one broken expected value converts the round into false-CONTRADICTED noise.

## Merge discipline (the coordinator is the commit layer)

1. **A judge claim is a LEAD, not a fact.** Re-verify every CONTRADICTED item
   against raw data yourself before acting.
2. **Convergence is load-bearing**: independent families flagging the same
   item (especially the coordinator's own draft) outrank any single verdict.
3. Resolve judge-vs-judge conflicts at the primary source; label every merged
   number with its evidence class; keep each claim's falsifier ("would change
   if: ...") for the next round.
4. Two rounds for approval artifacts: round 1 fresh critique; round 2 verifies
   the FIXES landed (brief lists each merged fix). Build vN+1 only after round 1.
5. **A convergence brief can name files that do not exist** (e.g. sibling
   red-teams named `<seat>/redteam-<my-skill>.md` when each seat actually
   red-teamed a different skill). Resolve inputs by listing the seat
   directories first; if the named path is absent, use the real artefact that
   carries the same ruling and disclose the substitution in the merge ledger —
   a silently skipped red-team loses its verdicts.
6. **Hit line budgets by density, not by cutting doctrine**: one statement per
   (unwrapped) line so the same content occupies ~1/3 the lines, and put every
   verdict in a disposition table (accepted / accepted-amended / rejected +
   one-line why). Rejections need a reason stronger than style; "stale doc
   table" is a reason, "I prefer the other wording" is not.

## Fleet tiering (large N)

Full 5-judge rounds ONLY on money gates (top spend/activity). Long tail:
2 judges. Batch rounds: per-target output schemas, fixed output files, and a
parser that fails loudly on missing detector lines.

## Top pitfalls

- **The fix that repeats the sin** — lowering requirement bars to fit a
  fallback is the relocated version of hardcoding answers. Restore the spec;
  mark the fallback DEGRADED explicitly.
- **Text-as-state** — success markers, parsed hashes, and log-line greps are
  diagnostics, never truth. Prefer exit codes, host-derived identity, and
  structured output.
- **Unrepresentable failure** — if the store/journal cannot record "failed",
  every downstream count lies (100% green is meaningless). Fix representation
  before patching symptoms.
- **Stale credentials kill whole fan-outs** — verify the provider key resolves
  in the execution env for ALL lanes before launching five sessions (CLI:
  provider env; gateway: the key actually answers one probe call).
- **Judge reviews the wrong version** — point the brief at an explicit file
  path; a judge dispatched at vN reports on vN.
- **Tautological tests** — a regression test that cannot fail is a lie.
- **Failure storms hide in totals** — check failed/timeout counts before any
  capacity or success-rate claim.
- **Hardcoded numbers in generators** — a number that cannot be recomputed
  from the data layer is a bug, not a finding. Judges should audit the
  generator.
- **Example-lane rot** — any model/provider pair written in a brief, runbook,
  or skill is an INSTANCE, not doctrine. Before dispatch, re-derive the lane
  set from the live registry; if the registry disagrees with the example, the
  registry wins and the example is already wrong.
- **Headless seats die on approval floors** — a `hermes chat -q --ignore-rules`
  seat whose brief tells it to spawn servers, background processes (`&`),
  docker, or ssh trips an approval floor and is SIGTERM'd at approvals.timeout
  (300s) with nobody home. Whole rounds can die in sync (all logs ~45 bytes,
  `exit=143`) while a seat whose brief spawns nothing survives — when only one
  seat lands, diff the briefs for spawn instructions before blaming lanes.
  Keep headless-seat briefs inside the no-approval envelope: read/grep/parse
  only, with live-behavior facts pre-supplied by the coordinator (run the
  commands yourself first and embed outputs as ground-truth "pre-run facts"
  the seats may trust).

## Doctrine — the Quorum Does Not Suspend the Rules

- **chat = PAYG, work = subs** — judge seats are work: ride the subs
  (opencode-go / flat-rate lanes / openai-codex), never DeepSeek PAYG.
- **Verify with evidence** — a verdict without file/line evidence is a vibe;
  a judge that cannot cite where it looked did not look.
- **No brief, no round** — a convening without a claim checklist is an
  audience, not a quorum.
- **The round ends** — merge, re-verify, disposition table, report, and
  dissolve the seats: `pgrep -f "hermes chat"`, harvest finished outputs, kill
  orphans (interrupted rounds leave judges burning tokens). Don't linger in
  round 3.
- **Below quorum, nothing happened** — if independence or diversity collapsed
  (one family, shared state, unverified leads committed), the round did not
  fail to reach a verdict; it never convened. Say so.
