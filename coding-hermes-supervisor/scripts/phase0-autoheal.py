#!/usr/bin/env python3
"""Phase 0 Auto-Heal: Schema fixes, state recovery, pinned-project drift, force-fire overdue jobs.

Run this FIRST in every supervisor tick, before any audit. All fixes are safe and deterministic.
Does NOT change schedules (speed) — that's Phase 2D's job.

Usage: python3 scripts/phase0-autoheal.py
"""
import json, os, time, re, socket

JOBS_PATH = os.path.expanduser("~/.hermes/cron/jobs.json")

with open(JOBS_PATH) as f:
    data = json.load(f)

jobs = data["jobs"]
now = time.time()
changes = []

# Pinned projects — NEVER change model/provider
# WARNING: Policy is uniform enforcement. Foremen ALWAYS get deepseek-v4-flash/deepseek-foreman.
# This dict MUST stay EMPTY. Any entry here reverts a foreman to a non-compliant provider.
# See skill pitfalls: "stale pinned table reverts models"
# Stale entries REMOVED 2026-07-13: bunker (kimi-for-coding), speclang-ci (MiniMax-M3),
#   mythos (grok-4.5/xai-oauth), helix (grok-4.5/xai-oauth) — all now on PAYG.
PINNED = {}

# Check if coding-herms-scheduler daemon is active (port :9090)
# When active, foremen are managed by the daemon — don't unpause them in 0B.
SCHEDULER_DAEMON_ACTIVE = False
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    SCHEDULER_DAEMON_ACTIVE = sock.connect_ex(('127.0.0.1', 9090)) == 0
    sock.close()
except Exception:
    pass

def parse_iso(ts):
    if not ts:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(ts).timestamp()
    except:
        return None

