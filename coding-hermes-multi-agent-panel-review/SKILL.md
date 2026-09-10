---
name: coding-hermes-multi-agent-panel-review
description: Decide or verify with a panel of 3-5 diverse full Hermes sessions — claim-checklist judge rounds plus a single strong-model deep-review. Use before approving money gates, specs, redesigns, or any evidence-heavy deliverable.
version: 1.0.0
author: totalwindupflightsystems
license: MIT
metadata:
  hermes:
    tags: [verification, judges, panels, multi-agent, decision-review]
---

# Multi-Agent Panel Review — full Hermes sessions as judges

One reviewer has one blind spot. Dispatch 3-5 **diverse** models as independent
full Hermes sessions (own process, full tools, own clock), each with a
CLAIM CHECKLIST — never an open critique. Every judge returns
`[VERIFIED|CONTRADICTED|UNRESOLVED]` per claim with file/line evidence. The
coordinator then re-verifies every CONTRADICTED lead against raw data before
merging. This is review-and-decide for: money gates, specs, architecture
redesigns, post-mortems, "did we repeat the same mistake" audits.

Not for: quick subtasks (use delegation), single Q&A synthesis (use a
deliberation MCP), or worker coding dispatch (that is a worker, not a judge).

## The two modes

**Parallel judge round (3-5 models).** One shared claim-checklist brief, one
session per model, outputs to separate files. Diversity is the point —
different model families catch different error classes (arithmetic, roster,
official-docs, structural).

**Deep-review (1 strongest model).** When the stakes are "what is STILL wrong
/ did this repeat past failures", one super-smart model with a repeat-offense
section finds deeper issues than any parallel round — especially the coordinator's
own recent "fix" reintroducing the banned failure class.

## Model selection (verify lanes first, never from memory)

Check the model routing registry for live lanes before dispatch; subs before
PAYG. A proven diverse set:

| Role | Model @ provider (example lanes) |
|---|---|
| Deep-review | strongest available reasoning lane (e.g. gpt-6-astra @ openai-codex) |
| Facts/numbers | k3 @ kimi-for-coding |
| Arithmetic/fit | glm-5.3 @ zai-glm |
| Docs contradictions | deepseek-v4-pro @ deepseek |
| Fifth reviewer | qwen3.8-max @ opencode-go (spare: grok-4.5 @ grok-build) |

All five lanes must exist in the registry before launch. If a lane flakes
mid-round, substitute the spare rather than re-running the same family.

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

## Dispatch pattern

```bash
# Write ONE brief per mode; reference it by file, never inline
hermes chat -q "$(cat /tmp/panel-deep-brief.txt)" -m <strong-model> --provider <p> --ignore-rules -Q > /tmp/review-deep.txt 2>&1
hermes chat -q "$(cat /tmp/panel-brief.txt)" -m <judge-1> --provider <p1> --ignore-rules -Q > /tmp/review-j1.txt 2>&1
# ... one per judge; all with background + completion notify
```

- Long briefs go in a file referenced by path; huge inline `-q` strings trip
  outer command gates and the launch silently never happens.
- Run all judges in parallel (background); they take 10-25 min.
- On completion, check each output **ends with the detector line**; a session
  id with no verdict above it = relaunch with the budget rule.
- Collect or kill orphans: interrupted rounds leave background judges burning
  tokens — `pgrep -f "hermes chat"`, harvest finished outputs, kill stragglers,
  and state which verdicts never returned.

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
  in the execution env for ALL lanes before launching five sessions.
- **Judge reviews the wrong version** — point the brief at an explicit file
  path; a judge dispatched at vN reports on vN.
- **Tautological tests** — a regression test that cannot fail is a lie.
- **Failure storms hide in totals** — check failed/timeout counts before any
  capacity or success-rate claim.
- **Hardcoded numbers in generators** — a number that cannot be recomputed from
  the data layer is a bug, not a finding. Judges should audit the generator.
