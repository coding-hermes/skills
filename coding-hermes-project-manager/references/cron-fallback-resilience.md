# Cron LLM Fallback Resilience — the `fallback_providers` Config Gotcha

## The failure signature (learned 2026-08-04, fleet-wide outage)

```
ERROR cron.scheduler: Job 'X' idle for 601s (inactivity limit 600s) |
    last_activity=waiting for non-streaming API response | iteration=1/200 | tool=none
ERROR cron.scheduler: Job 'X' failed: TimeoutError: ... idle for 601s (limit 600s)
    — last activity: waiting for non-streaming API response
```

**Key diagnostic facts:**
- When the LLM provider hangs (connection errors / stalled responses), EVERY
  cron job fails with the same signature within minutes of each other —
  not just the job you're looking at. Check the whole errors log, not one job.
- A direct API test right after the window may succeed (1s OK) — the outage
  was intermittent, which makes it look like a config bug. It was BOTH:
  transient provider instability PLUS a dead fallback chain that should have
  absorbed it.
- The log line to hunt: `WARNING ... Retrying API call ... provider=<name>
  model=<model> error=Connection error` — that's the provider failing.

## Root cause: `fallback_providers` format is stricter than it looks

In `~/.hermes/config.yaml`, the resolver (`hermes_cli/fallback_config.py` →
`get_fallback_chain` → `_iter_fallback_entries`) **silently skips any entry
that is not a dict with BOTH `provider` and `model` non-empty strings**.
Plain-string entries are dropped without a warning → the chain resolves to
empty → the error says "Fallback chain was exhausted or unavailable" and it
is literally true, even when good providers are configured.

**Broken (silently ignored):**
```yaml
fallback_providers:
  - openrouter        # ← string, skipped entirely
  - ollama-cloud      # ← string, skipped entirely
```

**Also broken:** listing a provider that has no `providers:` entry and no
API key (a "ghost provider") — it can never serve a request even if the
format were right.

**Working:**
```yaml
fallback_providers:
  - provider: ollama-cloud
    model: deepseek-v4-flash
  - provider: kimi-for-coding
    model: kimi-for-coding
```

## Rules for a healthy chain

1. Every entry is a dict: `{provider: <name>, model: <model>}` (+ optional
   `base_url`).
2. Every provider named must exist under `providers:` with an `api_key`
   (or a resolvable `api_key_env`).
3. Prefer fallbacks that carry the SAME model family as the primary (e.g.
   ollama-cloud hosts `deepseek-v4-flash`) so behavior stays consistent
   across failover.
4. Order matters: first entry is the first fallback.

## Verification (do all three)

```python
import yaml, sys
sys.path.insert(0, '~/.hermes/hermes-agent')
from hermes_cli.fallback_config import get_fallback_chain
cfg = yaml.safe_load(open('~/.hermes/config.yaml'))
print(get_fallback_chain(cfg))   # must show dict entries, not []
```

Then live-test each fallback provider (curl the chat completions endpoint
with its key + model) — a configured-but-dead fallback is as bad as none.

**No restart needed:** the gateway re-reads `fallback_providers` from disk
per cron job (`_refresh_fallback_model` — "Cron already does this per job via
get_fallback_chain"). Editing config.yaml takes effect on the next job run.

## DuckBrain HTTP read path can degrade — read JSONL from disk instead

DuckBrain's HTTP server (`:3000`) intermittently returns
`DUCKDB_CONNECTION_LOST` on the read path (multiple stdio MCP servers
contending over the same DuckDB file). MCP writes keep working. For anything
read-heavy that must be reliable (the hourly HTML report,
`~/.hermes/scripts/standin-report.py`), read the namespace JSONL directly
from disk instead of the HTTP API: entries live at
`~/.hermes/duckbrain/namespaces/coding-hermes/<domain>/<YYYY-MM>/<partition>.jsonl`
(e.g. stand-in events under `event/2026-08/0NaN.jsonl`). Disk reads survive
HTTP degradation and are faster; use MCP for writes.

## Generalize: the canary pattern for engines being integrated

When wiring a NEW engine/dependency into the hourly stand-in cycle (e.g.
<project>), don't trust its "done" board — the board is a claim. Run a
**canary probe** every cycle: a minimal real invocation whose output either
proves the engine works or is null/absent. Until the canary flips green,
keep the proven path (subagent hunters) as the primary and log the canary
state each cycle so the handoff to the engine happens automatically the
moment it starts returning real output. Build any engine-facing templates
only against the surface you have actually executed successfully — the
documented API surface (d.ts, templates, README examples) can be dead
(fetch() not injected, agent() panics, annotations break the transpile)
while the core still works. Prove each primitive with a minimal probe before
building on it.
