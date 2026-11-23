# Cross-cutting: flows (the deep discipline — hierarchy, conditionals, error flows)

A flow is not a paragraph. It is a structured artifact with hierarchy,
exhaustive branching, and error paths documented to the same depth as the
happy path.

## 1. The flow hierarchy
- **Flow**: one user- or machine-goal, start to terminal state (e.g. 'check
  out with saved card').
- **Sub-flow**: a reusable segment invoked by flows (e.g. 'address
  validation'), referenced by id, never restated — one definition, many
  callers.
- **Step**: one actor-visible or machine-atomic action with: input (the
  data it consumes), output, the system state before/after, and the surface
  it runs on.
- Every level carries: trigger, preconditions, postconditions, and the
  actor at each step. A step that changes no state and decides nothing is
  prose, not a step.

## 2. How each flow is written (the notation)
- Numbered steps: `N. actor action -> expected result`. Each step names the
  surface (API call, screen, background job) it manifests as.
- Data flow between steps is explicit: what step N passes to step N+1
  (the fields, or the pointer to the record).
- State at each step: what the system asserts true after the step
  (postconditions) — this is what tests assert.
- Sequence diagrams for flows with 3+ parties; step lists for everything
  (diagrams supplement, never replace the numbered list).

## 3. Conditionals — exhaustive or wrong
- Every decision point is a BRANCH TABLE: condition -> branch -> next
  step/sub-flow. Prose hiding a branch ('if needed, the system validates…')
  is a FAIL.
- The ELSE case is mandatory: every conditional states what happens when no
  branch condition matches.
- Compound conditions are decomposed: `A AND (B OR C)` expands to a truth
  table when any arm has a distinct behavior.
- Every branch terminates: a branch that 'continues' into unspecified
  behavior is a hole with a name.

## 4. Error flows are first-class flows
- EVERY step has failure exits, and each exit IS a flow with the same
  discipline: trigger (the exact failure), handling (retry/compensate/
  fail/requeue — which, and its budget), terminal state (what the user sees
  and what the system asserts), and the recovery path (automatic + manual).
- The error taxonomy per flow: which error classes are recoverable-async,
  recoverable-retry, fatal-to-flow, fatal-to-session. Each class maps to
  the failure matrix (cross-failures.md).
- Compensation: steps that moved state which later steps may invalidate
  state their compensation (or the saga/rollback boundary that owns it).
- The retry answer per step: idempotency key, max attempts, backoff, and
  what makes double-execution harmless.

## 5. Concurrency and re-entry inside flows
- Parallel steps: declared (which steps run concurrently), the JOIN point,
  and the partial-failure rule at the join.
- Re-entry: the flow is replayed mid-way (refresh, retry, crash-resume) —
  each step is idempotent or guarded; the resume point is derivable from
  stored state.
- Two actors, one flow instance: the lock/lease or the last-write rule, and
  what the loser sees.

## 6. The completeness checks (how flows get rated)
- **Surface coverage matrix**: every screen/endpoint/job appears in >= 1
  flow; every flow step maps to a real surface. Dead surfaces and phantom
  steps both FAIL.
- **Terminal-state check**: every flow and every branch ends in a terminal
  state (success or a named failure). 'And then it's done' without state
  assertion is a FAIL.
- **Error-depth parity**: count error flows vs steps — a 12-step flow with
  2 error flows is shallow by arithmetic.
- **Re-entry check**: each flow answers the mid-flow crash question.
- **Conditionals**: every branch table's ELSE is present.
