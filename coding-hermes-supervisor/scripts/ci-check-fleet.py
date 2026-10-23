#!/usr/bin/env python3
"""Fleet-wide CI check for all enabled projects.

Classifies by remote type (GitHub / GitLab / local), fetches latest run status,
and reports passing/failing/no_ci state.

Run after Phase 0 auto-heal and Phase 2 rebalance.
Usage: GITHUB_PAT=$(grep '^GITHUB_PAT=' ~/.hermes/.env | head -1 | cut -d= -f2- | tr -d "'\"") python3 scripts/ci-check-fleet.py

Fallback: when `gh` CLI fails with BlockingIOError (fork contention),
this script automatically uses curl-based GitHub API. See
references/ci-check-blockingioerror-fallback.md for details.

Quota-awareness (SCHED-GAP-1759):
- Before the per-project loop the GitHub /rate_limit endpoint is read ONCE
  (`gh api rate_limit`, curl fallback with GITHUB_PAT). If the sweep's estimated
  API calls would exceed the remaining quota, a one-line INCONCLUSIVE banner is
  written to stderr, per-project rows read `inconclusive` (never `unknown`), no
  per-project CI endpoint is called, and the process exits non-zero (3).
  A 403 under quota exhaustion is a rate-limit signal, NOT an auth one: the
  token is never re-authed or rotated, and gh error strings are kept verbatim.
- Per-repo results are cached in `.ci-check-fleet.cache.json` keyed by
  "<owner_repo>@<head_sha>" (TTL = the 4h supervisor interval). Cache hits skip
  the gh/curl call and are labelled `cache_hit` in the report detail.
- The report header prints `quota remaining/limit = <rem>/<lim>` with the epoch
  reset as ISO-8601, plus `cached=<n>`.

Diagnostics:
  --rate-limit-only   Run the quota precheck + report header only, then exit.
"""
import json, math, os, sys, subprocess, urllib.request
from datetime import datetime, timezone

SCHEDULER_URL = 'http://127.0.0.1:9090/api/v1/projects'
GITHUB_PAT = os.environ.get('GITHUB_PAT', '')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(SCRIPT_DIR, '.ci-check-fleet.cache.json')
CACHE_TTL_SECONDS = 4 * 3600          # >= the 4h supervisor interval
EXIT_INCONCLUSIVE = 3                 # non-zero exit when the sweep is over budget
SAFETY_MARGIN = 1.20                  # 20% reserve for other quota consumers in the window


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
    except Exception:
        return None
    if 'github.com' in r:
        parts = r.replace('https://github.com/', '').replace('git@github.com:', '').replace('.git', '').split('/')
        return ('github', '/'.join(parts[:2]) if len(parts) >= 2 else r)
    elif 'gitlab' in r:
        return ('gitlab', r)
    return ('local', r)


def get_head_sha(wd):
    """Short head sha for the cache key, or None when unavailable."""
    if not wd or not os.path.isdir(wd):
        return None
    try:
        r = subprocess.run(['git', '-C', wd, 'rev-parse', '--short=12', 'HEAD'],
                           capture_output=True, text=True, timeout=5)
        sha = r.stdout.strip()
        return sha if r.returncode == 0 and sha else None
    except Exception:
        return None


