# Paradigm: data processing pipelines (batch ETL, stream processing, CDC)

When the system transforms data at scale (not per-request), the pipeline is
a first-class machine with its own spec.

## What a complete pipeline spec documents
- **The shape**: batch (on schedule), streaming (on event), or CDC (on
  change-log) — chosen by freshness need vs cost, stated with the freshness
  SLO the choice delivers.
- **Process topology**: every stage, its input/output schema, its parallelism,
  and its failure answer (retry the stage? skip? dead-letter the record?).
- **Exactly-once honesty**: most pipelines are effectively-at-least-once;
  the spec names the dedup mechanism (idempotent writes, transactional
  sink, keyed upserts) that makes replay harmless.
- **Late & out-of-order data**: the watermark/grace-window answer, and what
  happens to records older than it.
- **Schema evolution**: the source schema WILL change; the compat rule and
  the poison-schema quarantine.
- **Backfill**: every pipeline gets re-run for a date range — the re-run is
  idempotent, throttled, and verifiable (cross-data-migration.md rules apply).
- **Observability**: lag per stage, records/sec in/out, error rate — the
  pipeline is monitored as a machine (it is one).

## Rating checks
- FAIL if replay of any window is not idempotent.
- FAIL if late data is unhandled (it always arrives).
- FAIL if no lag metric exists for a pipeline whose consumers assume freshness.
