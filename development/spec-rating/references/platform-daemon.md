# Platform: long-running daemon / background service

## Decisions that must be stated
- Supervision: what starts it, restarts it, and what backoff; who owns the socket/port.
- State: what lives in memory vs durable store; what a restart loses (and why that is acceptable).
- Scheduling: every periodic job's cadence, overlap policy (skip? coalesce? run-parallel?).
- Shutdown: signal handling, drain window, what finishes vs what is abandoned mid-flight.

## Contracts a builder needs
- Health/readiness definition: what /health checks (deps? just self?), liveness vs readiness split.
- The work queue/inbox contract: how work arrives, dedup key, at-least/at-most-once semantics.
- Metrics the daemon emits (the operational contract for the dashboard).

## Failure paths
- Downstream dependency outage: retry policy, dead-letter, and the backlog growth shape.
- Clock jumps (NTP step, VM migration): what the scheduler does.
- Split-brain / duplicate instances: the lock or lease that prevents double-work.
- Unbounded memory: what is bounded, what is capped, what OOMs first and why.

## Rating checks
- FAIL if restart behavior is unstated (daemons restart; that is their nature).
- FAIL if any periodic job lacks an overlap policy.
- FAIL if 'the process was killed mid-task' has no specified recovery.
