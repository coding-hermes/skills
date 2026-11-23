# Interface: HTTP services (REST/HTTP APIs)

## What a complete HTTP spec documents
- Per endpoint: method, path, auth tier, request schema, response schema (success AND each
  error class), pagination, rate limit, idempotency key rule.
- Conventions once, globally: date/time format (ISO-8601 UTC), currency/units, ID format,
  envelope shape, error code taxonomy (machine codes + human messages).
- Versioning: URL vs header, deprecation window, how clients learn they are deprecated
  (Sunset header? response field?).

## The questions the spec must answer
- What does a 409 mean HERE, concretely — which conflicts, with which payload?
- Which endpoints are safe to retry, and which need an idempotency key to be safe?
- What is the pagination contract for unbounded collections (cursor vs offset, sort stability)?
- How does a client discover the API (OpenAPI served? hand-written only?) and is the served
  doc authoritative or advisory?

## Rating checks
- FAIL if the error envelope exists only as prose ('returns an error').
- FAIL if any state-changing endpoint lacks both an idempotency rule and a retry answer.
- FAIL if pagination exists but no stability guarantee is stated for concurrent writes.
