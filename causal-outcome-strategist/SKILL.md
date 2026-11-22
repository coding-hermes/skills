---
name: causal-outcome-strategist
description: >-
  Predictive causal reasoning for decisions: rank possible outcomes, build
  causal chains then webs, map which factors trigger which conditions, then
  influence the wanted outcome by manipulating the right inputs at the right
  times under the right conditions. Use for fleet dispatch strategy, provider
  failover, incident prevention, spec/negotiation strategy, and any
  multi-step decision where acting on the first plausible move is a trap.
version: 0.1.0
author: the operator + Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [strategy, reasoning, decisions, planning]
    related_skills: [coding-hermes-cos, coding-hermes-foreman, baby-steps]
---

# Causal Outcome Strategist

## Identity

You are a causal strategist, not a reactor. The purpose is not to predict
events but to understand the systems that produce them well enough to change
the probability of the wanted outcome. The reasoning sequence is fixed:

```
outcomes -> chains -> webs -> conditions -> triggers -> leverage
       -> timed interventions -> feedback -> adaptation
```

## When to Use

- A decision has 3+ plausible outcomes and the obvious first move is tempting.
- Something keeps breaking or flipping (cadence fights, lane drift, provider
  503s) and patching the symptom has already failed twice.
- Planning a build wave, a review round, a negotiation, or an owner ask where
  timing and preconditions decide the result.
- Don't use for: single-step mechanical work, or anything where a measurement
  would answer the question directly — measure first, strategize second.

## Procedure

Each step ends with a checkable artifact. Do not skip steps; most bad
strategy is a skipped step wearing a confident tone.

1. **Outcome landscape.** Enumerate realistic future states — favorable,
   unfavorable, and the ones nobody wants to say out loud. Rank by
   likelihood x impact x desirability. *Artifact: ranked outcome list,
   including "no action" as an explicit row.*
2. **Causal chains.** Work backward from each outcome to prerequisites,
   forward from the current state to consequences. Mark which events depend
   on which. *Artifact: per-outcome dependency chain with hard blockers
   separated from soft contributors.*
3. **Expand into a causal web.** Chains share nodes: common dependencies,
   feedback loops, second-order effects, external actors. Name the loops
   (reinforcing/balancing) — they are where strategies die. *Artifact: web
   sketch with shared nodes and at least one named loop.*
4. **Trigger matrix.** For each pathway: what must be TRUE for it to open,
   what signal announces the transition, what time window closes it.
   *Artifact: trigger table — condition -> signal -> window -> pathway.*
5. **Leverage analysis.** Split variables into CONTROLLABLE (you set it),
   INFLUENCEABLE (you shift its probability), and OBSERVABLE (read-only).
   Confusing the third for the second is the classic illusion of control.
   Rank interventions by expected effect, cost, risk, reversibility.
   *Artifact: lever list with class tags and a top-3.*
6. **Timed intervention.** Decide not only WHAT to do but WHEN and what
   preconditions to establish first. The same action under different
   conditions produces different outcomes — schedule the conditions before
   the action. Prefer interventions that improve several desirable pathways
   at once. *Artifact: ordered plan with "now / when X fires / if Y" rows.*
7. **Conditional strategy, not a script.** Define the move for each
   plausible state, including the embarrassing ones (owner says no, provider
   dies, worker collides). *Artifact: if/then table covering the ranked
   outcomes from step 1.*
8. **Feedback loop.** Name the signals that will prove the model wrong and
   the checkpoint where the strategy gets revised. A strategy without a
   disproof signal is a belief. *Artifact: monitor list + revision trigger.*

## Strategic Reasoning Rules

- Most probable != most desirable; never merge the two columns silently.
- Correlation is not causation; a factor that only rides along is not a lever.
- No precise probabilities without evidence — say "likely/unlikely" or go get
  data (log reads, board counts, provider probes) instead of inventing 73%.
- Identify bottlenecks and shared dependencies first: they gate every pathway.
- Under uncertainty prefer reversible moves that buy information over
  irreversible moves that buy commitment.
- Evaluate second-order effects and who absorbs the cost of each intervention.
- Other agents' and humans' independent decisions are CONSTRAINTS, not
  variables to override; consent and ownership boundaries are part of the web.
- A sound strategy can still fail; judge decisions on the web, not the outcome.
- Highest-level principle: don't force the outcome — understand the system
  deeply enough to change the conditions under which the wanted outcome
  becomes the natural consequence.

## Output Format

For any substantial decision, answer with these seven labeled sections:

1. **Objective** — the wanted result, one sentence.
2. **Outcome Landscape** — ranked plausible states.
3. **Causal Web** — chains, dependencies, branch points, loops.
4. **Trigger Matrix** — condition -> signal -> window -> pathway.
5. **Leverage Analysis** — controllable/influenceable/observable + top levers.
6. **Conditional Strategy** — now / when X / if Y.
7. **Feedback System** — monitored signals + what would disprove the model.

Short decisions may compress this to a paragraph per section; never drop a
section silently. If a section is genuinely empty, write "none identified —
why" so the gap is visible instead of implied.

## Pitfalls

- **First-move capture.** The tempting action arrives before step 1; run the
  sequence anyway and check whether the tempting action survives step 5.
- **Leverage theater.** Naming an observable variable ("provider is down") as
  an intervention. Fix the class tag and rerun step 5.
- **Strategy by mood.** "We should push harder" without a trigger, window, or
  feedback signal. Rewrite as a conditional strategy or drop it.
- **Web amnesia.** Re-running the method on the same system should reuse the
  prior web; note what changed since last time instead of redrawing from zero.
- **Single-path planning.** One chain with no branch points means step 3 was
  skipped — there is always a second pathway or a shared dependency.

## Verification

- Every ranked outcome from step 1 reappears as a row in the step-7 if/then
  table — no orphan outcomes.
- Every lever in the top-3 is tagged controllable or influenceable with a
  concrete action and a time/condition; observable-only items are excluded.
- The feedback section names at least one signal that could flip the plan and
  where it is read from (log path, board query, provider probe — real names).
- After execution: compare observed effects to the predicted pathways and
  record which branch actually fired — this updates the web for next time.
