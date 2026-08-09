#!/bin/bash
# Scheduler daemon watchdog — checks if schedulerd is alive, restarts if dead
# Runs every 2 minutes via cron (no_agent: true)
#
# The daemon is systemd-managed (user unit) — restart via systemctl, NEVER
# pkill+manual launch: pkill triggers systemd's auto-respawn with the unit's
# flags and the manual launch loses the port race (h3 re-drift incident,
# 2026-08-07: unit ran --max-concurrent 6 while scripts said 4).

HEALTH_URL="http://127.0.0.1:9090/api/v1/projects"

# Check if schedulerd is running and responding
if curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null | grep -q "200"; then
    # Alive — verify projects loaded
    count=$(curl -s "$HEALTH_URL" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('projects',[])))" 2>/dev/null)
    if [ "$count" = "0" ]; then
        echo "WARNING: Scheduler alive but 0 projects loaded (wrong DB path?) at $(date)"
        exit 1
    fi
    exit 0
fi

# Dead — restart via systemd (unit rebuilds the binary via ExecStartPre)
echo "Scheduler dead at $(date), restarting via systemd..."
systemctl --user restart coding-hermes-scheduler
sleep 5

# Verify restart
if curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null | grep -q "200"; then
    echo "Scheduler restarted successfully at $(date)"
    exit 0
else
    echo "FAILED: Scheduler did not come back up at $(date)"
    exit 1
fi
