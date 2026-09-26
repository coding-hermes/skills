---
name: coding-hermes-retrospective-self-improvement
description: "Use when the owner says the agent is being stupid about work, is flailing/guessing, or says plan it / subgoals / verify — the full chain: problem → quorum → goal → subgoals → per-subgoal verify → quorum verify."
version: 3.1.0
author: totalwindupflightsystems
license: MIT
metadata:
  hermes:
    tags: [planning, self-improvement, retrospective, verification, quorum, evidence, chain, intervention, 改善]
    related_skills:
      - coding-hermes-quorum
      - coding-hermes-spec-lifecycle
      - coding-hermes-bankai
      - fleet-retrospective
---

# 改善 KAIZEN — the Chain

**改善 (kaizen)** is not "improvement" as a mood. 改 is the character in 改革 (reform); 善 is
goodness, and in the compound it comes *after* the 改 — you do not get the good part without the
looking-back part. The chain is the skill.

## WHAT THIS IS FOR — the owner's circuit breaker

This skill exists to be **invoked on an agent that is being stupid about work**. The owner calls
it by name when the agent is guessing, thrashing, doing the task without understanding it,
manufacturing plausible answers, or marking things done that only exist as code. It is not a
planning preference; it is a **process the agent is required to run instead of whatever it was
about to do**.

The premise: most bad work is not a capability failure, it is a *process* failure — the agent
skipped the reading, skipped the premise check, or graded itself. The chain removes the option to
skip.

> **When this is invoked, the agent stops improvising and runs the chain.** No new work from
> memory. No new plan from a summary. The first move is always the same: go read the actual
> artifacts.

### The agent's obligation when this fires

1. **Stop.** Do not finish the half-formed thing you were doing from memory. Do not defend it.
2. **Name the failure mode you were in**, in one line and without euphemism — guessing,
   not-read-the-artifact, thrashing, built-read-as-done, answering-from-summary, or flailing
   without a goal. Naming it is what makes the process real instead of theatrical.
3. **Run the chain from Stage 1**, in order, with the gates. If you cannot fill a stage, that is
   a finding — say which piece is missing rather than filling the gap with a plausible invention.
4. **Report stage by stage**, and include the section the chain forces: *what did not move*.
5. **Do not declare done.** The chain decides that, through the falsifier and Quorum #2.

## THE CHAIN

```
  user / problem / task
        │
        ▼
  ┌─────────────────┐
  │ QUORUM  #1      │  build the RAW DETAILS before any plan exists.
  │ (independent    │  Attack the premise, not the wording. Output: facts with
  │  families)      │  evidence classes + the explicit unknowns.
  └─────────────────┘
        │
        ▼
     GOAL  +  FALSIFIER        one sentence each: what "done" means, and the
        │                      measurement that would show it is NOT met.
        ▼
   SUBGOALS  (each: done-when · evidence · depends-on · falsifier)
        │
        ▼   ┌──────────────────────────────────────────────┐
        ├──▶│ SUBGOAL VERIFY  (per subgoal, immediately)   │  the EFFECT, not
        │   │  measure the outcome the subgoal predicted   │  the code. Not
        │   └──────────────────────────────────────────────┘  "the field was
        │                        │                             added".
        │                        ▼
        │                  ↻ next subgoal (smallest-first; commit proven work at once)
        │
        ▼
  ┌─────────────────┐
  │ RE-EVALUATE     │  the LAST subgoal is always this: re-run every original
  │ (the last        │  measurement, before vs after, and account for what did
  │  subgoal)        │  NOT move.
  └─────────────────┘
        │
        ▼
  ┌─────────────────┐
  │ QUORUM  #2      │  verify the RESULT and the re-evaluation — not the intent.
  │ (independent    │  Convergence is the signal; the coordinator re-verifies
  │  families)      │  every CONTRADICTED item against raw data (commit layer).
  └─────────────────┘
        │
        ▼
        │
        ├── FAIL ──▶ back to SUBGOALS: add subgoals that FIND the problem and
        │            RESOLVE it, then RE-APPEND the verification subgoal at the
        │            end. The verification subgoal is never consumed by running
        │            it — it is re-added after every failure until something
        │            passes.
        │
        └── PASS ──▶ DONE — and only when the FALSIFIER is settled.

  QUORUM #2 failing is the SAME SHAPE one level up: it relaunches the same goal
  (or derives a new one), the tree gains subgoals with a verification subgoal at
  the end, and when that tree believes it passes it comes BACK TO THE QUORUM.
  The two loops are one loop at two altitudes, and a verified pass is the only
  exit.
```

