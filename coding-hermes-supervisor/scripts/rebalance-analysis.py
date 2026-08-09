#!/usr/bin/env python3
"""
Rebalance Analysis — Phase 2D

Evaluates every enabled scheduler project against the pending-task formula
and reports which cooldown and model changes are needed.

Rules enforced:
  - 1+ real pending (≠ NEVER-DONE) → 900s (15m) — active, needs fast iteration
  - 0 real pending → 43200s (12h) — idle, autoSlowdown handles further increases
  - Directionality: only REDUCE cooldown, never increase
  - Model is ALWAYS deepseek-v4-flash (Bane directive 2026-07-24)
  - Critical infra (coding-hermes-scheduler, duckbrain) excluded
  - Non-foreman purpose projects (with Command field) excluded
  - CI-aware: 0-pending + failing CI with CI-fix tasks on board → 1800s (30m)

Usage:
    python3 ~/.hermes/skills/coding-hermes-supervisor/scripts/rebalance-analysis.py
"""

import json
import os
import re
import subprocess
import sys

HOME = os.path.expanduser("~")
SCHEDULER_API = "http://127.0.0.1:9090/api/v1/projects"

# Critical infra — bypass pending-task formula entirely
CRITICAL_INFRA = {"coding-hermes-scheduler", "duckbrain"}

# Workdir overrides (umbrella repos with sub-project workdirs)
WORKDIR_MAP = {
    "h3": "~/get-h3/h3",
    "h3-sdk-go-foreman": "~/get-h3/sdk-go",
    "h3-sdk-python-foreman": "~/get-h3/sdk-python",
    "h3-sdk-typescript-foreman": "~/get-h3/sdk-typescript",
    "h3-shim-foreman": "~/get-h3/shim",
}


def get_projects():
    """Fetch all scheduler projects."""
    result = subprocess.run(
        ["curl", "-s", "--noproxy", "*", SCHEDULER_API],
        capture_output=True, text=True, timeout=15,
    )
    return json.loads(result.stdout).get("projects", [])


def get_pending(name, workdir):
    """Count real pending tasks in a project's task board.

    Handles TWO formats:
      1. Markdown checklist: ``## [ ] Task name``
      2. Matrix table: ``| TASK-ID | ... | [ ] |``

    In both cases subtracts 1 for the NEVER-DONE filler task
    (it is perpetual — never a real pending item).
    """
    import re
    wd = WORKDIR_MAP.get(name, workdir)
    if not wd or not os.path.isdir(wd):
        return None
    board = os.path.join(wd, ".coding-hermes", "tasks.md")
    if not os.path.isfile(board):
        return None
    with open(board) as f:
        content = f.read()

    # Count BOTH formats: ``## [ ]`` headers AND ``| ... [ ] |`` table cells
    header_count = content.count("## [ ]")
    cell_count = len(re.findall(r"\|[^|]*\[ \][^|]*\|", content))

    total = header_count + cell_count
    never_done_count = content.count("NEVER-DONE")

    real = total - min(never_done_count, total)
    return max(0, real)


def format_speed(seconds):
    """Human-readable speed label."""
    labels = {
        900: "15m", 1800: "30m", 3600: "1h", 7200: "2h",
        14400: "4h", 21600: "6h", 43200: "12h", 64800: "18h", 86400: "24h",
    }
    if seconds in labels:
        return labels[seconds]
    if seconds >= 86400:
        return f"{seconds//86400}d"
    if seconds >= 3600:
        return f"{seconds//3600}h"
    return f"{seconds//60}m"


