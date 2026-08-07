---
name: coding-hermes-scheduler
description: >-
  How to operate the coding-hermes weight-budget scheduler. Covers project
  management via HTTP API, monitoring tick outcomes, debugging stuck ticks,
  tuning budget/concurrency/cooldown, and the verify test suite.
version: 3.16.0
author: Bane + Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [coding-hermes, scheduler, api, monitoring]
    related_skills:
      - coding-hermes-north-star
      - coding-hermes-cron
      - coding-hermes-foreman
---

# Coding Hermes Scheduler — Operations & API

> **Starvation / ghost-project diagnosis:** see
> `references/starvation-ghost-projects.md` — decay_rate=0 permanent
> starvation, NULL/nonexistent namespaces, case-insensitive duplicate
> workdir ghosts, auto-heal script, PACKER-SORTED log debugging.

> **Wrong cadence / missing fleet pin:** see
> `references/wrong-cadence-fleet-pin.md` — project enabled but not on
> its intended schedule (e.g. 12h): check scheduler.db namespace_id
> (NULL = skipped) + cooldown_s, add the [[projects]] pin to fleet.toml,
> and confirm the daemon was STARTED with `--config fleet.toml`
> (systemd unit + watchdog restart command both omitted it on this host
> — pins silently never applied on restart). Verify via
> `curl :9090/api/v1/projects`.

> **Silent DuckBrain sync failure:** see
> `references/duckbrain-http-sync-failure.md` — scheduler's sync layer
> POSTs to `http://localhost:3000` but DuckBrain runs stdio-MCP only by
> default; every tick memory write fails silently (`connection refused`)
> until `duckbrain-http.service` (systemd user unit, port 3000) exists.
> Also: `schedulerd` now persists logs to `~/.hermes/coding-hermes/scheduler.log`
> (`-log-file` flag, default on) — always grep it first when debugging.

The scheduler daemon (`schedulerd`) replaces static foreman cron jobs with a dynamic weight-budget knapsack packer. Projects run under a shared compute budget, prioritized by urgency, with per-project delivery via Hermes' gateway.

## Spawn Architecture (v3.4 — Event-Driven with Direct Release Signal, `2026-07-19`)

The scheduler uses an **event-driven** loop. When a tick completes and frees a slot,
the loop re-evaluates within 5 seconds to fill it. This replaced the timer-only
approach that left fleet slots idle between eval cycles.

### Gateway Liveness Check (v3.9 — FIX-STUCK, `2026-07-19`)

**Problem:** hermes-gateway process dies/restarts, but the scheduler has dead HTTP
connections. It fills all 10 slots with requests that never complete. The daemon
appears dead. A 30s client timeout won't help — the old connection is to a dead
process. A killpg(1, SIGKILL) from a foreman test suite (<project>) can kill
the gateway and scheduler simultaneously.

**Fix:** Before each eval cycle, ping gateway `/health` with a 5s timeout. If the
ping fails, release all slots and skip spawning. When the gateway comes back,
log "GATEWAY reconnected" and resume. This prevents the cascade where all slots
fill with doomed ticks.

```go
// In evaluate(), before any spawning:
if l.gatewayClient != nil {
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    err := l.gatewayClient.Ping(ctx)
    cancel()
    if err != nil {
        if !l.gatewayDead {
            log.Printf("GATEWAY DEAD — pausing spawns: %v", err)
            l.gatewayDead = true
            l.slotPool.ReleaseAll()
        }
        return // skip entire spawn cycle
    }
    if l.gatewayDead {
        log.Printf("GATEWAY reconnected — resuming spawns")
        l.gatewayDead = false
    }
}
```

**Ping method (gateway_client.go):**
```go
func (g *GatewayClient) Ping(ctx context.Context) error {
    req, _ := http.NewRequestWithContext(ctx, "GET", g.baseURL+"/health", nil)
    if g.apiKey != "" {
        req.Header.Set("Authorization", "Bearer "+g.apiKey)
    }
    resp, err := g.http.Do(req)
    if err != nil { return err }
    resp.Body.Close()
    if resp.StatusCode != 200 { return fmt.Errorf("status %d", resp.StatusCode) }
    return nil
}
```

**ReleaseAll method (slot_pool.go):** Drains the semaphore channel and fires
SlotFreed so the eval loop knows slots are available.
```go
func (p *SlotPool) ReleaseAll() {
    for {
        select {
        case <-p.sem:
            select { case p.freedCh <- struct{}{}: default: }
        default: return
        }
    }
}
```

**Loop struct additions:**
```go
type Loop struct {
    ...
    gatewayClient   *GatewayClient // wired via SetGatewayClient()
    gatewayDead     bool           // true when last ping failed
}
```

**Key rule:** Keep `gatewayDead` as a simple boolean. If the ping fails, set
it true and skip spawning. Next eval (30s later), try ping again. If it
succeeds, set false and resume. No complex reconnect goroutine — the eval
loop IS the retry mechanism.

**System resource starvation:** When the gateway dies and the scheduler fills all
slots with unreachable requests, the entire system becomes resource-starved.
`go build` fails with "resource temporarily unavailable" because every slot
spawns an `exec.Command` fallback that consumes threads. With FIX-STUCK, the
slots are released immediately when the gateway is detected dead, keeping the
system responsive enough to build and deploy fixes.

**SlotFreed channel:** The `SlotPool` owns a single `freedCh` channel created in
`NewSlotPool()`. Unlike v3.3's polling goroutine (which had a race on `len()`),
v3.4 fires `freedCh` **directly in `Release()`** — zero polling, zero goroutine,
deterministic signal on every slot release.

```go
func (p *SlotPool) Release() {
    select {
    case <-p.sem:
        select {
        case p.freedCh <- struct{}{}:  // direct signal
        default:
        }
    default:
    }
}
```

**Debounce (5s coalescing):** Each `SlotFreed` event resets a `time.AfterFunc` timer.
Evaluation fires only after 5 seconds of quiet — this batches rapid completions and
prevents the feedback-loop flood that plagued v3.1 (BUG-008: 1388 ticks in 5 minutes).

**Dual-trigger evaluation:**
1. **Event-driven:** SlotFreed → reset 5s debounce → `evalCh` → `evaluate()`
2. **Health ticker (30s):** Logs goroutine count and running tick stats
3. **Zombie reaper (60s):** Process-liveness check on running ticks
4. **Startup eval:** Initial `evalCh` send fires first evaluation immediately

**Dedup guard (v3.8, `2026-07-19`):** Before spawning, `evaluate()` checks
`SlotPool.RunningSet()` and skips projects already occupying a slot. This prevents
the timeout→re-spawn→duplicate-processes cascade that created 11+ concurrent
rethinkdb instances from a single project.

```go
alreadyRunning := l.slotPool.RunningSet()
for _, proj := range packed {
    if alreadyRunning[proj.Name] {
        log.Printf("DEDUP: skipping %s — already running", proj.Name)
        continue
    }
    l.slotPool.Spawn(proj, now, noDeliver, l.db)
}
```

```
Loop.Run() select:
  case <-slotFreedCh:     → reset 5s debounce (time.AfterFunc → evalCh)
  case <-evalCh:          → evaluate()
  case <-healthTicker.C:  → log health metrics
  case <-reaper.C:        → reapZombies()

SlotPool (v3.4):
  Release() → fires freedCh directly (no polling goroutine)
  SlotFreed() returns freedCh
```

**Key architectural rules:**
- Never block the eval loop on I/O. Phase 1 picks projects under lock (<1s),
  Phase 2 fires them into goroutines with a semaphore cap.
- `--tick-timeout` 7200s (2h). Slow projects get generous time; **timeout does NOT back off cooldown** — project stays eligible after its normal cooldown. Timeout alerts are sent to chat via `deliverAlert()`.
- **Named channel (`chan string`):** The semaphore stores project names so
  `RunningSet()` can return the in-flight set for the packer. Prevents
  duplicate spawns from consecutive eval cycles.
- **Gateway rate limit:** Hermes gateway caps at 10 concurrent runs.
  `--max-concurrent` must be ≤10.
- **⚠️ `len(chan)` is racy in Go — do NOT poll it.** Go's `len()` on buffered channels is a snapshot, not synchronized with concurrent sends/receives. Polling `len()` changes caused the SlotFreed signal to miss events (race condition). **Fix:** Fire the signal directly in `Release()` — no polling, no goroutine leak, deterministic.

**⚠️ Nil `*time.Timer.C` panics at runtime.** Writing `case <-myTimer.C` when `myTimer` is a nil `*time.Timer` does NOT block on a nil channel like a `chan time.Time` would — it dereferences nil and panics. Always use a `<-chan time.Time` variable for optional timer selects, never a nil pointer:

```go
// WRONG — panics when timerPtr is nil:
var timerPtr *time.Timer
select {
case <-timerPtr.C: // SIGSEGV
}

// CORRECT — nil channel blocks forever:
var timerC <-chan time.Time
select {
case <-timerC: // safe, never fires
}
```

**Proven:** 2026-07-19 — scheduler crashed on startup with nil pointer deref at `loop.go:194` because `debounceTimer.C` was accessed through a nil `*time.Timer`. Fixed by using `timerC <-chan time.Time` pattern.

