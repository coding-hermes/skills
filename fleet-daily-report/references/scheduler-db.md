# Scheduler SQLite Database — Direct Query Reference

The scheduler stores full tick history in SQLite at `/home/kara/.hermes/coding-hermes/scheduler.db`. Direct queries give far more detail than the web UI: per-tick cost, token counts, individual duration, and the ability to detect case-sensitivity duplicates.

## Tables

### `projects` — Project Configuration
```
name TEXT PRIMARY KEY       — project name (case-sensitive!)
repo_url TEXT NOT NULL      — local:/path or https://...
workdir TEXT NOT NULL
weight INTEGER NOT NULL DEFAULT 10
priority INTEGER NOT NULL DEFAULT 5
cooldown_s INTEGER NOT NULL DEFAULT 900
decay_rate REAL NOT NULL DEFAULT 1.0
model TEXT NOT NULL         — foreman model
provider TEXT NOT NULL      — foreman provider
enabled INTEGER NOT NULL DEFAULT 1
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
last_tick_started TEXT
last_tick_completed TEXT
command TEXT DEFAULT ''
namespace_id TEXT
deliver TEXT DEFAULT ''     — telegram delivery target
worker_model TEXT DEFAULT ''
worker_provider TEXT DEFAULT ''
```

**PITFALL:** Column is `name`, NOT `project_name`.

### `ticks` — Tick History
```
id TEXT PRIMARY KEY         — e.g. HEADING-2026-07-24-06-14-29
project_name TEXT NOT NULL  — references projects.name
session_id TEXT
status TEXT NOT NULL DEFAULT 'queued'
outcome TEXT                — committed, failed, timeout, empty
spawned_at TEXT
completed_at TEXT
exit_code INTEGER
commits INTEGER DEFAULT 0
files_changed INTEGER DEFAULT 0
tokens_in INTEGER DEFAULT 0
tokens_out INTEGER DEFAULT 0
cost_usd REAL DEFAULT 0.0
urgency REAL DEFAULT 0.0
weight_used INTEGER DEFAULT 0
error TEXT
created_at TEXT NOT NULL
pid INTEGER DEFAULT 0
```

### `namespaces` — Namespace definitions
```
id TEXT PRIMARY KEY
name TEXT NOT NULL
...
```

### `namespace_ticks` — Tick namespace assignments
```
tick_id TEXT
namespace_id TEXT
```

## Key Queries

### Project config for a specific project
```sql
SELECT * FROM projects WHERE name='HEADING';
```
**PITFALL:** `name`, NOT `project_name`. And names are case-sensitive — `HEADING` ≠ `heading`.

### Recent ticks for a project
```sql
SELECT id, status, outcome, spawned_at, completed_at, commits, files_changed, 
       tokens_in, tokens_out, cost_usd, error 
FROM ticks 
WHERE project_name='HEADING' 
ORDER BY spawned_at DESC LIMIT 10;
```
**PITFALL:** `project_name` in ticks, but `name` in projects. Inconsistent schema.

### Zombie tick detection
```sql
-- Zero-commit ticks (likely zombies)
SELECT COUNT(*) FROM ticks 
WHERE project_name='HEADING' AND commits=0 AND files_changed=0;

-- Percentage that are zombies
SELECT 
  ROUND(100.0 * SUM(CASE WHEN commits=0 AND files_changed=0 THEN 1 ELSE 0 END) / COUNT(*), 1) 
FROM ticks WHERE project_name='HEADING';
```

### Cost summary
```sql
SELECT COUNT(*), 
       ROUND(SUM(CAST(cost_usd AS REAL)), 2) as total_cost,
       SUM(CAST(tokens_in AS INTEGER)) as total_tokens_in,
       SUM(CAST(tokens_out AS INTEGER)) as total_tokens_out
FROM ticks WHERE project_name='HEADING';
```
**PITFALL:** `cost_usd` is stored as TEXT or REAL depending on SQLite version. Always CAST.

### Case-sensitivity duplicate detection
```sql
-- Find projects that share the same workdir with different case
SELECT LOWER(name), COUNT(*) 
FROM projects 
GROUP BY LOWER(name) 
HAVING COUNT(*) > 1;
```

### Full Python access pattern
```python
import sqlite3, json

db = sqlite3.connect('/home/kara/.hermes/coding-hermes/scheduler.db')
db.row_factory = sqlite3.Row

# Project config
row = db.execute("SELECT * FROM projects WHERE name='HEADING'").fetchone()
config = dict(row)

# Tick history
for r in db.execute(
    "SELECT id, status, outcome, spawned_at, completed_at, commits, "
    "files_changed, tokens_in, tokens_out, cost_usd, error "
    "FROM ticks WHERE project_name=? ORDER BY spawned_at DESC LIMIT 10",
    ('HEADING',)
).fetchall():
    print(dict(r))
```

## When to Use DB vs Web UI

| Data Need | Best Source |
|-----------|------------|
| Per-tick cost, tokens, duration | **SQLite DB** (web UI doesn't show this) |
| Zombie detection (zero-commit %) | **SQLite DB** |
| Case-sensitivity duplicates | **SQLite DB** (web UI shows both but only one fires) |
| Current project config (weight, priority, model) | Either |
| Real-time running status | **Web UI** (`/` — shows "running" for active ticks) |
| Namespace budget allocations | **Web UI** (`/` — Table 2) |
| Queue urgency view | **Web UI** (`/queue`) |
| Escalation events, starvation detection | **SQLite DB** (`events` table) |

## `events` Table — Escalation & Diagnostics

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    severity TEXT,          -- LOW, MEDIUM, HIGH, CRITICAL
    component TEXT DEFAULT '',  -- e.g. 'escalation', 'gateway', 'scheduler'
    message TEXT,
    details TEXT DEFAULT '{}',  -- JSON blob with extra context
    created_at TEXT
);
```

**Key diagnostic:** The `details` JSON contains the scheduler's live view of `cooldown` and `last_tick` — compare these against `projects.cooldown_s` to detect the **cooldown reversion pattern** (see below).

### Recent escalation events for a project
```sql
SELECT severity, message, details, created_at
FROM events WHERE message LIKE '%project_name%'
ORDER BY created_at DESC LIMIT 10;
```

## Cooldown Reversion Detection

This is a fleet-level bug pattern: the scheduler daemon loads cooldown from a **fleet TOML file** at startup, not from the DB. When a foreman re-fixes cooldown via API PUT, it survives only until the next daemon restart (~every 4h).

**Detection:**
1. Query `projects.cooldown_s` from the DB — this is the desired value
2. Query `events` table for "project starved" messages — the `details` JSON field contains the daemon's live `cooldown` and `last_tick` values
3. If DB says 43200 but events say 1800: cooldown reversion confirmed

**Foreman signature:** Repeated commit messages like "cooldown re-fixed 1800→43200", "daemon restart reversion", "fleet TOML root cause"

**Fix:** Update the fleet TOML file (not DB) to the desired cooldown. This must be done by a human with fleet config access. |
