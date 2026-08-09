#!/usr/bin/env python3
"""Query the coding-hermes scheduler daemon (:9090) for a project's state.

Cron-mode safe: plain script-file execution passes the terminal security filter
(no `python3 -c` one-liner, no sqlite3 direct access needed). The :9090 API is
the authoritative ground truth for Enabled / CooldownS / DecayRate / Priority /
Weight — the board's routing-notes claims are NOT (prior ticks fabricated
cooldown values for 7+ ticks before this API check existed).

Usage:
    python3 check_scheduler_project.py <project-name>
    python3 check_scheduler_project.py            # dump all projects

Output: one JSON line per matching project.
"""
import json
import sys
import urllib.request

API = "http://localhost:9090/api/v1/projects"
KEYS = ["Name", "Enabled", "CooldownS", "DecayRate", "Priority", "Weight",
        "UpdatedAt", "LastTickStarted"]
# snake_case equivalents for the post-2026-08-04 API shape (str.lower() is NOT
# a camelCase->snake_case converter: 'CooldownS'.lower() == 'cooldowns').
SNAKE_MAP = {"Name": "name", "Enabled": "enabled", "CooldownS": "cooldown_s",
             "DecayRate": "decay_rate", "Priority": "priority",
             "Weight": "weight", "UpdatedAt": "updated_at",
             "LastTickStarted": "last_tick_started"}


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        with urllib.request.urlopen(API, timeout=10) as r:
            d = json.load(r)
    except Exception as e:
        print(f"SCHEDULER_ERROR: {e}")
        sys.exit(1)
    projects = d if isinstance(d, list) else d.get("projects", [])
    found = False
    for p in projects:
        # API shape changed 2026-08-04 (daemon restart): project entries now
        # use snake_case keys (name, cooldown_s, priority, ...) instead of Go
        # field names (Name, CooldownS, ...). Accept both for forward compat.
        pname = p.get("Name") if p.get("Name") is not None else p.get("name")
        if name is None or pname == name:
            out = {}
            for k in KEYS:
                out[k] = p.get(k) if p.get(k) is not None else p.get(SNAKE_MAP[k])
            print(json.dumps(out))
            found = True
            if name is not None:
                return
    if name is not None and not found:
        print("PROJECT_NOT_FOUND")


if __name__ == "__main__":
    main()
