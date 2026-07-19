# Go Test Port-Dependent Error Assertions

## Problem

Tests that hit `localhost:<port>` with `http.Get()` or `client.Get()` produce different error messages depending on whether anything is listening on that port:

- **Nothing listening** → `connection refused` → the HTTP client returns an error wrapping with phrases like `"fetch spec from ..."` or `"Get ...: dial tcp ...: connect: connection refused"`
- **Something listening but returns non-200** → the HTTP call succeeds but status check fails → error wraps with phrases like `"unexpected status 404"`

A test assertion that checks for ONE of these patterns will intermittently fail depending on the environment's port state.

## Detection

Tests that hit hardcoded ports like `localhost:19999`, `localhost:12345`, etc. and assert on a specific substring of the error message. When CI or a different machine has different port occupancy, the assertion breaks.

## Fix

Accept either error path in the assertion. Use `strings.Contains` with OR logic rather than a single `assert.Contains`:

```go
// BEFORE — brittle, depends on port state
assert.Contains(t, err.Error(), "fetch spec")

// AFTER — accepts either error path
errStr := err.Error()
assert.True(t, strings.Contains(errStr, "fetch spec") || strings.Contains(errStr, "unexpected status"),
    "error should indicate fetch failure, got: %s", errStr)
```

Also rename the test to reflect both code paths (e.g., `"handles unreachable/error URL"` instead of `"handles unreachable URL"`).

## Proven

- **Muster** (2026-07-13, tick #42): `TestNewDiscoverCommand/handles_unreachable_URL` in `internal/builtin/discover_test.go` hit `localhost:19999/nonexistent`. On different runs, the port was either closed (connection refused → "fetch spec") or had a listener returning 404 (→ "unexpected status"). Fixed with dual-path assertion. Commit `ba555e5`.
