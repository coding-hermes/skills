#!/usr/bin/env python3
"""rabbit-hole combined signal scan (proven tick #133, 2026-08-03).

Runs ALL external-signal probes in ONE python3 call, replacing 4 separate
curl/go probes. Cron-safe: script file (no -c/-e flag), no curl|python pipes,
no sudo. Output is a single JSON dict.

Usage:
    python3 ~/.hermes/skills/coding-hermes-foreman/scripts/rabbit-hole-signal-scan.py

Probes:
  1. GitLab CI  — latest pipeline for project 17 (id/status/sha) + first 3 jobs
     (started_at=null + status=created = the standing 0-runners INFRA block).
     Reads GITLAB_TOKEN from ~/.hermes/.env (strip quotes; NEVER `export $(grep…)`).
  2. Off-by-One — GET /health (uptime) + GET /api/v1/stats (problems/answers,
     queue_depth, hit_rate) on localhost:8766.
  3. Storm-watch — GET /api/v1/ticks on localhost:9090; count running ticks
     grouped by ProjectName; dups = projects with >1 running. Invariant:
     running == unique, dups empty (count VARIES with fleet activity — 5 vs 6
     is not a regression).
  4. Deps — `go list -u -m all` in the repo; count lines containing '[' and
     sample the first 6. 39 outdated none actionable is the steady state
     (cilium/ebpf v0.17.3->v0.22.0 = standing block).

Notes:
  - The scheduler :9090 API uses GO-STYLE keys (Status, ProjectName, ID) —
    snake_case keys return None for every tick.
  - Timeouts are generous (15s CI, 5s ob1, 10s storm, 120s go list) so a hung
    probe degrades to an error field instead of hanging the tick.
"""
import json, os, re, subprocess, urllib.request

env_path = os.path.expanduser("~/.hermes/.env")
token = ""
with open(env_path) as f:
    for line in f:
        m = re.match(r'^GITLAB_TOKEN=(.+)$', line.strip())
        if m:
            token = m.group(1).strip('"').strip("'")
            break

out = {}

# 1. GitLab CI: latest pipeline for project 17
try:
    req = urllib.request.Request(
        "https://gitlab.readydedis.com/api/v4/projects/17/pipelines?per_page=1",
        headers={"PRIVATE-TOKEN": token})
    with urllib.request.urlopen(req, timeout=15) as r:
        pipes = json.load(r)
    if pipes:
        p = pipes[0]
        out["ci_latest"] = {"id": p.get("id"), "status": p.get("status"),
                            "ref": p.get("ref"), "sha": p.get("sha", "")[:7]}
        try:
            jreq = urllib.request.Request(
                f"https://gitlab.readydedis.com/api/v4/projects/17/pipelines/{p['id']}/jobs?per_page=20",
                headers={"PRIVATE-TOKEN": token})
            with urllib.request.urlopen(jreq, timeout=15) as jr:
                jobs = json.load(jr)
            out["ci_jobs"] = [{"name": j.get("name"), "status": j.get("status"),
                               "started_at": j.get("started_at")} for j in jobs[:3]]
        except Exception as e:
            out["ci_jobs_error"] = str(e)
except Exception as e:
    out["ci_error"] = str(e)

# 2. Off-by-one health + stats
try:
    with urllib.request.urlopen("http://localhost:8766/health", timeout=5) as r:
        out["ob1_health"] = json.load(r)
    with urllib.request.urlopen("http://localhost:8766/api/v1/stats", timeout=5) as r:
        out["ob1_stats"] = json.load(r)
except Exception as e:
    out["ob1_error"] = str(e)

# 3. Storm-watch: scheduler ticks running
try:
    with urllib.request.urlopen("http://localhost:9090/api/v1/ticks", timeout=10) as r:
        ticks = json.load(r).get("ticks", [])
    running = [t for t in ticks if t.get("Status") == "running"]
    by_proj = {}
    for t in running:
        by_proj.setdefault(t.get("ProjectName"), []).append(t.get("ID"))
    dups = {k: v for k, v in by_proj.items() if len(v) > 1}
    out["storm"] = {"running": len(running), "unique": len(by_proj), "dups": dups}
except Exception as e:
    out["storm_error"] = str(e)

# 4. Deps outdated
try:
    res = subprocess.run(["go", "list", "-u", "-m", "all"], capture_output=True, text=True,
                         cwd="~/rabbit-hole", timeout=120)
    outdated = [l for l in res.stdout.splitlines() if "[" in l]
    out["deps_outdated"] = len(outdated)
    out["deps_sample"] = outdated[:6]
except Exception as e:
    out["deps_error"] = str(e)

print(json.dumps(out, indent=1, default=str))
