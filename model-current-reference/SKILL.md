---
name: model-current-reference
description: Use when picking a model or refreshing the models list.
version: 1.0.0
author: Bane + Hermes
platforms: [linux, macos]
metadata:
  hermes:
    tags: [models, routing, freshness, registry, weekly, cron, fallbacks]
    related_skills: [task-router-product-ops, coding-hermes-model-router, coding-hermes-skills-shipping]
---

# Current models — the systems reference

One place that answers three questions the fleet keeps getting wrong:

1. **What is current?** — which models actually shipped inside the freshness window.
2. **What can we not use?** — which of those the registry does not carry, or carries with no
   tier row (a model with no tier can never be selected, however good it is).
3. **What should be used for what?** — per-category picks from the tier table, plus the declared
   fallback ladders.

It deliberately does **not** answer "what do I have access to". That is per-agent and is computed
at dispatch time from the agent's own configured providers, keys, quota and circuit state.
Conflating the two is what produces confident recommendations for a lane the caller cannot reach.

## Use it standalone (no fleet required)

The script is self-contained: stdlib only, no keys, no network.

```bash
curl -fsSL https://models.dev/api.json -o models-dev.json
python3 scripts/current-models-report.py --cache models-dev.json
```

That prints the current-model list with provider reach — no router registry needed. Add a registry
and you get the gap analysis and per-category picks on top:

```bash
python3 scripts/current-models-report.py --cache models-dev.json \
    --tables ./data/tables --write current-models.md
```

`--tables` expects `models.jsonl`, `model_tier.jsonl` and `fallback_lanes.jsonl` in that directory;
those files are yours to build (one JSON object per line — `model`, `provider`, `release_date` for
the first; `category`, `model`, `perf`, `tier_source` for the second). Without them nothing breaks,
you just get the feed view.

## When to Use

- Choosing a model for a task, or questioning one the router just proposed
- A new model launched and you need to know whether the fleet can use it yet
- The weekly refresh (see Procedure) — Friday morning cron
- A router chain looks stale, or the same three models keep winning every category

Don't use for: pricing negotiation or plan/quota questions (that is the router's `price` / plan
layer), or provider account provisioning.

## Where the data comes from (already gathered, no new credentials)

- **models.dev snapshot** — a models.dev `api.json` dump (default `~/.hermes/models_dev_cache.json`):
  233 providers, per-model `release_date`, `cost`, `limit`, `family`, `canonical_model_id`.
- **router registry** — `~/task-router/data/tables/models.jsonl`: provider lanes, prices,
  `release_date`, `replaced_by`, lifecycle.
- **tier table** — `~/task-router/data/tables/model_tier.jsonl`: `category` × `model` →
  `perf`, `tier`, `tier_source`.
- **declared ladders** — `~/task-router/data/tables/fallback_lanes.jsonl`: provider/model order
  with `key_env`.
- **bench probes** — `~/model_bench/`, `scripts/router_probe_run.py`: measured category scores.
- **vendor pages** — launch DATE only; never invent one.

The generated document is `references/current-models.md`. **It is generated, not authored.**
Hand edits are overwritten on the next run.

## Laws

1. **A model with no `model_tier` row is invisible to chain resolution.** It is filtered before
   ranking, so it never appears even as an exclusion. Presence in `models.jsonl` is not enough.
2. **`tier_source` class decides how much the number is worth.** `bench`/`measured`/`live-probe`
   outranks `family`/`estimate`/`inherited`. A declared 0.9 does not beat a measured 0.7 — the
   report sorts measured first for that reason and labels every pick.
3. **One battery can dominate every category.** If the same model tops five or more categories,
   the table is measuring that battery, not capability; the report prints a saturation warning
   and category leadership is weak evidence.
4. **Provider count is reach, not access.** A model on 90 providers is still unreachable if the
   caller has none of them configured.
5. **Freshness is two separate clocks.** The models.dev snapshot (≤7 days) and the registry's
   newest `release_date` (≤21 days). Either one stale makes the whole reference stale, and they
   are fixed by different work.
6. **`release_date` is a launch date, not when the row was added.** `valid_from` is registry entry
   time and says nothing about recency.
7. **Recommendation comes before configuration.** If a model should be used, it first needs a
   registry row and a tier; only then may a lane pin it.

## Procedure

### A. Read the current state (any time, cheap)

```bash
python3 scripts/current-models-report.py --json
```

Exit `0` = within thresholds, `2` = stale (the cron's only signal), `3` = no snapshot at all.
Read `problems[]` — it names which clock is stale, not just that something is.

### B. Weekly refresh (Friday morning)

1. **Snapshot first.** Confirm the models.dev cache is fresh; if not, the job that maintains it is
   broken — fix that before anything else, because every downstream number derives from it.
2. **Registry rows.** For each current model with no row: decide carry-or-skip and record the
   decision. Skip is legitimate (deprecated, duplicated by an alias, no provider we use).
3. **Rank before recommending.** A new row with no tier is a model the fleet will silently never
   choose. Ranking is `model-rank-maintenance` territory (audit → roster → probe → ingest →
   re-seed); never invent a tier to make a recommendation work.
4. **Regenerate:** `scripts/current-models-report.py --write references/current-models.md`.
   The generated file is written where you point it; it is not part of the shipped skill.
5. **Publish both copies** (per `coding-hermes-skills-shipping`): the local skill dir is the edit
   target; the public repo copy is updated in the same pass and verified from a fresh clone.
   Sanitize before pushing — no real names, host paths, or provider secrets.
6. **Report the delta** — new current models, newly routable models, models that lost their
   successor, and the status line. A refresh with no delta still reports status.

### C. Use it when choosing a model

1. Open `references/current-models.md` and find the row for your category (archetype when the
   category is absent).
2. Drop every pick whose source class is `declared` unless nothing measured exists.
3. Drop every pick whose provider you do not carry — check your own `providers:` block and the
   presence of that lane's `key_env`.
4. Apply the router's live gates (quota, circuit, health) from the routing view, not from this
   file.
5. Name a primary and one fallback. If the list is empty after filtering, that is a finding: the
   category has no reachable model, which is a coverage bug — not permission to guess.

## Pitfalls

- **A fresh snapshot does not mean a fresh registry.** The two clocks fail independently; the
  report separates them for exactly this reason.
- **Recommending from the top of a saturated category.** The same model winning 10 categories is
  a battery artefact (a multi-category key over a multi-task probe), not dominance.
- **Mixed units.** Our probes are damped at ingest, so a probe's 0.85 and a third-party 1.0 are
  not one scale. Compare within a source before calling one model stronger.
- **Aliases and canonical ids.** One model appears under a provider prefix, a `~alias`, and a
  snapshot-suffixed id. Identity is provable by matching measured profiles, not by name.
- **Non-chat rows.** Embeddings, rerankers, image/video and TTS entries live in the same snapshot;
  the generator filters a known list, but a new non-chat family slips through until it is added.
- **A pinned lane outranks this reference.** Scheduler/project pins in the fleet config AND the DB
  both win over any recommendation — clear both when a pick must actually change.
- **"Current" is not "better".** A brand-new model with no measurement is unknown, not strong.

## Verification

- [ ] `--json` shows both ages and both counts, and `status` matches the problems list
- [ ] `references/current-models.md` regenerated in the same pass as any data change
- [ ] every recommendation carries a source class, and no `declared`-only pick leads a category
      that has measured evidence
- [ ] the public repo copy carries the same generated date (fresh-clone diff, not local status)
- [ ] the digest names the delta and the status, or says explicitly that nothing changed