**Two quorums, and they are not the same review.** #1 runs *before* the plan exists — it stops you
building on a wrong premise, and it is the cheap one. #2 runs *after* the result exists — it is
the commit layer. A single family's verdict is a lead, not a ruling, at either one.

## Name and aliases

- **Canonical name:** `coding-hermes-retrospective-self-improvement` (correct spelling —
  *self-improvement*, hyphenated). The earlier spelling `coding-hermes-retrospective-selfimprovement`
  and the display name **改善 Kaizen** both name THIS skill; never create a second copy of it.
- **Search before you build.** Before creating or rebuilding a skill, a plan, or a board row,
  search the board (`tasks.jsonl`), the skills repo, and the session history FIRST. A
  "COST-PER-TASK ENGINE" and a "STATS ENGINE V2" were once re-derived as new work while they
  already existed, and this very skill was duplicated the same way — planning from memory, one
  level up.

## When this fires

- **The owner calls it on the agent** — "you're being stupid about this", "run the chain", "stop
  guessing", "plan it / outline it / make subgoals / verify it / don't just do the task", or the
  skill named directly. This is the primary trigger.
- The request has more than one moving part and no plan yet ("wire X to Y and get the metrics
  lined up").
- The owner says the plan must **reflect again** when it is done, or asks for a **quorum** on a
  plan or a result.
- **Self-trigger:** you catch yourself about to answer from memory instead of the artifact, or
  you cannot say where your last three facts came from. That is the moment this exists for.

Not for a single-step lookup or a one-line question. Ceremony is not improvement.

## 改善第零条 — the iron law of every stage: facts before claims

**Talking from the ass** is the failure class this whole chain exists to kill: asserting a cause,
a count, or a status from memory, from a prior summary, or from how the system "obviously" works,
without reading the thing itself.

1. **Read the artifact, not the summary of it.** A compaction summary, a memory entry, and a
   previous session's report are *claims about* the artifact — never the artifact.
2. **Name the evidence class** of every claim: measured (a command you ran, with output) /
   documented (path + line) / inferred (say so) / unmeasured (say so). Never let two wear the same
   costume.
3. **The live artifact wins.** When memory disagrees with the running system, the system is right
   and the memory is stale. Say which one you trusted.
4. **Test the hunch before acting on it.** A hypothesis is not a finding; find the measurement
   that would kill it and run that one first.
5. **A prior conclusion is a lead, not a fact.** Re-derive it or label it inherited. Work has been
   marked complete with its effect absent.

Gate at every stage: **can every factual sentence be traced to a path, a command, or a
measurement?** If not, it is a draft of a wish.

## Stage 1 — QUORUM #1 (raw details, before the plan)

Gather from the sources that already hold the material: live stores (DB, logs, registry, config);
the board rows that describe the work (their reasoning field usually names the intended *effect*
and the evidence that would prove it); the repo docs that define the contract. Then convene
`coding-hermes-quorum` and let independent families attack those raw details.

The owner's rule: **use the quorum first to build the raw details, then the goal with the
subgoals.** A quorum before the plan costs one round; a plan built on a wrong premise costs a
week.

Produce: facts with evidence classes · the explicit unknowns · the questions the plan must answer.

## Stage 2 — GOAL

One sentence. Plus the **falsifier**: the measurement that shows the goal is not met. A goal
without a falsifier cannot be finished, only abandoned. Write what "done" looks like from outside
— a number that changes, a question someone can answer — never "the feature exists".

## Stage 3 — SUBGOALS

```
SG-n  <imperative title>
  done-when:  <checkable condition, with the command that checks it>
  evidence:   <artifact path the proof will live at>
  depends-on: <SG-x | none>
  falsifier:  <what would show this subgoal is unnecessary or wrong>
```

Smallest decisive step first — prefer the subgoal that could kill the plan early. Watch for the
hidden edge: a subgoal that *precedes* another in the list but is actually a *precondition* of it.

## Stage 4 — SUBGOAL VERIFY (every subgoal, immediately)

Land one, verify it against its own done-when, commit proven work at once, then move. Never batch
three unverified changes and test the pile.

The dominant failure is **built read as done**: measure the *effect*, not the artifact's
existence. A field that was added is not a value that arrives; a mechanism that shipped is not an
outcome that appeared; a config flag is not a behaviour. Where a subgoal's check can pass while
nothing observable changes, the check is wrong — replace it with the outcome.

## Stage 5 — RE-EVALUATE (always the last subgoal)

1. Re-run the *same* measurement as Stage 1, now.
2. Compare: did the **effect** appear or only the **code**?
3. Verify each claim in your own plan against the artifact that should now carry it.
4. **Account for what did not move** — an honest "this did not improve" is a finding.
5. Derive the next subgoals from what the evaluation exposes, including negative results.
6. **On failure the tree re-opens — the verification subgoal is never consumed.** Add subgoals
   that FIND the cause and RESOLVE it, then **re-append this same verification subgoal at the
   end** and run the tree again. Repeat until it passes. Running the check is not discharging
   it; a failed check is an input, not an exit.

## Stage 6 — QUORUM #2 (verify the result)

Brief the families on the delivered artifact and the re-evaluation, never on your intentions.
Every judge works the whole claim checklist. Consensus between independent families is the signal;
one family is a lead. Re-verify every CONTRADICTED item against raw data yourself before accepting
it — the coordinator is the commit layer.

The highest-value output of the round is a CONTRADICTED against your own draft. That is the round
working.

**When the quorum fails, the whole chain re-enters one level up.** A failed quorum launches the
same goal — or derives a new one from the verdicts — re-runs Stage 3 to add subgoals including a
verification subgoal at the end, and when that tree believes it passes, it comes **back to the
quorum**. Nothing is declared done on the strength of the agent's own judgement; a verified pass
is the only exit.

**This can take an extremely long time to get going, and that is the design, not a bug.** The loop
converges by adding work each pass, never by lowering the bar. Expect many iterations; keep each
iteration legible (what failed, what was added, what changed) so a long run can be watched instead
of restarted; and never shorten it by calling a stage passed that has not passed.

## Stage 7 — the fixpoint law (grow, or pass)

The tree grows on every failure and stops for exactly one reason: **something passed.** Two failure
returns feed it — a failed *verification subgoal* (back to Stage 3) and a failed *verification
quorum* (back to Stage 2 to relaunch or re-derive the goal, then Stage 3). Neither is terminal:
both add subgoals that find and resolve the problem, and both re-append the verification stage at
the end.

If Stage 5 found nothing to add, that is usually a sign you re-read your own plan instead of
measuring the effect — not a sign you are done. Stop when the falsifier is settled, never because
the tree ran out of patience.

## Pitfalls (each cost real work)

- **The theory that died in the log.** A full causal case was built for a resource-allocation bug
  from arithmetic on paper; one log query returned the gate had fired **zero** times and the real
  constraint was elsewhere. Find the measurement that names the cause.
- **Code landed ≠ effect landed.** Mechanism built, deployed, marked complete — while a default
  left the effect unreachable. Reopen the row, keep the code, say why "complete" never showed up as
  working.
- **Stale counts dressed as findings.** A "never ran, oldest weeks ago" census was wrong: the lanes
  were days old and one had already run three times. Re-query; counts decay.
- **Legacy population read as current behaviour.** "Empty on all rows" described the historical
  set, not the current write path, which was already fixed. Ask *which population* first.
- **The plan built on a summary.** Compaction summaries drop the exact number you need. Go back to
  the store; never rebuild a plan on a paraphrase.
- **Pre-run facts get audited.** Reviewers will check your numbers, and one will be wrong
  sometimes — that is the method working. Pre-run every command so they verify instead of debug.
- **The switch that is a bet.** Do not flip a production default to prove a mechanism; run it in
  shadow (compute and record the new answer, serve the old one), then flip with the revert proven.
- **The tree that stops growing on a lie.** Nothing to add after Stage 5 usually means you re-read
  your plan instead of measuring the effect.
- **Verification consumed instead of re-appended.** A verification stage run once and then dropped
  turns a fixpoint into a single sample: the failure comes back as "we tried that" instead of as
  the next round's subgoals. If the check failed, the SAME check goes back on the end of the tree.
- **Shortening the loop to make it finish.** The convergence pressure on a long run is to declare a
  stage passed so the loop can end. That is the one move that makes the whole chain pointless — it
  produces a green result with an unsettled falsifier.

- **A capability marked complete because the CODE exists.** (Measured: a "COST-PER-TASK ENGINE"
  and a "STATS ENGINE V2" each sat `complete` on the board while the ordering they exist to drive
  was still `price`, and the switch that would enable it was reachable by nobody.) A done-when
  must name the EFFECT on live data; a file existing is not an effect.
- **A rate computed over a contaminated sample.** Own probes, one-off experiments and imported
  history masquerade as traffic — quote which rows a number came from, and how many. A band with
  n=1 is an anecdote, not evidence.
- **Quorum-by-deliberation-MCP instead of quorum-by-seats.** A multi-model deliberation call is
  not a quorum: the quorum is independent judge SEATS on full sessions, each working the SAME
  claim checklist, with the coordinator re-verifying every CONTRADICTED lead as the commit layer.

## Report shape

1. **The chain** — where it stands, stage by stage.
2. **Facts** — each with its evidence class and source path.
3. **Goal and falsifier.**
4. **Subgoals** — the tree with per-subgoal status and its verification result.
5. **The re-evaluation** — Stage 1's measurement re-run, before vs after.
6. **What did not move**, and why (never omit this section).
7. **The next subgoals** the re-evaluation produced.
8. **Quorum verdicts** at both stages — accepted / amended / rejected, each with its reason.

## Doctrine

- **Read before you reason.** The artifact is the authority; every other source is a claim.
- **Two quorums, two jobs.** #1 protects the premise; #2 verifies the result.
- **A plan is a set of predictions.** Each subgoal predicts an observable effect; Stage 5 grades
  them.
- **Never talk from the ass.** If it was not read or measured, it is a question, not a fact.
- **The loop does not end at "shipped".** It ends when the falsifier is settled.
- **Improvement requires the looking-back half.** Without Stage 5 and Stage 6 this is just task
  execution wearing a plan's clothes.
- **Failure is an input, never an exit.** A failed verification subgoal and a failed verification
  quorum are both handled the same way at their own altitude: add subgoals that find and fix the
  problem, re-append the verification stage, run again. The chain ends on a pass — not on
  exhaustion, not on a timeout, not on "we've done a lot of iterations".
- **Long convergence is expected, so make it legible instead of shorter.** Each pass adds work
  rather than lowering the bar, which is why this can take an extremely long time to get going.
  Report what failed, what was added, and what changed each iteration — a loop that can be watched
  is worth more than one that finishes fast and lies.
