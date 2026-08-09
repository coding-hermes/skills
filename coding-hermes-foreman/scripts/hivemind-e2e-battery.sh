#!/usr/bin/env bash
# hivemind E2E battery — verified route shapes (tick 215, 2026-08-03).
# Usage: bash hivemind-e2e-battery.sh <port>   (default 21576)
# Preconditions: fresh binary at $BIN (default /tmp/hivemind-e2e-bin) booted against
#   a FRESH data dir:  hivemind serve --addr 127.0.0.1:<port> --data-dir /tmp/<fresh>
#   --rate-limit-enabled=false --dump-enabled=false
# Exit code: 0 = all real checks pass; 1 = >=1 real failure (battery-shape mistakes
# are reported as SKIP, not failure).
#
# Pitfalls encoded (from references/hivemind-foreman-ops.md):
#   - workspace_id (not id) in create response; unique ws name per run (409 on dup)
#   - cron/memory/inbox are workspace-scoped; record?id= is a query param
#   - 500 HMSE0004 on sessions/resolve = opencode shim unreachable = environmental
#   - TS-ROUNDTRIP-001: grep created_at from the CREATE response, not later ones
#   - exports needs ?workspace_id=; isolation 404 = correct (no orchestrator)

PORT="${1:-21576}"
B="http://127.0.0.1:${PORT}"
WSNAME="e2e$(date +%s)"   # unique per run → avoids 409 on re-create
PASS=0; FAIL=0; SKIP=0
chk() { if [ "$2" = "$3" ]; then PASS=$((PASS+1)); echo "PASS: $1 ($3)";
  else FAIL=$((FAIL+1)); echo "FAIL: $1 — expected $2, got $3"; fi; }
code() { curl -s -o /tmp/hm_e2e_body.json -w "%{http_code}" --max-time 8 "$@"; }

echo "== E2E battery on :${PORT} (ws ${WSNAME}) =="

# --- health family ---
for p in health/live health/ready health/detail health/history v1/version v1/capabilities; do
  c=$(code $B/$p); chk "GET /$p" 200 "$c"
done

# --- workspaces CRUD ---
c=$(code -X POST $B/v1/workspaces -H 'Content-Type: application/json' -d "{\"name\":\"$WSNAME\",\"description\":\"e2e battery\"}")
chk "POST /v1/workspaces" 201 "$c"
WSID=$(grep -o '"workspace_id":"[^"]*"' /tmp/hm_e2e_body.json | head -1 | cut -d'"' -f4)
[ -n "$WSID" ] && { PASS=$((PASS+1)); echo "PASS: workspace_id extracted ($WSID)"; } \
  || { FAIL=$((FAIL+1)); echo "FAIL: workspace_id empty in create response"; }
c=$(code $B/v1/workspaces); chk "GET /v1/workspaces" 200 "$c"
c=$(code $B/v1/workspaces/$WSID); chk "GET /v1/workspaces/:ws" 200 "$c"
c=$(code -X PUT $B/v1/workspaces/$WSID -H 'Content-Type: application/json' -d "{\"name\":\"$WSNAME-u\"}"); chk "PUT /v1/workspaces/:ws" 200 "$c"

# --- cron (workspace-scoped) ---
c=$(code $B/v1/workspaces/$WSID/cron); chk "GET ws cron list" 200 "$c"
c=$(code -X POST $B/v1/workspaces/$WSID/cron/jobs -H 'Content-Type: application/json' -d '{"name":"hm-e2e-job","schedule":"0 * * * *","enabled":true}')
chk "POST ws cron jobs (201 = created)" 201 "$c"
# TS-ROUNDTRIP-001: created_at from the CREATE body (enable/disable omit it)
TS=$(grep -o '"created_at":"[^"]*"' /tmp/hm_e2e_body.json | head -1)
case "$TS" in
  *"T"*"Z"*|*"T"*"+00:00"*|*"T"*"-05:00"*) PASS=$((PASS+1)); echo "PASS: TS-ROUNDTRIP-001 RFC3339Nano ($TS)";;
  *) FAIL=$((FAIL+1)); echo "FAIL: TS-ROUNDTRIP-001 timestamp shape ($TS)";;
esac
JOBID=$(grep -o '"id":"[^"]*"' /tmp/hm_e2e_body.json | head -1 | cut -d'"' -f4)
if [ -n "$JOBID" ]; then
  c=$(code -X POST $B/v1/workspaces/$WSID/cron/jobs/$JOBID/enable);  chk "POST cron jobs/:id/enable (OpenAPI)" 200 "$c"
  c=$(code -X POST $B/v1/workspaces/$WSID/cron/jobs/$JOBID/disable); chk "POST cron jobs/:id/disable (OpenAPI)" 200 "$c"
  c=$(code -X POST $B/v1/workspaces/$WSID/cron/enable/$JOBID);       chk "POST cron enable/:job_id (legacy)" 200 "$c"
  c=$(code -X POST $B/v1/workspaces/$WSID/cron/disable/$JOBID);      chk "POST cron disable/:job_id (legacy)" 200 "$c"
fi
c=$(code -X POST $B/v1/workspaces/$WSID/cron/validate -H 'Content-Type: application/json' -d '{"schedule":"*/5 * * * *"}'); chk "POST cron validate" 200 "$c"

