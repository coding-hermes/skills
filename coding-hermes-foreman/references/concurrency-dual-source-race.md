# Concurrency — Dual Source-of-Truth Race

## Pattern

When two separate data structures track the same thing, they WILL diverge under load.

## Classic case: semaphore channel + mutable counter

```go
// WRONG — two sources of truth
type Limiter struct {
    mu           sync.RWMutex
    currentCount int          // source A
    semaphore    chan struct{} // source B (len(chan))
}

func (l *Limiter) Acquire() {
    l.semaphore <- struct{}{}  // increment source B
    l.mu.Lock()
    l.currentCount++            // increment source A
    l.mu.Unlock()
    // WINDOW: semaphore shows N+1, currentCount still shows N
}
```

**Observed failure:** ConcurrencyLimiter allowed 12 concurrent when limit was 10. Race detector caught it.

## Root cause

Between `<-semaphore` (Release) and `currentCount--`, a new Acquire can grab the freed slot. Counter shows stale value → overshoot.

## Fix: derive from channel only

```go
// RIGHT — single source of truth
func (l *Limiter) CurrentCount() int {
    return len(l.semaphore)
}
// Remove currentCount and mutex entirely.
```

The channel IS the semaphore. `len(chan)` is atomic enough for metrics. No separate counter needed.

## Check during discovery sweep (Step 1.5a)

When running `go build` checks, grep for `sync.Mutex` near any `chan` field in the same struct. If a struct has both, flag it for review — it's likely a latent race.

## Session evidence

DexDat Memory 2026-07-14 — ConcurrencyLimiter (internal/config/concurrency_limiter.go). 70 lines removed, 20 added. Fixed by deriving count from `len(c.semaphore)`.
