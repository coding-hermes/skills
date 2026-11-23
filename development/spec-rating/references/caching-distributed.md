# Caching: distributed caches (Redis/Memcached as a cache tier)

## What a complete distributed-cache spec documents
- Per cached data class: source of truth, key grammar, TTL, and the failure answer:
  'cache down -> read path falls back to where, at what added load?'
- Stampede defense: singleflight, probabilistic early expiry, or lock — pick and name it.
- Negative caching: do absent results get cached (and for how long), or does every miss
  hit the source?
- Invalidation wiring: WHO publishes the invalidation when the source of truth changes,
  and what happens if that message is lost.

## Rating checks
- FAIL if the fallback path on cache loss is unstated (a cache outage becomes a DB outage).
- FAIL if no stampede defense exists for a hot recomputed key.
- FAIL if invalidation loss has no reconciliation (TTL is the only corrector and TTL is
  assumed — state the max staleness).
