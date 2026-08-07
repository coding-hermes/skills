# Coding Hermes — Skills

This repository contains the skill files that power the Coding Hermes autonomous coding fleet. These skills define the processes, not the configuration. Your API keys, model names, and project paths go through the config skill — never hardcoded here.

---

## Skills Overview

| Skill | Layer | What It Does |
|-------|-------|-------------|
| [`coding-hermes-config`](coding-hermes-config/SKILL.md) | Foundation | First-run setup — asks for API keys, models, project paths |
| [`coding-hermes-north-star`](coding-hermes-north-star/SKILL.md) | Foundation | Architecture overview — the full system explained |
| [`coding-hermes-discovery`](coding-hermes-discovery/SKILL.md) | Foundation | Discovery sweep — finds work across all languages |
| [`coding-hermes-map`](coding-hermes-map/SKILL.md) | Foundation | Skill map — what each fleet skill does and when to use it |
| [`coding-hermes-foreman`](coding-hermes-foreman/SKILL.md) | Foreman | Per-project tick loop — inspects, plans, spawns workers |
| [`coding-hermes-self-heal`](coding-hermes-self-heal/SKILL.md) | Foreman | Pre-tick self-heal — identity, deps, CI, transient fixes |
| [`coding-hermes-worker-model`](coding-hermes-worker-model/SKILL.md) | Foreman | Worker model selection — cheapest model that works |
| [`coding-hermes-supervisor`](coding-hermes-supervisor/SKILL.md) | Supervisor | Fleet-wide oversight — health, starvation, failures, costs |
| [`coding-hermes-scheduler`](coding-hermes-scheduler/SKILL.md) | Broker | Operating the fleet scheduler daemon — API, config, ops |
| [`coding-hermes-broker`](coding-hermes-broker/SKILL.md) | Broker | Scheduling algorithm — weight-budget, urgency, packing |
| [`coding-hermes-worker`](coding-hermes-worker/SKILL.md) | Worker | Code implementation — writes code, runs tests, commits |
| [`coding-hermes-jsonl-board-append`](coding-hermes-jsonl-board-append/SKILL.md) | Board | JSONL board append + cache rebuild tooling |

---

## Architecture

```
┌──────────────────────────────────────────────┐
│                 SUPERVISOR                     │
│  Fleet health, starvation, failures, costs    │
└────────────────────┬─────────────────────────┘
                     │ queries scheduler API
┌────────────────────▼─────────────────────────┐
│                  BROKER                        │
│  Weight-budget knapsack scheduler             │
│  Urgency = priority × (1 + wait/interval)^d  │
└────────────────────┬─────────────────────────┘
                     │ spawns per tick
┌────────────────────▼─────────────────────────┐
│                  FOREMAN                       │
│  Per-project: inspect → plan → spawn worker   │
│  10-step loop: heal, read, hilo, duckbrain,   │
│  prompt, spawn, guard, judge, commit, write   │
└────────────────────┬─────────────────────────┘
                     │ spawns for coding tasks
┌────────────────────▼─────────────────────────┐
│                  WORKER                        │
│  Write code → run tests → commit → report     │
│  One task per spawn. No planning.             │
└──────────────────────────────────────────────┘
```

---

## Getting Started