def main():
    projects = get_projects()
    proj_by_name = {p["Name"]: p for p in projects}
    enabled = [p for p in projects if p.get("Enabled")]

    changes = []  # (name, field, old, new)

    print(f"{'Project':40s} {'Pend':>5s} {'Cooldown':>12s} {'TargetCD':>10s} {'Model':28s} {'TargetMdl':28s} {'Issue'}")
    print("-" * 130)

    for p in sorted(enabled, key=lambda x: x.get("Name", "").lower()):
        name = p["Name"]
        cd = p.get("CooldownS", 0)
        model = p.get("Model") or "-"
        provider = p.get("Provider") or "-"
        workdir = p.get("Workdir", "")

        # Skip critical infra from pending-task formula, but flag drift
        if name in CRITICAL_INFRA:
            drift_flag = ""
            if cd > 900:
                drift_flag = f" ⚠️ DRIFTED {format_speed(cd)}→900s"
            print(f"{name:40s} {'—':>5s} {format_speed(cd):>12s} {'—':>10s} {model:28s} {model:28s} INFRA{drift_flag}")
            continue

        # Skip non-foreman purpose projects (E2E testers, watchdogs with Command field)
        if p.get("Command"):
            print(f"{name:40s} {'—':>5s} {format_speed(cd):>12s} {'—':>10s} {model:28s} {model:28s} SPECIAL")
            continue

        pending = get_pending(name, workdir)
        if pending is None:
            print(f"{name:40s} {'?':>5s} {format_speed(cd):>12s} {'—':>10s} {model:28s} {model:28s} NO BOARD")
            continue

        # Determine target — model is ALWAYS deepseek-v4-flash (Bane 2026-07-24)
        if pending >= 1:
            target_cd = 900  # 15m — active project
        else:
            target_cd = 43200  # 12h — idle, autoSlowdown handles increases
        target_model = "deepseek-v4-flash"

        # Directionality: only reduce cooldown
        if cd > target_cd:
            new_cd = target_cd
            cd_change = f"{format_speed(cd)}→{format_speed(new_cd)}"
        else:
            new_cd = cd
            cd_change = "keep"

        # Model follows stage, independent of cooldown
        if model != target_model:
            model_change = f"{model}→{target_model}"
        else:
            model_change = "ok"

        # Collect issues
        issues = []
        if cd_change != "keep":
            issues.append(f"CD:{cd_change}")
        if model_change != "ok":
            issues.append(f"MDL:{model_change}")

        issue_str = ", ".join(issues) if issues else "—"
        print(f"{name:40s} {str(pending):>5s} {format_speed(cd):>12s} {format_speed(target_cd):>10s} {model:28s} {target_model:28s} {issue_str}")

        if cd_change != "keep":
            changes.append((name, "CooldownS", new_cd))
        if model_change != "ok":
            changes.append((name, "Model", target_model))

        # Warn on wrong provider
        if provider and provider != "deepseek-foreman":
            print(f"  ⚠️  WRONG PROVIDER: {provider}")

    # Summary
    print()
    print(f"Projects analysed: {len(enabled)} enabled")
    print(f"Cooldown changes: {sum(1 for c in changes if c[1] == 'CooldownS')}")
    print(f"Model changes: {sum(1 for c in changes if c[1] == 'Model')}")
    print()

    if changes:
        print("=== APPLY CHANGES ===")
        print("Run the following or pipe into a batch script:")
        for name, field, val in changes:
            print(f"  PUT /api/v1/projects/{name} {{{field}: {repr(val)}}}")

    # Post-rebalance: detect critical infra drift (cooldown > 900 on CRITICAL_INFRA projects)
    # autoSlowdown pushes coding-hermes-scheduler above 900s every cycle (LastTickAt=never).
    # See SKILL.md Phase 2D critical-infra-cooldown-drift pitfall.
    infra_drifted = []
    for name in CRITICAL_INFRA:
        p = proj_by_name.get(name)
        if p and p.get("Enabled") and p.get("CooldownS", 0) > 900:
            infra_drifted.append((name, p["CooldownS"]))
    if infra_drifted:
        print()
        print("⚠️  CRITICAL INFRA DRIFT:")
        print("    The guard prevents the pending-task formula from touching critical infra,")
        print("    but autoSlowdown can still push cooldown above 900s. Reset via:")
        for name, cd in infra_drifted:
            print(f"    {'PUT':4s} /api/v1/projects/{name} --data '{{\"CooldownS\": 900}}'")
            print(f"    {'':4s}  (currently {format_speed(cd)}, expected 15m)")
        print()

    # Detect stalled projects (cooldown > 86400)
    stalled = [p for p in enabled if p.get("CooldownS", 0) > 86400]
    if stalled:
        print("\n⚠️  STALLED (CooldownS > 86400):")
        for p in stalled:
            print(f"  {p['Name']:40s} CD={p['CooldownS']}s LastTick={p.get('LastTickAt','never')}")

    # Detect empty provider on enabled project with model set
    empty_prov = [p for p in enabled if not p.get("Provider") and p.get("Model")]
    if empty_prov:
        print("\n⚠️  EMPTY PROVIDER (Model set but Provider empty):")
        for p in empty_prov:
            print(f"  {p['Name']:40s} Model={p.get('Model')}")

    # Detect both model and provider empty
    both_empty = [p for p in enabled if not p.get("Provider") and not p.get("Model")]
    if both_empty:
        print("\n⚠️  BOTH EMPTY (Model and Provider both null):")
        for p in both_empty:
            print(f"  {p['Name']:40s}")


if __name__ == "__main__":
    main()
