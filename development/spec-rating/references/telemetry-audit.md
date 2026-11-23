# Telemetry: the audit pipeline (immutable trails, consumed by review)

Audit logs answer 'who did what' for compliance, forensics, and trust —
they are a legal artifact, not debug output.

## What a complete audit spec documents
- **The event inventory**: every auditable action (auth events, permission
  changes, data access/export/delete, config changes, financial actions)
  with: actor, subject, timestamp (UTC, monotonic-safe), source, reason.
- **Immutability**: the append-only store (WORM/object-lock at the storage
  layer, not app discipline), the integrity verification (hash chains or
  external anchor), and the tamper answer (who is alerted when the trail
  is modified).
- **Retention & legal hold**: the retention clock per event class (the
  compliance floor), the legal-hold override, and the certified-deletion
  path when retention ends (cross-privacy.md rules apply to audit logs
  too — PII in audit trails has a deletion answer).
- **Access & review**: who can read the trail (least privilege, the read
  is itself audited), and the CONSUMPTION cadence — access reviews, the
  anomaly review job, the report an auditor gets. An audit trail nobody
  reads is a liability with extra steps.
- **Completeness**: the action inventory is checked against the surface
  inventory (every mutating endpoint emits an audit event or is listed
  with the reason it needn't).

## Rating checks
- FAIL if audit storage is mutable by the application that writes it.
- FAIL if any state-changing action lacks an audit event (or a listed
  exemption).
- FAIL if the trail has no consumption/review loop (written, never read).
