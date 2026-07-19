# DuckBrain Namespace Split-Brain

## Problem

DuckBrain stores memories in namespaces (separate git repos). When a foreman tick calls `recall` or `remember` without an explicit `namespace` parameter, it uses the **default namespace**. The coding-hermes scheduler may configure a project with a different `NamespaceID` (e.g. `coding-hermes`), creating two independent memory stores for the same project.

Records written to the default namespace won't be visible to ticks that query the correct namespace, and vice versa. This produces **silent split-brain** — a foreman sees 0 prior idle ticks even though 6 exist in the other namespace.

## Detection

- DuckBrain `recall` returns 0 results for a key prefix that should have history
- Different result counts from the same key prefix with vs without `namespace` parameter
- Two namespaces both have partial history for the same project key

## Fix

Always pass `namespace` matching the scheduler project's `NamespaceID` when calling DuckBrain `recall` or `remember`:

```bash
# 1. Retrieve the namespace from the scheduler
curl -s http://127.0.0.1:9090/api/v1/projects/<name> | jq -r '.project.NamespaceID'

# 2. Use it in all DuckBrain calls
mcp__duckbrain__recall(keyPrefix="/project/<name>/", namespace="<NamespaceID>")
mcp__duckbrain__remember(key="/project/<name>/status/...", namespace="<NamespaceID>", ...)
```

## Proven Instance

SpecLang 2026-07-18:
- `recall` with `keyPrefix=/project/speclang/` (no namespace) → 6 idle-tick records
- `recall` with `keyPrefix=/project/speclang/`, `namespace=coding-hermes` → 3 different idle-tick records
- Both namespaces had partial history; neither had the full picture
- Scheduler project config showed `NamespaceID: coding-hermes` — the correct target
