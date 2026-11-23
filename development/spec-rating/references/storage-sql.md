# Storage: relational / SQL

## What a complete SQL spec documents (beyond table format)
- Schema: tables, columns, types, nullability, defaults, constraints (FK, unique, check).
- THE QUERIES: the query set the system will run — not 'we will query it', the actual
  query shapes, with the WHERE clauses and join paths.
- THE INDEXES: which indexes exist because which query needs them. Every query in the
  hot set maps to an index or is explicitly accepted as a scan.
- Transactions: isolation level per use case, where multi-statement transactions wrap
  business invariants, and which invariants live in the DB (constraints) vs the app.
- Migration policy: expand/contract, lock windows, who reviews, rollback per migration.

## The questions the spec must answer
- What is the row-count and growth curve per table (this decides partitioning and archival)?
- Which queries must be < X ms at the stated volume, and what proves the plan does that?
- Connection model: pool size, per-service credentials, statement timeout, lock timeout.
- Backup/restore: RPO/RTO, test-restore cadence, PITR or not.

## Rating checks
- FAIL if indexes are listed without the queries they serve.
- FAIL if a business invariant exists only in application code with no DB constraint
  and no statement of the race window that implies.
- FAIL if no query names a latency budget at a named volume.
