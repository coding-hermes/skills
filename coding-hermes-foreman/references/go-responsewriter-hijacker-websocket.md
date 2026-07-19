# Go responseWriter + WebSocket Hijacker Pattern

## Problem

When Go HTTP middleware wraps `http.ResponseWriter` to capture status codes, request IDs, or other metadata, the wrapper struct typically embeds `http.ResponseWriter` and overrides `WriteHeader()`. This breaks WebSocket upgrades because `gorilla/websocket` (and the standard `golang.org/x/net/websocket`) call `w.(http.Hijacker).Hijack()` on the response writer. The embedded `http.ResponseWriter` field does NOT auto-promote its `Hijacker` implementation — Go only promotes methods, not interface satisfaction through embedded fields for type assertions.

**Error:** `websocket: response does not implement http.Hijacker`

## Fix

Add a `Hijack()` method to the wrapper that delegates to the underlying writer if it supports hijacking:

```go
import (
    "bufio"
    "net"
    "net/http"
)

type responseWriter struct {
    http.ResponseWriter
    statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
    rw.statusCode = code
    rw.ResponseWriter.WriteHeader(code)
}

// Hijack implements http.Hijacker for WebSocket upgrades.
func (rw *responseWriter) Hijack() (net.Conn, *bufio.ReadWriter, error) {
    if hj, ok := rw.ResponseWriter.(http.Hijacker); ok {
        return hj.Hijack()
    }
    return nil, nil, http.ErrNotSupported
}
```

## Detection

- `go test -run TestWebSocket` fails with "response does not implement http.Hijacker"
- Server logs show ERROR with "websocket upgrade failed"
- Client gets HTTP 500 on WebSocket endpoint
- `go build` and `go vet` pass (the issue is a runtime type-assertion failure, not a compile error)

## Why It Happens

Go's `http.ResponseWriter` interface does NOT include `Hijack()`. `http.Hijacker` is a separate optional interface. The standard library's concrete `http.response` (the actual type behind `ResponseWriter` in `http.Server`) DOES implement `Hijacker`. But when middleware wraps the writer in a struct, the type assertion `w.(http.Hijacker)` sees the wrapper type, not the underlying concrete type — and the wrapper doesn't implement `Hijacker` unless explicitly coded.

This is NOT caught by `go vet` or `go build` — it's a runtime type-assertion failure.

## Provenance

Rabbit-Hole Phase 5 (2026-07-12) — 24 express tests all passed except `TestWebSocket`. The `responseWriter` in `middleware.go` wrapped `http.ResponseWriter` for status-code capture and logging, but lacked `Hijack()`. Adding the delegation method fixed it instantly. The same pattern applies to any Go HTTP service that uses middleware wrappers and wants WebSocket support.
