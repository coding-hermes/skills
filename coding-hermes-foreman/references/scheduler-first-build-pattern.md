# Scheduler-First Build Pattern

**Proven:** coding-hermes/scheduler — 2026-07-12 — 3,806 Go lines, 18MB binary, 14 phases, ~4h total

## Overview

When building a Go daemon from scratch (scheduler, API server, MCP server, dashboard, sync engine), follow this exact phase sequence. Each phase depends on the previous. Skipping phases causes rework.

## Phase Sequence

```
INIT → DB → SPEC → CORE → API → MCP → DASH → SYNC → CMD → PLUGIN → MIGR → DEPLOY → TEST → GAP-ANALYSIS → SIMULATION
```

### INIT — Project scaffold
- `go mod init github.com/<org>/<repo>`
- Package layout: `cmd/<daemon>/main.go`, `internal/<pkg>/doc.go`
- Makefile: build, test, run, lint, fmt, clean
- systemd unit stub
- `.gitignore`, `.gitleaks.toml`, `.gitreins/config.yaml`
- Hilo init: `.vfs/`

### DB — Data layer
- `internal/database/schema.go` — DDL with indexes
- `internal/database/migrations.go` — versioned migrations
- `internal/database/models.go` — Go structs (match column order for scan ergonomics)
- `internal/database/<table>.go` — CRUD per table
- Tests: every function covered, SQLite in-memory

**Key pitfall:** Use `project_name` not `project` as column name. Go JSON decoder uses struct field names (PascalCase) unless json tags are added. Add `json` tags early or document the convention.

### SPEC — Implementation specs (BLOCKING)
**Do NOT proceed to CORE without this phase.** Write axiom-level specs:
- Exact Go interfaces with method signatures
- Exact DDL with indexes and constraints
- Error paths for every function
- Wiring/dependency injection code
- Config with env var names and types
- 10-section structure per spec file

**Minimum spec set:**
1. System architecture (S01)
2. Data model (S02)
3. Core algorithm 1 — urgency (S03)
4. Core algorithm 2 — packing (S04)
5. Spawn + lifecycle (S05)
6. API contract (S06)
7. MCP contract (S07)

### CORE — Scheduler engine
- Urgency calculator (geometric interval + urgency formula)
- Weight-budget packer (greedy with cooldown enforcement)
- Spawn engine (exec hermes chat, capture session_id)
- Lifecycle tracker (queued → running → completed/failed/timeout)
- Main evaluation loop (60s ticker, cleanup → compute → pack → spawn)

### API — REST server
- 15 endpoints: health, status, projects CRUD, ticks, events, evaluate, pause, resume
- NULL handling: COALESCE all nullable columns in SELECT (outcome, completed_at, session_id, error, exit_code, tokens, cost)
- Route prefix stripping: `strings.TrimPrefix(r.URL.Path, "/api/v1/projects/")` before splitting

### MCP — JSON-RPC server
- 14 tools: fleet_status through fleet_resume_scheduler
- Protocol: JSON-RPC 2.0, initialize/tools/list/tools/call
- Deduplicate shared helpers (boolPtr, etc.) into common package

### DASH — HTML dashboard
- Single-file HTML, dark theme, responsive
- Fleet overview + per-project table
- Template functions: percent, shortTime

