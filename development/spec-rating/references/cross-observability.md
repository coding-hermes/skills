# Cross-cutting: observability

## A spec fails observability rating if any of these is missing
- The golden signals per machine: latency (with the SLO), traffic, errors (classified),
  saturation — named per service, not global hand-waving.
- Log discipline: levels and their meaning, correlation IDs that cross service boundaries,
  what NEVER gets logged (secrets, PII).
- Tracing: the propagation mechanism, sampled how much, one trace exemplar for the
  canonical user flow.
- Alerts: each alert's trigger, why a human must act, and the runbook link. No alert
  without a runbook, no runbook without an owner.
- Dashboards: the per-service panel and the per-user-journey panel, or the admission
  they don't exist yet.

## Rating checks
- FAIL if an SLO is stated with no alert on its burn rate.
- FAIL if errors are one undifferentiated bucket (500s that need different triage).
- FAIL if the canonical flow cannot be traced end-to-end in the design as written.
