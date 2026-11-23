# Cross-cutting: workflow & state machines

Any entity that moves through stages (orders, tasks, deployments,
subscriptions, content) is a state machine, and specs fail silently by
not saying so.

## What a complete workflow spec documents
- **The state diagram**: every state, every legal transition, drawn or listed
  exhaustively — including the terminal and failure states.
- **Transition guards**: per transition — who/what may fire it, the preconditions,
  and the side effects (a transition IS a transaction: what it atomically changes).
- **Concurrency**: two transitions racing (accept + cancel): the winner rule,
  the loser's UX, and the idempotency of replays.
- **Timeouts & timers**: per state — how long it may sit, the escalation timer,
  and who/what fires it (the daemon owns timers, stated in the machines section).
- **The audit trail**: every transition logged with actor, timestamp, and reason;
  the manual/state-fix path for operators (with its own guard rails).
- **Terminal-state invariants**: what is ALWAYS true when the machine settles
  (money conserved, no orphaned side effects) — the invariants the tests assert.

## Rating checks
- FAIL if any state transition lacks a guard or side-effect list.
- FAIL if no timeout exists for a waiting state (rows park forever).
- FAIL if racing transitions have no winner rule.
