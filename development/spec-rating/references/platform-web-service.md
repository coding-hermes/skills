# Platform: web service (HTTP API + server-rendered or SPA client)

A spec for a web service is incomplete without:

## Decisions that must be stated
- Process model: what serves requests (threads, workers, event loop), how many, behind what.
- The full surface: every route/verb, or the rule that generates them.
- Auth: who authenticates, how (token/session/mTLS), what expires, what refresh looks like.
- Rate limiting, request size caps, timeouts — per route class, not global-only.

## Contracts a builder needs
- One request/response example per route class, INCLUDING the error envelope
  (shape of a 4xx/5xx body — a builder must not invent it).
- Versioning rule: how a breaking change ships (header, path, new host).
- Idempotency rule for every non-GET that moves state (retry-safe or not).

## Failure paths that must be specified
- Dependency down (DB, cache, upstream API): what the endpoint returns, what it logs.
- Overload: which requests shed first, what the client sees.
- Graceful degradation list: what works with the DB up but the cache down, and vice versa.

## Rating checks
- FAIL if error responses are described only as 'proper error handling'.
- FAIL if no timeout is stated for any outbound call the service makes.
- FAIL if the spec names a route whose auth tier is unstated.
