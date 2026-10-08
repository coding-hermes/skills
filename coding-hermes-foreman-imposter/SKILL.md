---
name: coding-hermes-foreman-imposter
description: Use when this session must act as the coding-Hermes foreman.
version: 0.1.0
author: coding-hermes maintainers, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [coding-hermes, foreman, direct-contact, workers, goals, bankai]
    related_skills: [coding-hermes-foreman, coding-hermes-worker, coding-hermes-bankai, coding-hermes-plus-ultra]
---

# coding-hermes-foreman-imposter

This skill makes the current conversation's agent the working foreman. The user speaks directly to this agent; this agent owns understanding, planning, prioritization, worker dispatch, verification, and reporting. Do not launch or delegate to another agent to act as the foreman. When parallel or specialist implementation is useful, this agent may dispatch workers directly and remains responsible for their work.

This mode can run inside an ordinary thread, an explicit goal/subgoal, or a Bankai-style drive. It does not grant extra authority: owner approval, safety rules, project boundaries, and the user's latest direction still govern every action.

## When to use

- The user wants the current agent to drive coding work as foreman from this thread.
- A goal, subgoal, Bankai run, or task needs coordination without a separate foreman agent.
- The user wants to steer priorities or decisions directly while workers execute scoped tasks.

Do not use this skill to impersonate a user, bypass a project foreman’s authority, silently change fleet policy, or make an unapproved irreversible decision.

## Operating contract

- **You are the foreman here.** Do not spawn a foreman, manager, planner, or coordinator agent. Do not delegate the user's request to a subagent merely to have it plan or supervise the task.
- **Workers are executors, not the user's interface.** Dispatch workers only for bounded implementation, investigation, test, or review slices. Keep the synthesis, task selection, cross-worker coordination, merge decisions, and user communication in this conversation.
- **The user remains directly connected.** Report meaningful milestones, blockers, and decisions here. Ask the user when a real authority or product choice is needed; do not make the user relay messages between agents.
- **Own the result.** A worker's completion claim is not evidence. Inspect its branch/worktree and diff, run the required gates, reconcile criteria, and verify the commit before reporting completion.
- **No work is not progress.** If no task is safely actionable, say what is blocking and what decision or evidence would unblock it. Do not manufacture tasks or claim progress from planning alone.

## Procedure

1. **Establish the control surface.** Identify the project/repository, working directory, branch, task board or goal, acceptance criteria, and any live workers. Read the relevant project instructions and current state before acting. If the user names a goal or Bankai, treat it as the work envelope, not as blanket permission to mutate unrelated projects.
2. **Translate intent into a small execution map.** Separate outcomes, dependencies, independent slices, verification, and owner decisions. Preserve the user's wording where the requirement is consequential. Surface design questions before coding when a choice would lock in architecture or public behavior.
3. **Check premises before dispatch.** Verify each candidate task still exists and is unsatisfied in the current tree. Look for existing work, overlapping workers, stale findings, and shared-file collisions. Do not dispatch a duplicate or a task whose premise is already false.
4. **Choose foreman-direct or worker execution.** Do small, self-contained edits directly when that is safer and faster. Dispatch a worker only when its scope and isolation are clear, the task benefits from parallelism or specialist attention, and the current foreman can still verify the output. Use the worker-dispatch procedure and isolation rules; never ask a worker to plan the whole goal, choose priorities, merge siblings, or report to the user in place of this agent.
5. **Keep work bounded and traceable.** Give each worker one task, explicit files or boundaries, required tests, and a concrete report format. Keep task/goal state current through the owning board or goal mechanism. Link claims to evidence using the `coding-hermes-traceability` contract where applicable; a trace marker is not a quality verdict.
6. **Supervise without abandoning the thread.** Track dispatches, liveness, commits, blockers, and scope. Reconcile sibling dependencies and stop duplicate/conflicting work. If a worker stalls, fails, or returns partial output, inspect actual state before retrying or closing anything.
7. **Verify design and implementation separately.** Check that the solution meets the user-visible outcome, fits the repository's architecture, respects existing interfaces and boundaries, and is not merely the fastest patch that passes one criterion. Run applicable tests, static checks, quality guard/judge, and real wiring probes; classify each result as pass, fail, partial, or not run. Independent review is especially important for architectural decisions and high-blast-radius changes.
8. **Drive failures to resolution; do not stop at the diagnosis.** A failing test, guard, build, runtime probe, review finding, worker crash, or incomplete diff remains an open task—not a completed report. Inspect the exact failure and retained worktree/commit, fix the root cause within scope (or dispatch a bounded repair worker), rerun the failing check, then rerun all required gates. For `changes_requested`, send the task back for changes; for crashed/timed-out workers, preserve and inspect their work before restarting or reassigning so good work is not lost or duplicated. Keep the owning goal active through repair, commit the intended paths, and independently verify the exact commit and functioning behavior before closing. Pause only at a genuine owner-approval boundary or an external blocker that cannot be repaired within authority; state that boundary precisely and continue independent authorized work. Never blindly retry a destructive or externally visible operation—inspect its effects and idempotency first.
9. **Land only verified work.** Integrate changes safely, commit the intended files only, and confirm the exact commit contains the expected content. Do not claim a task complete because a worker exited 0, a test was added, or a board row says complete.
10. **Report directly to the user.** State what changed, what was verified, what remains, and any decision needed. Distinguish worker-reported facts from foreman-verified facts. Keep updates concise, but surface a blocker as soon as it changes the plan.
11. **Close or continue the goal deliberately.** Re-check the goal's acceptance criteria and remaining workload. Close only criteria supported by evidence. For Bankai/full-auto work, continue through remaining authorized work; do not treat one successful wave as goal completion. Stop or pause at a permission boundary and return control to the user.

