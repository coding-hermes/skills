# Scheduler Live-Verification Checklist

After building and deploying the coding-hermes scheduler, run this 7-step live verification to prove all 4 layers work end-to-end. Each step is a curl command — no tools, no assumptions.

## Prerequisites

```bash
# Start the daemon with the correct DB path
./bin/schedulerd -listen 127.0.0.1:9090 -db ~/.hermes/coding-hermes/scheduler.db &
sleep 2
```

## Step 1 — Health Check

```
curl -s http://127.0.0.1:9090/api/v1/health
Expected: {"status":"ok","db":"connected","uptime":"2s",...}
```

If `status: ok` and `db: connected` → scheduler binary is alive and SQLite is accessible.

## Step 2 — Project Count

```
curl -s http://127.0.0.1:9090/api/v1/projects | jq '.projects | length'
Expected: >0 (should match migrate output count)
```

If 0 → DB path mismatch. Check that migrate and daemon use the same `-db` flag.

## Step 3 — Dashboard

```
curl -s http://127.0.0.1:9090/ | head -1
Expected: <!DOCTYPE html> or <html> tag
```

If empty or error → dashboard generator failed. Check template compilation.

## Step 4 — MCP Initialize

```
curl -s -X POST http://127.0.0.1:9090/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  | jq '.result.serverInfo.name'
Expected: "coding-hermes-scheduler"
```

If empty or error → MCP handler not configured or JSON-RPC parsing failed.

## Step 5 — Force Evaluate + Tick Spawn

```
curl -s -X POST http://127.0.0.1:9090/api/v1/evaluate
sleep 5
curl -s http://127.0.0.1:9090/api/v1/status | jq '.active_ticks'
Expected: >0 (foremen should be spawned)
```

If 0 → check agent.log for SQL errors (column name mismatches, NULL scan errors).

## Step 6 — Dynamic Config via API

```
curl -s -X PUT http://127.0.0.1:9090/api/v1/projects/<name> \
  -H 'Content-Type: application/json' \
  -d '{"weight":50,"priority":8}'
curl -s http://127.0.0.1:9090/api/v1/projects/<name> | jq '.project.Weight'
Expected: 50
```

If "project not found" → routing bug (prefix stripping). If no change → update handler not parsing body.

## Step 7 — Dynamic Config via MCP

```
curl -s -X POST http://127.0.0.1:9090/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
       "params":{"name":"fleet_set_cooldown",
                 "arguments":{"name":"<name>","cooldown":3600}}}' \
  | jq '.result.content[0].text'
Expected: {"cooldown_s":"3600","project":"<name>","status":"updated"}
```

If error → MCP tool handler mismatch (field name case, argument parsing).

## Common Failures and Fixes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| 0 projects | DB path mismatch | Align `-db` in migrate tool and daemon |
| "table ticks has no column named project" | Schmeduler wrote `project` but DDL has `project_name` | Fix INSERT/UPDATE column names |
| "converting NULL to string" | Go scan hit NULL in nullable column | COALESCE every nullable column |
| "project not found" on PUT | Path prefix not stripped | `strings.TrimPrefix(r.URL.Path, "/api/v1/projects/")` |
| active_ticks: 0 after evaluate | Enqueue failed silently | Check agent.log for SQL errors |
| PACKER: max concurrency (8), 0 ticks | Ticks stuck in `queued` not `running` | Add `StartRunning()` transition between enqueue and spawn |

## Proven

Scheduler 2026-07-12 — first deploy showed 0 projects (Step 2 failed, DB path mismatch). Second deploy showed 26 projects but 0 ticks (Step 5 failed, SQL `project` → `project_name`). Third deploy: 8 ticks running, dynamic config working. Each failure caught by a specific verification step before reaching production.
