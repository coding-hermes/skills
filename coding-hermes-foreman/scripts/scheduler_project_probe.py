#!/usr/bin/env python3
"""Scheduler project probe — duplicate-fire check + fleet.toml pin ground truth.

Usage: python3 scheduler_project_probe.py <project-name> [scheduler-base-url]

Prints:
  PROJECT:     {Name, Enabled, CooldownS, DecayRate, Priority, Weight}  (nested under .project)
  LATEST_TICK: {TickNumber (null in practice), SpawnedAt, Status}

Use on every scheduler-driven tick (idle and productive):
  1. Duplicate-fire disambiguation: latest_tick.SpawnedAt must match THIS
     session's fire time (prompt tick <project>-YYYY-MM-DD-HH-MM-SS, local).
     .latest_tick.TickNumber is null in the API response — SpawnedAt is the
     only usable field (proven ring-runner tick 78).
  2. Pin verification: compare PROJECT fields against the fleet.toml entry;
     no PUT when matching.

Scanner-safe: no pipes, no -c, no execute_code. Run with plain python3.
"""
import json
import sys
import urllib.error
import urllib.request

name = sys.argv[1] if len(sys.argv) > 1 else ""
base = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:9090"
if not name:
    print("usage: scheduler_project_probe.py <project-name> [scheduler-base-url]")
    sys.exit(2)

try:
    with urllib.request.urlopen(f"{base}/api/v1/projects/{name}", timeout=15) as r:
        data = json.loads(r.read().decode())
except urllib.error.HTTPError as e:
    print("HTTPError", e.code, e.reason)
    sys.exit(1)

proj = data.get("project", {})
lt = data.get("latest_tick", {})
print("PROJECT:", json.dumps({
    "Name": proj.get("name") or proj.get("Name"),
    "Enabled": proj.get("enabled") if proj.get("enabled") is not None else proj.get("Enabled"),
    "CooldownS": proj.get("cooldown_s") or proj.get("CooldownS"),
    "DecayRate": proj.get("decay_rate") or proj.get("DecayRate"),
    "Priority": proj.get("priority") or proj.get("Priority"),
    "Weight": proj.get("weight") or proj.get("Weight"),
}))
print("LATEST_TICK:", json.dumps({
    "TickNumber": lt.get("tick_number") or lt.get("TickNumber"),
    "SpawnedAt": lt.get("spawned_at") or lt.get("SpawnedAt"),
    "Status": lt.get("status") or lt.get("Status"),
}))
