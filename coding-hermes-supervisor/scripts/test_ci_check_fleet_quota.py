"""Tests for ci-check-fleet.py quota-awareness and per-repo cache (SCHED-GAP-1759).

No network: the inconclusive path never touches gh/curl, and cache-hit tests
monkeypatch the fetch functions to fail loudly if called.
"""
import importlib.util
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    'ci_check_fleet', os.path.join(HERE, 'ci-check-fleet.py'))
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_decide_inconclusive_when_quota_exhausted():
    assert mod.decide_inconclusive(0, 1700) is True


def test_decide_inconclusive_when_quota_plenty():
    assert mod.decide_inconclusive(5000, 1700) is False


def test_decide_inconclusive_boundary_flags_at_equal():
    # needed >= remaining means the boundary itself is over budget.
    assert mod.decide_inconclusive(2040, 2040) is True
    assert mod.decide_inconclusive(2041, 2040) is False


def test_decide_inconclusive_when_quota_unreadable_falls_through():
    # remaining=None must NOT be treated as exhausted.
    assert mod.decide_inconclusive(None, 1700) is False


def test_needed_calls_applies_safety_margin():
    # (2*n + 10) inflated by the 20% safety margin.
    assert mod.needed_calls(0) == 12       # ceil(10 * 1.2)
    assert mod.needed_calls(845) == 2040   # ceil((1690+10) * 1.2)


def test_github_row_inconclusive_never_unknown(monkeypatch):
    # The negative control: with quota exhausted, a github project with CI must
    # read 'inconclusive' (never 'unknown') and must never call the API.
    def boom(*a, **k):
        raise AssertionError('network call in inconclusive path')
    monkeypatch.setattr(mod, 'check_github_ci_gh', boom)
    monkeypatch.setattr(mod, 'check_github_ci_curl', boom)
    status, detail, was_cached = mod.classify_github(
        'owner/repo', 'abc123456789', {}, inconclusive=True)
    assert status == 'inconclusive'
    assert 'unknown' not in detail
    assert was_cached is False


def test_cache_hit_skips_api(monkeypatch):
    def boom(*a, **k):
        raise AssertionError('network call on cache hit')
    monkeypatch.setattr(mod, 'check_github_ci_gh', boom)
    monkeypatch.setattr(mod, 'check_github_ci_curl', boom)
    cache = {'owner/repo@abc123456789': {
        'status': 'passing', 'ts': datetime.now(timezone.utc).isoformat(), 'detail': ''}}
    status, detail, was_cached = mod.classify_github(
        'owner/repo', 'abc123456789', cache, inconclusive=False)
    assert status == 'passing'
    assert was_cached is True
    assert 'cache_hit' in detail


def test_cache_expired_refetches(monkeypatch):
    def fake_gh(owner_repo):
        return 'passing', []
    monkeypatch.setattr(mod, 'check_github_ci_gh', fake_gh)
    stale = '2000-01-01T00:00:00+00:00'
    cache = {'owner/repo@abc123456789': {'status': 'passing', 'ts': stale, 'detail': ''}}
    status, detail, was_cached = mod.classify_github(
        'owner/repo', 'abc123456789', cache, inconclusive=False)
    assert was_cached is False
    assert status == 'passing'
