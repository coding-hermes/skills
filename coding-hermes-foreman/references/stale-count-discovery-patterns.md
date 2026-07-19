# Stale-Count Discovery Patterns

After any feature-expansion tick (new languages, new capabilities, API version bumps, new CLI flags, new MCP tools), documentation counts drift silently. Every doc page becomes wrong until the stale references are found and updated.

## Generic Discovery Patterns

```bash
# Language count
grep -rn '[0-9]\+ language' --include='*.md' .
# Tool/API endpoint count
grep -rn '[0-9]\+ tool' --include='*.md' .
# Version number
grep -rn 'v0\.' --include='*.md' . | grep -v CHANGELOG
# File count, edge count, package count
grep -rn '[0-9]\+ file\|[0-9]\+ edge\|[0-9]\+ package' --include='*.md' .
```

## Proven Instances

| Date | Tick | Old Count | New Count | Files Missed |
|------|------|-----------|-----------|--------------|
| 2026-07-14 | Hilo TASK-005/006/007 | 9 languages | 26 languages | 6 files |
| 2026-07-15 | Hilo TASK-002/003 | 8 MCP tools | 10 MCP tools | `docs/mcp-tools.md` |
| 2026-07-15 | Hilo DOC sweep | 8 MCP tools | 15 MCP tools | `AGENTS.md` (workspace structure section) |

## What to Fix

1. Every `N languages`, `N-language` string in `.md` files
2. Every `N tools` / `N endpoints` / `N commands` doc claim
3. Prose that says "currently supports N..." without a date stamp
4. README feature lists that enumerate old feature counts
5. Architecture docs with old capability numbers

All of these are safe for foreman-direct fix — no worker needed.

## Rust Workspace Version Staleness

Doc counts aren't the only thing that drifts. Cargo.toml `version = "0.1.0"` fields can be stale
across every crate in a workspace even after major features ship. Detection + mechanical bump
procedure is in `references/rust-workspace-stale-version-discovery.md`.
