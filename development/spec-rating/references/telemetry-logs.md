# Telemetry: the logging pipeline (logs are a system, not a stdlib call)

Logs are produced by every machine, consumed by humans and machines, cost
real money, and leak PII if undisciplined. The spec treats logging as a
pipeline with owners.

## What a complete logging spec documents
- **The logging standard per codebase**: library, structured format (JSON
  with schema), level semantics (what ERROR means vs WARN — one sentence
  each, enforced), and the field vocabulary (correlation/request ids,
  actor, component) that crosses service boundaries.
- **Collection & transport**: how logs get from process to queryable store
  (agent/collector per machine, the transport, the buffering when the
  backend is down — log loss vs backpressure stated per class).
- **The store & retention tiers**: hot (queryable, days), warm, cold
  (archive) — retention PER LOG CLASS (audit logs keep longest; debug
  logs die in hours), with the cost at stated volume.
- **PII discipline at ingest**: the scrubber (denylist fields, the
  surprise-PII detector), and the access control on the log store (who
  can read production logs — that's reading user data).
- **The query access**: how an operator asks a question across services
  (the correlation id journey), and the saved-query/runbook integration.
- **The cost governor**: log volume per service is a budgeted metric —
  the runaway-logger alert (a debug loop writing GBs is an incident).

## Rating checks
- FAIL if log levels have no stated semantics (ERROR means 'I saw it').
- FAIL if no PII scrubbing exists between the app and the store.
- FAIL if retention is 'whatever the default is' for any class holding
  user data.
- FAIL if the correlation id doesn't survive across service hops.
