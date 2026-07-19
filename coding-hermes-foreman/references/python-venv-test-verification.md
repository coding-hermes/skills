# Python Venv Test Verification — Foreman Must Verify, Not Trust

## The Pitfall

Workers write Python tests and commit them. They self-report "132 tests pass." But when the
foreman tries to run them, they fail with `ModuleNotFoundError`. The code is correct — the
venv is missing test dependencies (`pytest`, `httpx2`, `pytest-asyncio`).

**Why this happens:** Workers use `uv run python3 -c "import package"` to verify imports,
but `uv run` falls through to the system Python when the venv Python doesn't have the
package. Direct imports succeed but `pytest` collection fails because `pytest` isn't
installed in the venv.

**Proven:** H3 SDK Python (2026-07-14) — 34 tests in `sdk-python/`, 132 tests in `shim/`.
All imports resolved with `uv run python3 -c "import x"` but `pytest` failed collection
because `pytest` and `httpx2` weren't in the venv.

## Detection

If a worker or prior tick claims tests pass, the foreman MUST verify:

```bash
# Quick smoke: does pytest exist in the venv?
cd /home/kara/get-h3/<repo>
uv run python3 -m pytest --version 2>&1

# If "No module named pytest" → venv is broken, fix it
```

## Fix Recipe

```bash
cd /home/kara/get-h3/<repo>
uv add --dev pytest pytest-asyncio pytest-mock httpx2
uv run python3 -m pytest tests/ -v --tb=short
```

After fixing, mark the task board with the real pass/fail count.

## Foreman Rule

**Never trust a worker's self-reported test count.** After any TEST or POLISH task marked
complete, the foreman must:
1. `uv sync` in the repo
2. `uv run python3 -m pytest tests/ -v --tb=short`
3. Compare actual pass count against worker's claim
4. If mismatch → reopen task, fix deps, re-verify

## Why `uv run` Fails Silently

`uv run python3 -c "import h3_shim"` can succeed even when `pytest` isn't installed
because the system Python or a different venv resolves the import. But `uv run python3 -m pytest`
requires pytest IN the project's `.venv`. The foreman's verification command MUST use
`-m pytest`, not `-c "import ..."`.

## Idle-Tick Discovery Sweep — Venv Drift

Even when no worker touched the project, the venv can go stale between foreman ticks.
`requirements.txt` lists a dependency but the venv doesn't have it installed. Test
collection fails with `ModuleNotFoundError` for packages that ARE in requirements.txt.

**Why this happens:** The venv was created from an older snapshot of requirements.txt,
or a different process (`pip install --upgrade`, manual `uv pip uninstall`) modified
the venv without updating requirements.txt. The two drift apart silently.

**Proven:** DexDat Core 2026-07-18 — idle tick discovery sweep. `prometheus_client==0.25.0`
in requirements.txt but not in venv. 34 test collection errors (ImportError on
`from prometheus_client import ...`). `uv pip install -r requirements.txt` resolved
instantly — no code change needed.

**Foreman rule for idle ticks:** When the board is empty and you run a discovery sweep,
add a one-line venv-sync before running tests:

```bash
# Sync venv to requirements.txt (idempotent — fast if already current)
uv pip install -r requirements.txt 2>&1 | tail -3
```

If the output shows new packages installed, note it in the foreman report. If output
is empty or shows only version bumps, the venv was already current — move on. Never
spend more than one terminal call on this; the point is to catch drift, not to audit
every package.

**Distinct from post-worker verification:** Worker verification requires deeper checks
(`uv add --dev pytest`, smoke-tests against the specific worker's claims). Idle-tick
venv sync is a lightweight guard — one command, note drift if found, move on.