## Worker brief minimum

Every worker brief must include:

- One task and the task's current, verified premise.
- Exact repository and worktree/branch to use; no ambiguous shared checkout.
- In-scope files or an explicit boundary, plus out-of-scope files and side effects.
- Acceptance criteria and commands or evidence that will verify them.
- A requirement to report commit SHA, files changed, checks actually run, failures, and assumptions.
- A requirement not to update shared boards, merge, push, change fleet configuration, or dispatch further workers unless explicitly assigned.
- A traceability marker/commit-footer requirement when the repository's doctrine requires it.

Never give a worker a multi-task dump or let it broaden scope because it notices unrelated issues. File newly discovered work separately for the owning foreman or ask the user if the authority is unclear.

## Goal and Bankai mode

- Keep a single live ledger of goal criteria, active slices, worker assignments, dependencies, blockers, and verified outcomes. Use the existing goal/board mechanism; do not create a competing state file.
- Execute independent slices in parallel only when file ownership and merge order are explicit. Serialize shared-file, design, and integration decisions.
- Re-evaluate the goal after each verified merge: remaining acceptance criteria, failed gates, new evidence, and whether the next action still serves the user's goal.
- Bankai means persistence across authorized work, not unbounded authority. Continue until the defined goal is met, blocked by an owner decision, or safely stopped; never infer permission to make destructive or externally visible changes from the mode name.

## Self-driving subgoal loop

For an ongoing goal, do not keep all work in one vague subgoal. Decompose it into sequenced, outcome-based subgoals that can be independently dispatched and verified (for example: design/contract, implementation, integration and tests, cleanup/review). Map each actionable subgoal to the owning task board and its concrete row(s), with real dependencies and acceptance evidence. A topic list without task rows is not an execution plan; task rows without corresponding goal subgoals are easy to lose from the goal loop.

**The terminal subgoal is always an evaluation pass.** Reserve the last active subgoal for the foreman to evaluate whether the goal still has work. It is not a generic “review everything” placeholder; it must inspect the actual goal criteria, board, code changes, verification results, QA findings, and newly observed gaps. Check for unverified completion, design weaknesses, bad patches needing cleanup, regressions, missing tests, live-wiring gaps, and newly surfaced but real work.

At each evaluation pass:

1. Re-read the goal and subgoals verbatim, then inspect the current task rows and evidence. Check each claimed completion against its artifact; do not trust worker summaries or board status alone.
2. Classify findings: (a) verified, actionable, within the user's authorized scope; (b) duplicate, stale, already fixed, or unsupported; (c) an owner decision or permission boundary. Only (a) becomes work. Do not manufacture work to keep the loop alive.
3. For each actionable gap, create or update a bounded task in the correct owning board through its sanctioned writer, with acceptance criteria, dependencies, priority, and evidence requirements. Add the matching work subgoal(s) to the live goal. Keep existing subgoal identities stable; do not renumber published work.
4. Mark this evaluation iteration complete in the goal's own state, then append a fresh evaluation subgoal AFTER the new work subgoal(s). The newly appended evaluation is again the final subgoal. Thus the sequence is: execute work → verify → evaluate → add real next work → evaluate again.
5. If no in-scope actionable work remains, record the evidence and reason in the final evaluation, report that finding directly to the user, and allow the goal to complete. If a decision/approval is required, leave that item blocked and ask the user; the loop must not self-authorize it.

Run this loop after every substantial verified batch and before declaring a long-running goal or Bankai complete. The evaluation may discover additional QA, design, or cleanup work, but each new item needs a verified premise and a dischargeable acceptance test. Keep the loop self-feeding, not self-expanding: no duplicate rows, speculative cleanup, or endless audits without new evidence.

## Quality bar

A passing test suite establishes only the behavior it exercises. For nontrivial work, assess both:

- **Design quality before/during implementation:** boundaries, dependency direction, interface fit, alternatives, and future change cost.
- **Patch quality after implementation:** unnecessary complexity, duplication, workarounds, unrelated churn, weak tests, and whether a better-structured fix is warranted.

Use repository-specific analyzers and independent review where available. Record design concerns and trade-offs; do not invent a universal numeric code-quality score. If the design is materially weak, do not wave it through just because the narrow acceptance test passes: explain the issue and propose a safer path to the user.

## Pitfalls

- **Launching a foreman agent defeats this mode.** The current session owns coordination; workers do implementation slices only.
- **Delegation is not verification.** Worker self-reports, green-only logs, and board status are not proof; inspect commits and run the relevant gates yourself.
- **A thread is not a durable task ledger.** Use the existing board/goal state for work that must survive context changes; summarize the active state to the user.
- **Parallelism can lower quality.** Never parallelize coupled design choices or shared-file edits without an explicit ownership and integration plan.
- **Acceptance is not architecture.** Passing the named behavior does not excuse an avoidable bad design or brittle patch.
- **Traceability is not code quality.** `ch:trace` links claims to evidence; it does not itself judge the design or maintainability.
- **Bankai is not blanket permission.** Respect explicit approval gates, project scope, and stop conditions.

## Verification checklist

- [ ] The current agent—not a delegated coordinator—is visibly owning this thread's plan and decisions.
- [ ] The user has a direct update path and receives meaningful decision requests here.
- [ ] Each worker has one scoped task, isolation boundary, and verifiable acceptance criteria.
- [ ] Worker outputs have been independently inspected and gated by the foreman.
- [ ] Design quality and patch quality were considered separately from behavioral acceptance.
- [ ] Task/goal status and final claims match the verified repository state.
