#!/usr/bin/env bash
# Fair-window gate runner for perf-gated E2E suites under fleet contention.
#
# Polls host load until TWO consecutive samples (~25s apart) are below the
# threshold, then runs the given command IN THE SAME CALL (no round-trip gap
# for a wave to start between check and run).
#
# Proven ring-runner tick 101: a single-sample check (7.45/16) raced a fleet
# wave (gitleaks full-tree scan 670% CPU + cppcheck + gitreins judges; load
# peaked 28.53/16 mid-run) and the perf smoke failed 11/12. The double-sample
# + same-call pattern passed 12/12 at the solo baseline (p95 16.80ms) while
# the wave still churned around it.
#
# Usage: fair-window-run.sh <threshold> [--] <command...>
#   fair-window-run.sh 8.5 npx playwright test
#   fair-window-run.sh 8.5 -- npm run e2e
set -u

THRESHOLD="${1:?usage: fair-window-run.sh <threshold> [--] <command...>}"
shift
[ "${1:-}" = "--" ] && shift
if [ $# -eq 0 ]; then echo "no command given" >&2; exit 2; fi

for i in $(seq 1 30); do
  L=$(cut -d' ' -f1 /proc/loadavg)
  echo "$(date +%H:%M:%S) load=$L (threshold $THRESHOLD)"
  if [ "$(echo "$L < $THRESHOLD" | bc)" = "1" ]; then
    sleep 25
    L2=$(cut -d' ' -f1 /proc/loadavg)
    echo "$(date +%H:%M:%S) confirm=$L2"
    if [ "$(echo "$L2 < $THRESHOLD" | bc)" = "1" ]; then
      echo "SUSTAINED FAIR WINDOW — running: $*"
      exec "$@"
    fi
  fi
  sleep 25
done
echo "NO FAIR WINDOW in budget (30 polls, ~25 min)" >&2
exit 3
