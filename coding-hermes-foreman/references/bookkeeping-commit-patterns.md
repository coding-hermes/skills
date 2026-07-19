# Bookkeeping Commit Patterns — Config-Only & Code-Free Diffs

When the foreman encounters unstaged changes that are NOT source code changes, the correct action depends on what changed:

## Detection: Bookkeeping vs. Code

The foreman's self-heal dirty-workdir check (`git status --short`, `git diff --stat`) must classify changes:

| Signal | Classification | Action |
|--------|---------------|--------|
| Only `.md`, `.json`, `.yaml`, `.toml`, `.gitignore` files changed | **Bookkeeping** | `git add` + `git commit -m "chore:..."` + push |
| Only namespace mapping files (e.g., `duckbrain.config.json` with new namespace paths) | **Bookkeeping** | Commit as chore — no worker needed |
| Only lockfiles with new entries (e.g., `go.sum`, `package-lock.json`, `pnpm-lock.yaml` adding packages) | **Bookkeeping** | Commit as chore. If lockfile changes are the ONLY diff, the worker added deps but didn't commit |
| Only `.vfs/`, `.gitreins/`, `.coding-hermes/` changes | **Bookkeeping** | Commit as chore — board/config/project-state bookkeeping |
| Any `*.go`, `*.py`, `*.ts`, `*.rs`, `*.js`, `*.c`, `*.cpp`, `*.gd` file changed | **Code** | Follow Step 0's dirty-workdir flow (build+test → guard → commit or stash) |
| Mixed: code + bookkeeping | **Code** | Handle code changes first, then commit bookkeeping separately or together |

## Proven Patterns

### Project Config Files (e.g., duckbrain.config.json)

**Scenario:** A prior tick (or parallel process) added new namespace entries to the project's config JSON but didn't commit. The config file is the project's single source of truth for namespace routing — new namespaces are added as key-value pairs to the `namespaceMappings` section.

**Foreman action:**
```bash
git add duckbrain.config.json
git commit -m "chore: add <namespace-a> and <namespace-b> namespaces to config" --no-verify
git push origin main
```

**Proven:** DuckBrain 2026-07-15 — `vip-travel-agent` and `hermes-dagger` namespace additions were the only diff. `git diff --stat` showed 4 insertions, 2 deletions in `duckbrain.config.json`. No source code changed. Committed as chore, pushed, then `git pull --rebase` succeeded.

### Lockfile-Less Config (Config Only)

When a config file is NOT a lockfile but a project-specific routing/discovery file (e.g., `map.json` for namespace-to-path mappings, `registrations.json` for plugin paths), treat it same as duckbrain.config.json: bookkeeping.

## When to NOT Commit Bookkeeping

- If the config change is a work-in-progress (feature not yet implemented, namespace not yet populated on disk)
- If the config change is experimental or for testing only
- If the config change contradicts the board's current task (config points to namespace X, but the current task builds namespace Y)

In those cases, stash the config change and let the appropriate tick commit it with the feature it supports.
