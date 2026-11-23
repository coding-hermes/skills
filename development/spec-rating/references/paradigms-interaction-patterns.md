# Paradigm: individual vs batch vs stream vs queue (the interaction-pattern decision)

The HTTP philosophy question, generalized: for EVERY interaction between
two machines, the spec chooses the pattern deliberately.

## The pattern set and what each demands
- **Individual request/response**: one call per unit. Demands: the call-rate
  math (chattiness check: calls per user journey), per-call overhead budget,
  and the N+1 answer (the client-side aggregation or the bulk endpoint).
- **Batching**: N units per call. Demands: the batch boundary rule (size
  cap, time window — 'flush every 100 items or 250ms, whichever first'),
  partial-failure semantics (one bad unit fails the batch? per-item
  results? stated), and the latency cost accepted.
- **Streaming**: a continuous relationship. Demands: the framing (what
  delimits a record), the backpressure contract (what happens when the
  consumer is slow — THE failure mode of streams), resume/checkpoint, and
  the delivery guarantee per record.
- **Queueing**: decouple in time. Demands: durability (what a queue loss
  costs), ordering stance, dedup, the DLQ, and the backlog SLO (a queue
  that grows unbounded is a delay, not a buffer — the max-delay answer).
- **Pub/sub**: one event, many consumers. Demands: the schema contract per
  topic, per-subscriber delivery guarantees, and the fan-out cost model.

## The decision criteria (why you pick each)
Latency need, throughput need, durability need, ordering need, coupling
tolerance, and the load shape (bursty flows want queues; interactive flows
tolerate neither queue delay nor batching latency). A flow that needs BOTH
interactivity AND burst absorption states the hybrid: accept-then-process
(queue at the edge, sync response with a job id).

## Rating checks
- FAIL if a chatty pattern (N individual calls where one batch fits) is
  chosen without defending the overhead.
- FAIL if a batch's partial-failure semantics are unstated.
- FAIL if a stream exists with no backpressure contract.
- FAIL if a queue exists with no max-delay answer (unbounded backlog =
  silent data loss from the user's perspective).
