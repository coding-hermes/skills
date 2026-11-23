# Interface: RPC and message queues (gRPC, queues, jobs, events)

## What a complete async/RPC spec documents
- Per call/queue: protocol, serialization, timeout, retry policy, and the idempotency key.
- Delivery semantics per queue: at-most-once / at-least-once / exactly-once (and the
  mechanism that earns the claim — dedup window, transactional outbox, or admission it's a lie).
- Ordering: total, per-key, or none — and one sentence on what consuming code may assume.
- Poison handling: max deliveries, dead-letter destination, and who inspects the DLQ.

## The questions the spec must answer
- What happens to an in-flight message when the consumer dies mid-ack?
- What is the schema-evolution rule (additive-only? registry? none) and who breaks first?
- Backpressure: when the producer outpaces the consumer, what throttles — and what drops?
- Replay: can a consumer re-read history, from how far back, at what cost?

## Rating checks
- FAIL if 'exactly-once' is claimed without naming the dedup mechanism.
- FAIL if any queue lacks a DLQ or an equivalent, with a named operator for it.
- FAIL if two services share a schema with no stated compatibility contract.
