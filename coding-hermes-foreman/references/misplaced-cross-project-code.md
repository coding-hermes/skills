# Misplaced Cross-Project Code Detection

## Problem

Untracked code from a *different* project appears in the working directory. Unlike uncommitted work from a prior tick (same project, same module path), cross-project code:
- Compiles cleanly (uses only stdlib or its own deps)
- Passes `go vet` and `go test`
- Passes all the dirty-workdir checks in Step 0
- But references a completely different API, domain, or module path

The existing dirty-workdir detection (`go build ./... && go vet ./... && go test ./...`) produces **false positive** — all green, suggesting "completed work from prior tick." But the code isn't for this project at all.

## Detection Signals

| Signal | Misplaced code | Same-project uncommitted work |
|--------|---------------|-------------------------------|
| Module path in files | References different module | References current module |
| Import paths | No imports from current project's `internal/` | Imports current project's packages |
| Package name | Different domain (e.g., `sdk` for Consensus API) | Domain-appropriate for this project |
| Task board mention | Not mentioned anywhere | Corresponds to a board task |
| API references | References external API not owned by this project | References this project's own API |

## Detection Workflow

When `git status --short` shows untracked directories with source files AND `go build` passes:

1. **Read the package doc comment** (`head -20 <dir>/*.go`). Does it describe THIS project's domain?
2. **Check the package name and purpose.** An SDK client for "Consensus API" in a scheduler project is a mismatch.
3. **Grep for the project's module path** in the untracked files. Zero matches = not this project.
4. **Grep the task board** for any mention of the directory name. Zero matches = not planned work.
5. **Check imports.** Do the files import from `internal/` packages of this project? If not, they're independent.

## Resolution

Do NOT commit cross-project code. Options:
1. **Create a `## [ ] CLEANUP` task** — flag it for the user to decide (move to correct project or delete).
2. **If you know the target project**, move the files: `mv pkg/sdk /path/to/correct-project/pkg/sdk`. Commit the removal from this project + addition to the correct project.
3. **If unsure**, leave untracked and create the CLEANUP task. Don't delete without asking — the code may be valuable for its intended project.

## Proven Instance

**Scheduler foreman 2026-07-15:** `pkg/sdk/` (11 Go files) — Consensus API SDK client in the scheduler project. Compiled clean, passed vet, no board mention. References "Consensus agent platform API" but the scheduler module is `github.com/coding-hermes/scheduler`. Zero imports from scheduler internal packages. Created CLEANUP task on the board.
