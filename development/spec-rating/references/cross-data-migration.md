# Cross-cutting: data migration & backfills

Existing data is a first-class spec input. A spec that designs green-field
behavior while ignoring the data that already exists is incomplete if:

## What a complete migration section documents
- **The inventory**: what data exists today (stores, volumes, owners), and what
  happens to each class (migrate / archive / discard — with who decided).
- **The strategy per class**: big-bang vs dual-write vs expand/contract; the
  cutover moment; the read-from-old fallback window.
- **Backfill mechanics**: idempotent backfill jobs, checkpointing, throughput
  throttling (backfills must not become the day's outage), and the resume path.
- **Verification**: row counts, checksums, sampled deep-compare — and the sign-off
  owner for 'the data moved correctly'.
- **Rollback**: the point of no return, named precisely; what makes old reads work
  until it's passed.

## Rating checks
- FAIL if any store's existing data is unaddressed.
- FAIL if a backfill has no checkpoint/resume (a 3am failure restarts from zero).
- FAIL if 'the migration' has no verification artifact — trust is not a control.