> **Onboarding guide — complete install from zero to a running fleet scheduler.**
> If anything in this flow fails, the README of the
> [scheduler repo](https://github.com/coding-hermes/scheduler) is the
> authoritative reference, and `docs/fleet.md` there covers operations.

### 0. Prerequisites

- **Hermes Agent installed** — `hermes doctor` passes (install: https://hermes-agent.nousresearch.com/docs)
- **Hermes gateway running with the API server enabled** — `curl http://127.0.0.1:8642/health` returns `{"status":"ok",...}`. The API server key lives in `~/.hermes/.env` as `API_SERVER_KEY=...` (generate one: `openssl rand -hex 32`)
- **Go 1.23+** — `go version`
- **SQLite3** — `sqlite3 --version`

### 1. Install the skills

The skills are plain markdown folders — install them where Hermes can load them:

```bash
# Recommended: add this repo as a skill source (tap), then enable what you need
hermes skills tap add https://github.com/coding-hermes/skills
hermes skills enable coding-hermes-config coding-hermes-foreman coding-hermes-worker

# Alternative: manual clone + symlink (one symlink per skill folder)
git clone https://github.com/coding-hermes/skills.git ~/coding-hermes-skills
mkdir -p ~/.hermes/skills
for d in ~/coding-hermes-skills/coding-hermes-*; do
  ln -s "$d" ~/.hermes/skills/$(basename "$d")
done
```

### 2. Run the config skill

In Hermes:
```
Load skill coding-hermes-config and walk me through setup.
```

The config skill will ask you for:
- Your API keys (one per provider)
- Which models to use for foreman vs worker
- Your project paths and repos

### 3. Build the scheduler

```bash
git clone https://github.com/coding-hermes/scheduler.git
cd scheduler
make build
```

This produces `./bin/schedulerd` (the daemon) and `./bin/migrate` (cron-job importer).

### 4. Create your fleet configuration

Copy the example config and edit it for your projects:

```bash
cp fleet.example.toml fleet.toml
$EDITOR fleet.toml   # add one [[projects]] block per repo you want the fleet to manage
```

Minimal project block (see `fleet.example.toml` for all fields):

```toml
[[projects]]
name = "my-project"
repo_url = "https://github.com/user/my-project"
workdir = "/absolute/path/to/my-project"
weight = 10
priority = 5
cooldown_s = 7200          # 2h minimum between ticks; 900 for hot projects
model = "deepseek-v4-flash"
provider = "deepseek"
namespace_id = "coding-hermes"
enabled = true
```

### 5. Run the scheduler

Quick test (foreground):

```bash
./bin/schedulerd -db ~/.hermes/coding-hermes/scheduler.db \
  -config fleet.toml \
  -listen 127.0.0.1:9090 \
  --namespace-mode --max-concurrent 4 --min-interval 30s --tick-timeout 7200s \
  --gateway-url http://127.0.0.1:8642 --gateway-key "$API_SERVER_KEY"
```

Install as a systemd user service (template included in the scheduler repo):

```bash
# 1. Put your gateway key in a root-owned env file
sudo sh -c 'echo "API_SERVER_KEY=<your-key>" > /etc/coding-hermes/gateway.env && chmod 600 /etc/coding-hermes/gateway.env'

# 2. Install + start the service
cp deploy/coding-hermes-scheduler.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now coding-hermes-scheduler

# 3. (Optional) watchdog — auto-restarts the daemon if it dies
cp deploy/watchdog.service deploy/watchdog.sh ~/.config/systemd/user/ 2>/dev/null || true
```

### 6. Verify

```bash
curl http://127.0.0.1:9090/api/v1/health        # {"status":"ok",...}
curl http://127.0.0.1:9090/api/v1/projects       # your projects, scheduled state
```

### 7. Import existing cron jobs (optional)

If you already run per-project `hermes cron` foremen, migrate them:

```bash
make migrate        # dry run first: make migrate-dry
```

---

## How Skills Load

The skills form a dependency chain:

```
coding-hermes-config        ← ALWAYS loaded first (setup)
        ↓
coding-hermes-north-star    ← architecture reference
        ↓
coding-hermes-broker        ← scheduling logic
        ↓
coding-hermes-foreman       ← per-project execution
        ↓
coding-hermes-supervisor    ← fleet oversight
        ↓
coding-hermes-worker        ← code implementation
```

Each skill references the ones above it. The foreman loads config → north-star → itself → spawns workers. The supervisor loads config → north-star → broker → itself.

---

## What's NOT In These Skills

- **API keys** — handled by `coding-hermes-config` at setup time
- **Model names** — configured per user, stored in DuckBrain
- **Project paths** — configured per user
- **Provider URLs** — configured per user
- **Specific account details** — never in skills

---

## Related Repos

- [`coding-hermes/scheduler`](https://github.com/coding-hermes/scheduler) — The Go scheduler binary
- [`coding-hermes/`](https://github.com/coding-hermes) — GitHub organization
