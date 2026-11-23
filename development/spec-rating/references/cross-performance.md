# Cross-cutting: performance

## A spec fails performance rating if any of these is missing
- Latency budgets per user-visible operation (p50/p95/p99), derived from UX needs,
  decomposed per hop so the tail is attributable.
- Throughput targets at named concurrency, with the growth curve (2x users = ? cost).
- Resource envelopes: CPU/memory/IO per machine at target load, with the scaling axis
  (vertical until when? horizontal on what dimension?).
- The known expensive operations and their mitigation (N+1 queries, full scans, chatty
  APIs, large payloads).
- Measurement plan: what is benchmarked, on what data volume, and the regression gate.

## Rating checks
- FAIL if any budget exists only as an adjective.
- FAIL if the traffic patterns section and the performance section disagree.
- FAIL if no operation has a named regression gate (perf always loses to features otherwise).
