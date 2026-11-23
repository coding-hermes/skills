# Telemetry: distributed tracing (the journey across machines)

## What a complete tracing spec documents
- **Propagation**: the trace-context format and headers; every hop
  (HTTP, queue, scheduled job) propagates — a hop that starts a NEW trace
  id breaks the journey and is named as a violation.
- **Sampling**: the strategy (head/tail, the rate per class), and the
  keep-always rule for errors and the canonical flow.
- **Span discipline**: what gets a span (outbound calls, DB queries, queue
  produces, the slow steps), the attribute vocabulary, and the
  no-PII-in-attributes rule.
- **The exemplar flow**: the canonical user journey has a reference trace
  in the spec — the shape a healthy request should look like, so an
  operator can diff reality against it.
- **The storage & query**: retention (traces are heavy), the search model
  (by trace id from a log line; by service; by latency outlier), and the
  cost control.

## Rating checks
- FAIL if the canonical journey cannot be traced end-to-end in the design.
- FAIL if any async hop (queue/cron) breaks trace continuity without a
  stated carrier (baggage/field in the payload).
- FAIL if sampling drops 100% of errors.
