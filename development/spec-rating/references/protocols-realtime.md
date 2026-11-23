# Interface: realtime (WebSocket, SSE, streaming)

## What a complete realtime spec documents
- Transport + fallback: WS, with SSE/long-poll fallback for hostile proxies; protocol upgrade path.
- Frame schema: every message type, both directions, with one example each.
- Lifecycle: connect handshake, auth, heartbeat interval, idle timeout, reconnect policy
  (backoff, jitter, resume cursor).
- Backpressure: what happens when the client is slow (drop? buffer cap? disconnect?),
  and when the server is slow.

## The questions the spec must answer
- Is delivery at-most-once or at-least-once per message type, and what does the client dedup?
- What is the resume contract after a drop (missed messages? snapshot + delta? reconnect cold)?
- Fan-out math: at the stated concurrent-user target, how many sockets per server instance,
  and what shares state across them?

## Rating checks
- FAIL if reconnection is 'the client reconnects' without resume semantics.
- FAIL if no heartbeat/timeout is stated (half-open sockets accumulate).
- FAIL if any message type lacks a schema because 'it is just JSON'.
