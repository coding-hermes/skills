# Coding Hermes Scheduler — Web UI Reference

The coding-hermes fleet is managed by a centralized Go daemon (`schedulerd`) that exposes an HTMX-based web UI, not a JSON API. Data is extracted by scraping HTML pages.

## Endpoints

### `GET /` — Fleet Overview
The main dashboard. Contains three tables:

**Table 0 — Project List** (all enabled projects):
```
Project | W | P | Last Tick | Outcome | Running
<project> | 25 | 10 | 06:14 | committed |
bunker  | 15 | 10 | 06:26 |          | running
...
```
- W = weight (budget allocation)
- P = priority  
- Last Tick = time in CST (HH:MM) or "—" (em dash) if never
- Outcome = committed / failed / timeout / empty (for running/incomplete)
- Running = "running" if currently executing

**Table 1 — Recent Tick Activity** (last ~10 ticks):
```
Project | Status | Outcome | Spawned | Commits | Files
bunker | running | | 06:26 | 0 | 0
consensus | completed | committed | 06:22 | 0 | 0
<project>-e2e | failed | failed | 06:25 | 0 | 0
```

**Table 2 — Namespace Budgets**:
```
Namespace | Weight | Reserved | Hard Cap | Allocated | Used | Utilization | Borrowed | Lent | Projects
coding-hermes | 100 | 70 | 100 | 96 | 8 | 8% | | | 39
monitoring | 30 | 0 | 30 | 0 | 0 | 0% | | | 0
data-cleanup | 10 | 0 | 15 | 0 | 0 | 0% | | | 0
duckbrain-infra | 10 | 0 | 15 | 0 | 0 | 0% | | | 0
backup | 5 | 0 | 10 | 0 | 0 | 0% | | | 0
```

**Table 3 — Tick Group History** (budget allocation snapshots per namespace over time)

### `GET /health` — Health Dashboard
Summary cards: Daemon status, Database status, Gateway status, Uptime, Active Ticks, Total Ticks, Goroutines, Memory.

### `GET /ticks` — Full Tick History
Paginated tick history table (same format as Table 1 on / but full history).

### `GET /queue` — Queue View
Shows projects currently queued: columns #, Project, Weight, Priority, Cooldown, Urgency.

## Data Extraction Pattern

```python
import re, subprocess

result = subprocess.run(['curl', '-s', 'http://localhost:9090/'], capture_output=True, text=True)
html = result.stdout

# Find all tables
tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)

# Table 0: Projects
table0 = tables[0]
rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table0, re.DOTALL)[1:]  # skip header
for row in rows:
    cols = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
    clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cols]
    # clean = [name, weight, priority, last_tick, outcome, running]
```

## Time Parsing

Last Tick times are in CST (UTC-5). To compute stale hours:
```python
from datetime import datetime, timezone, timedelta

now_cst = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-5)))
now_total_m = now_cst.hour * 60 + now_cst.minute
tick_total_m = tick_h * 60 + tick_m

if tick_total_m > now_total_m:
    stale_min = (24*60 - tick_total_m) + now_total_m  # yesterday
else:
    stale_min = now_total_m - tick_total_m

stale_h = round(stale_min / 60, 1)
```

## Daemon Process

```bash
# Check if running
ps aux | grep schedulerd

# Typical invocation:
# ~/coding-herms-scheduler/bin/schedulerd \
#   -db ~/.hermes/coding-hermes/scheduler.db \
#   -listen 127.0.0.1:9090 \
#   -gateway-url http://127.0.0.1:8642 \
#   -max-interval 12h -min-interval 30s \
#   -max-concurrent 10 -tick-timeout 600s
```

## Key Facts

- The scheduler manages ~66 projects across 5 namespaces
- Projects are NOT defined in per-repo `.coding-hermes/tasks.md` files
- The scheduler database is at `~/.hermes/coding-hermes/scheduler.db`
- The gateway (separate process at port 8642) handles Hermes agent spawns
- Tick timeout is 600s (10 min)
- Max concurrent ticks: 10
- Cron jobs in `~/.hermes/cron/jobs.json` are the OLD system (all paused) — ignore them, use the scheduler
