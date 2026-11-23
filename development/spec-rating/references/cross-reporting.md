# Cross-cutting: reporting & analytics

## What a complete reporting/analytics section documents (when the product
reports on its own data)
- **The question inventory**: every report/dashboard the product promises,
  with the query shape behind it and the volume it runs at.
- **Source of truth**: analytics read from the OLTP store (small scale), a
  replica, or a dedicated warehouse — decided, with the sync lag stated.
- **Aggregation policy**: pre-aggregated rolls vs query-time aggregation; the
  materialized-view refresh schedule; what the user sees mid-refresh.
- **Correctness boundaries**: late/duplicate events, timezone bucketing, and
  the restatement policy when numbers change (audit-grade vs best-effort,
  stated per report).
- **Export & API**: the data-access contract for downstream consumers
  (formats, pagination, rate limits).

## Rating checks
- FAIL if a dashboard's query cost at stated volume is unexamined (the 3am
  DB-killing report).
- FAIL if numbers can silently change without a restatement policy.
- FAIL if the analytics store's lag vs OLTP is unstated while any report
  promises 'current' data.
