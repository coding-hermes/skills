# In-Process Smoke Test Pattern — Express + WebSocket APIs

## Problem

After a worker implements an Express API endpoint, the foreman needs to verify the endpoint works end-to-end. Starting the server as a background process, curling it, and tearing it down is fragile — port conflicts, race conditions on startup, orphaned processes. For WebSocket endpoints, testing requires a second process (ws client) and careful timing.

## Pattern

Boot the Express app + HTTP server + WebSocket server **in-process** inside a single smoke-test script. The script:

1. Imports `createApp()` from the app factory
2. Creates an HTTP server with `createServer(app)`
3. Attaches the stream manager with `attachStreamManager(server)`
4. Starts listening on a random or fixed port
5. Opens a WebSocket client to itself (`new WebSocket(wsUrl)`)
6. Exercises the full API contract via `fetch()` + WebSocket messages
7. Asserts results with simple pass/fail counters
8. Tears down: close WS, close stream manager, close server
9. Exits 0 on all-pass, 1 on any failure

## Template

```typescript
import { createServer } from "node:http";
import WebSocket from "ws";
import { attachStreamManager } from "../../src/websocket/index.js";
import { createApp } from "../../src/app.js";

const PORT = 4800;
const app = createApp();
const server = createServer(app);
const sm = attachStreamManager(server);

await new Promise<void>((r) => server.listen(PORT, r));

// Open WebSocket, subscribe, test endpoints...
const ws = new WebSocket(`ws://127.0.0.1:${PORT}/ws`);
await new Promise<void>((resolve) => ws.on("open", () => resolve()));

// Test: POST endpoint
const res = await fetch(`http://127.0.0.1:${PORT}/api/chat`, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ message: "test" }),
});
check("returns 202", res.status === 202);

// Test: WebSocket receives event
ws.send(JSON.stringify({ type: "subscribe", topic: `request:${streamId}` }));
await sleep(400);
check("ws received phase_change", received.some(m => m.type === "phase_change"));

// Teardown
ws.close(1000);
await sm.close();
await new Promise<void>((resolve) => server.close(() => resolve()));
process.exit(fail > 0 ? 1 : 0);
```

## Key Details

### Direct import, not compiled dist
When the project's `tsconfig.json` only includes `src/` (not `tests/`), the test won't be compiled by `tsc`. Use `npx tsx` to run it directly:

```bash
npx tsx apps/api/tests/chat/srv003-smoke.ts
```

`tsx` compiles and executes TypeScript in one step — no build step needed for test files outside the tsconfig include path.

### WebSocket timing: setTimeout not setImmediate
When the route handler broadcasts a phase_change event after responding 202, use `setTimeout(..., 250)` not `setImmediate()`. `setImmediate` fires on the next event-loop tick — before the HTTP response even reaches the client. The client needs time to parse the response, extract the topic, and send a `subscribe` message over its existing WS connection. 250ms is generous for a local in-process subscriber.

### Idempotency-Key cache in-memory is sufficient for smoke tests
For in-process testing, a simple `Map<string, CachedResponse>` in the route handler works. No Redis or persistent store needed — the test process lives for seconds, and the idempotency cache only needs to survive across two sequential `fetch()` calls.

### Clean teardown order
- Close WS client first (clean disconnect)
- Close stream manager (drains connections)
- Close HTTP server last (releases port)

Wrong order (server before WS) causes the WS close to race against server shutdown.

## When To Use

- Verifying any new Express route that interacts with WebSocket
- Testing request/response + streaming event in one script
- Pre-commit verification (smoke test before guard)
- Worker delivers an endpoint → foreman runs smoke test to confirm

## When NOT To Use

- Integration tests that need real external services (mock them in-process instead)
- Tests that need database state (seed the in-memory store, or use SQLite in-memory)
- Performance/stress tests (use separate processes for realistic timing)

## Proven

HEADING SRV-003 (2026-07-19) — worker implemented POST /api/chat endpoint. Smoke test booted Express + WS in-process, ran 10 scenarios (valid POST, missing body, bad IATA, unknown fields, idempotency dedup, different idempotency key, follow-up session reuse), all 20 assertions passing. Test caught 2 issues: phase_change broadcast timing (setImmediate → setTimeout 250ms) and error code mismatch (VALIDATION_ERROR → INVALID_BODY).
