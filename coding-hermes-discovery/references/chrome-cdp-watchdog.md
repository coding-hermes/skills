# Chrome CDP Watchdog Pattern

## Problem

Headless Chrome for E2E browser testing crashes silently. The foreman detects "Chrome DOWN" every tick, writes it in the report, and moves on. After 11+ consecutive ticks, the user asks: "why dont you fix the connection from chrome devtools insteed of comaplining about it."

The foreman's discovery sweep should fix operational issues, not just report them.

## Solution

A `no_agent` cron job that keeps Chrome alive independently. Silent when healthy, reports only when Chrome was dead and needed restart.

### Watchdog Script (`ensure-chrome-cdp.sh`)

```bash
#!/bin/bash
# ensure-chrome-cdp.sh — keep Chrome headless CDP alive on :9223
# no_agent cron runs every 5min — silent when healthy

CDP_PORT=9223
LOG=/tmp/chrome-${CDP_PORT}.log
PROFILE=/tmp/hermes-chrome-profile-stable

# Check if Chrome is already running and responding
if curl -s http://localhost:${CDP_PORT}/json/version > /dev/null 2>&1; then
    exit 0  # Chrome is healthy — silent, nothing to report
fi

echo "[$(date -Iseconds)] Chrome CDP :${CDP_PORT} DOWN — restarting"

# Kill any stale process
pkill -f "chrome.*${CDP_PORT}" 2>/dev/null
sleep 2

# Clean corrupted profile
rm -rf "${PROFILE}" 2>/dev/null
mkdir -p "${PROFILE}"

# Start Chrome headless with correct flags for kernel 7.0+
google-chrome \
  --headless \
  --no-sandbox \
  --disable-gpu \
  --disable-software-rasterizer \
  --disable-dev-shm-usage \
  --no-first-run \
  --no-default-browser-check \
  --no-pings \
  --window-size=1280,720 \
  --remote-debugging-port=${CDP_PORT} \
  --user-data-dir=${PROFILE} \
  --disable-extensions \
  --disable-component-update \
  --disable-features=TranslateUI,BlinkGenPropertyTrees \
  --enable-features=NetworkService,NetworkServiceInProcess \
  > "${LOG}" 2>&1 &

sleep 4

# Verify
VERSION=$(curl -s http://localhost:${CDP_PORT}/json/version | grep -o '"Browser":"[^"]*"')
if [ -n "$VERSION" ]; then
    echo "[$(date -Iseconds)] Chrome CDP :${CDP_PORT} RESTARTED OK — ${VERSION}"
else
    echo "[$(date -Iseconds)] Chrome CDP :${CDP_PORT} FAILED to restart"
    exit 1
fi
```

### Cron Setup

```bash
cronjob(action='create',
  name='<Project> Chrome CDP Watchdog (:9223)',
  schedule='*/5 * * * *',
  script='ensure-chrome-cdp.sh',
  no_agent=True,
  deliver='<chat-target>')
```

### Key Properties

- **`no_agent=True`**: No LLM tokens burned. The script IS the job.
- **Silent when healthy**: Zero cron notifications 99% of the time. The script exits 0 without output.
- **Reports only on restart**: The user gets a message ONLY when Chrome was down and had to be restarted.
- **`*/5 * * * *`**: Checks every 5 minutes. Fast enough to catch crashes before the E2E cron runs.
- **Clean profile each time**: Corrupted profiles cause Chrome to crash-loop. Wiping on restart prevents that.

### Foreman Integration

In the foreman's self-heal step (Step 0), run the script to verify Chrome is alive. Don't write "Chrome DOWN" in tick reports — fix it.

```bash
bash .coding-hermes/scripts/ensure-chrome-cdp.sh
```

### Chrome 149 Flag Notes

Chrome 149 on kernel 7.0.0-27 requires explicit flags:

| Flag | Why |
|------|-----|
| `--no-sandbox` | Container/host environments without namespaces |
| `--disable-gpu` | No display server in headless mode |
| `--disable-software-rasterizer` | Prevents segfault on `--screenshot` |
| `--disable-dev-shm-usage` | `/dev/shm` too small on many hosts |
| `--disable-features=TranslateUI` | Prevents network calls to Google |

Without `--disable-software-rasterizer`, `--screenshot` segfaults. Without `--disable-gpu`, Chrome may hang on GPU initialization. Both are required for stable headless on server hosts.

**Proven:** <project> 2026-07-24 — 11 consecutive "Chrome DOWN" foreman reports fixed by watchdog cron. User directive: "why dont you fix the connection from chrome devtools insteed of comaplining about it."