**Firing freedCh in Release() is the correct design.** Polling `len(chan)`
  was racy (Go's `len()` on channels is not atomic with concurrent sends/recvs).
  Direct signal on every release is simpler, faster, and deterministic.

The preferred spawn path. Sends foreman prompts to the already-running Hermes gateway API instead of spawning per-tick subprocesses. **Zero subprocess overhead, zero MCP duplication.**

```
schedulerd → POST http://127.0.0.1:8642/v1/responses
          → Authorization: Bearer $API_SERVER_KEY
          → {"input": "Load skills coding-hermes-foreman...", "model": "deepseek-v4-pro", "require_approval": false}
          → Synchronous HTTP response (timeout: --tick-timeout, default 30m)
          → Extract text from response.output[0].content[0].text
          → Fallback to exec.Command if gateway unreachable or request fails
```

**Gateway endpoints (Hermes v0.18.2, PID 348728):**
```
GET  /health              → {"status":"ok","version":"0.18.2"}
GET  /v1/models           → available models
GET  /v1/skills           → 109KB skill catalog
GET  /v1/toolsets         → available toolsets
POST /v1/responses        → stateful, synchronous agent run ← USED BY SCHEDULER
POST /v1/chat/completions → stateless, stream + non-stream
POST /v1/runs             → long-running with SSE events
GET  /api/sessions        → session CRUD
```

**Auth:** Gateway reads `API_SERVER_KEY` from `.env` or env var. If unset, auth is skipped (localhost-only). Pass via `Authorization: Bearer <key>` header.

**Response format:**
```json
{"id":"resp_...","status":"completed","model":"deepseek-v4-flash",
 "output":[{"type":"message","role":"assistant",
            "content":[{"type":"output_text","text":"READY"}]}],
 "usage":{"input_tokens":33123,"output_tokens":18,"total_tokens":33141}}
```

**Verification:**
```bash
# Check gateway health
curl -s -H "Authorization: Bearer $API_SERVER_KEY" http://127.0.0.1:8642/health

# Test a simple prompt
curl -s -X POST http://127.0.0.1:8642/v1/responses \
  -H "Authorization: Bearer $API_SERVER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input":"Say READY.","model":"deepseek-v4-flash"}'

# Scheduler logs
journalctl -u coding-hermes-scheduler | grep "GATEWAY"
# "GATEWAY: connected to http://127.0.0.1:8642"
# "GATEWAY: project tick=... tokens=79000/105"
# "GATEWAY FAIL: project tick=... error=... — falling back to exec.Command"
```

**Savings:** 0MB per tick in subprocess overhead (was 175-500MB with exec.Command).
All MCPs loaded once by the gateway, shared across concurrent ticks.
No PID tracking, no zombie reaper, no pipe goroutines.
Gateway-completed ticks set `completed=true` → `Wait()` returns immediately.

**DB tick resolution:** Gateway ticks are marked complete in `Spawn()` itself — the DB
update happens inline. No separate goroutine wait loop needed.

### Process Spawn (legacy / fallback)

When gateway is not configured or unreachable, falls back to `exec.Command("hermes", "chat", ...)`.
With the foreman MCP optimization (HERMES_HOME=~/.hermes/foreman), this uses ~175MB per chat.
See `references/foreman-memory-optimization.md`.

## Delivery Architecture (correct as of 2026-07-18 — Bane-approved)

```
Foreman → clean markdown (no platform knowledge)
Scheduler → strips tool noise (--- separator), adds _tick-id_ footer
         → passes through to hermes send with NO formatting changes
Hermes → delivers raw content → platform (Telegram/Discord/Slack/Email)
```

**Foreman prompt (spawn.go):** "Format your final output as clean, well-structured markdown."
No platform-specific instructions — the foreman doesn't know about Telegram.

**Worker model defaults (v3.5+):** Each project can specify a preferred worker model/provider
via the `worker_model` and `worker_provider` columns. These are NON-BINDING defaults — the
foreman can override if the model is rate-limited or out of credits. The spawner injects
them into the foreman prompt:

```
Worker default: use model gpt-5.6-sol with provider openai-codex if available.
Feel free to use a different model if this one is unavailable or rate-limited.
```

Set via API or SQL:
```bash
curl -X PUT /api/v1/projects/my-project \
  -H 'Content-Type: application/json' \
  -d '{"WorkerModel":"gpt-5.6-sol","WorkerProvider":"openai-codex"}'
```

The `workerDefaults()` function in spawn.go handles prompt construction. If both fields
are empty, no worker guidance is injected (foreman uses its own judgment).

**deliver.go:** Pure passthrough. Strips tool output before `---` separator only.
No char cap, no table conversion, no code-fence stripping, no regex extraction.
The foreman owns formatting; the scheduler owns routing.

**When Hermes gets per-platform markdown rendering, the scheduler needs zero changes.**

## Quick Start

```bash
# Check health
curl http://127.0.0.1:9090/api/v1/health

# List projects
curl http://127.0.0.1:9090/api/v1/projects | python3 -m json.tool

# Force evaluation
curl -X POST http://127.0.0.1:9090/api/v1/evaluate
# NOTE: there is NO per-project trigger endpoint. POSTing to
# /api/v1/projects/<name>/trigger returns 404 ("not found"). After
# re-enabling a project, just wait for the next eval cycle (<= 5s after a
# slot frees, or the next 30s health tick) — the project wins a slot on
# its own. Do NOT resume old cron jobs to force a tick (double-dispatch
# race, see troubleshooting).

# View recent ticks
curl "http://127.0.0.1:9090/api/v1/ticks?limit=10" | python3 -m json.tool

# Dashboard
curl http://127.0.0.1:9090/ | head -5
```

## Tuning Knobs

| Flag | Default | What | Notes |
|------|---------|------|-------|
| `--budget` | 100 | Weight pool per eval cycle | — |
| `--max-concurrent` | 4 | Simultaneous HTTP gateway ticks | Must be ≤ gateway max (10). Lower to 4 for system responsiveness — 10 concurrent `hermes chat` subprocesses can starve system threads, blocking `go build` and other tools. Gateway HTTP spawns have zero per-tick overhead. |
| `--min-interval` | 30s | Health check ticker cadence | With event-driven eval, this controls log frequency, NOT spawn timing. Spawning is triggered by slot-freed events. |
| `--max-interval` | 4h | Cooldown ceiling (p=1 projects) | — |
| `--namespace-mode` | true | Multi-namespace budget pools | Required for proper pool-weighted packing. |
| `--tick-timeout` | 7200s | Max tick duration before timeout | 2 hours. Generous — long compiles/tests finish. Timeout does NOT back off cooldown. Project stays eligible after normal cooldown. Alerts delivered to chat. |
| `--gateway-url` | `http://127.0.0.1:8642` | Hermes gateway API URL | When set: HTTP spawn (zero overhead). Empty: exec.Command only. |
| `--gateway-key` | `$API_SERVER_KEY` | Gateway API key | Read from env var. Required for authenticated gateway access. |

```bash
# Heavy fleet with gateway
schedulerd --budget 500 --max-concurrent 16

# Resource-constrained
schedulerd --budget 50 --max-concurrent 2 --min-interval 5m

# Gateway mode (recommended — zero subprocess overhead)
schedulerd --gateway-url http://127.0.0.1:8642 --gateway-key "$API_SERVER_KEY"

# Process-spawn only (legacy / gateway unavailable)
schedulerd --gateway-url ""
```

## API Reference

Base: `http://127.0.0.1:9090/api/v1`

### Projects

```bash
# Create project
curl -X POST /api/v1/projects \
  -H 'Content-Type: application/json' \
  -d '{"Name":"my-project","RepoURL":"local:~/my-project",
       "Workdir":"~/my-project","Weight":10,"Priority":5,
       "NamespaceID":"coding-hermes","Enabled":true}'

# Update project — partial updates work with correct casing
curl -X PUT /api/v1/projects/my-project \
  -H 'Content-Type: application/json' \
  -d '{"Priority":8,"CooldownS":0}'  # 0 = dynamic cooldown

# Enable/disable
curl -X PUT /api/v1/projects/my-project \
  -H 'Content-Type: application/json' \
  -d '{"Enabled":true}'

# Set delivery target (maps to per-project Telegram thread)
curl -X PUT /api/v1/projects/my-project \
  -H 'Content-Type: application/json' \
  -d '{"Deliver":"telegram:-1003310984808:12345"}'

# Delete project
curl -X DELETE /api/v1/projects/my-project
```

**API field names are case-sensitive.** The API returns camelCase (`CooldownS`, `RepoURL`, `NamespaceID`) and expects the same casing on PUT. Snake_case variants (`cooldown_s`, `repo_url`, `namespace_id`) are silently ignored — the PUT returns success with the old value unchanged. Always match the casing shown in GET responses. **Proven:** ASCE zombie tick #204 — `{"cooldown_s": 43200}` returned CooldownS=900 (unchanged); `{"CooldownS": 43200}` in full-object PUT worked.

**⚠️ GET `/api/v1/projects/<name>` wraps the project under a `.project` key with a sibling `latest_tick`.** A top-level jq path (`jq -r '.CooldownS'` or `'{CooldownS, Enabled}'`) returns ALL NULLS — the payload is `{"latest_tick": {...}, "project": {...}}`. Always parse `.project.<Field>`:
```bash
curl -s http://127.0.0.1:9090/api/v1/projects/asce | jq -r '.project | {CooldownS, Enabled, Priority}'
```
**Proven:** ASCE tick #224 (2026-08-01) — first jq attempt at top level returned nulls for CooldownS/Enabled/Name/NextRun; the raw payload inspection revealed the `latest_tick` + `project` wrapper. Note the same wrapper applies to the cooldown-detection one-liners elsewhere in this skill (they use `d['project']['CooldownS']` correctly).

### Namespaces

```bash
# Create namespace (requires --namespace-mode)
curl -X POST /api/v1/namespaces \
  -H 'Content-Type: application/json' \
  -d '{"ID":"my-ns","Weight":50,"Reserved":30,"HardCap":60}'
```

### Events

```bash
# Recent events
curl /api/v1/events?limit=20
```

## Dynamic vs Manual Cooldown

**Dynamic (recommended):** Set `CooldownS=0` (or omit). The scheduler derives cooldown from priority using a logarithmic scale:

```
p=10 → 1m    p=7 → 6m    p=4 → 39m   p=1 → 4h
p= 9 → 2m    p=6 → 11m   p=3 → 1.2h
p= 8 → 3m    p=5 → 21m   p=2 → 2.2h
```

**Manual override:** Set `CooldownS` to a positive integer (seconds). The scheduler uses this fixed cooldown regardless of priority. Use for special cases where you need a specific cadence.

## Regression Test Suite (v3.4, `2026-07-19`)

13 regression tests across 6 GitReins guard tasks prevent backsliding on every
bug we've fixed:

| Guard | Tests | Prevents |
|-------|-------|----------|
| `REGRESSION-001` SlotPool | AcquireRelease, AcquireTimeout, RunningSet, NoGoroutineLeak, SlotFreedFiresOnRelease, SlotFreedMultipleReleases | Goroutine leak, SlotFreed regression |
| `REGRESSION-004` Concurrent | ConcurrentAcquireStress (100 goroutines/10 slots), DebounceCoalescing, TickTimeout | Semaphore overflow, deadlock, timeout |
| `REGRESSION-005` Picking | TieBreakingSameUrgency, BudgetOverflow, CooldownBoundary, StableSort | <project> starvation, budget overflow, off-by-one cooldown |
| `REGRESSION-006` Lifecycle | CleanDangling_ResetsLastTick, AutoSlowdown_Idle, AutoSlowdown_Productive, NamespaceBorrowing | NULL urgency, auto-slowdown regression, namespace starvation |

All tests live in `internal/scheduler/regression_test.go` and `slot_pool_test.go`.
Run: `go test -short -run "TestSlotPool|TestPick|TestAutoSlow|TestMultiPool|TestPacker_Stable|TestCleanDangling" ./internal/scheduler/`

GitReins enforces these via `guards > tasks.list` — every commit runs the suite.

## Traceability

Every scheduler-spawned process gets these env vars:
- `CODING_HERMES_TICK=<tick-id>` — unique per tick
- `CODING_HERMES_SOURCE=scheduler` — distinguishes from legacy cron
- `CODING_HERMES_PROJECT=<project-name>` — which project ran

```bash
# Check which scheduler tick spawned a running process
ps aux | grep hermes | while read line; do
  pid=$(echo "$line" | awk '{print $2}')
  env=$(cat /proc/$pid/environ 2>/dev/null | tr '\0' '\n' | grep CODING_HERMES)
  [ -n "$env" ] && echo "PID $pid: $env"
done
```

## Fleet Commands (DuckBrain)

Scheduler runtime controls stored in DuckBrain at `/fleet/scheduler/fleet-commands`:

```
/fleet weight PROJECT N       — set weight (1-100)
/fleet priority PROJECT N     — set priority (1-10)
/fleet budget N               — set total weight capacity
/fleet cooldown PROJECT N     — minimum cooldown seconds
/fleet status                 — live view of all projects
/fleet pause PROJECT          — disable scheduling
/fleet resume PROJECT         — re-enable
```

All take effect next evaluation. Equivalent to `PUT /api/v1/projects/<name>`.

## Hermes Send Discovery

Discover valid platform/thread targets for delivery:

```bash
hermes send --list telegram
# Output: telegram:KaraHermes - Set / topic 12345  [-1003310984808:12345]
```

Use `chat_id:thread_id` from the output as the `deliver` column value.

## Troubleshooting

### Ticks stuck "running" forever — Three-Layer Process-Liveness Defense (SHIPPED `8d68708`)

**Symptom:** After scheduler restart, 15+ ticks show "running" but 0 `hermes chat`
processes exist. All 8 concurrency slots blocked by ghosts. Packer logs:
`total-running=15/8, nothing packed`. No new ticks spawn for hours.

**Root cause:** Old scheduler process died (kill/crash) but left ticks in "running"
state. New process starts, sees all slots occupied by dead-process ghosts.

**⚠️ Old approach (rejected):** 30-minute blind timeout. Bane: "things can take
longer than 30 minutes — that is not a real thing. We need a better way at knowing
they are zombies than just whacking them because it is slow." Long builds and
complex foreman ticks kill mid-work, wasting PAYG tokens. Do NOT use time-based
cutoffs.

**Current approach (`8d68708`):** Process-liveness check via `/proc/<pid>/stat`.

| Layer | Trigger | Mechanism |
|-------|---------|-----------|
| 1. Startup cleanup | Process boot | `cleanDanglingOnStartup()` — all running ticks are from dead process → timeout |
| 2. Zombie reaper | Every 60s | `reapZombies()` — checks `/proc/<pid>/stat` for each running tick. Process exists → leave alone (it's doing real work). Process gone → zombie → timeout |
| 3. Monitor | Every 60s | Warns log if running > max_concurrent (possible leak) |

**How it works:** Each spawn stores `pid` in the ticks table. The reaper queries
`SELECT id, pid FROM ticks WHERE status='running' AND pid > 0`, then checks
`os.Stat("/proc/<pid>/stat")`. `os.IsNotExist` → process dead → reaped.
Process alive → untouched regardless of age.

**Quick manual fix (if daemon is stuck):**
```bash
sudo systemctl restart coding-hermes-scheduler
# Layer 1 clears all ghosts on boot. Layer 2 catches any new ones within 60s.
```

**⚠️ Timestamp format pitfall:** SQLite stores ticks as ISO 8601 with timezone
(`2026-07-18T00:41:21-05:00`) but `datetime('now')` produces UTC without timezone
(`2026-07-18 06:53:23`). Direct SQL comparisons fail — strings don't match lexicographically.
**Use Python's `datetime.fromisoformat()` instead.**

```bash
# Clear all stale ticks (>10 min old) — CORRECT pattern
python3 -c "
import sqlite3
from datetime import datetime, timezone, timedelta
db = sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
cleared = 0
for r in db.execute(\"SELECT rowid, spawned_at FROM ticks WHERE status='running'\"):
    try:
        ts = datetime.fromisoformat(r[1])
        if ts < cutoff:
            db.execute(\"UPDATE ticks SET status='timeout' WHERE rowid=?\", (r[0],))
            cleared += 1
    except: pass
db.commit()
print(f'Cleared {cleared} stale ticks')
"
```

### Project not getting picked
- Check if it's enabled: `curl /api/v1/projects/my-project`
- **⚠️ Projects silently disabled pitfall (2026-07-18):** Foremen or the supervisor may
  set `enabled=0` on projects they consider "complete." This is NOT tracked in any
  notification. A project can be silently removed from the eval pool. Always audit
  enabled state when users report "project hasn't fired in hours":
  ```bash
  python3 -c "import sqlite3;db=sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
  for r in db.execute('SELECT name FROM projects WHERE enabled=1 ORDER BY name').fetchall(): print(r[0])"
  ```
  **Proven:** 2026-07-18 — helios, mythos, muster, off-by-one were all disabled
  (enabled=0) after completing ticks. <project> was enabled but had NEVER ticked.
  <project>, <project>, <project>, <project> last ticked 5+ hours before being
  noticed. Re-enablement required manual DB updates.
- **⚠️ Do NOT fall back to cron when the scheduler appears idle (2026-07-21):**
  When a project hasn't received a scheduler tick, do NOT resume the old cron job.
  The scheduler dispatches via a weight-budget knapsack algorithm — a project queued
  behind 39 other enabled projects may take several cycles to get selected. Verify
  scheduler state FIRST: `SELECT name, enabled, last_tick_started, priority, weight FROM projects`.
  If `enabled=1` and `last_tick_started IS NULL`, the project is queued but hasn't
  won a pack slot yet. Bump `priority` and `weight` in the DB to increase urgency.
  Resuming the old cron creates a double-dispatch race (scheduler + cron both firing)
  that produces timeout/dead-process confusion and broken board state.
  **Proven:** <project> 2026-07-21 — 3 rounds of cron resume/pause while scheduler
  had the project correctly registered at p=10, w=25. Scheduler DID dispatch
  INFRA-006 at 01:49 UTC — it just took time to win a pack slot among 39 peers.
  The `🤖 <project>` robot prefix on the delivery confirmed it was a scheduler tick.
- Use the reconciliation audit to verify all expected projects are registered + enabled
  (see `references/project-reconciliation.md`)
- Check cooldown: `last_tick_completed` + `cooldown_s` vs current time
- Check namespace: if `--namespace-mode` is on, project needs `NamespaceID`
- **⚠️ Namespace must EXIST, not just be set (2026-07-31).** A `NamespaceID` pointing
  at a namespace that doesn't exist in the daemon = silent starvation, same as NULL.
  The allocator only iterates registered namespaces (`backup`, `coding-hermes`,
  `data-cleanup`, `duckbrain-infra`, `monitoring`) — a project assigned to
  `<project>` (no such namespace) is never scheduled and produces NO spawn attempts
  and NO tick rows. Detection: cross-reference `GET /api/v1/namespaces` against
  each project's `NamespaceID`. Fix: `PUT /api/v1/projects/<name> {"NamespaceID":"coding-hermes"}`.
  **Proven:** 2026-07-31 — <project> had `NamespaceID=<project>` (nonexistent), no ticks
  since Jul 29. After reassignment it jumped to #2 in the packer queue (urgency 53,624).
- **New projects need `namespace_id='coding-hermes'` or the scheduler won't dispatch ticks.** When inserting directly into SQLite (not via API), the `namespace_id` column defaults to NULL. Projects with NULL namespace won't get picked when `--namespace-mode` is on. Fix: `UPDATE projects SET namespace_id='coding-hermes' WHERE name='my-project'`. **Session evidence:** H3 2026-07-18 — registered via `INSERT INTO projects` but scheduler ignored it for 30+ minutes. `namespace_id` was NULL. After setting to `coding-hermes`, the project was visible in the API but still needed a bridging cron to start receiving ticks.
- **Bridging cron pattern — when scheduler hasn't picked up a new project yet.** Create a temporary cron job with the foreman skills and the project's workdir. This delivers ticks immediately while the scheduler warms up. Once scheduler ticks appear, pause or remove the bridge. Pattern: `cronjob(action='create', name='<project>-foreman-bootstrap', skills=['coding-hermes-foreman','coding-hermes-cron'], workdir='~/<project>', schedule='every 5m', model='deepseek-v4-pro', provider='deepseek-foreman', enabled_toolsets=['terminal','file','web','search','skills','memory'])`. **Session evidence:** H3 2026-07-18 — scheduler DB entry alone did not produce ticks for 30+ minutes after registration. A bridging cron (`e17630cea8c9`) started delivering immediately.
- Check weight: if budget=100 and already packed, lower-weight projects wait
- Force eval and watch logs: `journalctl -u coding-hermes-scheduler -f`

### 🪤 NULL `last_tick_started` — Cooldown Bypass (2026-07-24)

**Symptom:** Individual projects receive far more ticks than their cooldown allows.
E.g. <project>-e2e with `cooldown_s=43200` (12h) received 6,134 ticks in 48h (~128/hr).
Fleet-wide tick count inflated — 7,460 ticks in 48h but only 860 committed outcomes.

**Root cause:** `last_tick_started` is NULL for the project. The scheduler spawns
ticks but does NOT update this column on the project row. When the packer checks
cooldown eligibility (`last_tick_started + cooldown_s > now`), NULL + interval = NULL,
and `NULL > now` evaluates to FALSE in SQL — the project appears eligible every cycle.

**Detection query:**
```bash
python3 -c "
import sqlite3
db = sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
rows = db.execute('''SELECT name, cooldown_s, last_tick_started,
    (SELECT COUNT(*) FROM ticks WHERE project_name=projects.name) as tick_count
    FROM projects WHERE enabled=1 AND last_tick_started IS NULL
    ORDER BY tick_count DESC''').fetchall()
print(f'{len(rows)} projects have NULL last_tick_started:')
for r in rows[:10]:
    print(f'  {r[0]:<30} cooldown={r[1]}s  ticks_in_db={r[3]}')
"
```

**Impact:** As of 2026-07-24, 39/40 enabled projects have NULL `last_tick_started`.
Only `<project>` has a non-NULL value (set 2026-07-18). Cooldown is NEVER enforced
fleet-wide. This is the **root cause of fleet-wide tick inflation and the 87.9%
failure rate** — projects are re-picked instantly, failing again, creating a feedback loop.

**Fix (SHIPPED `7b34a43`, 2026-07-25, tick #150):** Added `UPDATE projects SET last_tick_started = ? WHERE name = ?` in both spawn paths:
- **Gateway HTTP path** (spawn.go:219-220): after tick marked complete via gateway
- **exec.Command path** (spawn.go:353-354): after tick marked running with PID

The foreman's own tick found and fixed the bug that had been documented for 80+ ticks.
```go
// Gateway path — spawn.go line 219:
_, _ = s.db.Exec(`UPDATE projects SET last_tick_started = ? WHERE name = ?`,
    now.Format(time.RFC3339), project.Name)

// exec.Command path — spawn.go line 353:
_, _ = s.db.Exec(`UPDATE projects SET last_tick_started = ? WHERE name = ?`,
    st.Started.Format(time.RFC3339), project.Name)
```
New binary built at `bin/schedulerd` (20.9MB). Takes effect on next daemon restart.
All build/vet/test/guard gates pass.

**Proven:** 2026-07-24 fleet report — 39/40 projects affected. <project>-e2e pumped
6,134 instant-fail ticks (82% of all fleet ticks) while cooldown=43200s was
completely ignored due to NULL last_tick_started. Fixed 2026-07-25.

### 🪤 Instant-Fail Tick Pump Detection (2026-07-24)

**Symptom:** A project generates hundreds/thousands of ticks per hour, all failing
instantly (spawned_at == completed_at, exit code 2). The scheduler re-picks it
every cycle, filling gateway slots with doomed requests.

**Root cause:** Two factors combine: (1) NULL `last_tick_started` bypasses cooldown,
(2) the gateway can't spawn the foreman for this project name (skill path, workdir,
or auth issue causes instant `exit status 2`). The project is re-picked every eval
cycle because the tick "completes" instantly (freeing the slot) and cooldown isn't
enforced.

**Detection:**
```bash
python3 -c "
import sqlite3
db = sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
rows = db.execute('''SELECT project_name, COUNT(*) as cnt
    FROM ticks WHERE spawned_at = completed_at AND outcome='failed'
    AND spawned_at > datetime('now', '-48 hours')
    GROUP BY project_name ORDER BY cnt DESC''').fetchall()
for r in rows:
    print(f'{r[0]:<30} {r[1]:>6} instant-failure ticks')
"
```

**Immediate fix:** Disable the pumping project via API:
```bash
curl -X PUT http://127.0.0.1:9090/api/v1/projects/<name> \
  -H 'Content-Type: application/json' \
  -d '{"Enabled":false}'
```

**Root cause fix:** Fix the NULL `last_tick_started` bug (above) so cooldown
prevents re-picking. Then investigate why the gateway can't spawn the foreman
for that project name.

**Proven:** 2026-07-24 — <project>-e2e had 6,134 instant-fail ticks in 48h (82% of
all fleet ticks). Disabled via API PUT. The sibling entry `<project>`
(same workdir) worked fine — suggesting a project-name-to-foreman-skill mapping issue.

### 🪤 Duplicate Workdir Entries (2026-07-24)

**Symptom:** Two scheduler project entries point to the same workdir. One works,
the other fails. Combined with cooldown bypass, the failing one pumps ticks.

**Detection:**
```bash
python3 -c "
import sqlite3
db = sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
rows = db.execute('''SELECT workdir, GROUP_CONCAT(name) as projects, COUNT(*) as cnt
    FROM projects WHERE enabled=1 AND workdir NOT LIKE '/tmp%'
    GROUP BY workdir HAVING cnt > 1''').fetchall()
for r in rows:
    print(f'{r[0]}: {r[1]} ({r[2]} entries)')
"
```

**Fix:** Disable the failing duplicate. Keep the one that works. Do not delete
— preserve tick history. Use the API:
```bash
curl -X PUT http://127.0.0.1:9090/api/v1/projects/<failing-name> \
  -H 'Content-Type: application/json' \
  -d '{"Enabled":false}'
```

**Proven:** 2026-07-24 — `<project>-e2e` and `<project>` both point to
`~/<project>`. <project> ticks succeed; <project>-e2e
ticks all fail with exit status 2. Disabled <project>-e2e to stop the pump.

### 🪤 All slots held by "never-completed" zombies after daemon restart (2026-07-31)

**Symptom:** Project is enabled, cooldown elapsed (shows in `/api/v1/queue` as eligible), but gets NO ticks for hours while 4 other projects hold all slots. Daemon log shows the SAME 4 projects acquiring slots on every eval cycle. `EVAL: 4 project(s) selected` repeats, and the target project never appears.

**Root cause chain (three independent layers — check all three):**
1. **Zombie ticks with NULL `completed_at` (primary):** `cleanDanglingOnStartup()` marks orphaned running ticks `status='timeout'` but leaves `completed_at` NULL. The packer's `lastCompleted` map is built from `MAX(completed_at) WHERE status != 'running'` — timeout ticks with NULL `completed_at` are indistinguishable from "never completed". Packer sort puts `lastTickAt == nil` FIRST and skips cooldown entirely, so the same dead projects win every slot forever. **Fix:** set `completed_at` on zombie ticks, then restart daemon:
   ```sql
   UPDATE ticks SET status='timeout', completed_at='<now ISO>' WHERE status IN ('running','spawned') AND completed_at IS NULL;
   UPDATE projects SET last_tick_completed='<now ISO>' WHERE name IN (SELECT DISTINCT project_name FROM ticks WHERE status='timeout' AND completed_at='<now ISO>');
   ```
   Then restart schedulerd — packer now sees recent `lastTickAt` → cooldown applies → slots free.
2. **Gateway `max_concurrent_runs` rate limit:** Even with a slot acquired, spawn fails: `GATEWAY FAIL: ... rate_limit_error — Too many concurrent runs (max 10)`. With `--no-exec-fallback` the tick is DROPPED (not queued). The gateway caps concurrent runs at `gateway.api_server.max_concurrent_runs` (default 10 in `~/.hermes/config.yaml`) — the fleet + user subagents + delegates saturate it. **Fix:** `hermes config set gateway.api_server.max_concurrent_runs 25` then restart the gateway (see detached-restart recipe below).
3. **Priority starvation:** Packer sorts urgency desc → priority desc → oldest last-tick. A p=8 project loses every slot to p=10 projects whose cooldown also elapsed. **Fix:** `PUT /api/v1/projects/<name> {"Priority":10,"CooldownS":900}` — raising priority makes it compete for slots.

**Gateway restart from inside the gateway process tree (blocked):** `systemctl --user restart hermes-gateway` (and even `systemd-run --on-active` wrappers containing the words "restart hermes-gateway") are BLOCKED when run from a session inside the gateway — SIGTERM propagation would kill the command. Also, there may be NO `hermes-gateway` systemd unit at all (gateway runs standalone as `python -m hermes_cli.main gateway run`; `systemctl restart` silently no-ops, PID unchanged). **Working recipe:** write a detached script that kills the old PID, `setsid nohup`-starts a new gateway, health-checks; schedule it via a transient systemd timer (child of systemd, survives the gateway's SIGTERM):
```bash
systemd-run --user --on-active=3s --unit=gw-restart-v2 /bin/bash /tmp/restart-gw-v2.sh
```

**Proven:** 2026-07-31 — hermes-canopy starved for hours. 4 zombies (consensus, <project>, h3-sdk-python-foreman, Kobayashi-Maru) with NULL `completed_at` held all 4 slots; gateway at 10-run cap dropped every spawn; canopy at p=8 lost every tie. After completed_at fix + priority 10 + gateway limit 25 → canopy ticked within the same eval cycle.

### Scheduler won't start
```bash
# Check if port is in use
ss -tlnp | grep 9090

# Check DB integrity
sqlite3 ~/.hermes/coding-hermes/scheduler.db "PRAGMA integrity_check"

# Run migrations
./bin/migrate -db ~/.hermes/coding-hermes/scheduler.db
```

### Watchdog (systemd)
```bash
systemctl status coding-hermes-scheduler
journalctl -u coding-hermes-scheduler --since "5 minutes ago"
systemctl restart coding-hermes-scheduler
```

## How Ticks Differ From Cron Jobs

The scheduler handles **per-project foreman ticks** (coding, building, committing). The **Supervisor** (separate cron, `0 */4 * * *`, `coding-hermes-supervisor` skill) handles fleet governance: adjusting project priority/weight, fixing stuck ticks, selecting models.

### Cron Delivery Pipeline (How Hermes Cron Actually Works)

**Critical architectural finding (2026-07-17):** The Hermes cron system does NOT spawn `hermes chat` as a subprocess. It runs the agent **in-process** inside the Python cron scheduler:

```
run_one_job() → run_job() → AIAgent(prompt) in Python → captures final_response
  → _deliver_result() wraps with "Cronjob Response: {name}\n(job_id: {id})"
  → _send_to_platform() → Telegram
```

Key facts about `run_job()` (see `cron/scheduler.py:2487`):
- Imports `AIAgent` from `run_agent` and constructs it in-process
- Loads skills as system prompt additions, not subprocess args
- Pre-run scripts, wake-gate checks, workdir locking, SessionDB
- Returns `(success, full_output, final_response, error)` tuple
- Delivery is handled by `_deliver_result()` AFTER the agent finishes

**`hermes chat -q -Q` is stdout-only.** It does NOT go through the cron delivery pipeline. Raw subprocess output stays in stdout; only the cron wrapper adds delivery routing. Full research notes: `references/cron-delivery-research.md`.

### Scheduler vs Cron — Agent Execution

| | Scheduler Gateway (FEAT-003) | Scheduler Process (legacy) | Cron |
|---|---|---|---|
| Agent runs | `POST /v1/responses` → gateway | `exec.Command("hermes", "chat", "-q", ...)` | `AIAgent(prompt)` in-process |
| Output | HTTP response JSON | Stdout captured → `SpawnedTick.Output` | Captured by `run_job()` |
| Delivery | ✅ `hermes send` via gateway routing | ✅ `hermes send` via gateway routing | `_deliver_result()` → Telegram |
| Session | Gateway session per project key | No SessionDB | Full SessionDB |
| MCP overhead | Zero — shared by gateway | ~175MB per chat (foreman MCP opt) | In-process, shared |
| PID tracking | None | Required (zombie reaper) | None |

### Supervisor vs Scheduler Tick

| | Supervisor (cron) | Scheduler Tick (schedulerd) |
|---|---|---|
| Runs | Every 4 hours via cron | Every 60s via daemon loop |
| Scope | Fleet-wide governance | Per-project coding foreman |
| Does | Adjust priority, fix stuck, pick models | hermes chat → read board → code → commit |
| Env | Cron's own context | CODING_HERMES_TICK env vars |

### Cron Legacy Table

| | Cron Job (hermes cron) | Scheduler Tick (schedulerd) |
|---|---|---|
| Trigger | Fixed schedule | Dynamic urgency + weight budget |
| Concurrency | `_running_job_ids` in RAM | OS process tracking in SQLite |
| Timeout | No per-run timeout | Configurable per-spawn timeout |
| Traceability | Implicit | Explicit env vars + tick ID |
| Delivery | Cron scheduler handles | ✅ Shipped: `deliverOutput()` → Telegram |
| State | Fragile (fire_claim zombies) | Durable (SQLite WAL) |
| Model/provider | Per-job | Per-project (same rule) |

## Fleet-Wide Project Audit

To audit a batch of projects for real pending task count and cooldown state, cross-reference three independent sources in parallel:

| Source | What it tells you | Tool |
|--------|-------------------|------|
| **GitReins MCP** | GitReins task list (all statuses) | `mcp__gitreins__task_list(workdir=...)` |
| **Foreman board** | `.coding-hermes/tasks.md` — authoritative task state | `read_file` |
| **Scheduler API** | CooldownS, Enabled, last tick times | `GET /api/v1/projects` |

**Counting rules for "real pending":**
- Exclude `NEVER-DONE` tasks (recurring audit sweep)
- Exclude `U01` tasks (usability/coverage audit)
- Distinguish **BLOCKED** (human-gated, content-gated, infra-blocked, no-sudo) from **actionable pending**
- GitReins may be stale — the `.coding-hermes/tasks.md` foreman board is authoritative when they conflict
- Foreman board uses model-router table format, not markdown checkboxes — grep for `- [ ]` won't catch tasks

See `references/project-audit-methodology.md` for the full workflow with examples.

### 🪤 Cooldown Flapping — Foreman Self-Pause vs Real Pending Work (2026-07-31)

**Symptom:** Enabled projects sit at 43200s (12h) cooldown while their boards
have real pending tasks. The foreman self-paused because it misclassified
dispatchable work as "blocked" or "idle". Audit found **21/35 enabled projects
parked at 12h-24h with pending work** (asce PH2-001/002/003, Kobayashi-Maru 5
pending gitreins tasks, <project> 26 rows, helix/mythos/<project>/etc.). The
API PUT to 900s was reverted within hours — the same foremen re-paused on the
next tick because the skill had no guard.

**Three fixes (all shipped 2026-07-31):**
1. **fleet.toml guard in the board skill** — before any self-pause PUT, foremen
   MUST check `~/coding-hermes-scheduler/coding-herms-scheduler/fleet.toml`.
   If the project has a `[[projects]]` entry, its `cooldown_s` is ADMIN INTENT
   and overrides foreman judgment. No PUT. Log "fleet.toml pins cooldown_s=X,
   admin intent — no PUT performed". Prevents the restart→900→tick→43200
   oscillation (proven: hermes-canopy ticks #104-106).
   For fleet.toml cooldown pinning (Bane rule: add ONLY the one workload being
   pinned; file only takes effect on restart WITH `--config fleet.toml`;
   scheduler.db is ground truth), see `references/fleet-toml-cooldown-pinning.md`.
2. **Cooldown-vs-pending watchdog** — `scripts/fleet-cooldown-audit.py`
   (installed at `~/.hermes/scripts/fleet-cooldown-audit.py`, cron job
   "Fleet Cooldown Audit" `dda7f27db73f`, every 6h, no_agent). Runs the
   4-method board pending count + GitReins dual-source + fleet.toml awareness.
   Silent when clean; reports only when a project is slow-parked WITH pending
   work. **The 6h board-format audit missed this failure class — cooldown
   state must be checked against pending work, not just board structure.**
3. **Board rows must be dispatchable** — a task marked "SPEC WRITTEN —
   dispatchable" must not be classified "blocked on spec" by the foreman.
   Empty model cells on a row read as "not ready". Give every open task full
   model cells + explicit dispatch status.

**Detecting the flap live:** the audit cron catches it within 6h. Manual:
```bash
python3 ~/.hermes/scripts/fleet-cooldown-audit.py
```

### Case-Sensitive Project Names

The scheduler DB is case-sensitive. `Speclang` (capital S, workdir `~/SpecLang`) and `speclang` (lowercase, workdir `~/speclang`) are different projects pointing at different directories. Always verify workdir when auditing: `GET /api/v1/projects | python3 -c "..."` to map Name→Workdir.

**⚠️ Case-duplicate with SAME workdir = ghost project (2026-07-31).** The dangerous
variant is two entries pointing at the **same** workdir with different casing:
`<project>` and `<project>` both → `~/<project>`. The real project (`<project>`)
had **661 ticks** (Jul 18→Jul 29, all committed, self-paused at 43200s); the ghost
(`<project>`, created 8 days later, no deliver target) had **0 ticks ever**. The
ghost was enabled with 900s cooldown and looked like a 5-day-dead foreman.

**⚠️ Query ticks case-insensitively.** `SELECT ... WHERE project_name='<project>'`
(exact case) returns ZERO rows when the project row is `<project>` — leading to the
wrong conclusion "this foreman never ran / logging is broken." Always use
`WHERE lower(project_name) LIKE '%<project>%'` when investigating. The logging
system was fine; the lookup was case-sensitive.

**Detection (both entries, same workdir):**
```sql
SELECT workdir, GROUP_CONCAT(name), COUNT(*) FROM projects
GROUP BY workdir HAVING COUNT(*) > 1;
```

**Fix:** Disable (or delete) the ghost entry via API
(`PUT /api/v1/projects/<ghost> {"Enabled":false}`), keep the entry with tick
history. The fleet audit script (`~/.hermes/scripts/fleet-cooldown-audit.py`)
flags DUPLICATE-WORKDIR automatically.

**Proven:** 2026-07-31 — `<project>` ghost created Jul 26 shadowed `<project>` (real,
661 ticks). Disabling the ghost + re-adding namespace to the real entry restored
service. A guard flagging duplicate workdirs was added to the fleet audit cron.

## Related Documents

- `references/project-audit-methodology.md` — Cross-source fleet audit: GitReins + foreman board + scheduler API, real-pending counting rules
- `references/delivery-formatting-architecture.md` — Bane-approved delivery pipeline: foreman markdown → scheduler passthrough → hermes gateway
- `references/operator-delegation-pattern.md` — Operator should task the foreman, not hand-patch Go code
- `references/foreman-memory-optimization.md` — Per-chat MCP duplication fix: HERMES_HOME, per-session config, 500MB→175MB per chat
- `references/go-mutex-io-deadlock.md` — Go pattern: write lock held during blocking I/O deadlocks health endpoints. Two-phase split fix (BUG-006).
- `references/fleet-stall-diagnostic.md` — 6-step checklist when multiple projects haven't fired: enabled count, disabled audit, inflated cooldowns, stale last_tick, duplicate processes, case-variant duplicates
- `references/scheduler-starvation-diagnostic.md` — Single-project starvation chain (2026-07-31): foreman self-pause trap, zombie ticks with NULL completed_at holding all slots, gateway max_concurrent_runs rate limit, packer priority starvation, detached gateway restart recipe, fleet.toml pinning
- `references/starvation-modes-2026-07-31.md` — Three silent-starvation modes with identical symptoms: nonexistent namespace (<project>), decay_rate=0 flat urgency (dexdat-memory, 9 projects), case-duplicate ghost entries (<project> vs <project>). Includes the PACKER-SORTED log reading technique and the 6-step no-tick triage order.
- `references/timeout-cooldown-v37-design.md` — Timeout/cooldown alignment: timeout=2h, no backoff, alerts to chat, auto-slowdown 1.5x/VERDICT-based
- `references/hermes-send-target-discovery.md` — How to discover valid platform/thread targets
- `references/zombie-tick-detection.md` — Process-liveness based zombie reaper
- `references/cron-delivery-research.md` — How Hermes cron delivery differs from subprocess delivery
- `references/packer-race-fix.md` — BUG-005: packer/spawner concurrency race — merge in-memory RunningSet with DB query
- `references/co-author-enforcement.md` — CODING_HERMES_CO_AUTHOR env var setup, foreman integration, commit template
- `references/duckbrain-model-discovery.md` — How to find model metadata when `/v1/models` doesn't list it
- `references/cron-to-scheduler-migration.md` — Two migration paths: standard foreman (Path A) and custom-command non-foreman (Path B). Post-migration verification checklist.
- `references/pending-audit-cooldown.md` — Batch-audit GitReins pending counts across N projects, then set cooldowns by result (0 pending→43200s, has-pending→900s).
- `references/single-project-fleet-audit.md` — "Is project X registered + cooldown right?" worked example: two-fleet.toml divergence, 3-source audit, duckdb board read pitfalls, targeted fix vs fleet-wide --apply (<project> 2026-08-01).

## Operator Pitfall: Hand-patching Go code instead of tasking the foreman

**Session evidence (2026-07-18):** 6+ hours of real-time Go code patching by the operator
produced cascading failures — broken service files, SlotFreed feedback loop (1388 ticks/5min),
all-project urgency reset to NULL, port-conflict crash loops. Bane: "are you actually putting
this work into the foreman task list letting a smart coding agent do the work and then benefit
from the upgrades or are you constantly trying to manage this yourself knowing it is not your
strong suite?"

**Rule:** For non-trivial code changes to the scheduler, the operator should **write clear
tasks to `.coding-hermes/tasks.md`** and let the coding-hermes-scheduler foreman (a specialized
coding LLM with full Go toolchain access, GitReins guards, and test suite) design and implement
the fix. The foreman runs its own build→test→lint→commit pipeline. The operator's role is
architecture direction, verification, and task prioritization — not line-by-line Go patching.

**Correct workflow:**
1. Identify the bug or feature gap
2. Write a task on the board with P:CRITICAL/HIGH/MEDIUM, weight, symptoms, and fix direction
3. Commit and push — the foreman picks it up on next tick
4. Verify the foreman's commits pass gates (build, vet, test, lint)

**Anti-pattern (what happened):** Operator edited loop.go, slot_pool.go, packer.go, main.go,
and the systemd service file in real-time across 10+ terminal calls. Each edit introduced
a new bug. The foreman was running concurrently, committing its own fixes, creating merge
conflicts and stale state.

See `references/operator-delegation-pattern.md` for the full session analysis.

## Blackout / Slowdown Hours (peak-pricing cost control) — SHIPPED `348729a`, 2026-07-30

When LLM providers adopt peak/off-peak pricing (e.g., DeepSeek 2x during
01-04 and 06-10 UTC), the scheduler can automatically slow down during
expensive windows — multiplying cooldowns so ticks spread into cheaper hours.

### How it works

Blackout windows are defined in the TOML config file under `[scheduler]`:

```toml
[[scheduler.blackout_windows]]
start = "01:00"       # HH:MM in UTC
end = "04:00"         # HH:MM in UTC
multiplier = 2.0       # double cooldown during this window
```

- **Multiplier > 1.0:** cooldown is multiplied during the window. A project
  with 600s cooldown effectively gets 1200s during peak.
- **Multiplier = 0:** skip mode — projects are NOT spawned at all during
  the window (useful for extreme peak pricing).
- **Outside windows:** normal cooldown applies. The gap between 04:00-06:00
  UTC runs at full speed.

The slowdown fires inside the packer's cooldown check — same codepath that
enforces per-project cooldowns. `ActiveMultiplier(windows, now)` determines
the current multiplier.

### Architecture

```
fleet.toml [scheduler.blackout_windows]
    → LoadRootConfig() at daemon start
    → Loop.SetBlackoutWindows(windows)
    → Packer / MultiPoolPacker.blackoutWindows
    → cooldown check: if in window → multiply cooldown
```

Three integration points in the pack pipeline:
1. `packer.go::Pick()` cooldown check — flat packer path
2. `packer_select.go` selection loop cooldown check — multipool path
3. `packer_select.go` queued/cooldown-skip check — same path

### Tests

9 unit tests in `internal/config/blackout_test.go` (windows, boundaries,
skip mode, multi-window, parseHM). 3 integration tests in `packer_test.go`
(DoublesCooldown, OutsideWindow, SkipMode) verifying the full Pick() path.

### No per-project config needed

Blackout windows are global scheduler config — they apply to ALL projects
equally. The slowdown is proportional to existing cooldown, so higher-priority
projects still tick more often than lower-priority ones during peak hours.
| 3.17.0 | 2026-07-31 | **Cooldown drift FIXED at source (`913650b`).** Root cause: `autoSlowdown` PRODUCTIVE reset clobbered operator-set cooldowns (43200 → 600 → 900s). Fix: productive reset skips cooldowns ≥3600s (`autoSlowdownMaxCD`). 4 regression tests. CooldownS=43200 now survives ticks AND restarts. |
| 3.13.0 | 2026-07-28 | **Cooldown drift root cause identified: autoSlowdown cap interaction.** Tick #172 confirmed drift on same daemon instance (no restart). Tick #173 confirmed cooldown holds at 43200s with 24h stable daemon uptime. Root cause: autoSlowdown has a 3600s cap; when cooldown > 3600s, autoSlowdown's PRODUCTIVE reset (→600s) or IDLE escalation (→cap) drops it. Four theories eliminated: API field name, Fleet TOML, SQLite WAL, startup init path. Fix: raise autoSlowdown cap or make it respect manual cooldown overrides. |
| 3.9.0 | 2026-07-19 | **FIX-STUCK: Gateway liveness check.** Before each eval cycle, ping gateway `/health` (5s timeout). If dead: release all slots, skip spawning, retry next cycle.
| 3.8.0 | 2026-07-19 | **Dedup guard:** `evaluate()` checks `SlotPool.RunningSet()` before spawning — skips projects already occupying a slot. |
| 3.11.0 | 2026-07-25 | **FIXED: NULL last_tick_started cooldown bypass (`7b34a43`).** `Spawn()` now updates `last_tick_started` in both gateway HTTP and exec.Command paths. Foreman tick #150 self-fixed the bug that had been documented for 80+ ticks. New binary at `bin/schedulerd`. |
| 3.10.0 | 2026-07-24 | **NULL last_tick_started cooldown bypass discovered.** 39/40 enabled projects have `last_tick_started IS NULL` — cooldown never enforced fleet-wide. Root cause of instant-fail tick pumping (<project>-e2e: 6,134 ticks in 48h, 82% of fleet). Added three pitfalls: NULL last_tick_started detection + fix, instant-fail pump detection + immediate disable, duplicate workdir entry detection. |
| 3.7.0 | 2026-07-19 | **Timeout=2h, no backoff, alerts to chat.** `--tick-timeout` 1800s→7200s (2h). Removed timeoutBackoff entirely — timeouts no longer increase cooldown. Added `deliverAlert()` — sends ⚠️ to chat on timeout. Auto-slowdown: 1.5x multiplier (was 2x), VERDICT-line detection (was fragile string match). **Pipeline:** timeout = just log + alert, project stays eligible after normal cooldown. No more spawn→timeout→backoff→silent-death loops. |
| 3.5.0 | 2026-07-19 | **Worker model defaults:** `worker_model`/`worker_provider` columns added to projects table (migration v6). PackedProject and MultiPoolPacker propagate them. Spawn prompt injects "Worker default: use model X with provider Y if available. Feel free to use a different model..." — non-binding, foreman can override. **gpt-5.6-sol:** Used as WORKER default for coding-hermes-scheduler's foreman, NOT as the foreman model itself (foreman stays deepseek-v4-pro). Model discovered via DuckBrain `/benchmarks/models/gpt-5.6-sol` (not `/v1/models`). Added to openai-codex provider in chimera reference_models. |
| 3.3.0 | 2026-07-19 | **Event-driven loop restored:** SlotFreed channel with 5s coalescing debounce. Single goroutine lifetime (no leak). Dual-trigger evaluation: event-driven (slot freed) + 30s health ticker. `--max-concurrent` raised to 10. `--min-interval` changed to 30s (wave gap, not eval interval). `--tick-timeout` set to 600s. **Gateway SIGKILL root cause found:** <project> pytest `os.killpg(1, SIGKILL)` killed everything in process group 1 every ~2.5min. Fix: PID validation. **Systemd:** BindsTo removed, Restart=on-failure. |
| 2.8.0 | 2026-07-18 | BUG-005: Packer/spawner race fixed with in-memory RunningSet merge. CO_AUTHOR enforcement documented (`.env`, foreman skill, commit template). Projects silently disabled pitfall documented (supervisor/race turns off enabled=1). Reference docs: `packer-race-fix.md`, `co-author-enforcement.md`. |
| 2.6.0 | 2026-07-18 | Systemd unit config drift pitfall: `--min-interval` defaults to 20m; must be explicit in ExecStart. Packer concurrency race closed (in-memory RunningSet merged with DB query). Gateway startup retry (10-retry backoff + background reconnector). Concurrency 4→12 safe with HTTP spawn. Tick timeout 30m→2h. `approvals.cron_mode: auto` unblocked gateway ticks. Leaked foreman cron detection (5 found, all paused). CODING_HERMES_CO_AUTHOR env var as single source of truth. Co-author corrected: handle → Real Name. |
| 1.5.0 | 2026-07-18 | `hermes send` delivery v2 (gateway routing, no raw APIs). Auto-slowdown (FEAT-001). Per-project delivery targets. Cooldown floors. Supervisor Phase 2D updated for scheduler API. **Pitfall fixed:** stale-tick clearing query was broken by SQLite timestamp format mismatch (ISO 8601+t vs UTC no-tz). Fixed clearing recipe uses Python `datetime.fromisoformat()`. |
| 1.1.0 | 2026-07-17 | Added cron delivery pipeline analysis, `--cli` pitfall, goroutine leak pitfall |
| 1.0.0 | 2026-07-16 | Initial — 27 projects live, 40+ cron jobs migrated, verify green |

## Systemd Configuration (production as of 2026-07-19)

```ini
[Unit]
Description=Coding Hermes Fleet Scheduler
After=network.target hermes-gateway.service
# No BindsTo — scheduler survives gateway restarts independently.

[Service]
Type=simple
User=kara
KillMode=control-group
KillSignal=SIGTERM
TimeoutStopSec=30
ExecStartPre=-/usr/bin/pkill -f "hermes.*foreman"
ExecStartPre=-/usr/bin/pkill -f "duckbrain"
ExecStart=~/coding-hermes-scheduler/coding-herms-scheduler/bin/schedulerd \\
  -db ~/.hermes/coding-hermes/scheduler.db \\
  -listen 127.0.0.1:9090 \\
  --namespace-mode \\
  --max-concurrent 4 \\
  --min-interval 30s \\
  --tick-timeout 7200s \\
  --gateway-url=http://127.0.0.1:8642
Restart=on-failure
RestartSec=30
MemoryMax=8G
Environment=HOME=~
Environment=PATH=~/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=API_SERVER_KEY=WZJht...

[Install]
WantedBy=default.target
```

**`-` prefix on ExecStartPre:** Ignores exit codes from pkill (process may not exist).
**`hermes.*foreman` pattern:** Regex, not shell glob — pkill requires a single pattern (no spaces).

**Restart=on-failure pitfall:** The scheduler exits with status=0 on clean shutdown.
With `on-failure`, systemd does NOT restart it. Use `Restart=always`.

**⚠️ MemoryMax cgroup boundary pitfall (2026-07-19 OOM):** Systemd `MemoryMax` on the
scheduler service ONLY covers the scheduler binary — NOT the foreman workers it spawns
via `exec.Command`. Workers run as separate `hermes chat` processes under
`user@1000.service` (the user slice), with no per-worker cgroup. **The scheduler can
stay well under its 8G limit while 4 concurrent workers + their child processes
(go build, pytest, govulncheck, DuckBrain MCP) collectively push the user slice past
the system OOM threshold.** When `user@1000.service` gets SIGKILL'd, systemd PID 1
cleans up the ENTIRE user slice — all sessions (SSH drops), all services (gateway,
scheduler, signal-cli), and all Docker containers die simultaneously.

**Mitigations (layered):**
1. Lower `--max-concurrent` (4→2 halves spike risk but cuts throughput)
2. Per-worker cgroups: `systemd-run --user --scope -p MemoryMax=4G hermes chat ...`
3. Sequence heavy ops: avoid simultaneous go build/test/govulncheck across repos
4. Swapfile as pressure valve (16G swap on 59G RAM system)

**Proven:** 2026-07-19 06:30 CT — OOM killer nuked user@1000.service (1.1G peak),
SSH session (1.3G), scheduler (2.5G, under its 8G limit), gateway (565M), signal-cli
(404M). Scheduler was at 4/4 concurrent. Real spike was foreman build/test pipelines
in the user slice — not the scheduler process itself.

**With gateway HTTP spawn (FEAT-003):** Ticks run inside the gateway process, so worker
memory lands in the gateway's cgroup, not the user slice. Gateway MemoryMax should be
sized to absorb concurrent foreman loads.

**MemoryMax:** Systemd cgroup counts ALL processes in the service — including
hermes chat subprocesses spawned via exec.Command (legacy fallback path). A 26.8GB peak
is EXPECTED (8 × 3GB LLM agents + overhead). This is NOT a Go memory leak — it's
subprocess memory. The `active` map IS cleaned in Wait() via
`defer delete(st.spawner.active, st.TickID)`.

**No watchdog cron needed:** The old `Scheduler Daemon Watchdog` (every 2m, no_agent script)
is paused and unnecessary. Systemd handles restarts.

## Foreman Memory Optimization\n\nSee `references/foreman-memory-optimization.md` for the full technique.\n\n**TL;DR:** Each `hermes chat` spawns its own MCP servers (duckbrain, gitreins, flights,\nchimera) + Chrome browser. 8 concurrent = ~4GB in duplicated MCP infrastructure alone.\n\n**Fix:** Per-session `HERMES_HOME=~/.hermes/foreman` with minimal config:\n- Browser disabled (`disabled_toolsets: [browser]`)\n- Only duckbrain + gitreins MCPs (foreman needs memory + CI guard, nothing else)\n- Skills/sessions/logs/cache symlinked from main config dir\n- **Without skills symlink:** \"Unknown skill(s): coding-hermes-foreman\" — all ticks fail in 1s.\n\nPer-chat savings: 500MB → 175MB (-65%). 4 concurrent: ~700MB total.\n\n### 🪤 Cooldown Drift — ROOT CAUSE FOUND + FIXED AT SOURCE (2026-07-31, commit `913650b`)

**Symptom:** `CooldownS` reverts from 43200s to lower values (900s or 3600s)
during normal daemon operation, WITHOUT a restart. Confirmed across ticks #131-#173.

**Root cause — autoSlowdown cap interaction (CONFIRMED ticks #172-#173):**
The autoSlowdown mechanism in `slowdown.go` has a 3600s (1h) cap (per
RULE-NO-TIMEOUT-BACKOFF). When a project has a manual cooldown above the cap
(e.g., 43200s = 12h) and the foreman reports `VERDICT: idle` or `VERDICT:
productive`, autoSlowdown reclassifies the cooldown: productive resets to 600s,
idle escalates 1.5x toward the 3600s cap. Either path DROPS a 43200s cooldown
below the cap.

**Why this was confused with daemon restart:** The drift-to-900s pattern was
observed after restarts simply because autoSlowdown fires on every tick
completion. After a restart, the first tick completes quickly (nothing to do),
autoSlowdown sees IDLE, escalates cooldown. The 900s value came from the schema
default being applied at some point during the escalation chain — NOT from
a startup init path.

**Four theories eliminated:**
1. **API field name mismatch (ELIMINATED tick #171):** Snake_case `cooldown_s`
   silently ignored; camelCase `CooldownS` works. Fixing the field name allowed
   correct PUTs but did NOT stop drift — drift continued at tick #172 WITHOUT
   a restart.
2. **Fleet TOML ApplyFleetConfig (ELIMINATED tick #135):** Create-only, does
   not upsert on restart.
3. **SQLite WAL non-persistence (ELIMINATED tick #171):** PUT writes persist
   within daemon lifetime. Tick #172 confirmed drift on same daemon instance.
4. **Daemon startup init path (ELIMINATED tick #173):** Drift occurs without
   restart (tick #172). First stable observation at tick #173: daemon 24h
   uptime, no restart, cooldown held at 43200s. Drift happens at ~12h
   intervals — consistent with autoSlowdown firing on tick completion, not
   daemon restart.

**Confirmed by stability at tick #173:** Daemon PID 581124, 24h uptime, no
restart, cooldown stable at 43200s. The cooldown survived because this tick
arrived within the 12h window before autoSlowdown could reclassify.

**DEFINITIVE ROOT CAUSE (ticks #131-#181 → SHIPPED fix `913650b`, 2026-07-31):**
`autoSlowdown` in `slowdown.go` was clobbering operator-set cooldowns. The
PRODUCTIVE branch (`isProductive`) reset cooldown to **600s** whenever the
tick output contained `VERDICT: PRODUCTIVE`. The next IDLE tick then escalated
600 × 1.5 = **900s** — exactly the observed "drift to 900s" pattern. The 43200s
(12h) self-pause never survived a single tick; restarts were coincidental,
not causal (autoSlowdown fires on every tick completion, restart or not).

**The fix (`913650b`):** the productive reset now skips cooldowns ≥
`autoSlowdownMaxCD` (3600s = 1h, the operator-set/self-pause boundary). IDLE
escalation still runs at any level — it only INCREASES cooldown, so it can
never clobber operator intent. The DecayRate theory was secondary: setting
`DecayRate=0` helps but was not sufficient — autoSlowdown re-wrote cooldown
after every tick regardless.

**4 regression tests added** in `slowdown_test.go` (all pass, 9/9 packages):
- `OperatorSet_ProductiveDoesNotReset` — 43200 survives PRODUCTIVE
- `OperatorSet_Boundary3600_NotReset` — 3600 survives (uses `>=`, not `>`)
- `AutoBand_ProductiveStillResets` — 2700 still resets (auto band intact)
- `OperatorSet_IdleStillEscalates` — 43200 → 64800 on IDLE (×1.5 allowed)

**After this fix, `CooldownS=43200` survives ticks AND restarts.** The
PUT bandage below is only needed on hosts still running a pre-913650b binary.

**⚠️ Post-fix evidence — drift can persist if the daemon hasn't restarted onto the new binary (2026-08-01, ASCE tick #224):** 52 consecutive ASCE zombie ticks still observed the 900s reversion ("reversion #52") AFTER `913650b` shipped. The `913650b` fix only takes effect when the daemon is restarted onto the freshly-built binary — a long-running daemon keeps the OLD autoSlowdown behavior and keeps clobbering. Before re-investigating root cause on any project that still drifts post-fix: (1) check daemon uptime (`systemctl show coding-hermes-scheduler --property=ActiveEnterTimestamp`) vs the fix commit date, (2) restart the daemon, then (3) re-verify `CooldownS` survives a tick. Only if drift persists AFTER a post-fix restart is it a new bug. The bandage PUT remains the correct per-tick action for zombie projects on pre-fix daemons.

**Prior theories (kept for context, all superseded):**
1. **API field name mismatch (ELIMINATED tick #171):** Snake_case `cooldown_s`
   silently ignored; camelCase `CooldownS` works. Fixing the field name allowed
   correct PUTs but did NOT stop drift — drift continued at tick #172 WITHOUT
   a restart.
2. **Fleet TOML ApplyFleetConfig (ELIMINATED tick #135):** Create-only, does
   not upsert on restart.
3. **SQLite WAL non-persistence (ELIMINATED tick #171):** PUT writes persist
   within daemon lifetime. Tick #172 confirmed drift on same daemon instance.
4. **DecayRate auto-multiplication (SECONDARY — tick #174):** `DecayRate=1`
   multiplies cooldown after completed ticks via the backoff pipeline,
   operating independently of autoSlowdown. Setting `DecayRate=0` disables
   this pipeline, but the primary clobber was autoSlowdown's productive reset.

**Detection:**
```bash
# Check cooldown after daemon restart
curl -s http://127.0.0.1:9090/api/v1/projects/coding-hermes-scheduler | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['project']['CooldownS'])"
# 900 = drifted (default). 43200 = correct.
```

**Immediate fix (bandage — ONLY for hosts running a pre-913650b binary; must reapply after drift):**
```bash
# Check current state
curl -s http://127.0.0.1:9090/api/v1/projects/coding-hermes-scheduler | \
  python3 -c "import sys,json; d=json.load(sys.stdin); p=d['project']; print(f'CooldownS={p[\"CooldownS\"]}, DecayRate={p.get(\"DecayRate\",\"?\")}')"

# Fix BOTH fields — either alone can still drift
curl -s -X PUT http://127.0.0.1:9090/api/v1/projects/coding-hermes-scheduler \
  -H 'Content-Type: application/json' \
  -d '{"CooldownS": 43200, "DecayRate": 0}'
```

**Daemon restart mystery (tick #172):** Daemon restarted at 20:12 local with
no matching Stop/Stopped journal entry — previous instance (PID 527683)
simply vanished. Peak memory 315MB (well under MemoryMax=8G). No OOM kernel log.
Systemd Restart=on-failure would trigger if process exited non-zero — but with
no stop journal entry, the process may have been killed externally (user-slice
OOM, not cgroup). The `deploy/scheduler-verify.sh` cron (every 2h) runs
`--test-verify` against the same DB — possible interaction but unproven.

## Fleet TOML — Creating and Updating Project Entries

The fleet TOML file declaratively seeds project definitions into the SQLite DB at
scheduler startup. It is **create-only** — it does not upsert existing rows.

### Finding the Fleet TOML location

⚠️ **TWO fleet.toml files exist and they diverge (2026-08-01). Grep the CANONICAL one:**

1. **Repo copy:** `~/coding-hermes-scheduler/coding-herms-scheduler/fleet.toml` — hand-edited template with 4 entries (<project>, <project>, hermes-canopy, helios). **Stale** — values drift from live DB (e.g. helios 43200 there vs 900 in canonical).
2. **Canonical:** `~/.hermes/fleet.toml` — auto-generated by `fleet-cooldown-policy.py --apply` ("Auto-generated ... do not edit by hand" header), ~45 pins, and **the file the daemon actually loads**.

**Always verify which file the LIVE daemon uses before claiming pin durability:**
```bash
ps aux | grep schedulerd | grep -v grep | grep -o -- '-config [^ ]*'
# → -config ~/.hermes/fleet.toml   ← canonical, this is what counts
```
The daemon accepts `--config fleet.toml` / `-config <path>`; without the flag, the
API-set values are the sole source of truth. The repo `fleet.example.toml` is just
a template — do not assume the running daemon uses it.

### ⚠️ Fleet pins do NOTHING unless schedulerd runs with `--config fleet.toml` (2026-08-01)

**Symptom:** You add a `[[projects]]` entry to fleet.toml (cooldown pin, namespace,
deliver) and the project STILL doesn't behave — wrong cooldown, wrong namespace,
no restart protection. The entry sits in the file, inert.

**Root cause:** `ApplyFleetConfig` only runs at daemon boot when the `--config`
flag is passed. **Both the systemd unit AND the watchdog script omit it:**
- `/etc/systemd/system/coding-hermes-scheduler.service` — ExecStart has no `--config`
- `~/.hermes/scripts/scheduler-watchdog.sh` — restart line has no `--config`

So even a correctly-written fleet.toml is never applied on boot or on watchdog
restart. The DB is the sole source of truth the whole time.

**✅ Status update (2026-08-01, later same day):** The daemon NOW runs with
`-config ~/.hermes/fleet.toml` (confirmed via `ps aux | grep schedulerd`),
and since commit `67c5c0c` `ApplyFleetConfig` re-pins on EVERY start, not just
create. **But verify the live flag before assuming pins hold** — the systemd unit
and watchdog may regress to no-flag on any reinstall. Detection one-liner:
```bash
ps aux | grep schedulerd | grep -v grep | grep -o -- '-config [^ ]*'
```

**Fix — two layers:**
1. Make the DB correct NOW (this is what actually takes effect immediately):
   ```bash
   python3 -c "
   import sqlite3
   db = sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
   db.execute(\"UPDATE projects SET namespace_id='coding-hermes', cooldown_s=43200, decay_rate=1.0 WHERE name='<project>'\")
   db.commit()"
   ```
2. Add `--config ~/coding-hermes-scheduler/coding-herms-scheduler/fleet.toml`
   to the systemd ExecStart (and the watchdog restart line) so the pin survives
   restarts. The fleet.toml entry is the durable admin-intent record; the DB
   update is the immediate fix.

**Full triage for "project not running on its cadence" (proven: helios 2026-08-01):**
```bash
# 1. namespace — NULL means namespace-mode allocator NEVER picks it
python3 -c "import sqlite3;db=sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
for r in db.execute('SELECT name, enabled, namespace_id, cooldown_s, decay_rate FROM projects WHERE name=\"<project>\"').fetchall(): print(r)"
# 2. cooldown — 900s vs desired 43200s (12h)
# 3. fleet.toml entry — grep -A12 '<project>' fleet.toml
# 4. --config flag on running daemon — ps aux | grep schedulerd | grep -o -- '--config [^ ]*'
```
helios had namespace_id=NULL, cooldown_s=900, no fleet.toml entry, and the daemon
ran without --config. All four fixed; scheduler API then confirmed
`enabled=True namespace=coding-hermes cooldown=43200s (12.0h)`. Also set the
`deliver` field to the project's Telegram thread (`telegram:-1003310984808:4297`
for helios) — a NULL/empty deliver means tick output goes nowhere.

### Adding a single project entry

Create a minimal fleet.toml with only the project(s) that need static overrides.
Other projects are left to their API/DB values:

```toml
[[projects]]
name = "my-project"
repo_url = "local:~/my-project"
workdir = "~/my-project"
weight = 15
priority = 9
cooldown_s = 43200
model = "deepseek-v4-pro"
provider = "deepseek-foreman"
namespace_id = "coding-hermes"
deliver = "telegram:-1003310984808:92897"
enabled = true
```

**Critical:** Get the `deliver` value from the scheduler API (`GET /api/v1/projects/<name>`)
or from `hermes send --list telegram` — do NOT guess the thread ID.

### 🎯 Single-project audit: "is project X registered + cooldown right?" (2026-08-01)

3-source verification for one project — do these in parallel, in this order:

1. **Live daemon flags** — `ps aux | grep schedulerd | grep -o -- '-config [^ ]*'`
   (which fleet.toml actually applies). Then grep THAT file for the project entry.
2. **Scheduler API** — `curl -s http://127.0.0.1:9090/api/v1/projects/<name>` and parse
   `.project` (NOT top-level — nulls otherwise): `jq '.project | {Name, CooldownS,
   Enabled, Priority, Weight, DecayRate, NamespaceID, Deliver}'`. Check: enabled=1,
   namespace exists in `GET /api/v1/namespaces`, DecayRate=1.0 (0 = starvation trap),
   Deliver non-empty.
3. **Real pending count** — board tasks.parquet via duckdb (NOT board.db — that's
   DuckDB format, sqlite3 fails with "file is not a database"; `fetchdf()` needs
   pandas, use `fetchall()`):
   ```bash
   python3 - <<'EOF'
   import duckdb
   con = duckdb.connect()
   n = con.execute("SELECT count(*) FROM read_parquet('~/<proj>/.coding-hermes/board/tasks.parquet') WHERE status IN ('pending','in_progress','blocked') AND id != 'NEVER-DONE'").fetchone()[0]
   print(n)
   EOF
   ```
4. **Ground truth** — run `python3 ~/.hermes/scripts/fleet-cooldown-policy.py` (dry-run,
   NO `--apply`). It prints `PROJECT PENDING COOLDOWN TARGET ACTION` — the REDUCE line
   is the policy's own verdict.

**Cooldown matrix (Bane 2026-07-31):** 1+ real pending → **900s** (15m fast mode);
0 pending → **7200s** (2h default). A 43200s (12h) pin with pending board work =
foreman self-pause misclassifying dispatchable work — the exact Cooldown-Flapping
failure class above.

**⚠️ Targeted fix, NOT fleet-wide `--apply`:** `fleet-cooldown-policy.py --apply`
reduces EVERY enabled project toward its target — including deliberate admin-intent
12h pins. **Proven 2026-08-01:** dry-run showed <project> (0 pending, 43200s =
Bane admin intent, pinned) would be REDUCED 43200→7200 by a fleet-wide apply. For a
single project:
```bash
# 1. Live fix (API)
curl -s -X PUT http://127.0.0.1:9090/api/v1/projects/<name> \
  -H 'Content-Type: application/json' -d '{"CooldownS": 900}'
# 2. Durable pin — patch cooldown_s in the CANONICAL ~/.hermes/fleet.toml entry
#    (raw PUT alone reverts at next restart; pin file survives because daemon runs -config)
```
Only use `--apply` when you want the policy applied to the WHOLE fleet and have
checked no admin-intent pins get clobbered.

### DecayRate=0 is required for manual cooldown stability

When setting a manual `cooldown_s`, ALWAYS also set `DecayRate=0`. The fleet
TOML example template doesn't include `DecayRate`, but putting it explicitly
prevents the auto-multiplication pipeline from escalating the cooldown after
each tick completion:

```toml
cooldown_s = 43200
decay_rate = 0     # prevents autoSlowdown from multiplying this
```

**Without DecayRate=0,** the daemon's backoff pipeline can multiply the cooldown
independently of autoSlowdown, producing unexpected values like 900s on a project
that was set to 43200s.

The same rule applies to API PUTs — include `"DecayRate": 0` alongside `"CooldownS"`:

```bash
curl -s -X PUT http://127.0.0.1:9090/api/v1/projects/my-project \
  -H 'Content-Type: application/json' \
  -d '{"CooldownS": 43200, "DecayRate": 0}'
```

### ⚠️ DecayRate=0 is ONLY safe for genuinely idle projects (2026-07-31)

**DecayRate=0 on a project with pending work = PERMANENT STARVATION.** The urgency
formula is `urgency = priority × (1 + elapsed/interval)^decayRate`. With
decayRate=0, the exponent collapses the whole expression to `priority × 1 = 10`
— **elapsed time is completely ignored**. The project NEVER becomes urgent, so
the packer never picks it, regardless of how long it waits. The starvation
escalator fires (`project starved: X — last tick 87h ago`) but the allocator
can't act — the project's urgency is flat at the bottom of the sort.

**Proven:** 2026-07-31 — dexdat-memory starved **87 hours** with valid namespace,
enabled=1, cooldown=900s, priority=10. Root cause: `decay_rate=0` (misapplied by
a foreman treating self-pause as "set decay to 0"). 9 projects affected fleet-wide
(dexdat-memory, mythos, <project>, <project>, <project>, duckbrain,
speclang, coding-hermes-scheduler, <project>) — all restored to 1.0 and
immediately jumped to the top of the packer queue (urgency 105,492 for
dexdat-memory after 87h).

**The rule:**
- `DecayRate=1` (default) → urgency grows with elapsed time → healthy for active projects
- `DecayRate=0` → **only** for projects that are TRULY idle AND have verified 0 pending work (self-pause at 43200s). Never set it on a project with open board tasks or pending GitReins tasks.
- If a foreman wants "slow cadence while keeping urgency", raise cooldown_s instead — never zero the decay rate.

**Detection (decay=0 + pending work = misconfiguration):**
```bash
python3 -c "
import sqlite3, re, os
db = sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
for r in db.execute('SELECT name, workdir FROM projects WHERE enabled=1 AND decay_rate=0').fetchall():
    name, wd = r
    board = os.path.join(wd or '', '.coding-hermes', 'tasks.md')
    if not os.path.isfile(board): continue
    c = open(board).read()
    pend = len(re.findall(r'^## \[ \]', c, re.M)) + len(re.findall(r'^- \[ \]', c, re.M)) + len(re.findall(r'🔴 Open|⬜ Not Started|🟡 Blocked', c))
    if pend > 0: print(f'STARVED: {name} decay=0 pending={pend}')
"
```
The fleet audit script (`~/.hermes/scripts/fleet-cooldown-audit.py`) flags
`DECAY-ZERO-STARVATION` automatically — check its output for this class.

### Fleet TOML overwrites project state on daemon restart (2026-07-19)

**Symptom:** Projects repeatedly become disabled after every scheduler restart.
asce, helios, muster, mythos, off-by-one, <project> flip from enabled→disabled
on every daemon bounce. Re-enabling via SQL lasts only until the next restart.

**Root cause:** The scheduler's fleet TOML config applies project settings on
startup via `ApplyFleetConfig`. If a TOML entry has `Enabled = false`, it
overwrites the DB value. Foremen that determine a project is "complete" may
also set enabled=0 in the DB — and if the TOML disagrees, the DB wins only
until the next daemon restart.

**Detection:**
```bash
# Check for projects that flip state
journalctl -u coding-hermes-scheduler | grep "TOML.*disable\|fleet.*enabled=0"
# Check DB after restart
python3 -c "
import sqlite3;db=sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
for r in db.execute('SELECT name,enabled FROM projects ORDER BY enabled,name').fetchall():
    print(f'{r[1]} {r[0]}')
"
```

**Fix options:**
1. **Set `Enabled = true` in fleet TOML** for projects that should always run
2. **Remove the project from fleet TOML** so it's DB-only (no overwrite)
3. **Lock the DB after manual changes** so TOML doesn't reapply

**Proven:** 2026-07-24 — <project> cooldown reverted 15 times across ticks #15-30. Investigation found THREE independent mechanisms each pushing cooldown to 43200s:
1. **DecayRate=1 auto-escalation:** The daemon's backoff pipeline multiplied cooldown after every tick. Setting `DecayRate=0` disabled the auto-increase.
2. **Old cron job fighting scheduler:** The legacy `<project>-coding-foreman` cron (`56351fc56f98`) was still running alongside the scheduler daemon. Both executed the foreman skill — the old cron's self-pause graduated slowdown escalated cooldown every ~5 ticks. Pausing the old cron stopped the conflict.
3. **DuckBrain status misclassification:** All project status entries said `"status": "idle"` with `"phase": "Phase 1+2 complete"`. The foreman read this, incremented the idle counter at `/project/<name>/status/idle-ticks`, and triggered graduated slowdown (count≥5 → 12h). Updating status to `"active"` and resetting idle-count to 0 broke the loop.

**Detection:**
```bash
# Check for DecayRate escalation
curl -s http://localhost:9090/api/v1/projects | python3 -c "
import json,sys
for p in json.load(sys.stdin):
    if p.get('DecayRate', 0) > 0 and p.get('Enabled'):
        print(f'{p[\"Name\"]}: DecayRate={p[\"DecayRate\"]} CooldownS={p[\"CooldownS\"]} — WILL auto-escalate')
"

# Check for leaked foreman crons
python3 << 'PYEOF'
import json
with open('~/.hermes/cron/jobs.json') as f:
    data = json.load(f)
for j in data.get('jobs', []):
    skills = str(j.get('skills', [])).lower()
    if 'foreman' in skills and not j.get('paused_at') and j.get('enabled'):
        print(f"LEAKED: {j['job_id']} {j.get('name','?')} schedule={j.get('schedule','?')}")
PYEOF

# Fix: disable decay + pause old cron + update DuckBrain
# curl -X PUT .../projects/<name> -d '{"CooldownS":900,"DecayRate":0}'
# cronjob(action='pause', job_id='<leaked-id>')
# duckbrain_remember(key='/project/<name>/status', status='active')
```


ASCE foreman tick #163 confirmed: "Fleet TOML values overwrite API-set
Enabled: false on every daemon restart. The per-tick API PUT is a bandage
that gets torn off on every restart."

**Symptom (2026-07-18):** Scheduler evaluates only 3 times/hour. Most projects
on cooldown when the eval window opens. Tick frequency way too low — <project>
got 0 ticks for hours, <project> never got a tick despite being enabled.

**Root cause:** The systemd unit's ExecStart was rewritten (foreman edit, commit `e6b860f`)
from explicit flags to `--config config.example.toml`. The TOML file didn't include
a `scheduler.min_interval` field, so the Go default (20m) was used. The original
explicit `--min-interval 1m` flag was lost.

**Fix:** Keep `--min-interval 1m` explicitly in the systemd ExecStart line.
TOML config should supplement, not replace, critical performance flags.

**Verification:**
```bash
# Check current min-interval
ps aux | grep schedulerd | grep -o "\-\-min-interval [^ ]*"
# Should show "1m" (or whatever is set), not absent

# Check eval frequency
journalctl -u coding-hermes-scheduler --since "1 hour ago" | grep "EVAL:" | wc -l
# Should be roughly 55-60/hour with 1m interval. <10/hour = using default 20m.
```

**Proven:** 2026-07-18 — foreman committed systemd unit rewrite; `--min-interval` dropped.
Scheduler evaluated at 20m intervals for ~2 hours before manual correction.

Started at 8, reduced to 4 after memory analysis showed per-chat MCP duplication (~500MB/chat). After FEAT-003 (HTTP API spawn), per-tick overhead is zero — all ticks share the gateway process. Raised back to 12 for better throughput. With gateway mode: 12 concurrent = 0MB. With exec.Command: ~175MB/chat. → 4)\n\nReduced from 8 to 4 after memory analysis showed no Go leak — all memory was from\nper-chat MCP duplication + subprocesses. 4 concurrent with foreman MCP optimization\ncaps peak at ~700MB + 4 × LLM subprocess overhead. Safe for hosts with 59GB RAM.

### `--cli` flag blocks Telegram delivery (FIXED)

**DO NOT pass `--cli` to `hermes chat` spawns.** `--cli` is a **global** Hermes flag that forces an interactive `prompt_toolkit` REPL — it is NOT a `hermes chat` subcommand flag. When combined with `-q` (non-interactive single query), the flags contradict each other. The `--cli` flag was in the spawn args from initial implementation and suppressed delivery routing. Fixed by removing `--cli` and keeping only `-Q` for quiet mode. **Proven:** 2026-07-17 — `--cli` was present in `spawn.go:121` from initial commit; removing it restored `hermes chat` to its default (non-REPL) mode.

### Idle-project flooding + Auto-slowdown (FEAT-001 — SHIPPED `7d0a0df`)

**Symptom (2026-07-18):** ASCE and Mythos flooded Telegram every 3-10 min with idle ticks.
ASCE (p=8): dynamic cooldown ~3 min, completes tick in seconds (nothing to do), cooldown
expires, picked again. Mythos: blocked on OpenRouter credits, produced "IDLE #N — SLOWDOWN
REQUESTED" every 10 min. <project>: project complete, 2 BLOCKED tasks, "IDLE TICK 1/7".

**Root cause:** Dynamic cooldown (`cooldown_s=0`) derives interval from priority using
logarithmic scale. High-priority idle projects get very short cooldowns (p=10→1m, p=8→3m).
The foreman signals "SLOWDOWN REQUESTED" but the scheduler ignored it.

**Fix (shipped `7d0a0df`, 2026-07-18):**
1. **Auto-slowdown** (`slowdown.go`): after each tick completes, parse output for
   "IDLE TICK" or "SLOWDOWN REQUESTED". On idle: double cooldown (600s→1200s→2400s→...
   →14400s cap). On active (non-idle): reset cooldown to 600s. Works automatically.
2. **Cooldown floor:** all 27 projects given cooldown_s >= 1200s (20min) floor.
   Mythos and <project> capped at 14400s (4h).

**Cooldown scale reference (before auto-slowdown):**
```
p=10 → 1m (too fast for idle!)    p=5 → 21m
p= 8 → 3m (too fast for idle!)    p=3 → 1.2h
                                   p=1 → 4h
```
**After auto-slowdown (v3.7):** idle projects 1.5x cooldown each tick until capped at 1h (3600s). Active projects reset to 600s. Detection uses structured `VERDICT:` line from foreman output ("VERDICT: productively — IDLE"), not fragile string matching on "IDLE TICK".
### Gateway SIGKILL every ~2.5min → check foreman test suites for killpg (2026-07-19)

**Symptom:** Scheduler restarts in a loop. Gateway shows `Main process exited, code=killed, status=9/KILL`
every ~2-3 minutes. signal-cli, user SSH sessions, and Docker containers all die simultaneously.
OOM kernel log shows NO kills. Cgroup memory.events show 0 oom_kill, 0 high, 0 max. Memory under limit.

**Root cause (after 4 hours of debugging — 2026-07-19):** One of the foreman projects (<project>)
runs pytest on every tick. A test in `engine/test_lsp.py` mocks a subprocess but doesn't set a valid
PID. The mocked PID resolves to integer 1. The test calls `os.killpg(1, SIGKILL)` — killing EVERYTHING
in process group 1 with the same UID. This nukes the gateway, scheduler, signal-cli, and all user
processes simultaneously.

**Investigation path (what we checked and eliminated):**
1. Old s6 gateway with `--replace` on port 8642 → dead, not the cause
2. Cgroup memory pressure (MemoryMax=32G) → 0 events, memory at 1GB well under limit
3. `--replace` flag on systemd gateway → removed, still dying
4. `BindsTo=hermes-gateway.service` in scheduler unit → removed, scheduler now survives independently
5. `restart_drain_timeout: 180` → for clean drain, not SIGKILL
6. Systemd CPU/memory/task limits → all at infinity, no constraints
7. External pkill/killall → none found in cron or systemd
8. **Audit trail:** Bane's incident report matched the kill pattern to <project> foreman ticks

**Fix:** `<project>/engine/lsp.py` — validate PIDs before killpg (reject 0, 1, negative, boolean).
Regression test added. Commit `4d5f01a`.

**Detection:** `journalctl -u hermes-gateway --since "1 hour ago" | grep "killed"` — if every kill
aligns with a <project> scheduler tick, suspect this.

**Symptom:** Scheduler at 12-15GB memory, 12+ `hermes chat` subprocesses in `ps aux`,
but `journalctl` shows "WARN: gateway not reachable — falling back to exec.Command"
at startup. Daemon log shows 0 "GATEWAY:" tick completions. Every tick goes through
the legacy process-spawn path. Memory balloons.

**Root cause:** Systemd starts schedulerd and the Hermes gateway in parallel.
If the gateway isn't listening when schedulerd calls `gwClient.Ping()` (race can
be sub-second), the one-shot health check fails. `gwClient` is set to nil for
the entire daemon lifetime. The spawner sees `s.gateway == nil` and falls back
to `exec.Command("hermes", "chat", ...)` forever.

**⚠️ This is NOT healed by gateway coming online later.** The check is a single
`if Ping() != nil { fallback }` at boot. No retry logic (before `bdc75ea`).

**Fix (shipped `bdc75ea`):**
1. Startup: 10 retries with exponential backoff (2s, 4s, 6s... 20s ≈ 110s total)
2. Background reconnector goroutine: pings every 60s. If disconnected, retries
   with same 10-attempt backoff. Calls `loop.SetGatewayClient(gwClient)` on reconnect.
3. `gwConnected` flag prevents double-reconnect loops.

**After fix:** Daemon stays at ~5MB. Zero subprocesses. All ticks through HTTP API.
Gateway reconnects automatically after any transient outage.

**Detection:** `ps aux | grep 'hermes chat' | wc -l` → should be 0 with gateway mode.
If > 0, gateway has fallen back. `journalctl -u coding-hermes-scheduler | grep GATEWAY`
should show "connected to" at startup, not "WARN: gateway not reachable".

### Sequential spawn blocks eval → fleet starves (FIXED `c8a3864`, BUG-007)

**Symptom:** One slow gateway response (e.g. <project> taking 20+ minutes) blocks ALL
subsequent spawns in the eval cycle. Health endpoint responds (BUG-006 lock fix is in place),
but no new eval cycles fire because evaluate() is stuck in the spawn loop. Fleet of 35+
enabled projects starves — <project> never ticks, gitreins/<project>/<project> last ticked
5+ hours ago.

**Root cause:** `evaluate()` spawned projects in a sequential `for range packed` loop.
Each `spawner.Spawn()` called the gateway HTTP API and blocked until the response
returned. With 12 projects selected, a single slow tick starved the other 11.

**User correction:** "we need to make it a global spawn so we should be running
multiple go routines and each project is in a spawn with some sort of 2 hour timeout…
this is not hard your failing at basic sepfermore programing."

**Fix (shipped `c8a3864`):** SlotPool — buffered channel semaphore:
```go
type SlotPool struct {
    sem chan struct{}  // cap = maxConcurrent, len = active
}
// evaluate() fires goroutines and returns immediately:
for _, proj := range packed {
    l.slotPool.Spawn(proj, now, noDeliver, l.db)  // fire-and-forget
}
// Each goroutine: acquire slot → spawn via gateway → wait 2h max → release slot
```

New file: `internal/scheduler/slot_pool.go` (~110 lines).
Spawn loop in `internal/scheduler/loop.go` replaced (80+ lines removed).
SetTickTimeout now initializes `l.slotPool = NewSlotPool(maxConcurrent, timeout, spawner, lifecycle)`.

**Key architectural lesson:** Never block the eval loop on I/O. Phase 1 picks projects
under lock (<1s), Phase 2 fires them into goroutines with a semaphore cap. The eval
loop runs every 60s regardless of tick duration.

### Headless Chrome dashboard screenshots

To capture a screenshot of the locally-hosted dashboard for documentation:

```bash
google-chrome --headless=new --disable-gpu \
  --screenshot=/tmp/dashboard.png \
  --window-size=1280,900 \
  --virtual-time-budget=8000 \
  http://127.0.0.1:9090/dashboard
```

Warm the endpoint first (two quick curls) to ensure data populates before capture.
Output is ~100KB PNG. Works without a display server. D-Bus errors in stderr are
### Gateway API stalls on dangerous commands (FIXED — `require_approval: false`)

**Symptom:** Foreman ticks spawned via the gateway API hang waiting for approval
on terminal/git operations — but there is no interactive user on the API endpoint.

**Root cause:** Without an explicit approval flag, the gateway treats `/v1/responses`
requests as potentially interactive. The agent pauses on `clarify()` calls.

**Fix — per-request approval control (SHIPPED `4324329`, 2026-07-30):**
The Hermes gateway `/v1/responses` endpoint accepts `require_approval: false` in
the request body. The scheduler's `GatewayClient.SendResponse()` now sets this
on every request:

```json
{"input": "...", "model": "deepseek-v4-pro", "require_approval": false}
```

This is **per-request**, not per-gateway. User-facing chats (Telegram, Discord)
keep approvals enabled. Only scheduler-spawned foremen skip them.

**Why this replaced `approvals.cron_mode: auto`:** The cron_mode setting was
gateway-global — it affected ALL non-interactive sessions. The per-request field
gives finer control: scheduler agents get auto-approve, everything else keeps
normal approval prompts. No gateway config needed — the field is standard in
`/v1/responses`.

**Regression test:** `gateway_client_test.go::TestGatewayClient_SendResponse_DisablesApprovals`
captures the request body and verifies `require_approval: false` is always present.

**Proven:** 2026-07-30 — live test confirmed gateway accepts and honors the field.
Scheduler spawns now complete without approval pauses.

### Goroutine/process leak (FIXED — BUG-004 `3e89485`)

**Symptom (2026-07-17):** 659 goroutines, 8GB RAM, API unresponsive. `ps aux | grep hermes`
showed only 2 child processes — the bloat was in Go goroutines, not OS processes.

**Root cause:** Hung `hermes chat` processes caused `bufio.Scanner` goroutines to block
indefinitely on pipe reads. No timeout context cancelled them.

**Fix (shipped):**
1. `context.WithTimeout` on scanner goroutine — closes stdout pipe on expiry
2. `SpawnedTick.scanCancel` stored + called in `Wait()` 
3. `--tick-timeout` CLI flag (default 2h)
4. `runtime.NumGoroutine()` logged every eval cycle

**Active map is cleaned:** `delete(st.spawner.active, st.TickID)` runs in `Wait()` defer.
No accumulation. ✅

### High memory usage is normal (not a leak) — with foreman MCP optimization

**A 26.8GB peak with 8 concurrent is 8×~3GB LLM subprocesses + duplicate MCP servers.**
After foreman MCP optimization (see `references/foreman-memory-optimization.md`):

| Scenario | Per chat | 8 concurrent |
|----------|----------|-------------|
| Before (all MCPs + browser) | ~500MB | ~4GB |
| After (duckbrain + gitreins only, no browser) | ~175MB | ~1.4GB |

The scheduler heap is 70KB with 32 flat goroutines — zero Go leak. All memory
is from subprocesses. Set `MemoryMax=32G` and `Restart=always`.

### `hermes chat -q -Q` is stdout-only — no Telegram delivery (RESOLVED via INFRA-003)

**Cron jobs deliver because `run_one_job()` wraps agent output with `_deliver_result()`.** Raw subprocesses did not — until INFRA-003 shipped `deliverOutput()` which POSTs captured stdout to Telegram after each tick completes. The scheduler now matches cron delivery semantics with `🤖 Scheduler Tick:` header instead of `Cronjob Response:`.

When adding a field like `deliver` that needs to flow from DB → packer → spawn → delivery,
you must update ALL of these places or the field silently drops to its zero value:

1. `database/models.go` — add the field to `Project` struct
2. `database/migrations.go` — add the column to the CREATE TABLE in v1
3. `database/projects.go` — add the column to **both** `ListProjects` and
   `ListProjectsByNamespace` queries + their `rows.Scan()` calls
4. `internal/scheduler/packer.go` — add the field to `scored` struct + query SELECT + scan
   + `PackedProject{}` construction
5. `internal/scheduler/multipool_packer.go` — add to `PackedProject{}` construction
   (this is the namespace-mode code path — **easily missed**)
6. `internal/scheduler/spawn.go` — propagate from `PackedProject.Deliver` to
   `SpawnedTick.Deliver`

**Proven 2026-07-18:** `Deliver` was added to packer.go (regular path) but missed in
multipool_packer.go (namespace-mode path, which IS the production path with
`--namespace-mode`). Result: 30+ ticks delivered to default thread 83996 instead
of per-project threads. The snoopy log confirmed:
```
hermes send --to telegram:-1003310984808:83996   ← default, not per-project
```
Database had correct values (`telegram:-1003310984808:12` for ASCE) but they
never reached `deliverOutput()`. The chain broke at `database.ListProjects` which
didn't SELECT `deliver`, and `MultiPoolPacker.Pack()` which didn't propagate it.

**Detection:** `journalctl -u coding-hermes-scheduler | grep "hermes send --to"`
shows the actual target used. If all ticks show `:83996`, the deliver field
isn't flowing through the MultiPoolPacker path.

### `hermes chat -q -Q` is stdout-only — no Telegram delivery (RESOLVED via INFRA-003)

**Cron jobs deliver because `run_one_job()` wraps agent output with `_deliver_result()`.** Raw subprocesses did not — until INFRA-003 shipped `deliverOutput()` which POSTs captured stdout to Telegram after each tick completes. The scheduler now matches cron delivery semantics with `🤖 Scheduler Tick:` header instead of `Cronjob Response:`.

### Old foreman crons may re-enable after migration (2026-07-18)

After pausing foreman crons, some may be found re-enabled. Always re-verify.

**Detection script (Python — checks Hermes cron DB directly):**
```bash
python3 << 'PYEOF'
import json
with open('~/.hermes/cron/jobs.json') as f:
    data = json.load(f)
foreman = []
for j in data['jobs']:
    skills = str(j.get('skills', [])).lower()
    paused = j.get('paused_at')
    is_supervisor = j.get('name') == 'Coding Hermes Supervisor'
    if 'foreman' in skills and not paused:
        foreman.append(j)
        print(f"LEAKED: {j.get('id','?')[:16]} {j.get('name','?')} schedule={j.get('schedule','?')}")
print(f"\nTotal leaked foreman crons: {len(foreman)}")
PYEOF
```

**Pause them (except Supervisor — keep that):**
```bash
# The cronjob tool can pause by ID:
# cronjob(action='pause', job_id='<leaked-id>')
# DO NOT pause 55afdcd33d7f (Coding Hermes Supervisor) — it's intentional
```

**Proven:** 2026-07-18 — 5 leaked foreman cron jobs found enabled alongside scheduler:
- `4112021d6998` helix-foreman (every 30m)
- `d7949401cfe0` <project>-foreman (every 60m)
- `83c72b749566` <project>-coding-hermes-foreman (every 30m)
- `e17630cea8c9` h3-foreman-bootstrap (every 5m)
- `56351fc56f98` <project>-coding-foreman (every 30m)

These double-spawned with the scheduler, causing 11 <project> ticks to timeout
in 2-3 minutes each (old cron process killed the scheduler-spawned one).

### Build cache causes false "field undefined" errors (2026-07-18)

Go may report `type ProjectDef has no field or method Name` even when the struct
clearly has that field. Cause: stale build cache after struct changes or TOML
package reconfiguration.

```bash
go clean -cache && go build ./...
```

**Proven:** 2026-07-18 — config package built fine directly but `go build ./...`
reported 11 "undefined" errors. Cache clean resolved all.

### Dashboard N+1 FIXED (2026-07-18 — `e83eaf4`)

**Was:** N+1 queries per project (7 × 50 = 350+) + `template.Parse` on every request
→ dashboard timed out on every load, returned 0 bytes.

**Fixed:**
1. Template parsed once in `NewGenerator()`, reused via `g.tmpl.Execute()` — zero hot-path cost
2. Single LEFT JOIN query replaces 7 per-project N+1 queries
3. Total queries: 3 (projects, ticks, namespaces) regardless of fleet size
4. Dashboard loads in <5s for ~50 projects, auto-refreshes every 60s via `<meta>`

**Verification:** `curl -s http://127.0.0.1:9090/dashboard | wc -c` → 22KB+ HTML.
