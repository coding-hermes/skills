# DuckBrain Model Discovery

When a model isn't found in Hermes' built-in provider list (`/v1/models`),
check DuckBrain's benchmark database under the `default` namespace:

```bash
# Switch namespace
mcp__duckbrain__switch_namespace(name="default")

# List models
mcp__duckbrain__list_keys(prefix="/benchmarks/models/")
```

## Key fields per model entry

```
key: /benchmarks/models/gpt-5.6-sol
domain: config
attributes:
  provider: openai                → maps to Hermes provider (e.g. openai-codex)
  tier: frontier
  pricing: "$5/$30 per 1M tokens"
  context: 1M
  release_date: 2026-06-26
  benchmarks: {swe_bench_pro: 64.6, terminal_bench_2.1: 88.8, ...}
```

## Adding to Hermes config

Once you know the provider and model name:

1. Add to config.yaml under the provider's reference models:
   ```yaml
   reference_models:
     - model: gpt-5.6-sol
       provider: openai-codex
   ```
2. Update project's worker model in scheduler.db (NOT the foreman model —
   the `model` column controls the foreman itself, which should stay on
   deepseek-v4-pro for PAYG billing):
   ```sql
   UPDATE projects SET worker_model='gpt-5.6-sol', worker_provider='openai-codex'
   WHERE name='coding-hermes-scheduler';
   ```
   This injects into the spawn prompt as a non-binding default:
   "Worker default: use model gpt-5.6-sol with provider openai-codex if available."

## Critical distinction: foreman model vs worker model

The `model`/`provider` columns on a project control the FOREMAN (the orchestrator
that scans the board, dispatches workers, and verifies). The `worker_model`/
`worker_provider` columns (v3.5+) control the default WORKER model (what coding
agents use when the foreman delegates). These are separate — the foreman runs
on deepseek-v4-pro (PAYG), workers run on whatever the project specifies
(typically prepaid flat-rate buckets like gpt-5.6-sol).

## Proven

2026-07-19 — gpt-5.6-sol was not in `/v1/models` list but existed in
DuckBrain at `/benchmarks/models/gpt-5.6-sol`. Bane: "i promise you duck
brian has multiple parts of this under its ai benchmarks under the default
name space." Added to chimera reference_models, gateway accepted it on
next request. Rate-limited but model recognized — confirmed working.
