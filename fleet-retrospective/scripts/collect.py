#!/usr/bin/env python3
"""Retrospective data collector — parameterized for any fleet project.

Usage:
  python3 scripts/collect.py --name <scheduler-project-prefix> --repo <repo-path> \
      [--window-days 90] [--out <workspace-dir>] [--github-repo owner/name] \
      [--test-cmd "pytest --collect-only -q"]

Writes raw data files into --out (default ~/retro-workspace-<name>):
  git-timeline.txt, scheduler-ticks.txt, board-ci.txt, repo-stats.txt
Then the orchestrator distills facts.md and dispatches analyst agents (see SKILL.md).
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import urllib.request


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="scheduler project name prefix (e.g. gitreins-poc)")
    ap.add_argument("--repo", required=True, help="path to the git repo")
    ap.add_argument("--window-days", type=int, default=90)
    ap.add_argument("--out", default=None)
    ap.add_argument("--board-rel", default=".coding-hermes/board")
    ap.add_argument("--github-repo", default="", help="owner/name for CI stats via public API (optional)")
    ap.add_argument("--test-cmd", default="", help="test runner collect-only cmd (optional)")
    args = ap.parse_args()

    out = args.out or os.path.expanduser(f"~/retro-workspace-{args.name}")
    os.makedirs(out, exist_ok=True)
    since = (dt.date.today() - dt.timedelta(days=args.window_days)).isoformat()

    # 1. Git timeline
    git = {
        "FIRST/LAST": run(f'git log --reverse --since="{since}" --format="%h %ad %s" --date=short | head -3', args.repo)
        + "\n" + run(f'git log --since="{since}" --format="%h %ad %s" --date=short | head -3', args.repo),
        "TOTAL": run(f"git log --since='{since}' --oneline | wc -l", args.repo),
        "PER MONTH": run(f'git log --since="{since}" --format="%ad" --date=format:"%Y-%m" | sort | uniq -c', args.repo),
        "PER WEEK": run(f'git log --since="{since}" --format="%ad" --date=format:"%G-W%V" | sort | uniq -c', args.repo),
        "ADDS/DELS": run(
            'git log --since="%s" --shortstat --format= | awk \'/files? changed/{f+=$1;i+=$4;d+=$6} END{print "files:"f" insertions:"i" deletions:"d}\'' % since,
            args.repo,
        ),
        "RELEASES": run("git tag --sort=creatordate --format='%(refname:short) %(creatordate:short)'", args.repo),
        "TOP FILES": run(f'git log --since="{since}" --name-only --format= | sort | uniq -c | sort -rn | head -15', args.repo),
        "AUTHORS": run(f'git log --since="{since}" --format="%an" | sort | uniq -c | sort -rn', args.repo),
    }
    with open(os.path.join(out, "git-timeline.txt"), "w") as f:
        for k, v in git.items():
            f.write(f"=== {k} ===\n{v}\n\n")

    # 2. Scheduler ticks (global DB; may not exist on other hosts)
    db = os.path.expanduser("~/.hermes/coding-hermes/scheduler.db")
    with open(os.path.join(out, "scheduler-ticks.txt"), "w") as f:
        if os.path.exists(db):
            queries = [
                ("TICKS PER DAY", f"SELECT date(spawned_at) d, count(*), sum(commits), sum(files_changed) FROM ticks WHERE project_name LIKE '{args.name}%' AND date(spawned_at) >= '{since}' GROUP BY d ORDER BY d;"),
                ("OUTCOMES", f"SELECT status, outcome, count(*), sum(commits), sum(files_changed), round(sum(cost_usd),2) FROM ticks WHERE project_name LIKE '{args.name}%' AND date(spawned_at) >= '{since}' GROUP BY status, outcome;"),
                ("PER ROLE", f"SELECT project_name, count(*), sum(commits), sum(files_changed), round(sum(cost_usd),2) FROM ticks WHERE project_name LIKE '{args.name}%' AND date(spawned_at) >= '{since}' GROUP BY project_name;"),
                ("TOKENS/COST", f"SELECT round(sum(tokens_in)/1e6,1)||'M in', round(sum(tokens_out)/1e6,2)||'M out', '$'||round(sum(cost_usd),2) FROM ticks WHERE project_name LIKE '{args.name}%' AND date(spawned_at) >= '{since}';"),
                ("FAILED REASONS", f"SELECT substr(coalesce(error,'?'),1,80), count(*) FROM ticks WHERE project_name LIKE '{args.name}%' AND status IN ('failed','timeout') AND date(spawned_at) >= '{since}' GROUP BY 1 ORDER BY 2 DESC LIMIT 12;"),
            ]
            for title, q in queries:
                f.write(f"=== {title} ===\n{run(['sqlite3', db, q])}\n\n")
        else:
            f.write("no scheduler.db on this host\n")

    # 3. Board state (JSONL canonical; tolerate absence) + CI via public API
    with open(os.path.join(out, "board-ci.txt"), "w") as f:
        board = os.path.join(args.repo, args.board_rel, "tasks.jsonl")
        if os.path.exists(board):
            rows = [json.loads(l) for l in open(board) if l.strip()]
            from collections import Counter

            f.write(f"=== BOARD ===\ntotal: {len(rows)}\nby status: {dict(Counter(r.get('status') for r in rows))}\n")
            pending = [r.get("id") for r in rows if r.get("status") == "pending"]
            f.write(f"pending ids: {pending}\n\n")
        else:
            f.write("=== BOARD ===\nno JSONL board found at " + board + "\n\n")
        if args.github_repo:
            try:
                url = f"https://api.github.com/repos/{args.github_repo}/actions/runs?per_page=100"
                runs = json.load(urllib.request.urlopen(url, timeout=30)).get("workflow_runs", [])
                succ = sum(1 for r in runs if r.get("conclusion") == "success")
                fail = sum(1 for r in runs if r.get("conclusion") == "failure")
                f.write(f"=== CI (latest {len(runs)} runs) ===\nsuccess: {succ}  failure: {fail}\n")
            except Exception as e:
                f.write(f"=== CI ===\nunavailable: {e}\n")

    # 4. Repo stats (test count + optional LOC for python-style layouts)
    with open(os.path.join(out, "repo-stats.txt"), "w") as f:
        if args.test_cmd:
            f.write(f"=== TEST COLLECT ===\n{run(args.test_cmd, args.repo)}\n")
        loc = run('find . -maxdepth 2 -name "*.py" -not -path "./.venv/*" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1', args.repo)
        f.write(f"=== LOC (top-level py, adjust per project) ===\n{loc}\n")

    # 5. DuckBrain tick keys (project narrative history; optional)
    duck_ns = os.path.expanduser(f"~/duckbrain/namespaces/{args.name}")
    with open(os.path.join(out, "duckbrain-state.txt"), "w") as f:
        if os.path.isdir(duck_ns):
            keys = run(f"find '{duck_ns}' -name '*.md' -o -name '*.json' 2>/dev/null | head -40", None)
            f.write(f"=== DUCKBRAIN KEYS (first 40) ===\n{keys}\n")
        else:
            f.write(f"no duckbrain namespace at {duck_ns}\n")

    print(f"collected -> {out}")
    print("next: distill facts.md, dispatch 3 analysts, synthesize HTML (see SKILL.md)")


if __name__ == "__main__":
    main()
