# coding-hermes-north-star

**Status:** Active  
**Category:** architecture  
**Layer:** Foundation (Phase 0)

---

## Purpose

This is the north-star architecture document for coding-hermes. Every coding-hermes skill references this to understand the full system. It explains WHAT coding-hermes is, WHY it exists, and HOW the pieces fit together. All other skills are implementations of concepts defined here.

---

## What Is Coding Hermes?

Coding Hermes is a **fleet scheduler** for LLM-powered coding agents. It replaces dozens of static cron jobs with a single Go binary that dynamically decides which projects to work on, when to work on them, and how many can run at once.

### The Problem It Solves

Before coding-hermes, you had 33 cron jobs like:

```
*/120 * * * * hermes chat -q "foreman tick for project X"
0 */2 * * *   hermes chat -q "foreman tick for project Y"
...
```

Problems:
- **No coordination**: All 33 fire independently, unaware of each other.
- **No backpressure**: If 5 are already running, the 6th still fires.
- **No priority**: Every project gets equal attention, always.
- **No observability**: Which ones succeeded? Which committed? You grep logs.
- **No runtime control**: Changing a project's frequency requires editing cron syntax.

### The Solution

A single Go binary (`schedulerd`) that:

1. **Knows all projects** — their weight (resource cost), priority (importance), cooldown, model, provider, workdir.
2. **Evaluates every 60 seconds** — computes urgency for each project.
3. **Packs greedily by urgency** — fills a weight budget with the most urgent projects.
4. **Spaws foremen** — each gets a `hermes chat -q` process, waits for completion.
5. **Tracks outcomes** — every tick is recorded (queued → running → completed/failed/timeout).
6. **Exposes full control** — REST API + MCP + dashboard + DuckBrain sync.

---

## Architecture — The 4 Layers

```
┌─────────────────────────────────────────────────────────┐
│                     HERMES PLUGIN                         │
│  /fleet status, /fleet weight, /fleet priority, etc.    │
│  Python hook → MCP client → HTTP calls to scheduler      │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP POST /mcp
┌──────────────────────▼──────────────────────────────────┐
│                   SCHEDULER (Go binary)                   │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌────────────┐ │
│  │ REST API │  │ MCP Srvr │  │  Dash  │  │ DuckBrain  │ │
│  │ :9090    │  │ /mcp     │  │ /      │  │ Sync       │ │
│  └────┬─────┘  └────┬─────┘  └───┬────┘  └─────┬──────┘ │
│       │              │            │             │        │
│  ┌────▼──────────────▼────────────▼─────────────▼──────┐ │
│  │                   EVAL LOOP (60s)                    │ │
│  │  Urgency → Pack → Spawn → Track → Repeat            │ │
│  └──────────────────────┬──────────────────────────────┘ │
│                         │                                │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │              SQLite (scheduler.db)                   │ │
│  │  projects, ticks, events, migrations               │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## The 5 Skills That Make It Work

| Skill | Role | When Loaded |
|-------|------|-------------|
| `coding-hermes-config` | User setup — keys, models, paths | First — before anything |
| `coding-hermes-north-star` | Architecture — this document | By foreman + supervisor |
| `coding-hermes-foreman` | Inspect → plan → spawn workers | Every tick, per project |
| `coding-hermes-supervisor` | Multi-project oversight | Fleet-level monitoring |
| `coding-hermes-broker` | Weight-budget scheduling | Drives the scheduler |

---

## The Scheduler Algorithm

### Urgency Formula

```
interval = min_interval × (max_interval / min_interval) ^ ((priority - 1) / (num_levels - 1))
urgency  = priority × (1 + time_since_last_run / interval) ^ decay_rate
```

Where:
- `min_interval` = fastest tick (default 20m)
- `max_interval` = slowest tick (default 24h)
- `num_levels` = number of priority levels (default 10)
- `decay_rate` = per-project tuning (default 1.0)

### Greedy Packing

```
budget_remaining = weight_budget (default 100)
running = count_running_ticks()
selected = []

for project in sort_by_urgency_desc(all_enabled_projects):
    if running >= max_concurrent: break
    if project.weight > budget_remaining: skip
    if project.on_cooldown(): skip
    selected.append(project)
    budget_remaining -= project.weight
    running += 1

# Spawn foremen for selected projects
```

---

## Key Concepts

### Weight (1-100)
How much of the concurrency budget this project consumes per tick. A project with weight=50 can have at most 2 concurrent ticks with a budget of 100.

### Priority (1-10)
How urgently this project needs attention. Priority 10 runs every 20 minutes. Priority 1 runs every 24 hours. Uses a geometric curve — not linear — so high priorities spread out and low priorities cluster.

### Cooldown
Minimum seconds between successive ticks for the same project. Default 900s (15 min). Prevents a project from hogging the scheduler.

### Decay Rate
How fast urgency grows when a project hasn't run. Higher decay = faster starvation prevention. Default 1.0.

### Tick Lifecycle
```
QUEUED → RUNNING → COMPLETED / FAILED / TIMEOUT
```
Every tick gets a unique ID: `<project>-<YYYY-MM-DD-HH-MM-SS>`. Session IDs from spawned `hermes chat` processes are captured and stored.

---

## Deployment

```bash
# Build
git clone https://github.com/coding-hermes/scheduler
cd scheduler
make build

# Migrate existing cron jobs
make migrate-dry  # preview
make migrate      # import to SQLite

# Deploy
make deploy-install  # systemd unit
# Create ONE trigger cron to hit /api/v1/evaluate

# Verify
curl http://localhost:9090/          # dashboard
curl http://localhost:9090/api/v1/health
/fleet status                        # in Hermes
```

---

## Pitfalls

- **Don't run the old crons AND the scheduler.** Disable old cron jobs after migration.
- **The trigger cron is ONE cron.** Not 33. It hits `/api/v1/evaluate` every 60s.
- **Weight budget matters.** If all projects have weight=100, only one runs at a time.
- **DuckBrain sync needs MCP HTTP.** Stdio MCP from a Go binary requires a bridge.
- **Session capture is async.** The scheduler spawns foremen but doesn't wait to parse output.
