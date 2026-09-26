---
name: coding-hermes-retrospective-selfimprovement
description: "Use when a request spans many steps or the owner says plan it / subgoals / verify / don't just do it — the full chain: problem → quorum → goal → subgoals → per-subgoal verify → quorum verify."
version: 2.0.0
author: totalwindupflightsystems
license: MIT
metadata:
  hermes:
    tags: [planning, self-improvement, retrospective, verification, quorum, evidence, chain, 改善]
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
   GROW or STOP — what the evaluation and the review exposed becomes the next
   round's subgoals (back to SUBGOALS). Stop when the FALSIFIER is settled,
   never merely when the work is shipped.
```

**Two quorums, and they are not the same review.** #1 runs *before* the plan exists — it is
there to stop you building on a wrong premise, and it is the cheap one. #2 runs *after* the
result exists — it is the commit layer. A single family's verdict is a lead, not a ruling, at
either one.

## When this fires

- The owner asks for something with more than one moving part ("wire X to Y and get the metrics
  lined up"), or says **plan it / outline it / make subgoals / verify it / don't just do the task**.
- The owner says the plan must **reflect again** when it is done, or asks for a **quorum** on a
  plan or a result.
- You catch yourself about to answer from memory instead of from the artifact. That is the
  moment this skill exists for.

Not for a single-step lookup or a one-line question. Ceremony is not improvement.

## 改善第零条 — the iron law of every stage: facts before claims

**Talking from the ass** is the failure class this whole chain exists to kill: asserting a cause,
a count, or a status from memory, from a prior summary, or from how the system "obviously"
works, without reading the thing itself.

1. **Read the artifact, not the summary of it.** A compaction summary, a memory entry, and a
   previous session's report are *claims about* the artifact — never the artifact.
2. **Name the evidence class** of every claim: measured (a command you ran, with output) /
   documented (path + line) / inferred (say so) / unmeasured (say so). Never let two wear the
   same costume.
3. **The live artifact wins.** When memory disagrees with the running system, the system is
   right and the memory is stale. Say which one you trusted.
4. **Test the hunch before acting on it.** A hypothesis is not a finding; find the measurement
   that would kill it and run that one first.
5. **A prior conclusion is a lead, not a fact.** Re-derive it or label it inherited. Work has
   been marked complete with its effect absent.

Gate at every stage: **can every factual sentence be traced to a path, a command, or a
measurement?** If not, it is a draft of a wish.

## Stage 1 — QUORUM #1 (raw details, before the plan)

Gather from the sources that already hold the material: live stores (DB, logs, registry, config);
the board rows that describe the work (their reasoning field usually names the intended *effect*
and the evidence that would prove it); the repo docs that define the contract. Then convene
`coding-hermes-quorum` and let independent families attack those raw details.

The owner's own rule: **use the quorum first to build the raw details, then the goal with the
subgoals.** A quorum before the plan costs one round; a plan built on a wrong premise costs a
week.

Produce: facts with evidence classes · the explicit unknowns · the questions the plan must answer.

## Stage 2 — GOAL

One sentence. Plus the **falsifier**: the measurement that shows the goal is not met. A goal
without a falsifier cannot be finished, only abandoned. Write what "done" looks like from
outside — a number that changes, a question someone can answer — never "the feature exists".

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

## Stage 6 — QUORUM #2 (verify the result)

Brief the families on the delivered artifact and the re-evaluation, never on your intentions.
Every judge works the whole claim checklist. Consensus between independent families is the
signal; one family is a lead. Re-verify every CONTRADICTED item against raw data yourself before
accepting it — the coordinator is the commit layer. Each acceptance criterion must be as strong
under review as the subgoals were.

The highest-value output of the round is a CONTRADICTED against your own draft. That is the
round working.

## Stage 7 — GROW or STOP

New subgoals land before you report done. The tree stops growing for exactly one honest reason:
the falsifier is settled. If Stage 5 found nothing to add, ask whether you measured the effect or
only re-read your own plan.

## Pitfalls (each cost real work)

- **The theory that died in the log.** A full causal case was built for a resource-allocation bug
  from arithmetic on paper; one log query returned the gate had fired **zero** times and the real
  constraint was elsewhere. Find the measurement that names the cause.
- **Code landed ≠ effect landed.** Mechanism built, deployed, marked complete — while a default
  left the effect unreachable. Reopen the row, keep the code, say why "complete" never showed up
  as working.
- **Stale counts dressed as findings.** A "never ran, oldest weeks ago" census was wrong: the
  lanes were days old and one had already run three times. Re-query; counts decay.
- **Legacy population read as current behaviour.** "Empty on all rows" described the historical
  set, not the current write path, which was already fixed. Ask *which population* first.
- **The plan built on a summary.** Compaction summaries drop the exact number you need. Go back
  to the store; never rebuild a plan on a paraphrase.
- **Pre-run facts get audited.** Reviewers will check your numbers, and one will be wrong
  sometimes — that is the method working. Pre-run every command so they verify instead of debug.
- **The switch that is a bet.** Do not flip a production default to prove a mechanism; run it in
  shadow (compute and record the new answer, serve the old one), then flip with the revert proven.
- **The tree that stops growing on a lie.** Nothing to add after Stage 5 usually means you
  re-read your plan instead of measuring the effect.

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
