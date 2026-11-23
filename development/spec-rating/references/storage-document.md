# Storage: document databases (MongoDB, Couchbase, Firestore class)

## What a complete document-store spec documents
- Document shapes (the schema — document DBs have schemas, they just enforce them late).
- Embedding vs referencing per relationship, with the read pattern that justifies each choice.
- The access patterns: every query the app runs, with the indexes backing each
  (compound indexes in the right key order; a document DB without declared access
  patterns degenerates into collection scans).
- Consistency: read/write concern per operation class; what staleness is tolerable.
- Transaction scope: what fits in one document (atomic) vs what needs multi-doc
  transactions (and their cost) or idempotent compensation.

## The questions the spec must answer
- What is the 16MB-document escape hatch when a document wants to grow unboundedly
  (comments on a hot post, audit trails)?
- Sharding/partition key: chosen by what access pattern, and what skew is expected?
- Migration: how does a shape change roll out across documents written by two versions?

## Rating checks
- FAIL if any relationship's embed-vs-reference choice is unstated.
- FAIL if a hot query has no index and no acceptance of the scan.
- FAIL if unbounded array growth inside a document is not called out and bounded.
