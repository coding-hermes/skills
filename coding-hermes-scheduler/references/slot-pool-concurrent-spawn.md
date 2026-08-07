# SlotPool — Concurrent Tick Spawning (BUG-007 Fix)

**Commit:** `85c8612` (2026-07-18) — named channels, ticker-only, BUG-008 resolved
**Previous:** `106ee47` (event-driven SlotFreed, reverted in `85c8612` due to BUG-008 flood)
**Author:** Bane-directed fix: "this is not hard your failing at basic semaphore programming"

## Problem (BUG-007)

`evaluate()` spawned projects in a sequential `for range packed` loop. Each `spawner.Spawn()` called the gateway HTTP API and blocked until the response returned. With 12 projects selected, a single slow tick (e.g. <project> taking 20+ minutes) starved the other 11. `evaluate()` never returned → next eval cycle never fired → entire fleet stalled.

## Solution (v3.2 final)

Buffered channel as a semaphore. Cap = `maxConcurrent`. Each project spawns in its own goroutine. The goroutine acquires a slot (blocks if all N slots are occupied), spawns via gateway, waits for completion or 900s timeout, and releases the slot.

**Named channel (`chan string`, not `chan struct{}`):** The semaphore stores project names so `RunningSet()` can return the in-flight set for the packer. This prevents duplicate spawns from consecutive eval cycles. Without named channels, `RunningSet()` returns an empty map, the packer's DB query sees 0 running ticks (SlotPool goroutines haven't committed to DB yet), and the same projects are spawned again.

`evaluate()` fires goroutines and returns immediately in <1 second. The semaphore enforces the concurrency cap without blocking the eval loop.

## Architecture

```
evaluate()  ← returns in <1 second
  ├─ Phase 1 (locked): cleanup + pick N projects
  └─ Phase 2 (lock-free):
       for each project: slotPool.Spawn(proj)   ← goroutine, returns immediately
         │
         ├─ Acquire slot (channel semaphore, cap=N, stores project name)
         │    blocks here if all N slots occupied — max 5min wait then drops
         │
         ├─ Enqueue + StartRunning in lifecycle tracker
         │
         ├─ spawner.Spawn(proj, tickID)  ← gateway HTTP API call
         │
         ├─ Wait for completion or 900s timeout (matches default cooldown)
         │
         ├─ Release slot
         │
         ├─ Deliver output via hermes send
         └─ Auto-slowdown check
```

## Code (final `chan string` version)

```go
type SlotPool struct {
    sem       chan string // buffered channel = semaphore, value = project name
    maxSlots  int
    timeout   time.Duration
    spawner   *Spawner
    lifecycle *LifecycleTracker
}

func NewSlotPool(maxConcurrent int, timeout time.Duration, spawner *Spawner, lifecycle *LifecycleTracker) *SlotPool {
    return &SlotPool{
        sem:       make(chan string, maxConcurrent),
        maxSlots:  maxConcurrent,
        timeout:   timeout,
        spawner:   spawner,
        lifecycle: lifecycle,
    }
}

func (p *SlotPool) Acquire(ctx context.Context, name string) bool {
    select {
    case p.sem <- name:
        return true
    case <-ctx.Done():
        return false
    }
}

func (p *SlotPool) Release() {
    select {
    case <-p.sem:
    default:
    }
}

// RunningSet returns the set of project names currently occupying slots.
// Used by the packer to prevent duplicate spawns across eval cycles.
func (p *SlotPool) RunningSet() map[string]bool {
    set := make(map[string]bool)
    for i := 0; i < len(p.sem); i++ {
        name := <-p.sem
        set[name] = true
        p.sem <- name
    }
    return set
}
```

## Event-Driven Re-Eval — REMOVED (BUG-008)

v3.1 added `SlotFreed()` — a channel that fired when any slot was released, triggering immediate re-evaluation. This caused a feedback-loop flood:

```
tick completes → release slot → SlotFreed fires → evaluate() → spawn N more ticks
→ those ticks complete → release slots → SlotFreed fires → evaluate() → ...
→ 1388 ticks in 5 minutes
→ gateway rate-limited (max 10 concurrent), 2 ticks always fall back to exec.Command
→ CPU + IO saturated
```

**Removed in v3.2.** The 60s ticker is sufficient — SlotPool fires all N spawns at once, so the eval cadence is predictable. Event-driven re-eval added complexity and enabled runaway flooding.

## Gateway Rate Limit

Hermes gateway caps concurrent runs at **10**. `--max-concurrent` must be ≤10. At 12, the gateway returns `rate_limit_error — Too many concurrent runs (max 10)` and 2 of 12 ticks always fall back to `exec.Command`.

## Key Principles

1. **Never block the eval loop on I/O.** Phase 1 picks projects under lock (<1s), Phase 2 fires goroutines with a semaphore cap.
2. **Named semaphore channels** let the packer see in-flight ticks. Without this, DB-query-alone spawns duplicates.
3. **Ticker-only eval** (60s) is sufficient when SlotPool fires all N spawns concurrently. Event-driven refill adds risk of feedback loops.
4. **Match gateway limits:** `--max-concurrent` ≤ 10 to avoid rate_limit_error fallbacks.

## Files

- `internal/scheduler/slot_pool.go` — new file (~130 lines, `chan string` + `RunningSet()`)
- `internal/scheduler/loop.go` — Sequential spawn loop (80+ lines) replaced with `l.slotPool.Spawn()` calls. `SlotFreed()` case removed. `SetTickTimeout` initializes the pool.
