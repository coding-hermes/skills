#!/usr/bin/env python3
"""Fleet-wide CI check for all enabled projects.
Classifies by remote type (GitHub / GitLab / local), fetches latest run status,
and reports passing/failing/no_ci state.

Run after Phase 0 auto-heal and Phase 2 rebalance.
Usage: GITHUB_PAT=$(grep '^GITHUB_PAT=' ~/.hermes/.env | head -1 | cut -d= -f2- | tr -d "'\"") python3 scripts/ci-check-fleet.py

Fallback: when `gh` CLI fails with BlockingIOError (fork contention),
this script automatically uses curl-based GitHub API. See
references/ci-check-blockingioerror-fallback.md for details.
"""
import json, os, sys, subprocess, urllib.request

SCHEDULER_URL = 'http://127.0.0.1:9090/api/v1/projects'
GITHUB_PAT = os.environ.get('GITHUB_PAT', '')

def get_projects():
    with urllib.request.urlopen(SCHEDULER_URL, timeout=10) as resp:
        d = json.loads(resp.read())
    return [p for p in d.get('projects', []) if p.get('enabled', p.get('Enabled'))]

def get_remote_type(wd):
    """Classify remote: 'github', 'gitlab', 'local', or None."""
    if not wd or not os.path.isdir(wd):
        return None
    try:
        r = subprocess.run(
            ['git', '-C', wd, 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except:
        return None
    if 'github.com' in r:
        parts = r.replace('https://github.com/', '').replace('git@github.com:', '').replace('.git', '').split('/')
        return ('github', '/'.join(parts[:2]) if len(parts) >= 2 else r)
    elif 'gitlab' in r:
        return ('gitlab', r)
    return ('local', r)

def check_github_ci_gh(owner_repo):
    """Try gh CLI first."""
    result = subprocess.run(
        ['gh', 'run', 'list', '-R', owner_repo, '--limit', '3',
         '--json', 'conclusion,displayTitle,status,headBranch'],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode != 0:
        return None, f'gh_error: {result.stderr.strip()[:100]}'
    try:
        runs = json.loads(result.stdout) if result.stdout.strip() else []
    except:
        return None, 'parse_error'
    if not runs:
        return 'no_ci', []
    failures = [r for r in runs if r.get('conclusion') == 'failure']
    if failures:
        return 'failing', failures
    return 'passing', runs

def check_github_ci_curl(owner_repo):
    """Fallback to curl-based API when gh can't spawn (BlockingIOError)."""
    if not GITHUB_PAT:
        return None, 'no_pat'
    url = f'https://api.github.com/repos/{owner_repo}/actions/runs?per_page=3'
    req = urllib.request.Request(url, headers={'Authorization': f'token {GITHUB_PAT}'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            d = json.loads(resp.read())
    except Exception as e:
        return None, f'api_error: {e}'
    runs = d.get('workflow_runs', [])
    if not runs:
        return 'no_ci', []
    failures = [r for r in runs if r.get('conclusion') == 'failure']
    if failures:
        return 'failing', failures
    return 'passing', runs

def main():
    projs = get_projects()
    results = {}
    for p in projs:
        n = p.get('name', p.get('Name', ''))
        wd = p.get('workdir', p.get('Workdir', ''))
        rtype = get_remote_type(wd)
        if rtype is None:
            results[n] = {'status': 'no_dir', 'detail': wd or ''}
            continue
        kind, detail = rtype
        if kind == 'github':
            status, data = check_github_ci_gh(detail)
            if status is None and 'gh_error' in str(data):
                status2, data2 = check_github_ci_curl(detail)
                if status2 is not None:
                    status, data = status2, data2
            results[n] = {'status': status or 'unknown', 'detail': str(data)[:120]}
        elif kind == 'gitlab':
            results[n] = {'status': 'gitlab', 'detail': detail[:80]}
        elif kind == 'local':
            results[n] = {'status': 'no_ci', 'detail': ''}
        else:
            results[n] = {'status': 'unknown', 'detail': str(rtype)}

    print(f'{"Project":<30} {"Status":<14} {"Detail"}')
    print('-' * 95)
    for n in sorted(results):
        r = results[n]
        print(f'{n:<30} {r["status"]:<14} {r["detail"][:50]}')

if __name__ == '__main__':
    main()
