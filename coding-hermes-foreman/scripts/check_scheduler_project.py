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

GAP-111 board-acceptance trace: named lookup must find scheduler projects that
sort after the list endpoint's first lexical window.
"""
import json
import sys
import urllib.error
import urllib.parse
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


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def normalize_project(project):
    return {
        key: project.get(key) if project.get(key) is not None else project.get(SNAKE_MAP[key])
        for key in KEYS
    }


def project_from_response(response):
    """Accept the current nested response and legacy direct project objects."""
    if not isinstance(response, dict):
        return None
    project = response.get("project")
    if isinstance(project, dict):
        return project
    if "Name" in response or "name" in response:
        return response
    return None


def project_name(project):
    return project.get("Name") if project.get("Name") is not None else project.get("name")


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else None
    if name is not None:
        lookup_url = f"{API}/{urllib.parse.quote(name, safe='')}"
        try:
            project = project_from_response(fetch_json(lookup_url))
        except urllib.error.HTTPError as error:
            if error.code != 404:
                print(f"SCHEDULER_ERROR: {error}")
                sys.exit(1)
        except Exception as error:
            print(f"SCHEDULER_ERROR: {error}")
            sys.exit(1)
        else:
            if project is None:
                print("SCHEDULER_ERROR: single-project response did not contain a project")
                sys.exit(1)
            print(json.dumps(normalize_project(project)))
            return

    # GAP-111 correction (2026-10-29): the earlier pagination premise was stale.
    # Measurement shows the daemon clamps limit=1000 to 500 rows and returns a
    # lexical window. Named lookup therefore uses the authoritative
    # single-project endpoint; the list is only a 404 fallback for compatibility.
    try:
        response = fetch_json(API)
    except Exception as error:
        print(f"SCHEDULER_ERROR: {error}")
        sys.exit(1)
    projects = response if isinstance(response, list) else response.get("projects", [])
    found = False
    for project in projects:
        if not isinstance(project, dict):
            continue
        if name is None or project_name(project) == name:
            print(json.dumps(normalize_project(project)))
            found = True
            if name is not None:
                return
    if name is not None and not found:
        print("PROJECT_NOT_FOUND")


if __name__ == "__main__":
    main()
