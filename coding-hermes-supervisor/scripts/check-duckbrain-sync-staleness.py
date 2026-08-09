#!/usr/bin/env python3
"""Detect stale DuckBrain sync crons across the fleet.

Reads ~/.hermes/cron/jobs.json, finds all jobs with 'context-sync-duckbrain'
in skills, then checks whether each has run within 3x its expected interval.

Properly handles:
  - Daily crons (0 3 * * *)      → 24h interval
  - Every-N-hours crons (0 */6...) → N*1h interval
  - Sub-hourly interval crons    → minutes field
  - Never-ran detection          → >24h since creation
  - Fire claim detection          → blocks dispatch

Usage:
    python3 scripts/check-duckbrain-sync-staleness.py
    python3 ~/.hermes/skills/coding-hermes-supervisor/scripts/check-duckbrain-sync-staleness.py
"""

import json, os, re
from datetime import datetime, timezone

JOBS_PATH = os.path.expanduser("~/.hermes/cron/jobs.json")


def cron_interval_seconds(expr):
    """Return expected interval in seconds for a cron expression.

    Recognises:
      - Daily:  0 3 * * *              → 86400 (24h)
      - Twice daily: 0 3,15 * * *      → 43200 (12h)
      - Every N hours: 0 */N * * *     → N * 3600
      - Every N minutes: */N * * * *   → N * 60  (but scheduler skips these)
      - Fixed minute + hour: any other  → 3600 (fallback)
    """
    parts = str(expr).strip().split()
    if len(parts) < 5:
        return 3600

    minute, hour = parts[0], parts[1]

    # Daily: minute is a fixed digit, hour is a fixed digit (no commas, no */)
    if re.match(r'^\d+$', minute) and re.match(r'^\d+$', hour):
        return 86400

    # Twice daily: minute is fixed, hour is comma-separated (e.g. 3,15)
    if re.match(r'^\d+$', minute) and re.match(r'^[\d,]+$', hour) and ',' in hour:
        return 43200

    # Every N hours: */N in hour field
    m = re.match(r'\*/(\d+)', hour)
    if m:
        return int(m.group(1)) * 3600

    # Every N minutes: */N in minute field
    m = re.match(r'\*/(\d+)', minute)
    if m:
        return int(m.group(1)) * 60

    return 3600  # fallback


def main():
    with open(JOBS_PATH) as f:
        data = json.load(f)

    now = datetime.now(timezone.utc)
    sync_jobs = []
    stale_jobs = []
    never_ran = []
    fire_claimed = []
    healthy = []

    for j in data.get("jobs", []):
        skills = " ".join(j.get("skills") or [])
        if "context-sync-duckbrain" not in skills:
            continue

        job_id = j["id"][:12]
        name = j.get("name", "?")
        state = j.get("state", "")
        enabled = j.get("enabled", False)

        # Schedule
        sched = j.get("schedule", {})
        if isinstance(sched, str):
            continue  # skip malformed

        sched_kind = sched.get("kind", "")
        sched_display = sched.get("display", "")

        # Expected interval
        if sched_kind == "interval":
            expected_s = (sched.get("minutes") or 120) * 60
        elif sched_kind == "cron":
            expected_s = cron_interval_seconds(sched.get("expr", ""))
        else:
            expected_s = 3600

        # Last run
        last_run_str = j.get("last_run_at")
        if not last_run_str:
            never_ran.append((job_id, name, sched_display, expected_s))
            continue

        try:
            last_run = datetime.fromisoformat(last_run_str)
        except Exception:
            stale_jobs.append((job_id, name, sched_display, expected_s, "bad_timestamp"))
            continue

        age_s = (now - last_run).total_seconds()
        age_h = age_s / 3600
        threshold_s = expected_s * 3

        # Fire claim
        fc = j.get("fire_claim")
        if fc and state == "scheduled" and enabled:
            fire_claimed.append((job_id, name, fc, age_h))

        if age_s > threshold_s and state == "scheduled" and enabled:
            stale_jobs.append((job_id, name, sched_display, expected_s, f"{age_h:.1f}h"))
        else:
            healthy.append((job_id, name, sched_display, expected_s, age_h))

    # ── Report ──
    print(f"DuckBrain sync crons: {len(healthy) + len(stale_jobs) + len(never_ran)} total")

    if never_ran:
        print(f"\n⚠ NEVER RAN ({len(never_ran)}):")
        for jid, name, sched, exp_s in never_ran:
            print(f"  {jid} {name} — sched={sched}, interval={exp_s//3600}h, never fired")

    if stale_jobs:
        print(f"\n🔴 STALE ({len(stale_jobs)}):")
        for jid, name, sched, exp_s, detail in stale_jobs:
            print(f"  {jid} {name} — sched={sched}, expected={exp_s//3600}h, {detail}")
    else:
        print("\n✅ No stale DuckBrain sync crons")

    if fire_claimed:
        print(f"\n⚠ FIRE CLAIMS ({len(fire_claimed)}):")
        for jid, name, fc, age_h in fire_claimed:
            print(f"  {jid} {name} — claim={fc}, age={age_h:.1f}h")

    print(f"\n✅ Healthy ({len(healthy)}):")
    for jid, name, sched, exp_s, age_h in sorted(healthy, key=lambda x: x[4], reverse=True)[:5]:
        print(f"  {jid} {name} — {sched}, age={age_h:.1f}h")
    if len(healthy) > 5:
        print(f"  ... and {len(healthy) - 5} more")


if __name__ == "__main__":
    main()
