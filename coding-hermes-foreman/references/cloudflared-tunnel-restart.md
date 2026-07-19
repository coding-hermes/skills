# Cloudflare Quick Tunnel Restart — Operational Pattern

When a foreman tick discovers tunnels are DOWN (HTTP 000, connection refused, NXDOMAIN),
follow this exact restart sequence. Skipping steps causes duplicate processes, port conflicts,
and DNS failures.

## Detection

```bash
# Check current tunnels (from board or user)
curl -s -o /dev/null -w "%{http_code}" https://<hostname>.trycloudflare.com
# 000 = DOWN (connection failed or DNS NXDOMAIN)

# Check if cloudflared processes are still running
ps aux | grep "cloudflared.*tunnel" | grep -v grep
```

## Restart Sequence

### 1. Kill ALL existing cloudflared processes

```bash
# Kill user-level processes by PID
kill <pid1> <pid2> ... 2>/dev/null
sleep 2

# Verify dead
ps aux | grep "cloudflared.*tunnel" | grep -v grep || echo "All dead"
```

**Pitfall:** Starting a new cloudflared BEFORE killing the old one creates two processes
fighting for the same port. Both appear in `ps aux`, both claim the tunnel URL, but the
old one may hold the port while the new one gets a different hostname that doesn't resolve.
Always kill first.

**Docker container variant:** Cloudflared inside a Docker container runs as a different UID
(e.g., 65532). `kill <pid>` may fail with "Operation not permitted" if the process belongs
to the container's user namespace. If the container is no longer needed, use Docker commands
(`docker stop <container>`) — but in cron contexts this may be blocked by CLI approval filters.

### 2. Start fresh with nohup (NOT bare `&`)

```bash
nohup cloudflared tunnel --url http://localhost:<port> --no-autoupdate > /tmp/cloudflared-<name>.log 2>&1 &
echo "PID: $!"
```

**CRITICAL: never use bare `&` in a terminal() call.** When the shell proc exits, SIGHUP kills
the cloudflared child. The tunnel appears to start (precheck output shows in logs) but dies
before the URL can be used. Always wrap with `nohup` and redirect stdout/stderr to a log file.

**Cron context variant — `terminal(background=true)` is preferred over `nohup &`.** In cron
sessions, the Hermes `terminal(background=true)` provides process tracking and output capture
without needing `nohup` or `&`. Use the `tee` pattern to capture tunnel URLs to a file:

```bash
cloudflared tunnel --url http://localhost:<port> 2>&1 | tee /tmp/cloudflared-<name>.log
```

Then extract the URL from the log file:
```bash
grep "trycloudflare.com" /tmp/cloudflared-<name>.log | tail -1
```

**Tunnel registration timing:** The first `trycloudflare.com` URL line typically appears
within 3-8 seconds of the "Requesting new quick Tunnel" message. If no URL appears after
30 seconds, the registration is stuck (possible causes: named-tunnel cloudflared still
running on the host, QUIC connectivity failure with fallback hang, Cloudflare API rate
limit). Kill and retry.

### 3. Wait for URL in logs

```bash
sleep 8  # Cloudflare Quick Tunnel registration takes 5-10 seconds
grep "trycloudflare.com" /tmp/cloudflared-<name>.log | tail -2
```

The URL line looks like:
```
2026-07-15T14:30:35Z INF |  https://<random-words>.trycloudflare.com                             |
```

### 4. Verify the tunnel works

```bash
# Basic connectivity
curl -s -o /dev/null -w "HTTP %{http_code}" https://<hostname>.trycloudflare.com

# For API tunnels: verify /health endpoint
curl -s https://<hostname>.trycloudflare.com/health

# For web tunnels: verify page loads
curl -s -o /dev/null -w "HTTP %{http_code}" https://<hostname>.trycloudflare.com/
```

**DNS propagation pitfall:** The new hostname may return NXDOMAIN for 5-10 seconds after
cloudflared registers it. This is normal — TryCloudflare DNS records propagate asynchronously.
Wait 5 more seconds and retry before declaring failure.

### 5. Verify login through tunnel (if applicable)

```bash
curl -s -X POST https://<api-tunnel>/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<demo-user>","password":"<demo-pass>"}'
```

A valid JWT in the response confirms the tunnel → API → PostgreSQL path is fully functional.

### 6. Update the board

Replace all stale tunnel URLs on the board with the new hostnames. Update the live state
section AND any completed TUNNEL task entries.

## Proven Instances

| Project | Date | Task | Old → New |
|---------|------|------|-----------|
| EduOS | 2026-07-15 | TUNNEL-005 | 4 stale URLs → coverage-folding-recipes-attract (web), pricing-other-extended-scripting (api) |
| EduOS | 2026-07-16 | TUNNEL-012 | All containers Exited(255) + stale URLs → conjunction-sender-gained-searching (web), intelligence-deployment-listening-trader (api). Required Docker API restart first, then tunnel recreation. |
| EduOS | 2026-07-14 | TUNNEL-004 | stayed-vacuum-remark-roommates (web), rankings-minnesota-manually-faces (api) |
| EduOS | 2026-07-17 | TUNNEL-013 | uniprotkb-charge-differential-constitutes (web), subscribers-combination-counted-could (api) |
| EduOS | 2026-07-12 | TUNNEL-003 | lands-salon-reef-advert (web), undefined-vitamin-autumn-impose (api) |
| EduOS | 2026-07-07 | TUNNEL-002 | remote-ratings-bedford-riding (web), fri-highlighted-upper-mechanical (api) |
| EduOS | 2026-07-07 | TUNNEL-001 | role-cartridges-portraits-rugby (web), retail-shake-assured-joe (api) |

**Recurrence:** Tunnels expire roughly every 1-3 days (TUNNEL-008 through TUNNEL-013 were within 48 hours). This is normal TryCloudflare behavior — Quick Tunnels are ephemeral by design. A permanent tunnel solution (named tunnel with CNAME) would eliminate this recurring operational task. This is normal TryCloudflare behavior —
Quick Tunnels are ephemeral by design. A permanent tunnel solution (named tunnel with CNAME)
would eliminate this recurring operational task.
