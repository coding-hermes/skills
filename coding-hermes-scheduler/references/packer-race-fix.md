# BUG-005: Packer/Spawner Concurrency Race — RunningSet Merge

## Symptom (2026-07-18)

After gateway startup race fix, scheduler spawned 12+ ticks in the first eval cycle.
On the next eval cycle (60s later with `--min-interval 1m`), the packer spawned
ANOTHER 12 — hitting "max concurrency reached" on 7-8 projects per cycle.
Duplicate ticks on same projects. Memory ballooned from the exec.Command fallback.

## Root cause

`packer.Pick()` queried the DB for `status='running'` ticks:

```go
runningSet := p.runningProjectSet()  // DB query — reads committed rows
```

But `spawner.Spawn()` writes to the DB asynchronously (after fork/HTTP call).
Between the spawn and the DB write, the next eval cycle sees ZERO running
projects and picks the same ones again.

### Timeline

```
T=0:  EVAL → Pick() sees runningSet={} → spawns 12 projects
T=1s: Spawner writes 12 "running" rows to DB (async, slow)
T=60: EVAL → Pick() sees runningSet={} (DB write not done yet!) → spawns 12 again
T=120: EVAL → Pick() sees 24 "running" (DB catch-up) → 0 available slots
```

## Fix (shipped `466802b`, 2026-07-18)

Merge the spawner's in-memory active map with the DB query:

```go
// spawner.go — expose in-flight active set
func (s *Spawner) RunningSet() map[string]bool {
    s.mu.Lock()
    defer s.mu.Unlock()
    set := make(map[string]bool, len(s.active))
    for tickID := range s.active {
        idx := strings.LastIndex(tickID, "-202")
        if idx > 0 {
            set[tickID[:idx]] = true  // extract project name from tick ID
        }
    }
    return set
}
```

```go
// packer.go — merge in-memory set with DB set
func (p *Packer) Pick(now time.Time, spawnerRunning map[string]bool) ([]PackedProject, error) {
    currentlyRunning := p.runningCount()
    runningSet := p.runningProjectSet()  // DB

    // Merge: spawns may not be committed to DB yet (race condition)
    for name := range spawnerRunning {
        runningSet[name] = true
    }
    if len(runningSet) > currentlyRunning {
        currentlyRunning = len(runningSet)
    }
    // ...
}
```

```go
// loop.go — pass spawner's state to packer
packed, err = l.packer.Pick(now, l.spawner.RunningSet())
```

## Key design choice: tick ID → project name extraction

Tick IDs follow the pattern `project-name-YYYY-MM-DD-HH-MM-SS`.
We extract the project name by finding the last occurrence of `-202` (year prefix)
and taking everything before it. This works for any project name containing hyphens
(e.g., `h3-sdk-python-foreman` → `h3-sdk-python-foreman`).

Edge case: no hyphens before the date → `coding-hermes-scheduler-2026-07-18-12-00-00`
→ `coding-hermes-scheduler`. Correct.

## Test compatibility

Test callers don't have a spawner and pass `nil`:

```go
got, err := p.Pick(time.Now(), nil)  // tests — no in-memory layer
```

Production: real spawner → real RunningSet merge.

## Alternative considered (rejected)

Writing "running" status to DB synchronously INSIDE Spawn() before returning.
Rejected because:
- gateway SendResponse already marks completed inline (gateway path)
- exec.Command path would need dual write (pre-spawn + post-spawn update)
- adds DB write latency to the spawn hot path
- RunningSet is simpler: one map lookup, zero DB roundtrips
