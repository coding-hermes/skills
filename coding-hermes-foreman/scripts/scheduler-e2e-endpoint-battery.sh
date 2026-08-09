#!/bin/bash
# Scheduler E2E endpoint battery — coding-hermes-scheduler foreman ticks.
# Resolves live project/namespace slugs FIRST (guessing slugs produces false 404/500s),
# then sweeps all 16 endpoints incl. POST /mcp tools/list. Prints PASS/FAIL count.
# Proven: tick #202 (2026-08-02), 16/16. Run against the live daemon (127.0.0.1:9090).
B="http://localhost:9090"
echo "=== resolve slugs ==="
PNAME=$(curl -s --max-time 8 "$B/api/v1/projects" | grep -oE '"name":"[^"]*"|"Name":"[^"]*"' | head -5 | sed 's/"[Nn]ame":"//;s/"//' | tr '\n' ' ')
echo "projects: $PNAME"
NID=$(curl -s --max-time 8 "$B/api/v1/namespaces" | grep -o '"id":"[^"]*"' | head -8 | sed 's/"id":"//;s/"//' | tr '\n' ' ')
echo "namespaces: $NID"
echo ""
echo "=== endpoint sweep ==="
declare -a URLS=(
  "/api/v1/health"
  "/api/v1/status"
  "/api/v1/projects"
  "/api/v1/namespaces"
  "/api/v1/ticks"
  "/api/v1/queue"
  "/api/v1/events"
  "/api/v1/openapi.json"
  "/"
  "/dashboard/partial"
  "/health"
  "/queue"
  "/ticks"
  "/projects/coding-hermes-scheduler"
  "/namespaces/coding-hermes"
)
PASS=0; FAIL=0
for u in "${URLS[@]}"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$B$u")
  if [ "$code" = "200" ]; then PASS=$((PASS+1)); echo "200  $u"; else FAIL=$((FAIL+1)); echo "$code  $u"; fi
done
echo "--- POST /mcp tools/list ---"
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -X POST "$B/mcp" -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}')
if [ "$code" = "200" ]; then PASS=$((PASS+1)); echo "200  POST /mcp"; else FAIL=$((FAIL+1)); echo "$code  POST /mcp"; fi
echo ""
echo "RESULT: $PASS/16 pass, $FAIL fail"
