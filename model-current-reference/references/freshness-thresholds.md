# Model freshness — commands and thresholds

## Generator

```bash
python3 scripts/current-models-report.py                  # markdown to stdout
python3 scripts/current-models-report.py --write PATH     # write markdown to PATH
python3 scripts/current-models-report.py --json           # summary for monitors/crons
```

Flags:

- `--cache PATH` — models.dev `api.json` snapshot (default `~/.hermes/models_dev_cache.json`,
  env `MODELS_DEV_CACHE`)
- `--tables DIR` — registry tables (default `~/task-router/data/tables`, env `ROUTER_TABLES`);
  omit or point at a missing dir for a feed-only report
- `--window DAYS` — "current" window, default `90` (env `MODEL_WINDOW_DAYS`)
- `--max-age DAYS` — registry age ceiling, default `21` (env `MODEL_MAX_AGE_DAYS`)

Exit codes: `0` clean, `2` threshold breached, `3` cache missing or unparseable.

## Freshness definition

A model is **current** when `max(release_date)` from any provider carrying it falls inside
`MODEL_WINDOW_DAYS`. Registry ids and models.dev ids are matched through a normalizer that strips
the vendor prefix (`z-ai/`), the snapshot tag (`:0731`) and the alias marker (`~`).

Three states matter per current model:

- **routable** — registry row + at least one tier row → chains can select it
- **listed but blind** — registry row, zero tiers → never selected
- **untracked** — no registry row → not selectable at any price

## Thresholds that page

| Check | Ceiling | Why |
|---|---|---|
| models.dev snapshot age | 7 days | the feed is cheap; staleness means the update job broke |
| registry newest `release_date` | 21 days | fleet re-ranking can lag, but not for three weeks |
| untracked share of current models | 50% | past this, the registry describes last quarter |

A breach is a `problems[]` entry and exit code 2. Treat the code as the signal, the string as the
diagnosis.

## Snapshot refresh (the feed itself)

The cache is written by the existing models.dev registry crosscheck path. If the snapshot is
stale, do not hand-fetch a replacement into the skill: repair the job that owns it, then re-run
this generator. A generator that silently fetches its own data hides a broken pipeline instead of
reporting it.

## Publishing both copies

The local skill directory is the edit target. Publishing follows the repo's shipping rules:

1. regenerate locally;
2. copy SKILL.md + `scripts/` + `references/` into a clean worktree of the public skills repo;
3. sanitize (no real names, host paths or secrets), commit as the org identity with no co-author
   trailer;
4. verify from a second fresh clone that the generated date and file hash match.

A published reference older than the local one is a silent staleness bug for every other
consumer — print both dates in the digest.