### SYNC — DuckBrain replica
- 5-minute sync interval
- Requires MCP HTTP client (GAP-004 — os/exec hermes CLI doesn't work)

### CMD — Wire everything
- Compose all handlers into one mux: `/` dashboard, `/api/` API, `/mcp` MCP
- Start sync goroutine
- Graceful shutdown on SIGTERM/SIGINT
- Print fleet status banner on startup

### PLUGIN — Hermes integration
- `plugin/plugin.yaml` — name, version, mcp_ref
- `plugin/__init__.py` — register(ctx) entry point
- `plugin/hooks.py` — pre_llm_call route_fleet_command, pre_verify inject_fleet_context
- Symlink: `ln -s <repo>/plugin ~/.hermes/plugins/coding-hermes`

### MIGR — Cron → scheduler migration
- `cmd/migrate/main.go` — read jobs.json, extract workdir from prompt regex, create projects
- Dry-run mode (`--dry-run`)
- Deduplication (skip if project already exists)
- Workdir parsing: `Workdir:\s*(\S+)` with `strings.TrimRight(wd, ".,;:")`

### DEPLOY — Production
- systemd unit with correct ExecStart (including -db flag)
- Trigger cron: one `no_agent` cron running `curl -X POST /api/v1/evaluate` every 60s
- `make deploy-install` → systemd enable
- `make deploy` → build + restart

### TEST — Verification
- Integration test: spin up daemon, hit all 4 layers, verify tick lifecycle
- Use `//go:build integration` tag
- Use `TestMain` for binary build + cleanup
- Use unique temp DB per run: `os.CreateTemp("", "scheduler-test-*.db")`

### GAP-ANALYSIS — Hilo post-build
After all phases complete:
```bash
hilo graph warm && hilo graph stats
```
Find: orphan files, duplicate symbols, dead imports, untested packages, shell-out dependencies.
File as `## [ ] GAP — <description>` tasks.

### SIMULATION — Dry-run testing (NEW, proven 2026-07-12)
Run simulation testing BEFORE cutting over to production. This phase found 3 critical bugs that would
have been production incidents (see `references/bugs-found-2026-07-12.md`):

```bash
# Create test fixture, run multi-tick simulation
./bin/schedulerd --sim-setup --sim-ticks 5 -db /tmp/sim-test.db

# Verify: budget packing, cooldown cycling, disabled exclusion, success rates
# Expected output: 5+ projects per tick, 100% budget use, ghost-project never picked
```

**Simulation verifies:**
- Weight budget packing (does budget=100 limit actually work?)
- Concurrency cap (does max_concurrent=8 block spawns?)
- Priority ordering (does high-priority run before low-priority?)
- Cooldown enforcement (do projects cycle after completing?)
- Disabled exclusion (are disabled projects skipped?)
- Success rate distribution (85% default, tunable with --sim-success)
- Multi-tick behavior (do cooldowns expire and let projects run again?)

**Key tests to add to the simulation:**
- All-30-weight projects: should pack exactly 3 (3×30=90, 4th doesn't fit)
- Concurrency-saturated: spawn 8 lightweight projects, verify 9th blocked
- Starvation: run 10+ ticks, verify low-priority projects eventually picked (decay works)
- Disabled crew: all projects disabled → 0 packed (graceful degredation)

## Key Debugging Patterns

### SQL column name mismatch
```
Error: table ticks has no column named project
Fix: use project_name (DDL column), not project (scheduler code variable)
```

### NULL scan errors
```
Error: converting NULL to string is unsupported
Fix: COALESCE(col, '') for text, COALESCE(col, 0) for int
```

### Missing state transition
```
Bug: ticks stay in 'queued' forever, runningCount() returns 0
Fix: add StartRunning() transition between Enqueue and Spawn
```

### Route prefix stripping
```
Bug: GET /api/v1/projects/myproject → "project not found"
Cause: r.URL.Path = "/api/v1/projects/myproject", parts[0] = "api"
Fix: path = strings.TrimPrefix(r.URL.Path, "/api/v1/projects/")
```

### DB path mismatch
```
Bug: migrate says 26 imported, curl shows 0 projects
Cause: migrate writes to ~/.hermes/coding-hermes/scheduler.db, daemon reads ~/.hermes/scheduler.db
Fix: align both -db flags to same path
```

### DuckBrain sync CLI failure
```
Error: hermes mcp: invalid choice 'duckbrain'
Cause: hermes mcp CLI doesn't support subcommand duckbrain
Fix: disable sync until MCP HTTP client is available (GAP-004)
```

## Verification Checklist

After deployment, verify ALL 4 layers:

```bash
# Layer 1: Health
curl -s http://localhost:9090/api/v1/health
# → {"status":"ok","db":"connected"}

# Layer 2: API
curl -s http://localhost:9090/api/v1/projects | python3 -c "import json,sys; print(len(json.load(sys.stdin)['projects']), 'projects')"
# → 26 projects

# Layer 3: Dashboard
curl -s http://localhost:9090/ | grep '<title>'
# → <title>Coding Hermes Fleet</title>

# Layer 4: MCP
curl -s -X POST http://localhost:9090/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
# → {"jsonrpc":"2.0","result":{"protocolVersion":"2024-11-05","serverInfo":{"name":"coding-hermes-scheduler"}}}
```
