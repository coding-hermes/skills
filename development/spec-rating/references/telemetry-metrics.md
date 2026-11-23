# Telemetry: the metrics system (exposition to dashboard to SLO)

## What a complete metrics spec documents
- **The metric inventory per machine**: the golden signals (latency,
  traffic, errors, saturation) PLUS the domain metrics (queue depth, cache
  hit rate, model tokens/min, backlog age) — each metric has: name
  convention, unit, labels, and the question it answers.
- **Exposition & collection**: pull vs push, the scrape interval, the
  exposition format, and what happens when a machine is unreachable
  (gap = distinct from zero).
- **Cardinality control** (the classic explosion): per metric, the label
  cardinality bound (user-id as a label = death); the allowed-labels
  review; the runaway-cardinality alert.
- **Storage & downsampling**: raw retention window, rollup rules, and the
  query-latency contract for dashboards.
- **Dashboards as code**: per service panel + per user-journey panel,
  versioned in-repo, reviewed like code (a dashboard nobody owns rots).
- **SLO integration**: the SLO burn-rate queries derive from these metrics
  (cross-slo.md), and the error-budget alerts reference the same series.
- **The per-machine health standard**: every machine ships the same
  minimal metric set (up, restarts, resource saturation, its domain
  metrics) — the fleet looks uniform from the monitoring seat.

## Rating checks
- FAIL if any metric lacks a stated question it answers (dashboards of
  trivia).
- FAIL if cardinality is unbounded for any high-frequency metric.
- FAIL if dashboards exist only in someone's browser (not as code).
- FAIL if the machine inventory (cross-machines.md) and the metric
  inventory disagree.
