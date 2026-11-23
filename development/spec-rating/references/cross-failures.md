# Cross-cutting: failure modes

## The discipline
For EVERY machine, dependency, and flow in the spec, name:
1. What breaks (dependency down, disk full, cert expired, quota hit, poison message).
2. Detection: which signal fires, how fast (the alert exists — cross-ref observability).
3. User impact: exactly what the user sees, per surface.
4. Automatic recovery: what self-heals (retry, failover, breaker) and its budget.
5. Human recovery: the runbook step, the expected time, the owner.

## The matrix
A failure-mode table is the artifact. Rows = failure causes; columns = detection /
impact / auto-recovery / manual runbook. A flow with no row is a finding. Every
auto-recovery mechanism named anywhere in the spec must trace to at least one row.

## Rating checks
- FAIL if any external dependency appears with no failure row.
- FAIL if 'monitoring will catch it' without naming the alert.
- FAIL if automatic recovery exists without a bound (unbounded retries are an outage).
