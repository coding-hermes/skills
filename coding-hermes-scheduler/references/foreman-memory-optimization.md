# Foreman Memory Optimization

Each `hermes chat` process spawns its own MCP server infrastructure. With 8 concurrent
foreman ticks, this means 8 copies of every MCP server, browser, and tool. Total: ~500MB
per chat, ~4GB for the fleet.

## Root Cause: Per-Chat MCP Duplication

```
hermes chat Process Tree (per chat):
├── python3 main (200MB) — agent runtime
├── node duckbrain.js stdio (100MB) — DuckBrain MCP, per-chat
├── google-flights .venv/python (76MB) — Flights MCP, per-chat
├── gitreins .venv/python3 (33MB) — GitReins MCP, per-chat
├── chromebrowser/cloakbrowser (350MB) — CDP browser, per-chat
└── chimera-mcp subprocesses (19MB × 4) — Chimera deliberation, per-chat
```

Each MCP in `~/.hermes/config.yaml` with `command:` (stdio mode) starts fresh per session.

## Fix: HERMES_HOME Per-Session Config

Hermes resolves config from `HERMES_HOME` env var → `config.yaml`. Create a foreman-only
config directory with minimal MCPs:

### Step 1: Create foreman config directory

```bash
mkdir -p ~/.hermes/foreman

# Copy main config, then strip to foreman needs
python3 -c "
import yaml, os
with open(os.path.expanduser('~/.hermes/config.yaml')) as f:
    cfg = yaml.safe_load(f)

# Disable browser (foreman delegates to workers)
cfg['agent']['disabled_toolsets'] = ['browser']
cfg['agent']['max_turns'] = 75

# Keep only duckbrain + gitreins MCPs
mcp = cfg.get('mcp_servers', {})
keep = ['duckbrain', 'gitreins']
cfg['mcp_servers'] = {k: v for k, v in mcp.items() if k in keep}

with open(os.path.expanduser('~/.hermes/foreman/config.yaml'), 'w') as f:
    yaml.dump(cfg, f)
"
```

### Step 2: Symlink runtime directories

```bash
ln -sf ~/.hermes/skills    ~/.hermes/foreman/skills
ln -sf ~/.hermes/sessions  ~/.hermes/foreman/sessions
ln -sf ~/.hermes/logs      ~/.hermes/foreman/logs
ln -sf ~/.hermes/cache     ~/.hermes/foreman/cache
ln -sf ~/.hermes/.env      ~/.hermes/foreman/.env
```

Without the skills symlink, `hermes chat -s coding-hermes-foreman` fails:
"Unknown skill(s): coding-hermes-foreman" — all ticks fail in 1 second.

### Step 3: Set HERMES_HOME in spawn environment

```go
cmd.Env = append(os.Environ(),
    "HERMES_HOME="+foremanHomeDir,
    "CODING_HERMES_TICK="+tickID,
    // ...
)
```

Default: `$HOME/.hermes/foreman`. Configurable via `Spawner.SetForemanHome()`.

## Savings

| Component | Before | After | Savings |
|-----------|--------|-------|---------|
| Main Python | 200MB | 175MB | -12% |
| Chrome/CDP Browser | 350MB | **0** | -100% |
| DuckBrain (node) | 100MB | 100MB | kept (memory, needed) |
| Google Flights MCP | 76MB | **0** | -100% |
| GitReins MCP | 33MB | 33MB | kept (CI guard, needed) |
| Chimera MCP | 76MB | **0** | -100% |
| **Per chat** | **~500MB** | **~175MB** | **-65%** |
| **8 concurrent** | **~4GB** | **~1.4GB** | **-65%** |

## What Foreman Actually Needs

| MCP/Tool | Needed? | Why |
|----------|---------|-----|
| DuckBrain | ✅ Yes | Memory/knowledge layer — idle counters, fleet state |
| GitReins | ✅ Yes | CI guard checks on commits |
| Browser (Chrome/CDP) | ❌ No | Foreman delegates browser work to workers |
| Google Flights | ❌ No | Foreman never searches flights |
| Chimera | ❌ No | Multi-model deliberation — worker concern |

## Don't Disable Globally

Bane: "I don't want it globally disabled for normal chat, just for foreman."

The HERMES_HOME approach solves this — global config unchanged. Normal chats get
all MCPs + browser. Foreman ticks get the stripped set via HERMES_HOME env var.

## Foreman Prompt Instruction

Added to spawn.go prompt: "You are a FOREMAN, not a worker. Browser/interactive
work belongs in workers (delegate)." This prevents the foreman from attempting
browser calls even if browser were available.
