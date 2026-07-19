# Sidecar Glue-Package Investigation Pattern

## When to Use

When a task board item asks to create a "routing," "glue," or "coordination" package in
a sidecar project that imports a full-featured dependency, treat the task as
**investigation-first** rather than implementation. The dependency may already handle
all the pipeline logic — the task was likely written before the full integration existed.

## Detection Signals

1. Task asks for a new package in `<sidecar>/internal/<name>/`
2. The sidecar's `main.go` already imports and starts components from a dependency that
   handles the same pipeline (harness, API server, shim, event bridge)
3. The ACs describe a message/data flow that maps 1:1 onto the dependency's architecture
4. The package name is generic (routing, pipeline, orchestration) — not a specific
   algorithm or adapter

## Investigation Steps

1. **Trace the ACs against the dependency code** — grep for each pipeline stage:
   ```bash
   grep -rn "ReadActiveContext\|CallLLM\|ParseAgentResponse" <dep>/internal/harness/
   grep -rn "AgentOutput\|memory_state_changes\|system_actions" <dep>/internal/harness/
   grep -rn "EventBus\|Subscribe\|SSE\|text/event-stream" <dep>/internal/api/
   grep -rn "staging_buffer\|planning" <dep>/internal/harness/
   ```

2. **Verify the sidecar's main.go wires all dependency components** — if the sidecar
   starts the harness heartbeat, mounts the API server, opens the shim, and connects
   the event bridge, the pipeline is complete.

3. **Compile and test** — `go build ./... && go vet ./... && go test ./... -short` on
   the sidecar to confirm the dependency integration works.

4. **Check dependency's integration tests** — the dependency likely has E2E tests
   covering the full pipeline (e.g., `e2e_real_llm_serve_test.go`,
   `full_stack_e2e_test.go`).

## Decision

| Finding | Action |
|---------|--------|
| ALL ACs map to existing dependency code | Mark task `[x]` with note "pipeline already implemented in <dependency>" — **shortened loop, no worker** |
| Some ACs map, some don't | Narrow task to only the missing ACs. Create subtasks for specific gaps. |
| None of the ACs map — dependency doesn't handle it | Spawn a worker for full implementation |

## Why This Matters

Spawning a worker to create a routing package that the dependency already handles is
wasteful. The worker will either:
- Create an unnecessary pass-through layer that duplicates the dependency's API
- Discover the duplication and produce nothing (silent exit)
- Import the dependency's types and re-export them (pointless code)

**Proven:** DexDat CONSENSUS-9 (2026-07-13) — task asked for
`consensus-sidecar/internal/routing/` to implement message pipeline (user→LLM→user).
The Consensus module (`/home/kara/consensus`) already had:
- `internal/harness/` — ReadActiveContext, heartbeat, LLM call, AgentOutput parsing,
  memory_state_changes, system_actions, tool_requests, audit logging
- `internal/api/` — EventBus, SSE, session management, message service
- `internal/shim/opencode/` — protocol translation, `/session/{id}/message` endpoint
- `internal/harness/planning.go` — staging_buffer, multi-turn planning

All 10 ACs mapped to existing code. Shortened loop: verified, marked `[x]`, no worker.
