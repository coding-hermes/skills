# Go HTTP Server Test Patterns

Patterns discovered during Rabbit-Hole Phase 5 foreman tick (2026-07-12), where parallel sibling ticks exposed three recurring Go test/server pitfalls.

## 1. Use `net.Listen` Before `Serve` to Capture Actual Port

### Problem
When a server is created with `"127.0.0.1:0"` (OS-assigned port), `http.Server.Addr` stays as `"127.0.0.1:0"` after `ListenAndServe` — it does NOT update to reflect the actual bound port. Tests that call `srv.Addr()` to health-check the server get the wrong address.

### Anti-pattern (don't do this)
```go
// Test workaround: pre-listen to find a port, hope the server re-binds
ln, _ := net.Listen("tcp", "127.0.0.1:0")
addr := ln.Addr().String()
ln.Close() // race: port can be taken before server binds
srv := NewServer(store, logger, addr)
srv.Start() // may fail if port was taken
```

### Fix: pre-listen in Start() itself
```go
func (s *Server) Start(ctx context.Context) error {
    ln, err := net.Listen("tcp", s.srv.Addr)
    if err != nil {
        return fmt.Errorf("listen %s: %w", s.srv.Addr, err)
    }
    s.srv.Addr = ln.Addr().String() // capture actual bound address
    s.logger.Info("starting server", "addr", s.srv.Addr)
    go func() {
        if err := s.srv.Serve(ln); err != nil && err != http.ErrServerClosed {
            s.logger.Error("server error", "err", err)
        }
    }()
    return nil
}
```

Then tests can simply call `NewServer(store, logger, "127.0.0.1:0")` and `srv.Start()` — no port-finding dance needed. `srv.Addr()` returns the actual port.

**Proven:** Rabbit-Hole Phase 5 2026-07-12 — sibling test's `newTestServer` did the pre-listen+close+rebind workaround which failed intermittently; fixing `Start()` with `net.Listen` made all 22 tests pass reliably.

---

## 2. Nil-Safe Logger in Middleware

### Problem
When `withMiddleware(next, logger)` is called with a nil logger (common in tests: `NewServer(store, nil, addr)` or `withMiddleware(mux, nil)`), any panic in the handler triggers `logger.Error()` on the nil pointer, causing a secondary nil-pointer-dereference crash that masks the original panic.

### Fix
```go
func withMiddleware(next http.Handler, logger *slog.Logger) http.Handler {
    if logger == nil {
        logger = slog.Default()
    }
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // ... request ID, CORS, panic recovery, logging
    })
}
```

**Proven:** Rabbit-Hole Phase 5 2026-07-12 — `TestMiddleware_PanicRecovery` called `withMiddleware(mux, nil)` and the panic-recovery handler crashed on nil `logger.Error()` call. Adding the nil guard fixed it immediately.

---

## 3. Nil `*bytes.Buffer` vs Nil `io.Reader` Interface Pitfall

### Problem
In Go, a nil concrete type wrapped in an interface is NOT a nil interface. When a test helper declares:
```go
var bodyReader *bytes.Buffer  // nil *bytes.Buffer
```
And passes it to `http.NewRequest(method, url, bodyReader)`, the parameter type is `io.Reader`. A nil `*bytes.Buffer` wrapped as `io.Reader` is a non-nil interface (it has a type, just a nil value). `http.NewRequest` calls `bodyReader.(*bytes.Buffer).Len()` which panics on the nil receiver.

### Fix
Declare as the interface type:
```go
var bodyReader io.Reader  // truly nil interface
if body != nil {
    bodyReader = bytes.NewBuffer(b)
}
// http.NewRequest handles nil io.Reader correctly
```

**Proven:** Rabbit-Hole Phase 5 2026-07-12 — `doJSON(t, "GET", url, nil)` in a sibling's test crashed with `bytes.(*Buffer).Len` nil pointer dereference. Changing to `var bodyReader io.Reader` fixed it.
