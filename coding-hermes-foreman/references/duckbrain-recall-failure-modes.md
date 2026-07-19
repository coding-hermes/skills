# DuckBrain `recall` Failure Modes — Foreman Step 3

During Step 3 (DuckBrain Context Load), `recall()` can fail in four known ways. Modes 1–3 are transport-level issues — retrying `recall()` will produce the same error. Mode 4 is an index-staleness issue. The correct fallback for all four is `list_keys(prefix="/project/<name>/")`.

## Failure Mode 1: Missing Embedding Model

**Error:** `"requires embedding model"`

The DuckBrain instance has no embedding model configured. Semantic search (which requires vector embeddings) cannot run.

**Detection:** `recall(query="...", domain="concept")` returns the embedding-model error.

**Action:** Fall back to `list_keys()` immediately. Skip DuckBrain context load if the namespace has no keys.

## Failure Mode 2: BigInt Serialization Error

**Error:** `"Error: Do not know how to serialize a BigInt"`

The DuckBrain MCP transport (Python JSON encoder) cannot serialize a large integer field — usually a Unix timestamp in nanoseconds, a count field, or a uint64 ID. This is a DuckDB result → JSON serialization bug in the MCP server, not a data problem.

**Detection:** `recall()` or any query returning metadata with large numeric values triggers this error.

**Action:** Fall back to `list_keys()`. Do NOT retry `recall()` — the same BigInt values will be in the response.

**Proven:** MusterFlow 2026-07-16 — `recall(keyPrefix="/project/musterflow/")` returned the BigInt error; `list_keys()` worked correctly.

## Failure Mode 3: MCP Transport Timeout / Connection Closed

**Error:** Connection timeout, `ClosedResourceError`, `Connection Error: Connection was never established or has been closed already`, or generic MCP transport failure.

The MCP server process may be down, restarting, or overloaded — or the transport connection was broken and not re-established.

**Detection:** `recall()` returns any of the above errors. This mode has two sub-variants:
- **3a (recoverable via `list_keys`):** `list_keys()` succeeds — the connection is alive for simple calls but `recall()`'s heavier query path failed. Use `list_keys()` as fallback context.
- **3b (full outage):** `list_keys()` also fails with the same connection error — the MCP server is completely unreachable. Skip DuckBrain entirely for this tick.

**Action (3a):** Fall back to `list_keys(prefix="/project/<name>/", maxDepth=3)`. If keys exist, use them as context. Do NOT retry `recall()` — it will fail identically within the same tick.

**Action (3b):** Skip `recall()` and `list_keys()` for this tick — the read path is fully down. **BUT still attempt Step 10 `remember()` write.** The write path uses a different transport connection (or a different code path in the MCP server) and can succeed even when reads fail. If `remember()` succeeds, write the idle-tick counter and status as normal. Only skip Step 10 entirely if `remember()` also fails.

**Do NOT retry `recall()` or `list_keys()` in 3b** — retrying won't open a new connection within the same tick. But `remember()` is a different operation — try it once.

**Proven:**
- Mode 3a: MusterFlow 2026-07-16 (ClosedResourceError, `list_keys` worked)
- Mode 3b: Mythos 2026-07-19 ("Connection was never established or has been closed already", `list_keys` also failed)
- Mode 3b with successful write: DexDat Memory 2026-07-19 — recall + list_keys both returned connection error, but `remember()` succeeded on first attempt. The write path outlives the read path.

## Failure Mode 4: Silent Empty Recall (No Error)

**Symptom:** `recall()` returns `{"memories": [], "count": 0}` — no error message, just zero results. But `remember()` to the SAME key succeeds, and `list_keys(prefix=...)` may show the key exists.

This is NOT a transport failure or serialization error. It's a recall-index staleness issue: the key-value store has the data, but the lookup index used by `recall()` hasn't indexed it yet, or the key-based lookup path differs from the write path. The `remember()` write succeeds independently of the recall index.

**Detection:** recall returns `count: 0` with empty `memories` array, no error string. `remember()` to the same key works (returns UUID, partition, author). Subsequent `recall()` for the same key may still return empty — the index lag can persist across ticks.

**Proven:** Hivemind-work 2026-07-19 and many prior ticks (77–95): `recall(key="/project/hivemind-work/idle-counter")` returned `{"memories":[],"count":0}` on ~70% of ticks, while `remember()` to the same key always succeeded. Ticks where recall worked: 73, 75, 79, 85, 88, 90, 91. Ticks where recall was empty: 74, 76, 77, 80, 81, 82, 83, 84, 86, 87, 89, 92, 93, 94, 95. This is a persistent intermittent index-staleness pattern, not a transient failure.

**Action:**
1. Do NOT retry `recall()` — the index is stale and retrying in the same tick won't help.
2. Fall back to `list_keys(prefix="/project/<name>/")` to confirm key existence.
3. For idle-tick counting: if recall returns empty, treat `consecutive_idle = 0`. Do NOT fabricate a count from `list_keys` output (key names don't carry attribute data). Write `count: 1` via `remember()` — the write succeeds even when recall is broken, and the next tick that gets a working recall will see the accumulated entries to compute the real count.
4. Always attempt `remember()` for the counter write — it succeeds independently of the recall index.

## Common Recovery

All four modes share the same recovery path for the read path. The write path (`remember()`) is treated separately — always attempt it.

### Read path (context load):
```python
try:
    result = duckbrain_list_keys(prefix="/project/<name>/", maxDepth=3)
    keys = result.get("keys", [])
    error = result.get("error")
except Exception:
    keys = []
    error = str(e)

if not keys or error:
    # Either empty project or DuckBrain unreachable (connection error returns error field)
    skip to Step 4 — no DuckBrain context available from recall
else:
    # Use keys as context (key names may indicate what's stored)
    pass
```

### Write path (Step 10 — always attempt):
Even when the read path fails entirely (Mode 3b), the write path may still work. Always attempt `remember()` in Step 10:
```python
try:
    duckbrain_remember(key=..., domain=..., attributes=..., embedding_text=...)
except Exception:
    # Write path also down — skip DuckBrain entirely this tick
    pass
```
