# Platform: distributed system (multi-node, async, partial failure is normal)

## Decisions that must be stated
- Consistency model per data class: linearizable / read-your-writes / eventual — per datum, not global.
- Identity & membership: how nodes join/leave, how the cluster notices death, split-brain defense.
- The partition-tolerance stance: during a net-split, which side serves, what is rejected.
- Idempotency everywhere: every retried message/request is safe or keyed.

## Contracts a builder needs
- Message schemas + their versioning; the schema-registry or compat rule.
- Ordering guarantees per stream/queue (total? per-key? none?) and what consuming code may assume.
- Retry/timeout/backoff budget per hop, so tail latency is computable, not folklore.
- The CAP tradeoffs made per feature, named (e.g. 'carts stay writable during splits; billing does not').

## Failure paths
- Node loss mid-write: replication factor, quorum rule, what the client sees.
- Network partition: behavior per the stance above, and the healing path (anti-entropy, reconciliation).
- Cascade prevention: load shedding, circuit breakers, and where the breaker resets.
- Duplicated delivery (at-least-once): the dedup window and where it lives.

## Rating checks
- FAIL if 'eventually consistent' appears without naming which reads are affected and the
  convergence bound.
- FAIL if any cross-service flow assumes atomicity across nodes without a protocol (2PC/saga/outbox).
- FAIL if the spec has no answer for two nodes claiming the same unique key during a partition.