def get_rate_limit():
    """Read GitHub core rate limit ONCE. Returns (remaining, limit, reset_epoch).

    Mirrors the script's existing token mechanism: `gh` CLI first, curl fallback
    with GITHUB_PAT on fork contention. Returns (None, None, None) when the quota
    cannot be read — the caller treats that as 'proceed', never as exhausted.
    """
    try:
        r = subprocess.run(['gh', 'api', 'rate_limit'],
                           capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            core = json.loads(r.stdout).get('resources', {}).get('core', {})
            rem, lim, reset = core.get('remaining'), core.get('limit'), core.get('reset')
            if rem is not None and lim is not None:
                return rem, lim, reset
    except Exception:
        pass
    if GITHUB_PAT:
        try:
            req = urllib.request.Request(
                'https://api.github.com/rate_limit',
                headers={'Authorization': f'token {GITHUB_PAT}'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                core = json.loads(resp.read()).get('resources', {}).get('core', {})
            rem, lim, reset = core.get('remaining'), core.get('limit'), core.get('reset')
            if rem is not None and lim is not None:
                return rem, lim, reset
        except Exception:
            pass
    return None, None, None


def iso_from_epoch(epoch):
    if not epoch:
        return 'unknown'
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()
    except Exception:
        return 'unknown'


def needed_calls(n_github):
    """Estimated API calls for THIS sweep, with a 20% safety margin.

    The per-project sweep costs >=2 GitHub API calls per project (`gh run list`
    plus a possible curl fallback), plus ~10 calls of fixed overhead. A single
    sweep is NOT the only quota consumer: at 845 projects, >=2 calls/project x up
    to 3 sweeps inside the 4h window would exceed the 5000/h core limit, so we
    inflate the raw estimate (2*n+10) by SAFETY_MARGIN before comparing against
    remaining.
    """
    return int(math.ceil((2 * n_github + 10) * SAFETY_MARGIN))


def decide_inconclusive(remaining, needed):
    """True (INCONCLUSIVE) when the sweep's estimated needs exceed remaining quota.

    remaining=None means the quota could not be read: fall through to a normal
    sweep rather than flagging a blackout we cannot prove.
    """
    if remaining is None:
        return False
    return needed >= remaining


def cache_key(owner_repo, head_sha):
    return f'{owner_repo}@{head_sha}' if head_sha else f'{owner_repo}@nohead'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_cache():
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    try:
        with open(CACHE_PATH, 'w') as f:
            json.dump(cache, f)
    except Exception:
        pass  # cache is best-effort; never crash on write failure


def cache_get(cache, key):
    entry = cache.get(key)
    if not isinstance(entry, dict) or entry.get('status') is None or not entry.get('ts'):
        return None
    try:
        dt = datetime.fromisoformat(entry['ts'])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - dt).total_seconds()
    except Exception:
        return None
    if age > CACHE_TTL_SECONDS:
        return None
    return entry


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
    except Exception:
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


def classify_github(owner_repo, head_sha, cache, inconclusive=False):
    """Classify one github repo, honouring the per-repo cache.

    Returns (status, detail, was_cached). In the inconclusive (quota-blackout)
    case the API is never touched and the row reads `inconclusive`, never
    `unknown`.
    """
    if inconclusive:
        return 'inconclusive', 'quota_exhausted', False
    key = cache_key(owner_repo, head_sha)
    hit = cache_get(cache, key)
    if hit is not None:
        return hit['status'], 'cache_hit: ' + str(hit.get('detail', '')), True
    status, data = check_github_ci_gh(owner_repo)
    if status is None and 'gh_error' in str(data):
        status2, data2 = check_github_ci_curl(owner_repo)
        if status2 is not None:
            status, data = status2, data2
    final_status = status or 'unknown'
    detail_out = str(data)[:120]
    if final_status != 'unknown':
        cache[key] = {'status': final_status, 'ts': now_iso(), 'detail': detail_out}
    return final_status, detail_out, False


def print_header(remaining, limit, reset_iso, cached):
    if remaining is not None and limit is not None:
        print(f'quota remaining/limit = {remaining}/{limit}  reset={reset_iso}  cached={cached}')
    else:
        print(f'quota remaining/limit = unknown/unknown  reset={reset_iso}  cached={cached}')


def main():
    rate_limit_only = '--rate-limit-only' in sys.argv

    if rate_limit_only:
        try:
            projs = get_projects()
        except Exception:
            projs = []
    else:
        projs = get_projects()

    rows = []
    n_github = 0
    for p in projs:
        n = p.get('name', p.get('Name', ''))
        wd = p.get('workdir', p.get('Workdir', ''))
        rtype = get_remote_type(wd)
        head_sha = None
        if rtype is not None and rtype[0] == 'github':
            head_sha = get_head_sha(wd)
            n_github += 1
        rows.append((n, rtype, head_sha))

    needed = needed_calls(n_github)
    remaining, limit, reset = get_rate_limit()
    reset_iso = iso_from_epoch(reset)
    inconclusive = decide_inconclusive(remaining, needed)

    if inconclusive:
        print(f'CI-CHECK INCONCLUSIVE - GitHub API quota too low: '
              f'needed={needed} remaining={remaining} limit={limit} reset={reset_iso}',
              file=sys.stderr)

    if rate_limit_only:
        print_header(remaining, limit, reset_iso, 0)
        sys.exit(EXIT_INCONCLUSIVE if inconclusive else 0)

    cache = load_cache() if not inconclusive else {}
    cached_count = 0
    results = {}
    for n, rtype, head_sha in rows:
        if rtype is None:
            results[n] = {'status': 'no_dir', 'detail': ''}
            continue
        kind, detail = rtype
        if kind == 'github':
            if inconclusive:
                results[n] = {'status': 'inconclusive', 'detail': 'quota_exhausted'}
            else:
                status, detail_out, was_cached = classify_github(detail, head_sha, cache)
                if was_cached:
                    cached_count += 1
                results[n] = {'status': status, 'detail': detail_out}
        elif kind == 'gitlab':
            results[n] = {'status': 'gitlab', 'detail': detail[:80]}
        elif kind == 'local':
            results[n] = {'status': 'no_ci', 'detail': ''}
        else:
            results[n] = {'status': 'unknown', 'detail': str(rtype)}

    print_header(remaining, limit, reset_iso, cached_count)
    print(f'{"Project":<30} {"Status":<14} {"Detail"}')
    print('-' * 95)
    for n in sorted(results):
        r = results[n]
        print(f'{n:<30} {r["status"]:<14} {r["detail"][:50]}')

    if not inconclusive:
        save_cache(cache)
    sys.exit(EXIT_INCONCLUSIVE if inconclusive else 0)


if __name__ == '__main__':
    main()
