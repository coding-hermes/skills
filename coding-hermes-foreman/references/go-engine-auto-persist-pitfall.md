# Go Engine Auto-Persist Pitfall

## Problem

When a Go engine/method both **processes data AND persists it internally**, tests that
call a separate `Store*` method after the engine will hit UNIQUE constraint violations
on the second insert.

## Root Cause

The engine's `Classify()` (or equivalent) method includes an internal `store.StoreFlows(ctx, flows)`
call as part of its pipeline. This is by design — the engine handles the full
classification + persistence lifecycle. Calling `store.StoreFlows()` separately
after `engine.Classify()` attempts to insert the same rows twice.

## Detection

- Test calls `engine.Classify()` → receives flows → calls `store.StoreFlows()`
- Error: `UNIQUE constraint failed: flows.id (1555)` on the SECOND insert
- The first insert (from the engine's internal call) already succeeded
- Running the test multiple times: random PASS/FAIL depending on which goroutine wins

## Fix

Remove the explicit `store.StoreFlows()` call after the engine method.
The engine already persisted the data. If the engine method's auto-persist
behavior is not desired for a particular test, inject a nil store:

```go
// Engine auto-persists — no separate StoreFlows needed
flows, err := engine.Classify(ctx, sessionID, traces)
// flows are already in the database

// For tests that should NOT persist:
engine := NewClassificationEngine(model, nil, logger) // nil store
```

## Where to check

When encountering a UNIQUE constraint error on a freshly-created in-memory DB,
check the engine/processor method for internal `store.Store*` or `INSERT` calls
BEFORE adding explicit store calls to the test.

## Proven

Rabbit-Hole 2026-07-14 — `ClassificationEngine.Classify()` at
`internal/classify/engine.go:104-108` calls `e.store.StoreFlows(ctx, flows)`
after classification. E2E test `TestE2E_ServeAttachSearchDetach` hit UNIQUE
constraint on the test's subsequent `store.StoreFlows()`. Removing the
duplicate call resolved it. 5/5 deterministic runs pass.