# --- memory ---
c=$(code -X POST $B/v1/workspaces/$WSID/memory -H 'Content-Type: application/json' -d '{"id":"mem-e2e-1","type":"event","content":"e2e battery event"}'); chk "POST memory create" 201 "$c"
c=$(code $B/v1/workspaces/$WSID/memory/tree);  chk "GET memory tree" 200 "$c"
c=$(code $B/v1/workspaces/$WSID/memory/index); chk "GET memory index" 200 "$c"
c=$(code "$B/v1/workspaces/$WSID/memory/record?id=mem-e2e-1"); chk "GET memory record?id= (query param)" 200 "$c"
c=$(code "$B/v1/workspaces/$WSID/memory/search?q=e2e"); chk "GET memory search" 200 "$c"

# --- tasks ---
c=$(code "$B/v1/tasks?workspace_id=$WSID"); chk "GET /v1/tasks?ws=" 200 "$c"
c=$(code $B/v1/tasks); chk "GET /v1/tasks (no ws — 400 binding)" 400 "$c"

# --- inbox (workspace-scoped family) ---
c=$(code -X POST $B/v1/workspaces/$WSID/inbox/messages -H 'Content-Type: application/json' -d '{"from":{"workspace_id":"'$WSID'","agent_id":"foreman"},"to":[{"workspace_id":"'$WSID'","agent_id":"worker"}],"type":"event","subject":"e2e test"}'); chk "POST inbox/messages" 201 "$c"
c=$(code $B/v1/workspaces/$WSID/inbox/worker/messages); chk "GET inbox/:agent/messages" 200 "$c"

# --- sessions (500 HMSE0004 = environmental, known-pass) ---
BODY=$(curl -s -o /tmp/hm_e2e_body.json -w "%{http_code}" --max-time 8 -X POST $B/v1/sessions/resolve -H 'Content-Type: application/json' -d '{"conversation_key":"conv-e2e","workspace_id":"'$WSID'","directory":"/tmp"}')
case "$BODY" in
  200) PASS=$((PASS+1)); echo "PASS: sessions/resolve (200, shim reachable)";;
  500) if grep -q "HMSE0004" /tmp/hm_e2e_body.json; then
         SKIP=$((SKIP+1)); echo "SKIP: sessions/resolve 500 HMSE0004 (opencode shim unreachable — environmental, known-pass)"
       else FAIL=$((FAIL+1)); echo "FAIL: sessions/resolve 500 without HMSE0004: $(head -c 200 /tmp/hm_e2e_body.json)"; fi;;
  *)   FAIL=$((FAIL+1)); echo "FAIL: sessions/resolve unexpected $BODY";;
esac

# --- opencode config (workspace-scoped) ---
c=$(code -X POST $B/v1/workspaces/$WSID/config/opencode/validate -H 'Content-Type: application/json' -d '{"content":"{\"model\":{\"default\":\"glm-5.2\"}}"}'); chk "POST config/opencode/validate" 200 "$c"

# --- misc (correct shapes — no bare GETs) ---
c=$(code -X POST $B/v1/doctor/all); chk "POST /v1/doctor/all" 200 "$c"
c=$(code $B/v1/federation/status);  chk "GET /v1/federation/status" 200 "$c"
c=$(code $B/v1/events/tail);        chk "GET /v1/events/tail" 200 "$c"
c=$(code $B/v1/channels);           chk "GET /v1/channels" 200 "$c"
c=$(code $B/v1/alerts);             chk "GET /v1/alerts" 200 "$c"
c=$(code $B/v1/locks);              chk "GET /v1/locks" 200 "$c"
c=$(code $B/v1/peers);              chk "GET /v1/peers" 200 "$c"
c=$(code $B/v1/webhooks);           chk "GET /v1/webhooks" 200 "$c"
c=$(code $B/v1/templates);          chk "GET /v1/templates" 200 "$c"
c=$(code $B/v1/config/user);        chk "GET /v1/config/user" 200 "$c"
c=$(code $B/v1/config/system);      chk "GET /v1/config/system" 200 "$c"
c=$(code $B/v1/config/network);     chk "GET /v1/config/network" 200 "$c"
c=$(code $B/v1/security/config);    chk "GET /v1/security/config" 200 "$c"
c=$(code $B/v1/query/predefined);   chk "GET /v1/query/predefined" 200 "$c"
c=$(code $B/v1/user/profile);       chk "GET /v1/user/profile" 200 "$c"
c=$(code $B/v1/notifications);      chk "GET /v1/notifications" 200 "$c"
c=$(code $B/v1/backup);             chk "GET /v1/backup" 200 "$c"
c=$(code $B/v1/merge-queue);        chk "GET /v1/merge-queue" 200 "$c"
c=$(code $B/v1/onboarding/status);  chk "GET /v1/onboarding/status" 200 "$c"
c=$(code "$B/v1/exports?workspace_id=$WSID"); chk "GET /v1/exports?ws= (param required)" 200 "$c"
c=$(code $B/v1/exports); chk "GET /v1/exports (no ws — 400 binding)" 400 "$c"

# --- MCP (custom dialect) ---
c=$(code -X POST $B/v1/mcp -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"memory.search","params":{"workspace_id":"'$WSID'","query":"e2e"}}'); chk "POST /v1/mcp memory.search" 200 "$c"

# --- isolation: 404 without orchestrator = correct ---
c=$(code $B/v1/isolation/metrics); chk "GET /v1/isolation/metrics (404 = no orchestrator)" 404 "$c"

echo
echo "=== BATTERY: $PASS PASS / $FAIL FAIL / $SKIP SKIP (known-environmental) ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
