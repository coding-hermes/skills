# Storage: key-value stores (Redis, Memcached, DynamoDB, etcd class)

## What a complete KV spec documents
- Key namespace convention: `<domain>:<entity>:<id>[@version]` — the grammar, documented,
  because keys ARE the schema.
- Value shapes and sizes: what fits (strings, hashes, JSON blobs), and the byte ceiling per value.
- TTL policy per key class: every key has a TTL or a named reason it is immortal.
- Eviction policy (LRU? LFU? none?) and what the system does when eviction hits a live key.
- Persistence stance: cache-only (loss OK, stated per data class) vs durable (AOF/RFS
  replicas, and the window of loss on failover).

## The questions the spec must answer
- What is the cluster/redundancy story: single instance? sentinel? cluster mode? and what
  does a failover cost the callers (in-flight keys vanish — who re-reads from source of truth)?
- Atomicity: which operations assume atomic single-key ops, and which need Lua/transactions?
- Hot-key: what happens to one key receiving 100k reads/sec (replicas? local cache in front?).

## Rating checks
- FAIL if any key class lacks a TTL without a stated reason.
- FAIL if the source of truth for cached data is not named (cache is the DB = fail).
- FAIL if failover loss semantics are unstated for any key class that holds user-visible state.
