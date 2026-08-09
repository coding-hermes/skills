#!/usr/bin/env python3
"""Validate fleet-data.json against expected schema. Exit 0 if valid, 1 with errors if not."""
import json, sys, os
from datetime import datetime

def validate(path):
    with open(path) as f:
        data = json.load(f)

    errors = []

    for key in ["metrics", "fleet", "what_got_done", "issues_detected", "changes_made", "generated"]:
        if key not in data:
            errors.append(f"Missing top-level key: {key}")

    if not isinstance(data.get("fleet"), list) or len(data["fleet"]) == 0:
        errors.append("Fleet array is empty or missing")

    m = data.get("metrics", {})
    fleet_count = len(data.get("fleet", []))
    metric_sum = m.get("healthy", 0) + m.get("warn", 0) + m.get("error", 0) + m.get("paused", 0)
    if metric_sum != fleet_count:
        errors.append(f"Metrics sum ({metric_sum}) != fleet count ({fleet_count})")

    required_fields = ["project", "workdir", "foreman_model", "foreman_provider", "status"]
    for i, f in enumerate(data.get("fleet", [])):
        for field in required_fields:
            if field not in f:
                errors.append(f"Fleet[{i}] missing field: {field}")
        status = f.get("status", "")
        if status not in ("healthy", "warn", "error", "stale"):
            errors.append(f"Fleet[{i}] invalid status: {status}")

    done = data.get("what_got_done", {})
    for key in ["tasks_resolved", "commits_landed", "bugs_queued", "ci_regressions", "spec_doc_fixes", "tool_health"]:
        if key not in done:
            errors.append(f"what_got_done missing key: {key}")

    try:
        datetime.fromisoformat(data.get("generated", ""))
    except (ValueError, TypeError):
        errors.append(f"Invalid generated timestamp: {data.get('generated')}")

    if errors:
        print("❌ Validation errors:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"✅ Valid: {fleet_count} fleet entries, {m.get('total_pending_tasks', 0)} pending tasks")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validate-fleet-data.py <fleet-data.json>")
        sys.exit(1)
    sys.exit(validate(sys.argv[1]))
