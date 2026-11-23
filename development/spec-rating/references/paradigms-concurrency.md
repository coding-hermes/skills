# Paradigm: concurrency model (per component, a stated decision)

Every component that does more than one thing at a time has a concurrency
model. Specs fail by never naming it and letting the runtime decide.

## The models (and what each demands from the spec)
- **Synchronous single-threaded**: one thing at a time. Demands: the latency
  budget that makes this viable, the queue that serializes work, and what
  backs up when the single thread stalls.
- **Threaded / shared-state**: N threads over shared memory. Demands: the
  lock inventory (every lock, its scope, ordering), the shared-state map
  (what data two threads touch), the race discipline (what a data race
  costs and the sanitizer that catches it), and the deadlock answer.
- **Async event loop**: cooperative scheduling on one (or few) threads.
  Demands: the never-block rule (which calls are forbidden in the loop —
  sync IO, CPU-heavy work), the offload path for CPU work (worker pool),
  and the cancellation discipline (what happens to in-flight tasks on
  shutdown/cancel).
- **Structured concurrency / CSP** (goroutines, async tasks with scopes,
  actors): Demands: the ownership tree (who spawns, who joins, who
  cancels), the channel/mailbox semantics (buffered? unbounded? what on
  full?), and the supervision policy (actor restart, error propagation).
- **Multi-process**: isolation over sharing. Demands: the IPC contract, the
  state-sharing answer (none? shared store?), and the coordination story.

## The questions every spec answers per component
- How many things execute at once here, on what model, and WHY that model
  (the load shape that justifies it — IO-bound vs CPU-bound decides).
- What state is shared across executions, and what guards it.
- What happens under overload BEFORE the model is chosen (backpressure is
  designed with the model, not after).

## Rating checks
- FAIL if any concurrent component lacks a named model and its guard story.
- FAIL if shared mutable state exists with no synchronization inventory.
- FAIL if an event loop can block (a sync call inside async is a hidden outage).
- FAIL if cancellation semantics are unstated (leaked goroutines/tasks are
  the classic slow leak).
