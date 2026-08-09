#!/usr/bin/env python3
"""Check for supervisor auto-pause orphan chains in Hermes cron jobs."""
import json, sys

JOBS_PATH = "~/.hermes/cron/jobs.json"

with open(JOBS_PATH) as f:
    data = json.load(f)

replaced = []
for j in data["jobs"]:
    reason = j.get("paused_reason", "") or ""
    if ("replaced" in reason.lower() or "auto-pause" in reason.lower()) and j.get("state") == "paused":
        replaced.append(j)

if not replaced:
    print("No supervisor-paused replacement crons found.")
    sys.exit(0)

print(f"Found {len(replaced)} cron(s) paused with replacement reason:\n")
orphans = 0
for j in replaced:
    rid = j["id"][:12]
    name = j["name"]
    reason = j.get("paused_reason", "")
    last_run = j.get("last_run_at", "never")
    print(f"  {name} ({rid})")
    print(f"    Paused: {reason}")
    print(f"    Last run: {last_run}")

    # Check if it names a replacement — look for cron name keywords
    # This is heuristic; the paused_reason text is freeform
    for other in data["jobs"]:
        other_name = other.get("name", "")
        if other_name != name and other.get("state") == "paused":
            # Check if the other cron might be the named replacement
            if any(word in reason.lower() for word in other_name.lower().split() if len(word) > 3):
                print(f"    ⚠️  Possible replacement ALSO paused: {other_name} ({other['id'][:12]})")
                print(f"        Last status: {other.get('last_status', '?')}, last run: {other.get('last_run_at', 'never')}")
                orphans += 1

print(f"\n{orphans} potential orphan chain(s) detected.")
if orphans > 0:
    print("ACTION: Re-enable the original cron or fix + re-enable the replacement.")
