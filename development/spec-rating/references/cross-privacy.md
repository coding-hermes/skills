# Cross-cutting: privacy (PII lifecycle)

## What a complete privacy section documents (beyond the security matrix)
- **The PII inventory**: per datum — classification, where it's stored (every store,
  including caches, logs, analytics, backups), why it's collected, lawful basis.
- **Retention**: per datum class, a clock (days/years) and the sweeper that enforces it.
- **Deletion**: the erasure flow that reaches EVERY store in the inventory within the
  promised window; the backup exception and its expiry story; the third-party
  propagation (delete reaches their API too).
- **Minimization**: what we collect but don't need (the deletion is cheaper than the risk).
- **Access**: who inside can read PII, on what trigger, logged how.
- **Breach runbook**: detection -> containment -> notification duties per regime, with
  the 72h clock named.

## Rating checks
- FAIL if any PII store is missing from the erasure flow (backups and caches included).
- FAIL if retention is 'forever' by default with no owner decision.
- FAIL if logs may contain PII with no scrubber and no retention limit.
