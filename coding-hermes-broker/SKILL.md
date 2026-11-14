---
name: coding-hermes-broker
description: >-
  Scheduling brain — explains the weight-budget knapsack model deciding which
  projects run and when; reference for tuning fleet scheduling.
version: 1.0.1
author: Bane + Hermes
---

# coding-hermes-broker

**Status:** Active  
**Category:** scheduling  
**Layer:** Broker (Phase 2)

---

## Purpose

The broker is the scheduling brain. It decides WHICH projects run and WHEN. It implements the weight-budget knapsack algorithm. This skill explains the scheduling model so any agent can understand and tune it.

---

## Concepts

### The Two Axes

Every project has TWO independent dimensions:

| Axis | What It Means | Range | Default |
|------|--------------|-------|---------|
| **Weight** | How much concurrency budget this project consumes per tick | 1-100 | 10 |
| **Priority** | How frequently this project should be checked | 1-10 | 5 |

### Weight Budget

The scheduler has a FIXED weight budget (default: 100). It packs projects greedily until the budget is exhausted. A project with weight=50 can have at most 2 concurrent ticks with budget=100.

### Priority → Interval

Priority maps to tick interval using a GEOMETRIC curve (not linear):

```
position = (max_priority - priority) / (max_priority - 1)
interval = min_interval × (max_interval / min_interval) ^ position
```

Example with min=20m, max=24h, 10 levels:

| Priority | Interval |
|----------|----------|
| 10 | 20m |
| 9 | 34m |
| 8 | 59m |
| 7 | 1h 41m |
| 6 | 2h 54m |
| 5 | 5h 0m |
| 4 | 8h 37m |
| 3 | 14h 50m |
| 2 | 24h 0m |
| 1 | 24h 0m |

### Urgency Formula

```
urgency = priority × (1 + time_since_last_run / interval) ^ decay_rate
```

- When `time_since_last_run = 0` → urgency = priority
- When `time_since_last_run = interval` → urgency = priority × 2^decay_rate
- When `time_since_last_run = 2×interval` → urgency = priority × 3^decay_rate

Higher urgency projects get picked first. Starvation is mathematically impossible — urgency grows without bound.

### Cooldown

After a project runs, it enters cooldown (default: 900s = 15 min). During cooldown, it's skipped even if urgency is high. This prevents a single project from monopolizing the scheduler.

### Decay Rate

Per-project tuning knob. Higher decay → urgency grows faster → starves less aggressively. Default: 1.0.

---

## Scheduling Algorithm

```
function evaluate(now):
    // 1. Cleanup stale running ticks
    mark_stale_as_timeout(max_age=2h)
    
    // 2. Compute urgency for all enabled projects
    scored = []
    for project in enabled_projects:
        interval = compute_interval(project.priority)
        urgency = project.priority * (1 + time_since_last_run(project) / interval) ^ project.decay_rate
        scored.append({project, urgency})
    
    // 3. Sort by urgency descending
    sort(scored, by=urgency, desc)
    
    // 4. Greedy pack within weight budget
    budget_remaining = weight_budget
    running = count_running_ticks()
    selected = []
    
    for s in scored:
        if running >= max_concurrent: break
        if s.project.weight > budget_remaining: continue
        if is_on_cooldown(s.project, now): continue
        selected.append(s.project)
        budget_remaining -= s.project.weight
        running += 1
    
    // 5. Spawn foremen for selected projects
    for project in selected:
        tick_id = project.name + "-" + now.format("YYYY-MM-DD-HH-MM-SS")
        enqueue(tick_id, "queued")
        start_running(tick_id)
        spawn(project, tick_id)
```

---

## Runtime Commands

### `/fleet weight <project> <N>`
Change a project's weight. Higher = more expensive to run concurrently.
```
PUT /api/v1/projects/<project>  {"weight": <N>}
```

### `/fleet priority <project> <N>`
Change a project's priority. Higher = more frequent ticks.
```
PUT /api/v1/projects/<project>  {"priority": <N>}
```

### `/fleet cooldown <project> <duration>`
Set minimum time between ticks (e.g., `30m`, `2h`).
```
MCP: fleet_set_cooldown  {"name": "<project>", "cooldown": <seconds>}
```

### `/fleet decay <project> <rate>`
Tune starvation aggressiveness. Higher = faster urgency growth.
```
MCP: fleet_set_decay  {"name": "<project>", "decay": <rate>}
```

### `/fleet budget <N>`
Change the total weight budget.
```
Requires scheduler restart (--budget flag)
```

### `/fleet range <min> <max>`
Change the geometric interval range (all projects affected).
```
Requires scheduler restart (--min-interval, --max-interval flags)
```

### `/fleet pause <project>`
Temporarily stop ticks for a project.
```
POST /api/v1/projects/<project>/pause
```

### `/fleet resume <project>`
Resume ticks for a paused project.
```
POST /api/v1/projects/<project>/resume
```

### `/fleet status`
Show fleet-wide status.
```
GET /api/v1/status
```

### `/fleet projects`
List all projects with their config.
```
GET /api/v1/projects
```

### `/fleet ticks [project]`
Show recent ticks, optionally filtered by project.
```
GET /api/v1/ticks?project=<name>&limit=20
```

### `/fleet evaluate`
Force an immediate evaluation cycle.
```
POST /api/v1/evaluate
```

---

## Tuning Guide

### "My important project never runs"
→ Increase its priority (e.g., 5 → 8). This shrinks its interval from 5h to 1h.

### "Too many things run at once"
→ Increase weights on resource-heavy projects, or decrease the budget.

### "One project dominates the scheduler"
→ Increase its cooldown. Or decrease its weight so others can fit.

### "A project hasn't run in days"
→ Check if it's paused or disabled. Check cooldown isn't too high. Increase decay rate.

### "API costs are too high"
→ Decrease priorities on low-value projects. Increase their cooldowns. Decrease budget.

---

## Pitfalls

1. **All projects with weight=100**: only one runs. Distribute weights.
2. **All projects with priority=5**: everything runs at the same cadence. Differentiate.
3. **Cooldown > interval**: a priority-10 project with 1h cooldown still runs every 20m. Cooldown only prevents BACK-TO-BACK runs.
4. **Decay rate too low**: starving projects grow urgency very slowly. Increase decay_rate.
5. **Budget too small**: important projects get skipped. Increase budget or decrease weights.
