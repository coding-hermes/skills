# Off-by-One Live Service Verification

## The "Health Is a Liar" Problem

`GET /health → {"status":"ok"}` only proves the HTTP server is accepting connections on the port. It does NOT verify the solver cron loop is running. The solver is only initialized when ALL three flags are present:

```
-bwrap /usr/bin/bwrap
-pi-agent /home/kara/.local/bin/pi-agent
-cron-interval 60s (or any non-zero interval)
-load-threshold -1 (or any non-zero threshold)
```

Without these, the server starts and serves endpoints but silently:
- Logs: `cron loop not started (no solver)`
- All submissions fail with exit status or connection errors
- Health still returns `{"status":"ok"}`

## Correct Systemd Service

```ini
[Unit]
Description=Off-by-One pre-solve daemon
After=network.target

[Service]
Type=simple
User=kara
Group=kara
EnvironmentFile=/home/kara/off-by-one/.env
ExecStart=/home/kara/off-by-one/off-by-one \
  --port 8766 \
  -load-threshold -1 \
  -cron-interval 60s \
  -pi-agent /home/kara/.local/bin/pi-agent \
  -bwrap /usr/bin/bwrap
WorkingDirectory=/home/kara/off-by-one
Environment="PATH=/home/kara/.local/bin:/usr/local/bin:/usr/bin:/bin"
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Critical Gotchas

| Gotcha | Why It Happens | Fix |
|--------|---------------|-----|
| **Solver dead, health OK** | Missing `--bwrap`, `--pi-agent`, or `--cron-interval` flags | Add all flags to ExecStart |
| **bwrap permission denied** | Service running as root, can't access `/home/kara/.local/bin` | Add `User=kara` to [Service] |
| **DeepSeek 401 auth error** | Stale API key hardcoded in service file | Use `EnvironmentFile=/home/kara/off-by-one/.env` instead |
| **Systemd restarts silently** | `Restart=always` means bad flags cause crash loop | Check `journalctl -u off-by-one` for the error before restart count |

## Live Verification Checklist

After starting/restarting the service:

```bash
# 1. Check health (should be "ok")
curl -s http://localhost:8766/health

# 2. Check stats (should be non-empty)
curl -s http://localhost:8766/api/v1/stats

# 3. Submit a shell problem (fastest solve type)
curl -s -X POST http://localhost:8766/api/v1/problems/submit \
  -H 'Content-Type: application/json' \
  -d '{"problem_class":"shell-echo-hello","cadence":"post-debug",
       "description":"Print hello world","language":"shell","environment":"bash"}'

# 4. Wait 90s then verify it solved
sleep 90
curl -s http://localhost:8766/api/v1/queue | grep '"status":"complete"'

# 5. Discover the solution
curl -s -X POST http://localhost:8766/api/v1/problems/discover \
  -H 'Content-Type: application/json' \
  -d '{"problem_class":"shell-echo-hello"}'
```

**Session evidence (2026-07-19):** Off-by-One ran as a systemd service for 69+ hours with bare `--port 8766`. Health endpoint returned `{"status":"ok"}` but the cron loop was dead — 18 problems accumulated in the queue, 0 solved. Root cause: systemd ExecStart had no solver flags. Fixed by adding User=kara, EnvironmentFile, and full flags. Solved in 60s after restart.
