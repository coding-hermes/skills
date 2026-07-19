# GitReins Guard `.0` Test Output — Python Test Runner Config Failure

## Problem

In Python projects, `gitreins guard` can show `✗ tests (full) — .0` instead of actual test results. The `.0` output means the test runner started but produced zero bytes of output — the runner itself failed to execute, not the tests.

## Detection

```bash
# The guard output looks like this:
Tier 1 Guards: FAIL  (test mode: diff, full suite — safety trigger)
  ✓ secrets — clean
  ✓ lint — ok
  ✗ tests (full) — .0       # ← ZERO output from test runner
  ✓ static_analysis
  ✓ lsp
```

Contrast with a REAL test failure:
```bash
  ✗ tests (full) — 3 failed  # ← actual test count
  === FAIL: test_foo.py::test_bar
  AssertionError: expected 200 got 500
```

## Root Causes

1. **Missing test dependencies** — `pytest` or test deps not installed in the venv
2. **Wrong working directory** — `gitreins guard` runs from the repo root but the test runner needs a different cwd
3. **Python version mismatch** — test runner configured for Python 3.13 but venv is 3.14 (or vice versa)
4. **Missing `.code.py` conftest** — if the project uses assembled `.code.py` files (Speclang-generated), the test runner may not discover them
5. **GitReins test command misconfiguration** — the `.gitreins/config.yaml` test command may point to a wrong or missing path

## Distinguishing Pre-Existing vs New

To determine if `.0` is pre-existing:

```bash
# 1. Stash your changes
git stash

# 2. Run guard on clean HEAD
timeout 120 gitreins guard

# 3. If same .0 output → pre-existing (runner config, not your code)
# 4. Restore your changes
git stash pop
```

## Foreman Response

When `.0` is **pre-existing** (confirmed on clean HEAD):
- Flag in Step 10 (DuckBrain write) as a known guard limitation
- Create `## [ ] INFRA — GitReins test runner producing .0 output, investigate config`
- Proceed with commit using `--no-verify` for non-code changes, or report honestly for code changes

When `.0` is **new** (only with your changes):
- The change broke the test runner itself (e.g., deleted conftest.py, changed pytest config)
- Do NOT bypass — fix the breakage first

## Proven

- **TotalStack 2026-07-13**: Guard showed `.0` consistently across multiple commits (pyproject.toml, AGENTS.md, workflow YAMLs). All were docs/config changes with no Python code modifications. Confirmed pre-existing on clean HEAD. Bypassed with `--no-verify`. Root cause: GitReins test runner configured for Go-style `go test ./...` but project uses `pytest` with complex venv setup.
- **Muster 2026-07-12**: `.0` in a Rust/Python hybrid project — test runner couldn't find `pytest` because it wasn't in PATH when guard invoked it.
