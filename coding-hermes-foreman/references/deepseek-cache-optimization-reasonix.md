# DeepSeek Cache Optimization — Reasonix Architecture Patterns

## Source
DeepSeek Reasonix (`esengine/DeepSeek-Reasonix`), MIT license, launched May 25, 2026. A Go-based terminal coding agent purpose-built for DeepSeek's prefix cache.

## Real-World Results

From a user's DeepSeek dashboard on **2026-05-01**, anonymized:

| Metric | Value |
|--------|-------|
| Input — cache hit | 435,033,856 |
| Input — cache miss | 767,616 |
| Output | 179,763 |
| Day total | 435,981,235 |
| **Cache hit ratio** | **99.82%** |

Cost comparison:

| Scenario | v4-flash cost/day | v4-pro cost/day |
|----------|------------------|-----------------|
| 99.82% cached (Reasonix) | $1.38 | $2.07 |
| 0% cache (naive client) | $61.06 | $189.73 |
| **Savings** | **97.7%** | **98.9%** |

Bane's Hermes current: **96.73%** cache hit rate on v4-pro (from June 14–July 13, 2026 usage data), resulting in ~$14.34/day. At 99.82%, daily cost would drop to ~$2/day.

## Four Architectural Pillars

DeepSeek's API ships prefix caching enabled by default. The cache is DeepSeek's; the hit rate is the CLIENT'S. Different clients on the same API produce wildly different hit rates:

- DeepSeek web chat: 60–80% within a conversation, 0% on new session
- Cherry Studio / Open WebUI / generic OpenAI SDKs: 30–60%
- Cline / XML-tool-call clients: even lower (tool results inline into conversation, shifting cache keys)

99.82% comes from these four design choices in Reasonix:

### 1. `ImmutablePrefix`
System prompt + tool specs are frozen at session start. Same byte sequence every turn. Every request shares the same prefix, so DeepSeek's cache never misses on it.

**For Hermes workers:** Freeze tool definitions and system prompt at session start. Never re-serialize tool specs between turns. Any change to the system prefix breaks the cache key for ALL subsequent turns.

### 2. `AppendOnlyLog`
Turns only append. No reordering messages, no editing history in place. Every byte added to the conversation stays at a fixed position. The prefix (everything before the latest turn) stays cache-stable.

**For Hermes workers:** Do not reorder conversation history. Do not edit prior messages. Append-only. If compaction is needed, see Auto-compact below.

### 3. `VolatileScratch`
Chain-of-thought reasoning and per-turn scratch work lives OUTSIDE the cached prefix. Reasoning tokens from DeepSeek V4 Pro don't poison the next turn's cache hit because they're never part of the cached prefix.

**For Hermes workers:** DeepSeek V4 Pro's reasoning tokens should NOT be stored inline in the conversation history. Store them separately and strip before the next API call. If 10K reasoning tokens sit in the message history, the next turn loses the cache hit on those 10K bytes plus everything after them.

### 4. `Auto-compact`
When context approaches the cap, older turns fold into a summary message. The summary request is shaped to reuse the already-cached system/tool/history prefix. The following main-agent request pays a cold miss ONLY for the newly synthesized summary segment — not the entire history.

**For Hermes workers:** When compacting conversation history, generate the summary using a SEPARATE request that reuses the cached prefix. Then insert the summary as a single new message. The next turn pays cache miss only for the summary — not the entire history dump.

## How Generic Clients Break Cache

The four patterns above exist because generic clients inadvertently break cache in four ways:
1. Re-serializing tool specs per request (every serialization produces slightly different byte sequences)
2. Reordering conversation history (assistant messages spliced between user messages, or vice versa)
3. Storing reasoning tokens inline (each turn's reasoning produces unique bytes that shift the prefix for subsequent turns)
4. Naive compaction (the summary request uses a different prefix than the main agent, so the next turn is a cold miss)

## Provenance
- June 28, 2026 session: Research on Reasonix vs Hermes worker architecture
- Benchmarks from `esengine/DeepSeek-Reasonix/benchmarks/real-world-cache/`
- Bane's usage data: June 14–July 13, 2026: 96.73% cache hit, $430.26 over 30 days
