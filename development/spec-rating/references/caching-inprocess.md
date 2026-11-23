# Caching: in-process (memoization, app-local caches)

## What a complete in-process cache spec documents
- What is cached per process: keys, value shapes, size bound (entries AND bytes).
- Invalidation: TTL? event-driven? version-tagged? — and the staleness window per key class.
- Coherence across instances: what happens when instance A invalidates and B still holds
  the old value (pub-sub bus? short TTL? accepted staleness, named).
- Warmup: what a cold process does (thundering herd on the backing store? singleflight?).

## Rating checks
- FAIL if the cache has no size bound (unbounded local maps are slow leaks).
- FAIL if multi-instance staleness is neither handled nor accepted in writing.
- FAIL if no singleflight/request-coalescing exists for an expensive cold key.
