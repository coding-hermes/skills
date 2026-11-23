# Paradigm: synchronous vs asynchronous (choosing deliberately)

## The decision, per interaction
Async is a COST (complexity, propagation, harder debugging) bought for a
BENEFIT (throughput under IO wait, responsiveness). The spec states, per
interaction, which side it chose and why:

- **Default to synchronous** unless a stated reason overrides: the call is
  fast, local, and the caller can wait. Sync is simpler to reason about,
  test, and debug — the spec should DEFEND every async boundary.
- **Async earns its place when**: the operation is genuinely slow (IO,
  human-in-the-loop, long compute) and the caller's time matters more than
  the result's immediacy.
- **The async infection**: one async boundary forces async upstream. The
  spec marks the boundary set deliberately (where sync turns async) and
  keeps the CORE sync where possible.

## What the async spec must answer (per flow)
- The completion contract: how does the caller learn the result (callback,
  poll, subscription, webhook) and what if it never comes (timeout,
  dead-letter, reconcile)?
- The status-visibility contract: what does the user see while async work
  runs (pending state, progress, cancel affordance)?
- The failure contract: retry ownership (caller vs system), the idempotency
  of the retry, and the 'it failed while the user waited' UX.
- The ordering contract: do async completions apply in submission order,
  and what breaks if not (the classic: two updates, reversed application).

## Rating checks
- FAIL if an async flow has no completion-detection and no timeout answer.
- FAIL if async was chosen for a fast local operation (complexity without
  benefit — the spec must defend it).
- FAIL if no answer exists for reversed application of out-of-order completions.
