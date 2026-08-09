#!/bin/bash
# km-e2e-full-battery.sh — Kobayashi-Maru E2E-001 FULL battery runner.
# Run at the FIRST tick of each E2E-001 due window (~every 5-10 ticks; per
# kobayashi-maru-foreman-ops.md: the first tick of a due window runs the FULL
# battery, never "any tick in that range").
# Plain bash + curl, cron-safe (no python pipes). Body checks via head -c.
# Usage: bash <foreman-skill-dir>/scripts/km-e2e-full-battery.sh
#   PORT env override (default 18999).
# Output: 9 checks (health + 4 GETs w/ body + login 400/401 + 2x 404) + 501-stub scan.
# Proven: Tick 187 (2026-08-04) 9/9 PASS, zero 501 stubs.
B=http://localhost:${PORT:-18999}
pass=0; fail=0
ck() { # ck <desc> <expected_code> <actual_code>
  if [ "$2" = "$3" ]; then pass=$((pass+1)); echo "PASS $1 -> $3"; else fail=$((fail+1)); echo "FAIL $1 -> expected $2 got $3"; fi
}
code=$(curl -s -m 5 -o /tmp/km-e2e-health.json -w "%{http_code}" $B/health)
ck "GET /health" 200 "$code"
echo "  body: $(head -c 200 /tmp/km-e2e-health.json)"
for ep in benchmarks episodes leaderboard scenarios; do
  code=$(curl -s -m 5 -o /tmp/km-e2e-$ep.json -w "%{http_code}" $B/api/v1/$ep)
  ck "GET /api/v1/$ep" 200 "$code"
  echo "  $ep body: $(head -c 260 /tmp/km-e2e-$ep.json)"
done
# Login probes: handler reads {"username","password"} — empty/{} body -> 400, bad creds -> 401
code=$(curl -s -m 5 -o /tmp/km-e2e-login-empty.json -w "%{http_code}" -X POST -H 'Content-Type: application/json' -d '{}' $B/api/v1/auth/login)
ck "POST /api/v1/auth/login empty" 400 "$code"
code=$(curl -s -m 5 -o /tmp/km-e2e-login-bad.json -w "%{http_code}" -X POST -H 'Content-Type: application/json' -d '{"username":"nobody","password":"wrong"}' $B/api/v1/auth/login)
ck "POST /api/v1/auth/login bad creds" 401 "$code"
code=$(curl -s -m 5 -o /tmp/km-e2e-bm-404.json -w "%{http_code}" $B/api/v1/benchmarks/99999)
ck "GET /api/v1/benchmarks/99999" 404 "$code"
echo "  body: $(head -c 120 /tmp/km-e2e-bm-404.json)"
code=$(curl -s -m 5 -o /tmp/km-e2e-ep-404.json -w "%{http_code}" $B/api/v1/episodes/99999)
ck "GET /api/v1/episodes/99999" 404 "$code"
echo "  body: $(head -c 120 /tmp/km-e2e-ep-404.json)"
stubs=$(grep -l "501" /tmp/km-e2e-*.json 2>/dev/null | wc -l)
echo "501-stub files: $stubs"
echo "RESULT: $pass pass, $fail fail"
# exit 0 only if all checks passed and no stubs
[ "$fail" = "0" ] && [ "$stubs" = "0" ]
