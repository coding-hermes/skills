#!/usr/bin/env python3
"""Zombie "Already Running" Cross-Reference Auditor.

Cross-references agent.log "already running — skipping" messages against
jobs.json state to classify zombies as Class A (stale state, JSON-resettable)
or Class B (hung thread, needs gateway restart).

Usage:
    python3 scripts/zombie-audit-crossref.py [--window-minutes 120] [--class-b-threshold 5]
"""

import json, subprocess, sys, os
from datetime import datetime, timezone, timedelta

JOBS_PATH = os.path.expanduser("~/.hermes/cron/jobs.json")
LOG_PATH = os.path.expanduser("~/.hermes/logs/agent.log")
SCHEDULER_PATH = os.path.expanduser("~/.hermes/hermes-agent/cron/scheduler.py")

WINDOW_MINUTES = 120       # How far back to check for current-window skips
CLASS_B_THRESHOLD = 5      # Skips in window to classify as Class B


def parse_args():
    global WINDOW_MINUTES, CLASS_B_THRESHOLD
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--window-minutes" and i + 1 < len(args):
            WINDOW_MINUTES = int(args[i + 1]); i += 2
        elif args[i] == "--class-b-threshold" and i + 1 < len(args):
            CLASS_B_THRESHOLD = int(args[i + 1]); i += 2
        else:
            i += 1


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def main():
    parse_args()

    # 1. Check whether auto-clear timeout exists in scheduler source
    has_timeout = bool(run(f"grep '_STALE_RUNNING_TIMEOUT' {SCHEDULER_PATH} 2>/dev/null"))

    # 2. Load jobs
    with open(JOBS_PATH) as f:
        data = json.load(f)
    jobs_by_name = {j.get("name", ""): j for j in data["jobs"] if j.get("name")}

    # 3. Total counts from entire log
    total_raw = run(
        f"grep 'already running.*skipping' {LOG_PATH} 2>/dev/null | "
        "sed \"s/.*Job '\\([^']*\\)'.*/\\1/\" | sort | uniq -c | sort -rn"
    )
    totals = {}
    for line in total_raw.split("\n"):
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            totals[parts[1]] = int(parts[0])

    # 4. Current-window counts
    cutoff = (datetime.now() - timedelta(minutes=WINDOW_MINUTES)).strftime("%Y-%m-%d %H:")
    current_raw = run(
        f"grep 'already running.*skipping' {LOG_PATH} 2>/dev/null | "
        f"awk '/{cutoff}/' | "
        "sed \"s/.*Job '\\([^']*\\)'.*/\\1/\" | sort | uniq -c | sort -rn"
    )
    current = {}
    for line in current_raw.split("\n"):
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            current[parts[1]] = int(parts[0])

    # 5. Auto-clear log verification
    auto_clear_tail = run(
        f"grep 'auto-clearing zombie lock' {LOG_PATH} 2>/dev/null | tail -5"
    )

    # 6. Gateway restart check
    last_restart = run(
        f"grep 'Starting Hermes Gateway' {LOG_PATH} 2>/dev/null | tail -3"
    )

    # ── Report ──
    print("=" * 110)
    print("ZOMBIE AUDIT — Cross-Reference Report")
    print("=" * 110)
    print(f"_STALE_RUNNING_TIMEOUT in scheduler source: {'YES ✅' if has_timeout else 'NO ❌ — Class B recovery needs gateway restart'}")
    print(f"Window: last {WINDOW_MINUTES} minutes | Class B threshold: ≥{CLASS_B_THRESHOLD} skips")
    print(f"Last gateway start:\n{last_restart}")
    print(f"Last auto-clears (timeout working?):\n{auto_clear_tail or 'NONE — timeout has never fired in this log window'}")
    print()

    header = f"{'JOB NAME':<40} {'TOTAL':>5} {'WIN':>5} {'STATE':>11} {'ENAB':>5} {'PROVIDER':<22} {'MODEL':<20} {'LAST_RUN':<20} {'CLASS'}"
    print(header)
    print("-" * 145)

    class_b, class_a, low = [], [], []

    for name in sorted(totals, key=lambda n: totals.get(n, 0), reverse=True):
        job = jobs_by_name.get(name)
        cw = current.get(name, 0)
        if not job:
            print(f"{name:<40} {totals[name]:>5} {cw:>5} {'NOT IN JSON':>11}")
            continue

        state = job.get("state", "?")
        enabled = "T" if job.get("enabled") else "F"
        provider = job.get("provider", "") or "default"
        model = job.get("model", "") or "default"
        last_run = (job.get("last_run_at", "") or "")[:19]

        if cw >= CLASS_B_THRESHOLD:
            klass = "🔥 CLASS B (hung)"
            class_b.append(name)
        elif cw >= 3:
            klass = "🟡 CLASS A? (stale)"
            class_a.append(name)
        else:
            klass = "🟢 LOW"
            low.append(name)

        print(f"{name:<40} {totals[name]:>5} {cw:>5} {state:>11} {enabled:>5} "
              f"{provider:<22} {model:<20} {last_run:<20} {klass}")

    # Summary
    print(f"\n{'=' * 110}")
    print(f"SUMMARY: {len(class_b)} CLASS B, {len(class_a)} CLASS A, {len(low)} LOW")
    print(f"{'=' * 110}")

    if class_b:
        print(f"\n🔥 CLASS B — Hung threads (need gateway restart):")
        providers = set()
        for n in class_b:
            j = jobs_by_name.get(n, {})
            p = j.get("provider", "") or "default"
            providers.add(p)
            print(f"   {n}  provider={p}  last_run={str(j.get('last_run_at','?'))[:19]}")
        print(f"   Common providers: {providers}")
        if "custom:opencode-go" in providers:
            print(f"   ⚠️ opencode-go is overrepresented — check for provider 502/503")

    if class_a:
        print(f"\n🟡 CLASS A — Stale state (JSON reset may work):")
        for n in class_a:
            j = jobs_by_name.get(n, {})
            print(f"   {n}  state={j.get('state','?')}  provider={j.get('provider','') or 'default'}")

    if not has_timeout and class_b:
        print(f"\n⛔ NO auto-clear timeout deployed. {len(class_b)} Class B jobs "
              f"will remain perpetually locked until 'hermes gateway restart'.")


if __name__ == "__main__":
    main()
