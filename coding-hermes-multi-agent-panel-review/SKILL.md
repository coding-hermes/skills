---
name: coding-hermes-multi-agent-panel-review
description: Decide or verify with a panel of 3-5 diverse full Hermes sessions — every judge verifies every claim against a shared claim-checklist, then one strong-model deep-review. Use before approving money gates, specs, redesigns, or any evidence-heavy deliverable.
version: 2.0.0
author: totalwindupflightsystems
license: MIT
metadata:
  hermes:
    tags: [verification, judges, panels, multi-agent, decision-review]
---

# Multi-Agent Panel Review — process-first judge panels

One reviewer has one blind spot. Dispatch 3-5 **diverse** models as independent
full Hermes sessions (own process, full tools, own clock). **Every judge
verifies EVERY claim** — the shared CLAIM CHECKLIST is the unit of work, never
a per-judge slice. Diversity supplies different *error-class emphasis*, not a
division of labor. Every judge returns
`[VERIFIED|CONTRADICTED|UNRESOLVED]` per claim with file/line evidence. The
coordinator then re-verifies every CONTRADICTED lead against raw data before
merging. This is review-and-decide for: money gates, specs, architecture
redesigns, post-mortems, "did we repeat the same mistake" audits.

Not for: quick subtasks (use delegation), single Q&A synthesis (use a
deliberation MCP), or worker coding dispatch (that is a worker, not a judge).

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
failure class.

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
files. A panel may mix transports.

**A. CLI (`hermes chat`) — interactive-adjacent, simple, per-process.**

```bash
hermes chat -q "$(cat /tmp/panel-brief.txt)" -m <model> --provider <p> \
  --ignore-rules -Q > /tmp/review-j1.txt 2>&1
```

Good for: small panels, when you want each judge in its own OS process with
its own workspace. Long briefs go in a file referenced by path; huge inline
`-q` strings trip outer command gates and the launch silently never happens.

**B. HTTP gateway (`POST /v1/responses`) — the unattended/batch path.**

The same gateway the scheduler uses for fleet ticks. One long-lived gateway,
N concurrent judge requests, no per-judge process management:

```bash
curl -sS -X POST "$GATEWAY_URL/v1/responses" \
  -H "x-api-key: $GATEWAY_KEY" -H "Content-Type: application/json" \
  -d "$(jq -n --rawfile b /tmp/panel-brief.txt \
        '{model: $model, input: $b}')"
```

Auth is the `x-api-key` header (Bearer gets 401). Good for: batch panels,
containerized judges, anything the scheduler would run unattended — the
transport the fleet already trusts for its own ticks. Verify the gateway
resolves the model lane BEFORE fanning out (one probe request per lane; a
stale key kills whole fan-outs — see pitfalls).

Either transport: run judges in parallel (10-25 min), write to separate
output files, and never share state between judges — independence IS the
method. If a judge cannot complete: an unfinished review is a failed review.

## Brief anatomy (claim checklist, not vibes)

1. **Stakes** — what breaks if the review is wrong; prior failure classes by name.
2. **File paths** — "read the actual files, do not review from memory."
3. **Numbered claims grouped by doctrine** — each phrased as a verify-me claim
   with expected value; include the strongest model's repeat-offense section:
   "What in THIS artifact causes the SAME failure classes again? (a) credential
   paths, (b) success-marker string checks, (c) state ladders, (d) silent-skip
   paths, (e) fixes that weaken requirements to fit a lane, (f) green-but-did-nothing."
4. **Output format mandated, in order** — verdicts per claim with evidence,
   corrections ranked, new verified facts, top-N fixes ranked. End with a
   truncation detector line (`PANEL REVIEW COMPLETE`).
5. **Deliverable-first budget rule** — verdict sections are MANDATORY; cap
   verification experiments (1 for deep-review, ~3 for judges); an unfinished
   review is a failed review. Research-rich/report-poor sessions are the
   #1 panel killer.
6. **Pre-run every command the brief prescribes** — judges execute verbatim;
   one broken expected value converts the round into false-CONTRADICTED noise.

## Merge discipline (coordinator's job)

1. **A judge claim is a LEAD, not a fact.** Re-verify every CONTRADICTED item
   against raw data yourself before acting.
2. **Expect 3-5 CONTRADICTED per round** — that is the round working. The
   round that finds nothing found nothing.
3. **Convergence is load-bearing**: independent families flagging the same
   item (especially the coordinator's own draft) outrank any single verdict.
4. Resolve judge-vs-judge conflicts at the primary source; label every merged
   number with its evidence class; keep each claim's falsifier ("would change
   if: ...") for the next round.
5. Two rounds for approval artifacts: round 1 fresh critique; round 2 verifies
   the FIXES landed (brief lists each merged fix). Build vN+1 only after round 1.

## Fleet tiering (large N)

Full 5-judge panels ONLY on money gates (top spend/activity). Long tail:
2 judges. Batch panels: per-target output schemas, fixed output files, and a
parser that fails loudly on missing detector lines.

## Top pitfalls

- **The fix that repeats the sin** — lowering requirement bars to fit a fallback
  is the relocated version of hardcoding answers. Restore the spec; mark the
  fallback DEGRADED explicitly.
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
- **Hardcoded numbers in generators** — a number that cannot be recomputed from
  the data layer is a bug, not a finding. Judges should audit the generator.
- **Example-lane rot** — any model/provider pair written in a brief, runbook,
  or skill is an INSTANCE, not doctrine. Before dispatch, re-derive the lane
  set from the live registry; if the registry disagrees with the example, the
  registry wins and the example is already wrong.
