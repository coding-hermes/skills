# Patterns: consistency (saga, outbox, idempotent consumer, reconciliation)

When cross-service or cross-store work cannot share a transaction, the
consistency PATTERN must be chosen and named per flow. 'The DB transaction
handles it' is unavailable, and 'it will be fine' is not a pattern.

## The pattern catalog (and when each is the answer)
- **Saga**: a multi-step business flow as a sequence of local transactions
  + compensations. Demands: the step list, each step's compensation, the
  saga-orchestrator owner (code or choreography), and the stuck-saga answer
  (timeout, the operator's repair path).
- **Transactional outbox**: writes to the DB and the event it must emit are
  atomic because BOTH live in the DB; a relay publishes. Demands: the
  outbox table, the relay's at-least-once contract, and the consumer dedup.
- **Idempotent consumer**: delivery is at-least-once; the consumer makes
  replay harmless (dedup key, version-stamped apply, upsert-not-insert).
  Demands: the key choice and its collision answer.
- **Read-repair / reconciliation job**: eventual consistency needs the
  sweeper that finds drift (counts, checksums, cross-store compare) and
  repairs it. Demands: cadence, the drift alert, and the repair authority.
- **Two-phase commit / distributed transaction**: when truly needed — with
  the blocking-failure answer (the coordinator dies mid-commit: who
  resolves?). Most designs should NOT need this; choosing it demands a
  written justification.
- **CRDT / last-write-wins**: for merge-tolerant data (counters, presence).
  Demands: the data type must actually tolerate the merge semantics —
  LWW on a balance field is a bug, not a pattern.

## What the spec must state per distributed flow
- Which pattern, the invariant it preserves (money conserved, no lost
  updates), the invariant it DOESN'T (what's temporarily inconsistent, the
  bound), and the stuck-state answer.

## Rating checks
- FAIL if a cross-service flow claims atomicity with no pattern.
- FAIL if at-least-once delivery exists with no idempotent consumer.
- FAIL if eventual consistency has no reconciliation sweeper and no bound.
