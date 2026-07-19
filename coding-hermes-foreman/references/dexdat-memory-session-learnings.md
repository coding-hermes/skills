# Session Learnings — DexDat Memory (2026-07-14)

## Concurrency Primitives: One Source of Truth

When a semaphore (channel) and a mutable counter track the same thing independently, there's a race window between Acquire and Release where the counter overshoots the limit.

**Bug:** `ConcurrencyLimiter` allowed 12 concurrent on a limit of 10 because `semaphore <-` and `currentCount++` weren't atomic. Between `Acquire()` sending to the channel and incrementing, and `Release()` reading from the channel and decrementing, the counter could drift past the limit.

**Fix:** Derive count from the channel directly — `len(semaphore)` replaces a separate `currentCount int` and its `sync.RWMutex`. Remove the mutable counter entirely. All methods (`CurrentCount`, `UtilizationPercent`, `AvailableSlots`, `IsAtLimit`, `CheckAlertLevel`, `GetStats`) read `len(c.semaphore)` with no lock.

**Commit:** dexdat-memory `ed701723` — 70 lines removed, 20 added. Race detector clean on all packages.

## Python + Go API: JSON Double-Encoding

When a Python loader sends `json.dumps(dict)` as a field value, the outer `json.dumps(request_body)` produces a serialized string inside the JSON payload. The Go `json.RawMessage` field receives `"\"{\\\"key\\\":...}\""` — a JSON *string*, not a JSON *object*. The Go decoder silently drops this as an unknown field shape.

**Bug:** Loader sent `"metadata_json": json.dumps({"original_id": _id, ...})`. memoryd's `BatchMemoryItem` DTO had no `MetadataJSON` field, so Go's decoder silently ignored it. After adding the DTO field, the double-encoded string was stored as a string in `json.RawMessage` — queries like `metadata_json->>'original_id'` returned NULL.

**Fix:** Two changes:
1. DTO: Add `MetadataJSON json.RawMessage` to `BatchMemoryItem` + handler assignment
2. Loader: Pass dict directly — `"metadata_json": {"original_id": _id, ...}` — not `json.dumps()`

**Commit:** dexdat-memory — memory_dto.go +1 field, memory.go +4 lines handler, loader.py fix.

## Bunker SSH: DOCKER_HOST Must Be Set Explicitly

The `authorized_keys` `environment="DOCKER_HOST=..."` directive doesn't always propagate via SSH. When SSH-ing as `bunker-<project>@<host>`, you must set it manually.

**Working pattern:**
```bash
ssh -i ~/.ssh/id_ed25519_bunker -o IdentitiesOnly=yes \
  bunker-<project>@<host> \
  'export DOCKER_HOST=unix:///run/bunker/<project>/docker.sock && docker ps'
```

**Failed pattern:**
```bash
ssh bunker-<project>@<host> 'docker ps'  # $DOCKER_HOST is empty, docker fails
```

**Socket path:** `/run/bunker/<project>/docker.sock` — exists on all Bunker agents. Check with `ls /run/bunker/<project>/docker.sock` before using.

**Why this matters:** Direct SSH has no 180s timeout (unlike `bunker exec`). Long DB operations (ANALYZE, dedup, VACUUM) that time out via bunker exec work fine via SSH + explicit DOCKER_HOST.
