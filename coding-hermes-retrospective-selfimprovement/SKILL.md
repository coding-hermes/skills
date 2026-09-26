---
name: coding-hermes-retrospective-selfimprovement
description: "Use when a request spans many steps or the owner says plan it / subgoals / verify / don't just do it — facts-first goal→subgoal→verify loop with quorum."
version: 1.0.0
author: totalwindupflightsystems
license: MIT
metadata:
  hermes:
    tags: [planning, self-improvement, retrospective, verification, quorum, evidence, 改善]
    related_skills:
      - coding-hermes-quorum
      - coding-hermes-spec-lifecycle
      - coding-hermes-bankai
      - fleet-retrospective
---

# 改善 KAIZEN — Retrospective Self-Improvement

**改善 (kaizen)** is not "improvement" as a mood; it is *change made good by looking back first*.
改 is the character in 改革 (reform) and 改善 itself; 善 is goodness, and it appears in the
compound 改善 only after the 改 — you do not get the good part without the looking-back part.
The loop is the skill. Anyone can announce a plan; the discipline is that **every pass ends by
looking at what actually happened and re-deciding**.

> **One line:** plan from measured facts, execute in verified subgoals, then re-evaluate the
> whole thing against its own falsifier before declaring it done.

## When this fires

- The owner asks for something with more than one moving part ("wire X to Y and get the
  metrics lined up"), or says **plan it / outline it / make subgoals / verify it / don't just
  do the task**.
- The owner says the plan must **reflect again** when it is done, or asks for a **quorum** on
  a plan or a delivered result.
- You catch yourself about to answer from memory instead of from the artifact. That is the
  moment this skill exists for.

Do **not** use this for a single-step lookup, a one-line question, or a task whose whole
answer is one tool call. Ceremony is not improvement.

## 改善第零条 — The Iron Law: facts before claims

**Talking from the ass** is the failure class this skill is built to kill: asserting a cause,
a count, or a status from memory, from a prior summary, or from how the system "obviously"
works, without reading the thing itself. It has produced wrong diagnoses, reopened rows, and
weeks of misdirected work.

The law, in order:

1. **Read the artifact, not the summary of it.** The file, the live DB row, the daemon log,
   the board row, the process list. A compaction summary, a memory entry, and a previous
   session's report are all *claims about* the artifact — never the artifact.
2. **Name the evidence class of every claim.** Measured (a command you ran, with output) /
   documented (a file path + line) / inferred (stated as inferred) / unmeasured (say so
   plainly). Never let two of these wear the same costume.
3. **The live artifact wins.** When memory or a brief disagrees with the live system, the
   live system is right and the memory is stale. Say which one you trusted and why.
4. **Test the hunch before you act on it.** A hypothesis is not a finding. Find the
   measurement that would kill it and run that one first — a cheap decisive query beats a
   plausible story (see Pitfalls: *the theory that died in the log*).
5. **A prior pass's conclusion is a lead, not a fact.** Re-derive it, or label it as
   inherited. Rows have been marked complete when their *effect* was absent.

Gate before writing any plan: **can every factual sentence in it be traced to a path, a
command, or a measurement?** If not, the plan is not ready — it is a draft of a wish.

## The loop — 0 → 5, and then back to 4

### Phase 0 — Harvest raw details FIRST (before the plan)

Do not write the plan from your own head. Gather the raw material from the sources that
already hold it:

- the live stores (DB, logs, registry, config), read directly;
- the board rows that describe the work (their *reasoning* field usually names the intended
  effect and the evidence that would prove it);
- the repo docs that define the contract;
- **and the independent reviewers — convene `coding-hermes-quorum` (or a deliberation) with
  the raw details and let them attack them.** This is the owner's rule in his own words:
  *use the quorum first to build the raw details, then the goal with the subgoals*. A quorum
  run at Phase 0 is cheaper than a quorum run on a plan built on a wrong premise.

Output of Phase 0: a pile of facts with evidence classes, and a list of what is *unknown*.

### Phase 1 — The goal

One sentence. Plus its **falsifier**: the measurement that would show the goal is NOT met.
A goal without a falsifier cannot be finished, only abandoned.

### Phase 2 — The subgoal tree

Each subgoal carries three things:

- **Done-when** — a checkable condition, not a feeling. ("`router_spawn.py` sorts by predicted
  cost per task by default, demonstrated by a spawn whose chosen lane changes.")
- **Evidence** — what will be produced and where it will live.
- **Depends-on** — which subgoal must land first.

Order by *cheapest decisive step first*. Prefer the subgoal that could kill the plan early.

### Phase 3 — Execute, smallest first, each verified

Land one subgoal, verify it against its own done-when, then move. Commit proven work
immediately — a verified subgoal that is not committed can be wiped by the next deploy.
Never batch three unverified changes and then test the pile.

### Phase 4 — THE LAST SUBGOAL IS ALWAYS A RE-EVALUATION

The terminal subgoal is never "finish the feature". It is:

> **Re-evaluate everything against the goal and its falsifier, verify what you claim, and
> then write the next subgoals.**

This is the spine of the skill. At Phase 4:

1. Re-measure the original problem — the same query as Phase 0, run again, now.
2. Compare: did the *effect* appear, or only the *code*? (Code landing is not the effect
   landing. A row that shipped the mechanism and left the default untouched is not done.)
3. Verify each claim in your own plan against the artifact that should now carry it.
4. Account for what did NOT move, and say so plainly. An honest "this did not improve"
   is a finding; a quietly dropped subgoal is a lie by omission.
5. **Grow the tree**: the gaps found here become the next round's subgoals — then return to
   Phase 2 with them. Stop only when the falsifier is settled, not when you are tired.

### Phase 5 — Quorum review of the result

Convene `coding-hermes-quorum` on the delivered artifact and the re-evaluation, not on your
intentions. Independent families, one shared claim checklist, every judge works every claim.
Convergence between families is the signal; a single family's verdict is a lead. Re-verify
every CONTRADICTED item against raw data yourself before accepting it — the coordinator is
the commit layer.

The quorum is **not** a rubber stamp at the end. Its highest-value output is a
CONTRADICTED against your own draft — that is the round working.

## Subgoal anatomy (copy this shape)

```
SG-n  <imperative title>
  done-when:  <checkable condition, with the command that checks it>
  evidence:   <artifact path the proof will live at>
  depends-on: <SG-x | none>
  falsifier:  <what would show this subgoal is unnecessary or wrong>
```

## Pitfalls (each one cost real work)

- **The theory that died in the log.** A whole causal case was built for a resource-allocation
  bug from arithmetic on paper. One log query returned `budget=0` and `load_gate=0` — the gate
  never fired — and the real constraint was elsewhere. *Find the measurement that names the
  cause; do not infer the cause from the mechanism.*
- **Code landed ≠ effect landed.** The mechanism was built, deployed, and marked complete while
  the default ordering still made the effect unreachable. Reopen the row, keep the code, and
  say why complete never showed up as working.
- **Stale counts dressed as findings.** "100 lanes have never run, oldest from weeks ago" was
  wrong: the lanes were days old and one had already run three times. Re-query; counts decay.
- **Legacy population read as current behaviour.** "The column is empty on all rows" described
  the historical set, not the current write path, which was already fixed. Ask *which
  population* before calling something broken.
- **The plan built on a summary.** Compaction summaries drop the exact number you need. Go
  back to the store; never rebuild a plan on a paraphrase.
- **Coordinator pre-run facts get audited.** Independent reviewers will check your numbers and
  one of them will be wrong sometimes — that is the method working, not failing. Pre-run every
  command you put in a plan so the reviewers verify rather than debug.
- **Green but did nothing.** A subgoal can pass its own check while changing nothing
  observable. Pair every done-when with an effect check in Phase 4.
- **The tree that stops growing on a lie.** If Phase 4 finds nothing to add, ask whether you
  measured the *effect* or only re-read your own plan.

## Report shape

1. **The goal**, and its falsifier.
2. **Facts** — each with its evidence class and source path.
3. **Subgoals** — the tree, with status per subgoal.
4. **The re-evaluation** — the same measurement as Phase 0, run again, before/after.
5. **What did not move**, and why (never omit this section).
6. **The next subgoals** the re-evaluation produced.
7. **Quorum verdicts** and what was accepted, amended, or rejected — with the reason.

## Doctrine

- **Read before you reason.** The artifact is the authority; every other source is a claim.
- **A plan is a set of predictions.** Each subgoal predicts an observable effect; Phase 4 is
  where predictions get graded.
- **Never talk from the ass.** If it was not read or measured, it is not a fact — it is a
  question, and it belongs in Phase 0.
- **The loop does not end at "shipped".** It ends when the falsifier is settled.
- **Improvement requires the looking-back half.** Without Phase 4 this is just task execution
  wearing a plan's clothes.
