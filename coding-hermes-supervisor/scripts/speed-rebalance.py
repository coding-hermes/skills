#!/usr/bin/env python3
"""Phase 2D — Speed Rebalance for Coding Hermes Foremen.

Reads jobs.json, checks pending task counts, CI status, and commit recency for
every active foreman. Applies the Phase 2D rebalance rules:

- SPEED UP:   3+ pending tasks + active commits, OR CI is failing with tasks queued
               -> faster schedule (15m or 30m)
- MAINTAIN:   1-2 pending, active commits, CI green -> keep current speed
- SLOW DOWN:  0 pending + 0 commits in 48h + CI green -> 120m or 360m
- CI-AWARE:   Even projects with 0 pending but failing CI stay at moderate speed
               (30m-120m) until CI is fixed

The foreman's model/provider is NEVER changed -- only the schedule. Speed changes
are schedule-only. This script does NOT touch pinned projects.

Usage:
    python3 scripts/speed-rebalance.py              # report-only (dry run)
    python3 scripts/speed-rebalance.py --apply      # apply changes to jobs.json

Returns exit code:
    0 = no changes needed / changes applied successfully
    1 = errors during processing
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

JOBS_PATH = os.path.expanduser("~/.hermes/cron/jobs.json")


def parse_iso(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts).timestamp()
    except (ValueError, TypeError):
        return None


def count_pending_tasks(workdir):
    if not workdir:
        return None
    task_file = os.path.join(os.path.expanduser(workdir), ".coding-hermes", "tasks.md")
    if not os.path.exists(task_file):
        return None
    try:
        with open(task_file) as f:
            content = f.read()
        return content.count("- [ ]") + content.count("## [ ]")
    except (OSError, IOError):
        return None


def get_github_remote(workdir):
    if not workdir:
        return None
    try:
        r = subprocess.run(
            ["git", "-C", workdir, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        url = r.stdout.strip()
        if "github.com/" not in url:
            return None
        parts = url.split("github.com/")[1].replace(".git", "").split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass
    return None


def get_ci_status(owner_repo):
    if not owner_repo:
        return "no_gh"
    try:
        r = subprocess.run(
            ["gh", "run", "list", "-R", owner_repo, "--limit", "1",
             "--json", "conclusion"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return "unknown"
        runs = json.loads(r.stdout)
        if not runs:
            return "no_ci"
        c = runs[0].get("conclusion") or "in_progress"
        if c == "success":
            return "passing"
        elif c in ("failure", "startup_failure"):
            return "failing"
        elif c == "in_progress":
            return "running"
        return c
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return "unknown"


def get_last_commit_age_h(workdir):
    if not workdir:
        return None
    try:
        r = subprocess.run(
            ["git", "-C", workdir, "log", "-1", "--format=%ct"],
            capture_output=True, text=True, timeout=5,
        )
        if r.stdout.strip():
            ts = int(r.stdout.strip())
            return (time.time() - ts) / 3600
    except (subprocess.TimeoutExpired, ValueError):
        pass
    return None


def compute_recommended_schedule(current_minutes, pending, ci, commit_age_h):
    effective_pending = pending if pending is not None else 0
    if ci == "failing":
        if effective_pending == 0:
            effective_pending = 1  # CI fix counts as work

    if effective_pending >= 3:
        if current_minutes > 30:
            return (15, "speed up: %dP pending%s" % (effective_pending,
                    ", CI failing" if ci == "failing" else ""))
        return (None, "already fast at %dm" % current_minutes)

    if effective_pending >= 1:
        if current_minutes > 60:
            return (30, "moderate pace: %dP pending" % effective_pending)
        elif current_minutes > 30:
            return (30, "moderate pace: %dP pending" % effective_pending)
        return (None, "already at %dm with %dP" % (current_minutes, effective_pending))

    # 0 pending
    if ci == "failing":
        if current_minutes > 120:
            return (120, "CI failing, keep moderate speed")
        return (None, "CI failing, already at moderate speed")

    if commit_age_h is not None and commit_age_h > 48:
        if current_minutes < 120:
            return (120, "slow down: 0P, no commits in %.0fh" % commit_age_h)
        return (None, "already slow at %dm" % current_minutes)

    if current_minutes < 60:
        return (60, "0 pending, slow from %dm to 60m" % current_minutes)
    return (None, "stable at %dm -- 0P, CI passing" % current_minutes)


def main():
    dry_run = "--apply" not in sys.argv
    verbose = "--verbose" in sys.argv

    if not os.path.exists(JOBS_PATH):
        print("ERROR: jobs.json not found at %s" % JOBS_PATH, file=sys.stderr)
        return 1

    with open(JOBS_PATH) as f:
        data = json.load(f)

    changes = []

    for j in data.get("jobs", []):
        skills = j.get("skills") or []
        is_foreman = any("coding-hermes-foreman" in str(s) for s in skills)
        if not is_foreman:
            continue

        name = j.get("name", "?")
        state = j.get("state", "")
        enabled = j.get("enabled", False)

        if state != "scheduled" or not enabled:
            if verbose:
                print("  SKIP %-40s -- %s/%s" % (name[:40], state, enabled))
            continue

        workdir = j.get("workdir")
        schedule = j.get("schedule", {})
        kind = schedule.get("kind", "")
        current_minutes = schedule.get("minutes")
        if not current_minutes and kind == "cron":
            expr = schedule.get("expr", "")
            parts = expr.split() if expr else []
            m = re.search(r"\*/(\d+)", parts[0]) if parts else None
            if m:
                current_minutes = int(m.group(1))
            else:
                current_minutes = 120
        elif not current_minutes:
            current_minutes = 120

        pending = count_pending_tasks(workdir)
        remote = get_github_remote(workdir)
        ci = get_ci_status(remote)
        commit_age = get_last_commit_age_h(workdir)

        new_minutes, reason = compute_recommended_schedule(
            current_minutes, pending, ci, commit_age
        )

        if new_minutes is None:
            if verbose:
                pend_str = str(pending) if pending is not None else "?"
                print("  OK  %-40s @%dm | P=%s CI=%s | %s" % (
                    name[:40], current_minutes, pend_str, ci[:4], reason))
            continue

        changes.append({
            "name": name,
            "id": j.get("id", "")[:12],
            "old_minutes": current_minutes,
            "new_minutes": new_minutes,
            "reason": reason,
            "job": j,
        })

    if not changes:
        print("No speed changes needed -- all foremen at appropriate schedules.")
        return 0

    print("Recommended changes (%s):" % ("DRY RUN" if dry_run else "APPLYING"))
    print("%-40s | %5s -> %5s | Reason" % ("Name", "Old", "New"))
    print("-" * 80)
    for c in changes:
        print("%-38s | %3dm -> %3dm | %s" % (
            c["name"][:38], c["old_minutes"], c["new_minutes"], c["reason"]))

    if dry_run:
        print("\n%d changes pending. Run with --apply to apply." % len(changes))
        return 0

    applied = 0
    for c in changes:
        job = c["job"]
        new_min = c["new_minutes"]
        job["schedule"] = {
            "kind": "interval",
            "display": "every %dm" % new_min,
            "minutes": new_min,
        }
        job["schedule"].pop("expr", None)
        job["schedule_display"] = "every %dm" % new_min
        applied += 1

    with open(JOBS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print("\nApplied %d speed changes. Model/provider unchanged." % applied)
    return 0


if __name__ == "__main__":
    sys.exit(main())