for job in jobs:
    name = job.get("name", job.get("id", "unknown"))
    skills = job.get("skills") or []
    # Narrower checks: only foremen for model/state ops, all CH crons for schema
    is_ch_foreman = any("coding-hermes-foreman" in s for s in skills)
    is_ch_supervisor = any("coding-hermes-supervisor" in s for s in skills)
    is_ch_cron = any("coding-hermes-cron" in s for s in skills)
    is_ch = is_ch_foreman or is_ch_supervisor or is_ch_cron
    changed = False
    schedule = job.get("schedule", {})
    kind = schedule.get("kind", "")
    display = schedule.get("display", "")

    # 0A. Schedule Schema Auto-Fix
    if kind == "every":
        m = re.search(r'(\d+)m', display)
        minutes = int(m.group(1)) if m else 120
        schedule["kind"] = "interval"
        schedule["minutes"] = minutes
        schedule["display"] = f"every {minutes}m"
        changed = True
        changes.append(f"0A: {name} — fixed kind=every → interval({minutes}m)")
    
    if kind == "cron" and "expr" not in schedule:
        schedule["expr"] = display
        changed = True
        changes.append(f"0A: {name} — added missing schedule.expr = '{display}'")
    
    if kind == "interval" and "minutes" not in schedule:
        m = re.search(r'(\d+)m', display)
        minutes = int(m.group(1)) if m else 120
        schedule["minutes"] = minutes
        changed = True
        changes.append(f"0A: {name} — added missing schedule.minutes = {minutes}")
    
    top_display = job.get("schedule_display", "")
    nested_display = schedule.get("display", "")
    if top_display and nested_display and top_display != nested_display:
        job["schedule_display"] = nested_display
        changed = True
        changes.append(f"0A: {name} — synced schedule_display")

    # 0B. Stale State Auto-Fix
    state = job.get("state", "")
    enabled = job.get("enabled", False)
    
    if state == "completed" and enabled:
        job["state"] = "scheduled"
        job.pop("paused_at", None)
        job.pop("paused_reason", None)
        changed = True
        changes.append(f"0B: {name} — state=completed+enabled → scheduled")
    
    if state == "paused" and not job.get("paused_reason"):
        # Scheduler daemon guard: don't unpause foremen if daemon is active
        if is_ch_foreman and SCHEDULER_DAEMON_ACTIVE:
            # Scheduler daemon manages these foremen — skip unpausing
            changes.append(f"0B-SKIP: {name} — foreman paused w/o reason, daemon active, kept paused")
        else:
            job["state"] = "scheduled"
            job["enabled"] = True
            changed = True
            changes.append(f"0B: {name} — state=paused w/o reason → scheduled")

    # 0G. Foreman Model Drift Auto-Fix (foremen ONLY — skip supervisor + non-foreman crons)
    # Bane directive 2026-07-24: ALL foremen use deepseek-v4-flash regardless of schedule.
    # No active/idle model split. Must match enforce-foreman-models.py logic.
    if is_ch_foreman and name not in PINNED:
        model = job.get("model")
        provider = job.get("provider")
        if model != "deepseek-v4-flash":
            job["model"] = "deepseek-v4-flash"
            job["provider"] = "deepseek-foreman"
            changed = True
            changes.append(f"0G: {name} — model drift {model} → deepseek-v4-flash (Bane 2026-07-24)")
        elif provider not in ("deepseek-foreman", "deepseek"):
            job["provider"] = "deepseek-foreman"
            changed = True
            changes.append(f"0G: {name} — provider drift {provider} → deepseek-foreman")

    # 0G-POST. Safety net — catches any v4-pro that 0G somehow missed or was
    # set by a previous script version. Should never fire after 0G fix above.
    # Keep as defense-in-depth. Known pre-Bane-directive foremen: none remaining.
    if is_ch_foreman and name not in PINNED:
        model = job.get("model")
        if model == "deepseek-v4-pro":
            job["model"] = "deepseek-v4-flash"
            changed = True
            changes.append(f"0G-POST: {name} — v4-pro → v4-flash (safety net)")
    
    # Fix pinned projects
    if name in PINNED:
        expected = PINNED[name]
        if job.get("model") != expected["model"] or job.get("provider") != expected["provider"]:
            changes.append(f"0G-PIN: {name} — FIXING drift {job.get('model')}/{job.get('provider')} → {expected['model']}/{expected['provider']}")
            job["model"] = expected["model"]
            job["provider"] = expected["provider"]
            changed = True

    # 0C-FIX. Fix repeat=1 on new foremen (polymorphic guard: repeat can be int or dict)
    if is_ch_foreman:
        repeat = job.get("repeat")
        times_val = None
        if isinstance(repeat, dict):
            times_val = repeat.get("times")
        elif isinstance(repeat, int):
            times_val = repeat
        if times_val == 1 or times_val is None:
            job["repeat"] = {"times": 2147483647, "completed": 0}
            changed = True
            changes.append(f"0C-FIX: {name} — repeat={times_val} → infinite")

    # 0A-POST. Force Overdue Jobs (only for CH foremen, not paused)
    def parse_cron_interval(expr):
        """Parse cron expression and return expected seconds. Fixes */N in hour field."""
        parts = str(expr).split()
        if len(parts) >= 5:
            minute, hour = parts[0], parts[1]
            m = re.match(r'\*/(\d+)', minute)
            if m:
                return int(m.group(1)) * 60
            m = re.match(r'\*/(\d+)', hour)
            if m:
                return int(m.group(1)) * 3600
        return 3600

    last_run = parse_iso(job.get("last_run_at"))
    expected_sec = 3600
    if kind == "cron":
        expected_sec = parse_cron_interval(schedule.get("expr", ""))
    elif kind == "interval":
        expected_sec = schedule.get("minutes", 120) * 60
    elif kind == "every":
        expected_sec = schedule.get("minutes", 120) * 60
    
    if enabled and state == "scheduled" and is_ch_foreman and not job.get("paused_reason"):
        if last_run is None or (now - last_run) > (2 * expected_sec):
            job["next_run_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now - 300))
            staleness = int((now - (last_run or 0)) / 3600) if last_run else 999
            changed = True
            changes.append(f"0A-POST: {name} — {staleness}h stale (intv={expected_sec//60}m), force-fire")

if changes:
    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Applied {len(changes)} fixes:")
    for c in changes:
        print(f"  {c}")
else:
    print("No changes needed.")
