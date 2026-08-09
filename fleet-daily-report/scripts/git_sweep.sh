#!/usr/bin/env bash
# Light-cache day git sweep for the fleet daily report.
# One pass over every ENABLED project workdir from the scheduler API JSON:
#   - last commit (date + subject)
#   - commit count since midnight (proves foreman liveness; scheduler UpdatedAt lies)
# Usage:
#   curl -s http://127.0.0.1:9090/api/v1/projects -o /tmp/fleet_projects.json
#   bash scripts/git_sweep.sh [/tmp/fleet_projects.json]
# Writes /tmp/fleet_sweep.txt (also echoes to stdout). Safe under cron mode
# (plain bash + jq + git — no python3 -c, which needs interactive approval).
set -u
JSON="${1:-/tmp/fleet_projects.json}"
TODAY="${FLEET_TODAY:-$(date +%F)}"
OUT=/tmp/fleet_sweep.txt
: > "$OUT"

if [ ! -f "$JSON" ]; then
  echo "No scheduler JSON at $JSON — fetch it first:"
  echo "  curl -s http://127.0.0.1:9090/api/v1/projects -o $JSON"
  exit 1
fi

# Live API (2026-08) returns snake_case fields (enabled/workdir); older Go-style
# (Enabled/Workdir) also supported. `//=` coalesce handles both.
jq -r '.projects[] | select((.Enabled // .enabled)==true) | (.Workdir // .workdir)' "$JSON" | sort -u | while read -r wd; do
  if [ -d "$wd/.git" ]; then
    last=$(git -C "$wd" log -1 --format='%ad %s' --date=format:'%m-%d %H:%M' 2>/dev/null)
    todaycount=$(git -C "$wd" log --since="${TODAY} 00:00" --format='%h' 2>/dev/null | wc -l)
    printf '=== %s | today=%s | last: %s\n' "$wd" "$todaycount" "$last" | tee -a "$OUT"
  else
    printf '=== %s | NO GIT\n' "$wd" | tee -a "$OUT"
  fi
done

echo "--- sweep written to $OUT"
echo "--- follow-up: for any workdir with today=N, run:"
echo "    git -C <workdir> log --since='${TODAY} 00:00' --format='%h %ad %s' --date=format:'%H:%M' | head -8"
