# Go Mutex + Blocking I/O Deadlock Pattern

## The Bug

Holding a `sync.RWMutex` write lock during blocking I/O (HTTP calls, DB queries
over slow connections, file reads from network mounts) deadlocks ALL read-lock
attempts for the duration of the I/O.

## Pattern

```go
// BROKEN: health endpoint deadlocks while spawn blocks on HTTP
func (l *Loop) evaluate() {
    l.mu.Lock()
    defer l.mu.Unlock()     // ← held for entire HTTP round-trip
    // ... pick projects ...
    for _, proj := range packed {
        st, _ := l.spawner.Spawn(proj, tickID)  // ← blocks on HTTP POST
        // ...
    }
}

func (l *Loop) LastEvalTime() time.Time {
    l.mu.RLock()            // ← deadlocked until evaluate() finishes
    defer l.mu.RUnlock()
    return l.lastEval
}
```

## Fix: Two-Phase Split

Split the function into a locked state-update phase and a lock-free I/O phase.

```go
func (l *Loop) evaluate() {
    // ---- Phase 1: state update (under lock) ----
    l.mu.Lock()
    l.lastEval = now
    packed := l.packer.Pick(now, l.spawner.RunningSet())
    if len(packed) == 0 {
        l.mu.Unlock()        // ← release before returning
        return
    }
    // Snapshot mutable fields read during spawn phase.
    simulate := l.simulate
    noDeliver := l.noDeliver
    l.mu.Unlock()
    
    // ---- Phase 2: spawn projects (lock-free) ----
    for _, proj := range packed {
        st, _ := l.spawner.Spawn(proj, tickID)  // ← lock-free HTTP call
        // ...
    }
}
```

## Rules

1. **Never hold a write lock across I/O.** The lock should protect in-memory
   state transitions, not external calls.
2. **Snapshot before releasing.** Fields read in the lock-free phase must be
   captured to local variables while the lock is held.
3. **Explicit unlock on early returns.** `defer l.mu.Unlock()` becomes multiple
   explicit `l.mu.Unlock()` calls at each return point.
4. **Health endpoints need RLock only.** If a health check only reads `lastEval`,
   it should use `RLock()`. The write lock during I/O blocks even these readers.

## Detection

- Health endpoint times out but daemon process is alive
- `pprof` goroutine dump shows goroutines in `sync.RWMutex.RLock` waiting
- One goroutine in `http.(*persistConn).roundTrip` (or similar I/O) holding
  the write lock
- `curl :9090/health` hangs indefinitely during slow gateway responses

## Proven

coding-hermes-scheduler BUG-006 (2026-07-18). `evaluate()` held `l.mu.Lock()`
across `GatewayClient.SendResponse()` → HTTP POST to gateway. When gateway
was slow (8+ min), 8 goroutines deadlocked on `RLock()` waiting for health
check. Fix: split into Phase 1 (locked, state update) and Phase 2 (lock-free,
spawn + alert escalation). Commit `6db45e5`.
