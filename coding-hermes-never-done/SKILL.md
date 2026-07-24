---
name: coding-hermes-never-done
description: Foreman self-improvement loop — empty board means find more work, not stop
version: 1.12.0
category: software-development
---

# Never Done — Continuous Self-Improvement

**Core principle:** An empty board does NOT mean the project is done. It means the foreman hasn't looked hard enough. The foreman's job is continuous improvement — find gaps, add tasks, fix them, repeat. Never declare victory.

## Permanent Board Fixture

**These two tasks are ALWAYS the last items on every board and are NEVER marked `[x]`.**

Every project's `.coding-hermes/tasks.md` MUST end with:

```
- [ ] E2E-001 — E2E Testing Tick (self-improving loop)
  Spawn Luna (browser/screenshots) or Step 3.7 Flash (CLI/API). Deploy/build,
  Playwright, screenshots, endpoints, console. → e2e-output/tasks.md → inject
  into board. See foreman Step 1.5i. Every 5-10 ticks.

- [ ] NEVER-DONE — Run coding-hermes-never-done 13-point audit
  Load coding-hermes-never-done skill. Run ALL 13 checks: spec alignment,
  doc coverage, test gaps, package upgrades, pitfall hunt, performance audit,
  endpoint verification, CI/CD health, DuckBrain sync, code quality,
  middle-out wiring, usability smoke test, E2E testing tick. Create a task
  for EVERY gap found. This task is never complete — the audit always finds something.
```

**Rules for these tasks:**
1. E2E-001 runs every 5-10 ticks — triggers browser/CLI testing
2. NEVER-DONE is never marked `[x]` — it remains open permanently
3. When all other tasks are done, the foreman picks up NEVER-DONE and runs the audit
4. The audit creates new tasks ABOVE these two — the cycle repeats
5. On new project onboarding, the foreman MUST write both tasks as the final items

## When This Skill Loads

Load this skill when:
- The board has 0 pending tasks (all `[x]`)
- Or the foreman is about to mark the last task `[x]`
- Or the board has been empty for 2+ consecutive ticks

## The 13-Point Self-Improvement Audit

Run this audit EVERY tick when the board is empty or nearly empty. Each pass creates new tasks. The loop is infinite — there is always something to improve.

**⚠️ Before creating tasks from audit findings, verify each one is real.** Audit commands run in a separate session with its own VIRTUAL_ENV, PATH, and git state. A finding that says "dep outdated" or "spec stale" may be a false positive. See `references/audit-false-positive-verification.md` for the verification protocol and root-cause taxonomy.

**Edge case — empty scaffold (no source code):** See `references/empty-scaffold-audit.md` for how the 11 checks break down when the workdir has zero source files (only infrastructure config). Several checks become N/A but security config audit still applies.

**Edge case — single-file / client-only (no backend, no build step):** See `references/single-file-client-audit.md` for adapting the audit to single-file HTML/JS/CSS dashboards, static sites, or client-only apps with CDN dependencies. Checks 7 (endpoint verification) and 11 (middle-out wiring) are N/A; checks 4 (package upgrades → CDN version check), 5 (pitfalls → innerHTML XSS, CSV parser edge cases, no `'use strict'`), 6 (perf → browser main-thread concerns), 8 (CI/CD → static deploy), and 10 (code quality → monolithic file smell, global namespace) all need adaptation.

### 1. SPEC ALIGNMENT — Do specs match reality?

**For efficient batch verification at scale (10+ specs), use the `execute_code` pattern documented in `references/spec-alignment-batch-verification.md`.** The generic bash loop below is a fallback for small projects.

```bash
# Compare spec files against actual code
for spec in specs/*.md specs/**/*.md; do
    [ -f "$spec" ] || continue
    # Extract interface signatures, data models, API endpoints from spec
    # Check if they exist in actual code
done
```

What to check:
- Every interface in spec exists in code
- Every endpoint in spec returns the documented shape
- Every data model field in spec is present in code
- Every error path in spec is handled in code
- Every config value in spec is used in code

Create: `## [ ] SPEC — <specific gap>` for each mismatch.

### 2. DOC COVERAGE — Are docs complete?

```bash
# Check for undocumented files, missing README sections
find . -name '*.go' -o -name '*.py' -o -name '*.ts' | while read f; do
    # Check if file has doc comments, is referenced in docs
done
```

What to check:
- Every public function has a doc comment
- README covers setup, usage, API, configuration
- CONTRIBUTING.md exists and is accurate
- Architecture decisions are documented in DuckBrain
- API docs match actual endpoints (run curl against live server)
- **LICENSE file exists when package.json / pyproject.toml / Cargo.toml declares a license.** A `[x]` task claiming LICENSE was created does NOT mean it exists — verify with `git show HEAD:LICENSE` or `ls LICENSE`. **Proven:** SpecLang 2026-07-20 — DOC-LICENSE-001 marked `[x]` for 5 ticks but LICENSE never existed in git. **Proven:** mafia-ai-benchmark 2026-07-20 — audit found no LICENSE despite package.json declaring MIT; foreman created the file directly (standard MIT template) rather than spawning a worker for a 1-second mechanical fix.

**Self-heal mechanical gaps — do NOT create tasks for template files.** When the audit finds a gap that is a standard template or boilerplate file (LICENSE, .gitignore entry, default config, standard CI badge), fix it DIRECTLY as part of the audit tick. Commit it as a `chore` alongside the board update. Creating a DOC task for a mechanical gap guarantees the anti-pattern above: the task gets marked `[x]` for multiple ticks while the file never materializes. Workers are for code — templates are for foremen. This applies to: LICENSE, .gitignore entries, CONTRIBUTING.md boilerplate, CODEOWNERS, standard CI config snippets, and any file whose content is a well-known template rather than project-specific logic.

Create: `## [ ] DOC — <gap>` for each missing piece that requires project-specific content (not a template).

### 3. TEST GAPS — What isn't tested?

**DETECT THE PROJECT LANGUAGE FIRST.** Do NOT run Go commands on a TypeScript project, TypeScript commands on a Rust project, or Go `_test.go` same-name checks on ANY non-Go language. The naive `find . -name '*.go' ! -name '*_test.go'` check produces massive false positives when the project isn't Go. TypeScript tests live in `__tests__/` directories (not same-directory). Rust integration tests live in `tests/` (not `src/`). Running the wrong language's commands wastes time on false positives that must be manually verified.

Quick language detection — run before any test-gap commands:
```bash
# Determine primary language by counting source files
echo "Go:     $(find . -name '*.go' ! -path './.git/*' ! -path './vendor/*' 2>/dev/null | head -5 | wc -l)"
echo "TS:     $(find . -name '*.ts' ! -name '*.test.ts' ! -path './node_modules/*' ! -path './.git/*' 2>/dev/null | head -5 | wc -l)"
echo "Rust:   $(find . -name '*.rs' ! -path './target/*' ! -path './.git/*' 2>/dev/null | head -5 | wc -l)"
echo "Python: $(find . -name '*.py' ! -path './.venv/*' ! -path './.git/*' 2>/dev/null | head -5 | wc -l)"
```

Then follow the appropriate language guide below. If the primary language isn't covered, fall back to directory-level test detection: check if ANY `*_test.*` or `__tests__/` directory exists per package.

**Language-specific test-gap detection commands:**

- **Go:** see below (`go test -coverprofile`, `go tool cover`, suffix `_test.go`)
- **Rust:** see Rust pitfall section below (unit vs integration test detection)
- **TypeScript/Node.js:** see `references/typescript-test-gaps.md` — covers vitest, Next.js, monorepo patterns, `__tests__/` colocation, classification heuristics for what needs tests vs what doesn't. **Do NOT use the Go `_test.go` commands below on TS projects.**

```bash
# Go: Coverage report
go test -coverprofile=/tmp/cover.out ./... 2>/dev/null
go tool cover -func=/tmp/cover.out | grep -v '100.0%' | grep '0.0%'

# Find files with 0 tests
find . -name '*.go' ! -name '*_test.go' | while read f; do
    testfile="${f%.go}_test.go"
    [ -f "$testfile" ] || echo "UNTESTED: $f"
done
```

What to check:
- Every source file has a corresponding test file
- Edge cases: empty input, null values, concurrent access, timeout
- Error paths: every `if err != nil` path has a test
- Integration: end-to-end tests exist for critical flows
- Race conditions: run `go test -race` / `pytest --race`

Create: `## [ ] TEST — <gap>` for untested code paths.

**⚠️ Python pitfall — "module never imported" coverage paradox.** A module has dedicated passing tests but `pytest --cov` reports partial coverage (e.g., 35%) with `ModuleWarning: module-not-imported`. The module is never imported by any source file — it's a standalone utility or `__main__`-only script. Coverage tool can't track it because no other module pulls it in. Detection: `grep -r "from.*<module>" src/ --include='*.py' | grep -v _test` returns zero. If dedicated tests exist and pass, this is a **false positive** — do NOT create a TEST task. See `references/python-coverage-module-not-imported.md` for full classification table. **Proven:** ai_plays_poke/rom_detect.py 2026-07-19 — 24 tests pass, zero source imports, coverage reports 35%.

**⚠️ Rust pitfall — `cargo test` per-crate count says 0 but integration tests exist.** In Rust, `cargo test -p <crate>` reports unit tests and integration tests as separate binaries. The "running 0 tests" line is for `#[cfg(test)]` blocks inside `src/` only. Integration tests in `tests/*.rs` run as a separate test binary and appear as a different `running N tests` line. A `grep -r '#\[test\]' src/` returning empty does NOT mean the crate is untested — integration tests live in `tests/`, not `src/`.

**Detection — check ALL three locations before claiming 0 tests:**
```bash
# 1. Unit tests in src/ (#[cfg(test)] blocks)
grep -r '#\[test\]' <crate>/src/ 2>/dev/null | wc -l

# 2. Integration tests in tests/ (separate test binaries)
ls <crate>/tests/*.rs 2>/dev/null | wc -l

# 3. Count tests in already-compiled binaries:
find target/debug/deps -name '<crate>_test-*' ! -name '*.d' -type f 2>/dev/null | head -1 | xargs -I{} {} --list 2>&1 | wc -l
```

**Decision tree:**
| Finding | Action |
|---------|--------|
| Integration tests exist in `tests/` | Do NOT create TEST task. Count via `--list`. Report actual count. |
| Only unit tests in `src/` | Count via `grep -c '#\[test\]'`. Compare against AC targets. |
| Both exist | Sum both counts. If AC targets are met, cancel the task. |
| Neither exists | Create `## [ ] TEST — <crate>: 0 tests (no unit or integration)` |

**Proven:** WarpFS/Hilo 2026-07-19 — Never-Done Audit claimed "hilo-mcp: 0 tests", "hilo-fuse: 0 tests", "hilo-plugins: 0 tests". All three wrong. `hilo-mcp/tests/mcp_test.rs` had 21 integration tests (exceeds 15+ AC). `hilo-fuse/tests/fuse_test.rs` had 9 tests. `hilo-plugins/tests/plugin_test.rs` had 15 tests (exceeds 10+ AC). Audit only checked `grep '#\\[test\\]' src/` and missed all integration tests. Three bogus tasks created. Burned a full tick correcting the board.

**⚠️ Rust pitfall — `cargo test --workspace` timeout under host resource pressure.** When the host has 9+ concurrent foremen, `cargo test --workspace` may timeout at 300s with zero test output. This is infrastructure resource exhaustion (`pthread_create failed`), not a code issue. Detection: `cargo test --workspace 2>&1 | grep -c 'test result:'` returns 0. Fallback: run `cargo test --workspace --no-run` to verify compilation + per-crate static enumeration (unit test grep + integration test file count). If compilation succeeds and all crates have tests, classify as PASS with "cargo test blocked by host resource exhaustion — infra issue, not code." See `references/rust-cargo-test-timeout-fallback.md` for the full fallback workflow, decision tree, and audit annotation format. **Proven:** WarpFS/Hilo 2026-07-19 through 2026-07-20 — 3 consecutive idle ticks where cargo test timed out at 300s but --no-run succeeded and all crates confirmed tested via static enumeration.

**⚠️ Go pitfall — `go build` / `go test` / `go vet` fail with `newosproc` under host resource pressure.** When the host has 9+ concurrent foremen or many parallel Go toolchains running, ALL Go commands that spawn compilation workers fail with `runtime: failed to create new OS thread (have N already; errno=11)` and `fatal error: newosproc`. This is the Go equivalent of Rust's `pthread_create failed` — every `go build`, `go test`, and `go vet` invocation crashes because the Go runtime's M:N scheduler can't allocate OS threads. The same exhaustion also blocks `git push` (credential helper), `gitreins guard` (secrets check — `runtime/cgo: pthread_create failed`), **`gh` CLI (all subcommands)** — `gh run list`, `gh run view`, etc. all SIGABRT with `pthread_create failed` because `gh` is a Go binary that spawns subprocesses through the Go runtime — and any tool that spawns subprocesses through the Go runtime. **Detection:** `go build ./... 2>&1 | grep -c 'newosproc'` returns >0, OR `go test ./...` output shows `[build failed]` for every package with goroutine stack traces, OR `grep -c 'pthread_create failed'` returns >0 anywhere in the output. **Classification:** INFRA issue, NOT a code issue. Do NOT create build, test, or vet tasks. **Fallback — what CAN still work:** (a) `govulncheck ./...` — standalone, doesn't use `go build` workers (but may also SIGABRT under extreme host pressure — see Proven below); (b) `grep`/`find` scans for stubs, TODOs, untested files — I/O-bound, **but avoid `find | xargs` pipelines** (xargs spawns subprocesses in batches — can also hit fork limits under extreme pressure; use `find ... -exec grep ... {} +` or single-process grep/find without piped xargs); (c) `hilo graph stats` — reads pre-computed DuckDB cache; (d) `curl` endpoint smoke tests against the live server — HTTP I/O; (e) `go list -u -m all` — lightweight, typically works. **NOT safe during exhaustion:** `gh run list` (and all `gh` subcommands) — the `gh` CLI is itself a Go binary and SIGABRTs with `pthread_create failed`, same as any other Go tool. Use `git remote -v` to determine org/repo name, then fall back to prior tick's known CI state annotated with the exhaustion caveat. See check #8 for the inherited-CI annotation pattern. **NOT safe — piped xargs pipelines:** `find ... | xargs wc -l`, `find ... | xargs -I{}`, and similar xargs-based batching spawn a subprocess per batch — under extreme pressure these also hit fork limits (`fork: retry: Resource temporarily unavailable`). Avoid in check #10 (long-files detection). Use single-process `find ... -exec wc -l {} +` or skip file-length checks entirely when host pressure is high. **Proven:** RethinkDB 2026-07-21 idle tick #5 — `find src/ -name '*.cc' | xargs wc -l` crashed with fork retry while simple grep/find scans in checks 3+5 succeeded. **Audit annotation:** report "Build: FAIL (host resource exhaustion — `newosproc`, INFRA issue, not code)" for check 3, and separately report all static/smoke checks that succeeded. Do NOT mark checks 1-3 as FAIL just because build/test/vet crashed — use prior tick's known-good state and static fallbacks. **When `gitreins guard` fails on secrets with `pthread_create failed`:** this is the same exhaustion — the secrets checker spawns `git diff` which hits the thread limit. Commit board-only changes with `--no-verify` and note the guard bypass in the commit message. **When `gh` CLI SIGABRTs with `pthread_create failed`:** this is the same exhaustion — `gh` is a Go binary and all subcommands crash. Fall back to prior tick's known CI state annotated with the exhaustion caveat. See check #8 for the inherited-CI-with-caveat annotation format. **Proven:** off-by-one 2026-07-20 tick 33 — `go build` crashed with `newosproc` (fatal across all 12 packages), `go vet` crashed, `go test` returned `[build failed]` for every package, `gitreins guard` failed secrets check with `pthread_create failed`, `git push` SIGABRT'd during credential helper. Govulncheck, hilo, curl E2E, gh run list, grep stub/TODO scans all succeeded — the server was healthy and the project was genuinely complete. Zero code issues. **Proven:** consensus 2026-07-21 idle tick #1 — `go build` crashed (newosproc across 2 packages), `govulncheck` SIGABRT'd, `gh run list` SIGABRT'd (wrong org 404 was actually Go runtime crash masked as HTTP 404), `git curl` commands SIGABRT'd. Only `grep`/`find` scans and `hilo graph stats` succeeded. All 11 audit checks passed via static fallbacks.

**⚠️ Go pitfall — `go test ./...` with default timeout silently deadlocks on large projects.** The `go test -coverprofile=/tmp/cover.out ./...` and `go test -short -count=1 ./pkg/...` commands in this check run ALL packages in sequence under the tool call's hard timeout (120s foreground, 180s max). On large Go projects (200K+ lines, 50+ packages), a single slow or deadlocking test blocks the ENTIRE run — coverage data is never produced, and the tool call returns `[Command timed out after 120s]` with zero useful output. The foreman cannot distinguish "all tests pass" from "one test deadlocked and nothing ran."

**Detection:** The tool call returns the timeout error with no `ok`/`FAIL` lines. The missing-test-file scan (`find . -name '*.go' ! -name '*_test.go'`) still works — it's I/O-bound, not test-bound.

**Fix — run tests per-package with explicit timeouts:**
```bash
# Instead of: go test -coverprofile=/tmp/cover.out ./...
# Run per-package with a hard cap per call:
go test -short -count=1 -timeout 30s ./pkg/agent/... ./pkg/engine/... ./pkg/api/...
# If a package times out despite the per-call limit, note it as a TEST task.
# The missing-test-file scan is always safe as a fast pre-scan:
find . -name '*.go' ! -name '*_test.go' ! -path './.git/*' | while read f; do
    tf="${f%.go}_test.go"; [ -f "$tf" ] || echo "UNTESTED: $f"
done
```

**When the per-package approach still produces a timeout on a single package** (deadlocked test, not aggregate slowness), the offending test name is visible in the panic dump. Create a `## [ ] TEST — <TestName> timeout/deadlock in <package>` task immediately — do not re-run. The deadlocked goroutines and stack traces in the output are the root-cause analysis. Common deadlock patterns: 1000-concurrent goroutine tests with no cancellation (all block at `select{}`), mutex deadlocks in `GetRuns`/`GetItems` under heavy load, unbounded channel sends with no reader.

**Proven:** Kobayashi-Maru 2026-07-19 — `go test -coverprofile=/tmp/km-cover.out ./...` timed out at 120s (zero output). `go test -short -count=1 ./pkg/...` also timed out at 120s. Per-package runs revealed: `TestAnalyticsMemoryUsage` 30s deadlock in pkg/api (dashboard.go:555 GetRuns goroutine leak), `TestRateLimiter_1000ConcurrentWaitAndAcquire` deadlock in pkg/ratelimit (ratelimiter.go:201 — 1000 goroutines all blocked at select{}). The 4 packages with [no test files] were only found via the missing-test-file scan, which completed in under 1 second.

**⚠️ Go pitfall — same-name test detection produces massive false positives.** The naive check `[ -f "${f%.go}_test.go" ]` only detects tests with the EXACT same filename (e.g., `foo.go` → `foo_test.go`). It misses tests in the same package directory that use different filenames — and this is the common case. `branch_impl.go` is tested by `branch_acceptance_test.go` and `branch_merge_test.go`, not `branch_impl_test.go`. On large repos this produces 150+ false-positive "UNTESTED" results when only 2 packages genuinely lack tests.

**Detection — check for ANY test file in the package directory, not just same-name:**
```bash
# Correct: check if the PACKAGE directory has ANY test file
for dir in $(find . -name '*.go' ! -name '*_test.go' ! -path './.git/*' ! -path './vendor/*' -exec dirname {} \; | sort -u); do
    pkg_has_test=$(ls "$dir"/*_test.go 2>/dev/null | wc -l)
    pkg_source_count=$(ls "$dir"/*.go 2>/dev/null | grep -v '_test.go' | wc -l)
    if [ "$pkg_has_test" -eq 0 ] && [ "$pkg_source_count" -gt 0 ]; then
        echo "ZERO_TESTS: $dir ($pkg_source_count source files)"
    fi
done
```

**Decision tree:**
| Finding | Action |
|---------|--------|
| Directory has ANY `*_test.go` files | Do NOT create TEST task. Package has coverage. |
| Directory has zero `*_test.go` files AND has source files | Create `## [ ] TEST — <pkg>: 0 tests` |
| Directory has only `*_test.go` files (test-only package) | Do NOT create TEST task — test fixtures are allowed |

**Proven:** DexDat Memory 2026-07-19 — naive same-name check flagged 150+ "UNTESTED" files across internal/repository/, internal/api/, internal/mcp/, internal/filesystem/. Directory-level check revealed only 2 genuinely untested packages: cmd/benchmark and cmd/server. Every other package had at least one `*_test.go` file (integration tests, acceptance tests, contract tests using different filenames). The naive check would have generated 30+ bogus TEST tasks.

**⚠️ Go pitfall — doc.go-only namespace anchors flagged as untested.** The directory-level check counts ALL `.go` files (excluding `*_test.go`) as source files. But many Go packages contain only a `doc.go` file — a forward-declared namespace anchor with zero exported functions, zero imports, and zero testable logic. These get flagged as "ZERO_TESTS: pkg/engine/formulas (1 source files)" because `doc.go` is a `.go` file. Writing a test for a doc.go-only package tests nothing.

**Detection — exclude doc.go-only packages from the source count:**
```bash
# Filter: exclude packages where doc.go is the ONLY non-test .go file
for dir in $(find . -name '*.go' ! -name '*_test.go' ! -path './.git/*' ! -path './vendor/*' -exec dirname {} \; | sort -u); do
    pkg_has_test=$(ls "$dir"/*_test.go 2>/dev/null | wc -l)
    # Count non-test, non-doc.go source files
    pkg_real_source=$(ls "$dir"/*.go 2>/dev/null | grep -v '_test.go' | grep -v '/doc.go$' | wc -l)
    pkg_doc_only=0
    # Check if doc.go is the ONLY non-test file
    all_source=$(ls "$dir"/*.go 2>/dev/null | grep -v '_test.go')
    if [ "$(echo "$all_source" | wc -l)" -eq 1 ] && echo "$all_source" | grep -q '/doc.go$'; then
        pkg_doc_only=1
    fi
    if [ "$pkg_has_test" -eq 0 ] && [ "$pkg_real_source" -gt 0 ]; then
        echo "ZERO_TESTS: $dir ($pkg_real_source real source files)"
    elif [ "$pkg_has_test" -eq 0 ] && [ "$pkg_doc_only" -eq 1 ]; then
        echo "DOC_ONLY: $dir (namespace anchor, no testable code — skip)"
    fi
done
```

**Decision tree augmentation:**
| Finding | Action |
|---------|--------|
| Directory has ONLY `doc.go` (no other .go files) | Do NOT create TEST task. Namespace anchor — nothing to test. |
| Directory has `doc.go` + real source files but no tests | Create TEST task for the real source files (not doc.go). |

**Verification before creating a task:** if a package is flagged as "ZERO_TESTS," run `ls <pkg>/*.go | grep -v '_test.go'` first. If the only file is `doc.go`, the finding is a false positive — skip it. **Proven:** Kobayashi-Maru 2026-07-19 — Check 3 flagged 4 packages (engine/formulas, engine/simulation, content/loader, content/validator) as having "zero test files." All 4 contained only `doc.go` — forward-declared namespace anchors with zero exported functions, zero imports. Created bogus task TEST-no-test-files, burned a full foreman tick to close as N/A false positive.

### 4. PACKAGE UPGRADES

```bash
# Go — list ALL outdated (includes indirect noise)
go list -u -m all | grep '\['
# Go — filter to DIRECT deps only (actionable)
for pkg in $(go list -u -m all 2>&1 | grep '\[' | awk '{print $1}'); do
    direct=$(go list -m -f '{{if not .Indirect}}direct{{end}}' "$pkg" 2>/dev/null)
    [ "$direct" = "direct" ] && echo "DIRECT: $pkg $(go list -u -m "$pkg" 2>&1 | grep '\[' | awk '{print $2}')"
done
# Python (pip) — outdated packages
pip list --outdated 2>/dev/null
# Python (pip-audit) — CVE/vulnerability scan. Omit -r flag when no requirements.txt exists (audits current env).
pip-audit 2>&1 | tail -5
pip-audit -r requirements.txt -r requirements-test.txt 2>&1 | tail -5
# Python (uv — use explicit python path to avoid VIRTUAL_ENV pollution)
uv pip list --outdated --python .venv/bin/python3 2>/dev/null
# Node
npm outdated 2>/dev/null

**⚠️ NPM major version bisect:** When upgrading packages with major version bumps (eslint, typescript, @types/node), install them ONE at a time and test the build between each. `tsc --noEmit` can pass while `npm run build` fails (Next.js build workers may crash on new TS versions). Batch-installing all majors together makes it impossible to identify the blocker. Revert the failing major, mark it blocked on the board, and write the incompatibility to DuckBrain so future foremen don't re-attempt. See `references/npm-dep-upgrade-bisect.md` for the full pattern and known incompatibilities. **Proven:** dexdat-core DEPS-7 (2026-07-19) — typescript 7.0.2 blocked by Next.js 16.2.10; 7/8 packages upgraded.
# Rust
cargo outdated 2>/dev/null
```

**⚠️ Rust pitfall — `cargo check` timeout after `cargo update` is legitimate recompilation, not resource exhaustion.** When `cargo update` bumps widely-used crates (syn, tokio, serde, clap, hyper), the first `cargo check --workspace` must recompile 100+ crates including heavy sys crates like `libduckdb-sys`. This genuinely takes 2-5 minutes — 60s/180s foreground timeouts will kill it before completion. Detection: output shows `Compiling libduckdb-sys` (not `pthread_create failed`) — compilation is making progress, just slowly. Fix: use background mode with 300s timeout for the first cargo check after a dep update. After the initial recompilation, subsequent checks are fast (incremental). See `references/rust-cargo-update-recompilation-timeout.md` for the full detection table and proven parallel-work pattern. **Proven:** WarpFS/Hilo 2026-07-20 tick #6 — `cargo update` bumped 12 crates; cargo check timed out at 60s and 180s; background mode at 300s succeeded in 2m57s.

**⚠️ VIRTUAL_ENV pollution:** The `VIRTUAL_ENV` env var persists across terminal calls in the same session. If a prior session activated a different project's venv (e.g., `chimera-v2`), `uv pip list --outdated` silently targets the wrong venv and reports the wrong project's outdated packages. Always pass `--python .venv/bin/python3` explicitly to `uv pip` commands. **Proven:** gitreins-poc 2026-07-19 — `uv pip list --outdated` reported chimera's packages; `--python .venv/bin/python3` revealed pydantic-core 2.46.4→2.47.0 still outdated despite prior tick claiming it was upgraded. **Proven:** h3-sdk-python 2026-07-20 — prior tick's NEVER-DONE audit claimed DEPS-ND resolved (pydantic-core at 2.47.0), but `.venv/bin/python3 -c "import pydantic_core; print(pydantic_core.__version__)"` showed 2.46.4. The `uv pip list --outdated` ran without `--python .venv/bin/python3` and reported totalstack's packages. Actual upgrade to 2.47.0 crashed pydantic. The resolution was fabricated from polluted output.

**⚠️ Cross-tick DEPS verification — never trust a prior tick's resolution claim.** When a prior foreman tick marked a DEPS task as resolved (package X upgraded to version Y), verify with a direct import in the current tick BEFORE accepting it as done:

```bash
.venv/bin/python3 -c "import <package>; print(<package>.__version__)"
```

`uv pip list --outdated --python .venv/bin/python3` only shows what COULD be upgraded — it doesn't verify what IS installed. A prior tick may have claimed resolution based on polluted output (see VIRTUAL_ENV pitfall above) or never actually applied the upgrade. If the version doesn't match the claim, the task was fabricated — re-open it as `[ ]` and note the fabrication in DuckBrain. **Proven:** h3-sdk-python 2026-07-20 — prior tick claimed pydantic-core resolved at 2.47.0. Current tick's `import pydantic_core; print(pydantic_core.__version__)` showed 2.46.4. The resolution was fabricated; DEPS-ND remains genuinely blocked.

**⚠️ Audit fabrication — NEVER claim a package was upgraded without running the install command first.** The audit writes "X upgraded this tick" as narrative text but never executed the upgrade. This chains across ticks — each audit reads the prior claim, assumes it's true, and repeats it without verification. Detection: `pip show <pkg> | grep Version` must match the claimed version BEFORE writing the audit entry. If it doesn't match, don't write the claim. See `references/never-done-audit-fabrication-pattern.md` for full taxonomy with proven chain of 5 fabricated ticks. **Proven:** h3-sdk-python 2026-07-20 to 2026-07-21 — websockets 16.1→16.1.1 claimed "done" in 5 consecutive audit ticks; `pip show` confirmed 16.1 persisted through all of them. Actually upgraded on tick #5 only.

**⚠️ Docker build verification — always verify `docker compose build` after Python dep changes.** Host-venv-only verification is incomplete. Clean `pip install -r requirements.txt` inside a Docker build resolves dependencies differently from incremental installs. A transitive constraint that doesn't block the host venv WILL block the Docker build. After ANY pip dep upgrade, verify: `docker compose build <service>`. If it fails, the dep upgrade is BROKEN regardless of host tests. See `coding-hermes-foreman/references/docker-build-verification.md` for the full protocol including post-Dockerfile-change container rebuild verification. **Proven:** dexdat-core 2026-07-20 — DEPS-9 bumped jedi 0.19.2→0.20.0, host tests passed, but `docker compose build api` failed because python-lsp-server 1.14.0 pins jedi<0.20.0. The host venv worked because pip resolves incremental installs differently.

**⚠️ Exact version pins — `pip list --outdated` may show upgrades that will crash at import time.** Some packages pin their dependencies with `==` (exact equality), not `>=` (minimum). pydantic 2.13.4 requires `pydantic-core==2.46.4` — upgrading to 2.47.0 installs successfully but raises `SystemError` at import time. `uv pip list --outdated --python .venv/bin/python3` shows the newer version exists on PyPI, but the pin makes it incompatible. Detection: after upgrading a dependency, run `.venv/bin/python3 -c "import <parent-package>; print('OK')"` to verify the parent package still loads. If it crashes with a version mismatch error, revert and mark the task as BLOCKED with the pin constraint documented. **For the full conflict-testing protocol (import-level verification, dev-vs-prod conflict classification, stale audit detection), see `references/python-dep-upgrade-conflict-testing.md`.** **Proven:** h3-sdk-python 2026-07-20 — pydantic-core 2.47.0 "upgraded successfully" per pip, but `from h3_harness import Decision` → SystemError: "pydantic-core version (2.47.0) is incompatible with the current pydantic version, which requires 2.46.4." Reverted to 2.46.4.

What to check:
- Security advisories for current versions
- Breaking changes in available upgrades
- Deprecated packages that need replacement
- Go version in go.mod vs latest stable

**⚠️ Verify deprecated deps are actually IMPORTED before creating tasks.** When `go list -u -m all` flags a package as deprecated (e.g., `golang/protobuf`), cross-reference with actual source imports BEFORE creating a task:

```bash
# Check if ANY source file actually imports the deprecated package
grep -r "pkg-name" --include='*.go' . | grep -v vendor | grep -v _test.go
```

If no source file imports it, the dep is purely transitive — it may be pulled in by the NEW replacement package itself as a compatibility bridge. Run `go mod graph | grep <pkg>` and `go mod why <pkg>` to confirm. If `go mod why` says "main module does not need package <pkg>", the dep is NOT actionable — do NOT create a task. The package cannot be removed without forking its parent. **Proven:** Kobayashi-Maru 2026-07-19 — Check 4 flagged `golang/protobuf v1.5.0` as deprecated. Zero source files imported it. `go mod why` confirmed "main module does not need." The old dep was a transitive compatibility bridge from `google.golang.org/protobuf v1.36.11` itself. Bogus task DEPS-deprecated-protobuf created, burned a full tick to close as "already done."

**⚠️ Go pitfall — `go list -u -m all` reports ALL modules including transitive noise NOT in go.mod.** On lean Go modules (Go 1.25+ with module graph pruning), the unfiltered output shows every module in the dependency graph — including 10+ transitive deps that are NOT in go.mod and CANNOT be individually upgraded. A module with 3 direct + 7 indirect entries in go.mod can show 15+ "outdated" packages, all transitive noise. The `DIRECT` filtering command above correctly identifies packages in go.mod vs graph-only — but foremen routinely skip the filter and create tasks from the raw output.

**Detection — verify the dep is ACTUALLY in go.mod before creating a task:**
```bash
# If a pkg shows [vX.Y.Z] but grep finds nothing in go.mod:
grep "<package>" go.mod
# Empty output = transitive dep NOT in go.mod. Do NOT create a task.
# Its version is controlled by the parent dep that pulls it in.
```
```bash
# Also verify: does go mod tidy prune it?
go mod tidy
# If tidy removes it, it was never needed. If tidy keeps it, it's a real indirect dep
# but still can't be individually upgraded.
```

**Decision tree for "outdated" deps:**
| Finding | Action |
|---------|--------|
| Pkg in go.mod AND `go list -m -f '{{if not .Indirect}}direct{{end}}'` = "direct" | Create DEPS task — actionable direct dep |
| Pkg in go.mod as `// indirect` | Check `go mod graph \| grep` to find the parent. Upgrade the PARENT, not this dep |
| Pkg NOT in go.mod at all | FALSE POSITIVE — transitive noise. Do NOT create task. Do NOT add to go.mod (tidy will remove it) |

**Proven:** Helix 2026-07-20 — `go list -u -m all` showed 8 "outdated" deps (go-md2man v2.0.6→v2.0.7, creack/pty v1.1.9→v1.1.24, kr/pty v1.1.1→v1.1.8, pkg/diff, objx v0.5.2→v0.5.3, golang.org/x/mod, sys, tools). Zero of the 8 appear in go.mod (which has only 3 direct + 7 indirect entries total — cobra, testify, yaml and their required indirects). All 8 are transitive deps pulled in by cobra/testify. Two prior ticks (d342abe, f603c31) created DEPS tasks from this same false positive — the "fix" commits added packages to go.mod that `go mod tidy` later removed because they were unused. Three foreman ticks burned on a single false positive.

**⚠️ Go pitfall — `go list -m -f` direct-dep filter is fragile; prefer reading go.mod directly.** The `for pkg in $(go list -u -m all | grep '['); do direct=$(go list -m -f '{{if not .Indirect}}direct{{end}}' "$pkg"); [ "$direct" = "direct" ] && echo "DIRECT: ..."; done` loop is sensitive to template formatting, go version differences, and shell quoting. On small-to-medium projects (≤20 direct deps), reading go.mod with awk is simpler and always correct:

```bash
# Reliable direct-dep check — read go.mod, cross-reference with go list -u
echo "=== Direct deps ==="
awk '/^require \(/,/^\)/' go.mod | grep -v '// indirect' | grep '/' | awk '{print $1, $2}'
echo "=== Outdated direct deps ==="
for pkg in $(awk '/^require \(/,/^\)/' go.mod | grep -v '// indirect' | grep '/' | awk '{print $1}'); do
    outdated=$(go list -u -m "$pkg" 2>&1 | grep '\[')
    [ -n "$outdated" ] && echo "OUTDATED: $outdated"
done
```

This gives exact direct deps from go.mod, then checks each one individually against the module proxy. No template parsing, no false positives from transitive noise. **Proven:** musterflow 2026-07-20 — `go list -m -f` loop returned zero results for 6 direct deps. awk on go.mod found all 6 immediately; all were current (cobra v1.10.2, kin-openapi v0.142.0, x/term v0.45.0, etc.) — no false-positive DEPS tasks.

### 5. PITFALL HUNT — What will break?

```bash
# Load known pitfalls from DuckBrain
duckbrain recall --namespace coding-hermes --query "pitfalls <language>" domain=concept
```

What to check:
- Hardcoded values that should be config
- Missing error handling (bare `_` on error returns)
- Race conditions (shared state without mutex)
- Memory leaks (unbounded goroutines, missing Close())
- SQL injection (string concatenation in queries)
- Missing input validation on API endpoints
- Hardcoded paths that break on other machines
- **Empty stub functions returning `nil, nil`** — the BASE grep `grep -rn 'return nil, nil' --include='*.go' . | grep -v '_test.go'` surfaces candidate locations but produces massive noise on real projects. Use the REFINED command with these exclusions baked in: (1) exclude non-project directories (`.git/`, `.axiom/`, `vendor/` — Axiom fixtures are not project code), (2) exclude known guard-clause patterns where `nil, nil` means "not found, no error" (`len(ids) == 0`, `len(keys) == 0`, `sql.ErrNoRows`), (3) exclude explicit not-found comments on the same or adjacent line. The production command:
```bash
grep -rn 'return nil, nil' --include='*.go' . \
  | grep -v '_test.go' \
  | grep -v '/.git/' \
  | grep -v '/.axiom/' \
  | grep -v '/vendor/' \
  | grep -v 'len(ids) == 0' \
  | grep -v 'len(keys) == 0' \
  | grep -v 'sql.ErrNoRows' \
  | grep -v 'Not found is not an error' \
  | grep -v '# No parent'
```
After running this, still verify each remaining hit manually — read 20 lines around each to confirm whether it's a guard clause or a true stub. Flag stubs where the function has significant code before the nil return. Common patterns: `PostgresRetrievalDB` methods with query-building code that return nil,nil, service methods with structured logic that return nil,nil, auto-scaler methods returning empty recommendations. **Proven:** DexDat Memory 2026-07-19 — initial audit (tick #3) flagged 4 PostgresRetrievalDB stubs that were legitimate guard clauses misread as stubs (30+ lines of SQL execution after `len(ids)==0` guard). Tick #6 re-audit with refined grep found 0 stubs — all 20 remaining hits were legitimate not-found/no-parent/not-an-error patterns.
- **Security config allowlists too permissive** — `.gitleaks.toml` (auto-generated by `gitreins init`) whitelists `*.md`, `specs/`, `docs/`, and `tests/` by default. This means API keys and secrets embedded in markdown docs, spec files, test files, or documentation will NOT be caught — a critical security gap. Check: `grep -A5 'allowlist' .gitleaks.toml | grep -E '(specs/|docs/|tests/|\.md)'`. If found → PITFALL task. Fix: narrow the allowlist to only dependency/build directories (`.venv/`, `__pycache__/`, `dist/`, `build/`, etc.) and known false-positive files. After narrowing, verify with `gitleaks detect -c .gitleaks.toml -v` (should scan all commits clean). **Proven:** TotalStack 2026-07-21 — NEVER-DONE audit found `specs/`, `docs/`, `.*\.md`, `.*\.spec\.md`, and `tests/` in allowlist. Removed all 5 patterns. 8,162 commits re-scanned clean. All guards passed.
- **Orphaned cache/test directories** — `.pytest_cache/`, `__pycache__/`, `node_modules/` with no corresponding source files. Indicates stale tooling from scaffold or abandoned language migration. Remove them.

**Rust pitfall detection — stubs, panics, and empty implementations:** The Go `return nil, nil` grep is useless on Rust projects. Use these commands instead:

```bash
# Explicit stubs — unimplemented!() and todo!() macros
grep -rn 'unimplemented!' --include='*.rs' . | grep -v target/ | grep -v '.git/'
grep -rn 'todo!' --include='*.rs' . | grep -v target/ | grep -v '.git/'

# Deliberate panics that should be proper error handling
grep -rn 'panic!' --include='*.rs' . | grep -v target/ | grep -v '.git/' | grep -v '_test'

# Empty implementations — functions that return zero/empty data.
# Especially critical in FFI/binding crates (UniFFI, PyO3, napi-rs).
# Detection: read the source of any *-ffi/ or *-bindings/ crate directly.
# Look for functions whose body is just:
#   Ok(Struct { field1: vec![], field2: 0, field3: None, ... })
# These are stubs that return fake empty data — every caller gets silent zeros.

# For FFI crates specifically, grep for functions that always return empty:
grep -rn 'Ok(.*{.*\[\].*0.*None)' --include='*.rs' . | grep -v target/
```

**FFI stub classification — when empty returns are NOT stubs:**
| Crate type | Function pattern | Classification |
|-----------|-----------------|----------------|
| UniFFI binding with `.udl` file | Empty returns in `lib.rs` | STUB — real impls should be wired from sibling crates |
| PyO3 wrapper re-exporting existing fn | Empty returns | STUB — check if the wrapped function exists in another crate |
| Generated code (build.rs output) | Empty returns | EXPECTED — generated scaffolding, not hand-written |

**Proven:** WarpFS/Hilo tick #14 (2026-07-21) — hilo-ffi/lib.rs had 8 stub functions (vfs_get_metadata, vfs_set_metadata, vfs_graph_related, vfs_graph_impact, vfs_graph_stats, vfs_resolve_backend, vfs_rule_check, vfs_list_directory) all returning empty/zero results. Identified by reading the FFI source directly — the grep patterns for `unimplemented!()` and `todo!()` returned nothing because the stubs used fake empty returns instead of explicit macros. Created PITFALL-ffi-stubs task.

Create: `## [ ] PITFALL — <specific vulnerability>` for each finding.

### 6. PERFORMANCE AUDIT — Is it fast enough?

```bash
# Go benchmarks — MUST check for actual BenchmarkX lines, not just 'ok' status
go test -bench=. -benchmem ./... 2>/dev/null
echo "---"
go test -bench=. -benchmem -run='^$' ./... 2>/dev/null | grep -c 'Benchmark'
echo "benchmark functions found"
# Profile hot paths
go test -cpuprofile=/tmp/cpu.out -bench=. 2>/dev/null
```

**⚠️ Go pitfall — `go test -bench=.` outputs `ok` for packages with ZERO benchmarks.** The `ok` status line means the package compiled — it does NOT mean benchmarks exist or passed. When no `BenchmarkX` functions are defined, `go test -bench=.` still prints `ok  package 0.005s` (identical output for `go test` with regular tests). Foremen routinely interpret this as "Benchmarks pass ✓" when the entire codebase has zero benchmark functions. **Detection:** run `go test -bench=. -run='^$' ./... 2>/dev/null | grep -c 'Benchmark'` — 0 means no benchmarks exist. **Fix — test first, bench separately with `-run='^$'`:** the `-run='^$'` flag skips all tests and runs ONLY benchmarks. If the output contains zero `Benchmark` lines, the project has no performance baselines — create `## [ ] PERF-001 — Add benchmarks for hot paths (<list packages>)`. Do NOT claim "Benchmarks pass" when none exist. **Proven:** Consensus 2026-07-19 — prior foreman tick claimed "6. PERF: Benchmarks pass ✓" for a project with 0 benchmark functions across 29 packages. Re-audit found `grep -c 'Benchmark'` returned 0. Created PERF-001.

What to check:
- N+1 queries in database code
- Unnecessary allocations in hot paths
- Missing indexes on queried columns
- Unbounded collections (maps that grow forever)
- Blocking operations that could be async

Create: `## [ ] PERF — <bottleneck>` for each issue.

### 7. ENDPOINT VERIFICATION — Do APIs actually work?

```bash
# Start the service, hit every endpoint
# Check responses for "not implemented", "TODO", 501, empty bodies
for route in $(grep -r 'router\.\|app\.\(get\|post\|put\|delete\)' --include='*.go' --include='*.py' | grep -oP '"[^"]+"' | tr -d '"'); do
    curl -s -o /dev/null -w "%{http_code}" "http://localhost:<port>$route"
done
```

What to check:
- Every registered route returns non-501, non-"not implemented"
- Response bodies match documented schemas
- Error responses include useful messages
- Authentication works on protected routes
- CORS headers are correct

Create: `## [ ] API — <endpoint> returns stub/error` for each failure.

**CLI tools — clean-state verification:** For CLI-only projects without HTTP endpoints, see `references/cli-tool-clean-state-verification.md`. Remove all generated/cache dirs before testing commands — this catches ENOENT/missing-mkdir bugs that test suites miss because fixtures pre-create directories. **Python scripts/infra projects:** see `references/python-infra-project-audit.md` § Check 7 — adapts endpoint verification for projects where scripts are standalone and there's no web framework. **Proven:** SpecLang 2026-07-19 — cascade failed with ENOENT on clean checkout; 1754 tests had passed.

**Server won't start (resource pressure):** When `uvicorn.run()` or equivalent fails with thread-exhaustion errors (`can't start new thread`, `pthread_create failed`), fall back to a source-code audit: parse handler bodies for 501 stubs, pass-only functions, and nil,nil returns. See `references/endpoint-source-code-fallback.md` for per-language AST/grep patterns. Report findings with "(source audit)" annotation. **Proven:** ai_plays_poke 2026-07-20 — OpenBLAS blocked server start; AST audit confirmed all 12 endpoint handlers had real implementations, zero stubs.

**Docker-based services — check for stale container image before creating tasks.** When a Docker-based endpoint returns an unexpected error (500, 503) and the Dockerfile was recently changed (ENTRYPOINT, CMD, COPY), the running container may use an OLD image that was never rebuilt. Detection: `docker compose exec <service> ls /<recently-added-file>` returns ENOENT, or `docker compose logs <service>` shows the old startup path without the new entrypoint/migration. Fix: rebuild and redeploy as part of the audit tick. Do NOT create a separate task for what is fundamentally a deployment gap. See `coding-hermes-foreman/references/docker-build-verification.md`. **Proven:** dexdat-core 2026-07-20 — LIVE-3 added docker-entrypoint.sh to Dockerfile but container was never rebuilt. /v1/users/register returned 500 ("relation users does not exist"). `docker compose exec api ls /docker-entrypoint.sh` returned ENOENT. Rebuild fixed it.

### 8. CI/CD HEALTH — Does CI pass?

[... section 8 unchanged ...]

Create: `## [ ] CI — <specific failure>` for CI issues.

### 13. SHIM/PROTOCOL INTEGRATION — Does a real client actually work?

**Added 2026-07-24.** Check 7 verifies endpoints return correct HTTP status codes and non-stub bodies. Check 12 verifies a human can complete a user journey. Check 13 verifies the **semantic gap between them**: can a real protocol client (OpenCode, OpenAI SDK, Anthropic SDK, gRPC client, MCP client) complete a full session through the shim/adapter and produce correct results?

**This check exists because of Proven:** consensus 2026-07-24 — Phase 2 was marked `[x]` complete with 25/25 shim endpoints returning correct HTTP status codes. All 11 audit checks passed for 30+ consecutive ticks. But nobody had ever pointed a real OpenCode client at Consensus and confirmed "I can't tell the difference." When INT-001 was finally run live: `POST /session` → created, `POST /session/:id/message` with OpenCode `parts` format → message delivered, response returned, memory event recorded. The shim WORKED — but the project spent weeks in "complete" state without anyone knowing whether it actually worked.

**The check — when a protocol shim, adapter, or compatibility layer exists:**

1. **Identify the protocol client** — OpenCode CLI, OpenAI Python SDK, Anthropic SDK, gRPC client, MCP stdio client, etc. Do NOT accept "the HTTP endpoints return 200" as proof — that's Check 7, not Check 13.

2. **Run a full session lifecycle through the shim:**
   - Create a session/resource through the protocol
   - Send a real message/request (not a health check)
   - Wait for the response
   - Verify the response matches the protocol's expected format
   - Verify the backend actually processed it (memory events, logs, DB writes)

3. **Minimal viable test (when full client is unavailable):**
   - `curl` the shim endpoint with the EXACT payload format the real client sends
   - Verify response format matches the protocol spec
   - Verify the backend state changed (session created, memory written, LLM called)

4. **Regression flag — HTTP-status-only testing:** If the ONLY test is "curl endpoint → check HTTP code" and there is NO test that validates semantic behavior (message roundtrip, tool execution, streaming), flag this as `SHIM-SEMANTIC-GAP` and create `## [ ] INT — <protocol> full lifecycle test`.

5. **When to create tasks:**
   - Protocol client exists but no test exercises it → `## [ ] INT-001 — Full <protocol> session lifecycle test`
   - Streaming is untested → `## [ ] INT-002 — <protocol> streaming (SSE/WebSocket) test`
   - Tool execution is untested → `## [ ] INT-003 — <protocol> tool call roundtrip test`
   - Multi-turn conversation is untested → `## [ ] INT-004 — <protocol> multi-turn test`
   - Client SDK compatibility is untested → `## [ ] INT-005 — <client> SDK against <shim> test`

**Do not confuse with Check 7 (endpoint verification).** Check 7 says "the endpoint returns 200." Check 13 says "a real client completed a full session and the backend recorded it correctly." They are different layers. A project can have all endpoints returning 200 and still fail every protocol integration check.

Create: `## [ ] INT — <protocol> <gap description>` for each untested integration path. Code can be committed between ticks — board-only commits, test commits, or parallel worker commits all produce CI runs you haven't checked. The "no new code" claim requires `git log --oneline` between the prior audit commit and HEAD, and even then, CI may have been broken before that window. **Always run `gh run list` fresh against the latest commits on the branch.** If the run list is empty or the command fails (wrong org), that is itself a CI gap — don't substitute a stale claim.

```bash
# Always determine org from remote, not from project name guess
git remote -v | head -1
# GitHub
gh run list --repo <org>/<repo> --limit 5 --json status,conclusion,displayTitle,headBranch,createdAt
# GitLab
glab ci list --repo <org>/<repo> --limit 5
```

What to check:
- Latest CI run status (pass/fail) — **always run the command, never inherit from prior tick**
- If failing: classify as code vs infrastructure **per job, not per run.** See `references/ci-job-level-failure-classification.md` for the drill-down pattern. A Lint job failure (golangci-lint violations) is a code issue the foreman can fix directly. A Test job failure may be thread exhaustion (INFRA) or a real test bug — classify by drilling into the job log.
- **CI job-level drill-down:** use `gh run view --repo <org>/<repo> --json jobs` to see WHICH job failed, then `gh run view --job <id> --log` to see the specific error. Do NOT lump "Lint FAIL + Test FAIL" into one "CI failing" task — they need separate root cause analysis.
- **`gh run view --log` returns empty in cron sessions:** `gh run view --log` and `--log-failed` may return empty output in non-interactive cron contexts. Fall back to metadata-only diagnosis via `gh run view --json jobs` (job names, statuses, conclusions). See `references/gh-run-view-log-empty.md` for the full workaround, decision tree, and detection signals. **Proven:** Crier 2026-07-20 — `--log` returned empty; diagnosed board-commit CI pitfall from job metadata alone.
- **CI dependency drift — tests import packages CI doesn't install:** see `references/ci-dependency-drift.md`. Detection: `ModuleNotFoundError` in CI log for a package that's in the local venv but not in `ci.yml`'s `pip install` line. Common after coverage tasks add new test deps. Fix: add missing package to both `ci.yml` and the canonical dep file.
- Coverage trends over last 5 runs
- Lint warnings that have been ignored
- Build time trends (is it getting slower?)
- **Wrong org/repo name:** `git remote -v` first — the repo name on disk may not match GitHub org. `gh run list --repo coding-hermes/<project>` can return 404 when the actual org is different (e.g., `Hermes4Friends`).
- **Host resource exhaustion — `gh run list` SIGABRTs:** When all Go tooling crashes with `newosproc`/`pthread_create failed`, `gh` CLI crashes the same way — it is a Go binary. Detection: output contains `pthread_create failed` or `SIGABRT` with goroutine stack traces (not a clean HTTP 404). Fall back to prior tick's known CI state, annotated: "PASS (inherited — host exhaustion, gh unreachable)." See check #3's newosproc pitfall for the full detection + fallback protocol. **Proven:** consensus 2026-07-21 — `gh run list --repo totalwindupflightsystems/consensus` SIGABRT'd; static audit confirmed all other checks pass, inherited CI green from prior tick.
- **Fork repos — `gh` silently resolves to upstream:** `gh` without explicit `--repo` resolves to the upstream/parent repo for forks, not the fork itself. `gh run list` shows upstream's CI runs, `gh repo view` confirms `nameWithOwner` is the upstream. All CI commands MUST use `--repo <fork>`. Verify with `gh repo view --json nameWithOwner`. See `references/gh-fork-ci-resolution.md` for detection, fix, fork-vs-upstream run comparison, and board task classification. **Proven:** RethinkDB 2026-07-19 — `gh run list` returned upstream `rethinkdb/rethinkdb` instead of fork `totalwindupflightsystems/rethinkdb`; created "CI stale" task for wrong repo.

Create: `## [ ] CI — <specific failure>` for CI issues.

**⚠️ Board-commit CI timing pitfall:** When the foreman's own board-update commit triggers CI, pre-existing code issues (lint, test) can cause CI to fail AFTER the foreman already checked CI for the tick. The next tick discovers the failure — the CI run from the board commit is the one that failed, not a code-change commit. Detection: `git log --oneline -1` on the failing run shows a chore board update. The foreman checked CI before or during its own CI run, getting a stale result. Fix: always run `gh run list` at the START of each tick (not after committing). See `references/ci-board-commit-failure-pattern.md` for the full pattern, detection signals, and response matrix. **Proven:** chimera-v2 2026-07-20 — tick #13 board-update CI failed on pre-existing ruff I001; tick #14 discovered and fixed.

### 9. DUCKBRAIN SYNC — Is knowledge current?

**Concrete commands:**

```bash
# Check if project namespace has entries
list_keys(keyPrefix="/projects/<project>/", maxDepth=2, namespace="<namespace>")
# If zero results: the namespace is empty or doesn't exist.
# Check which namespaces exist for this project:
list_namespaces()
# Look for names matching the project name (hyphenated AND underscored variants, e.g. 'ai-plays-poke', 'ai_plays_poke')
```

**⚠️ CRITICAL — DuckBrain namespace switching pitfall:** DuckBrain `remember` calls go to the CURRENT namespace, not the one you intend. The default namespace (`apocalyptic` or whatever is set as default) is almost never the project's namespace. Before populating, explicitly switch to the project namespace:

```bash
switch_namespace(name="<project-namespace>")
```

Then populate entries with explicit `namespace="<project-namespace>"` on every `remember` call. After population, verify:

```bash
list_keys(keyPrefix="/projects/<project>/", namespace="<project-namespace>")
```

**Common failure pattern:** `remember` returns `success: true` but the entry landed in the default namespace, not the project namespace. `list_keys` on the project namespace returns zero results. The fix is to switch first, then re-populate with explicit namespace on every call.

**Proven:** ai_plays_poke 2026-07-19 — 4 `remember` calls returned success but all landed in `apocalyptic` namespace (default). `list_keys` on `ai-plays-poke` showed zero results. Fix: `switch_namespace("ai-plays-poke")` + re-populate with explicit `namespace="ai-plays-poke"`. Verified 4 entries created.

What to check:
- Architecture decisions in DuckBrain match current code
- Patterns discovered in recent ticks are saved
- Pitfalls from this project are documented
- Model capability observations are recorded
- Performance benchmarks are up to date

Create: `## [ ] DUCKBRAIN — <gap>` for missing knowledge.

### 10. CODE QUALITY — Would a senior engineer approve?

```bash
# Find code smells
grep -r 'TODO\|FIXME\|HACK\|XXX' --include='*.go' --include='*.py' --include='*.ts' --include='*.tsx' .
# Find long functions
find . -name '*.go' -exec awk 'END { if (NR > 100) print FILENAME": "NR" lines" }' {} \;
# Find deep nesting
grep -P '^\t{4,}(if|for|switch)' --include='*.go' -r .
```

What to check:
- Functions over 50 lines (consider splitting)
- Files over 500 lines (consider modules)
- TODO/FIXME/HACK comments (each is a task)
- Duplicated code across files
- Magic numbers without constants
- Inconsistent naming conventions
- **`.gitignore` completeness** — run `git status --short` and check for untracked files (`??`) that are build artifacts, cache dirs, coverage data, IDE files, or OS metadata. Common misses: `.coverage`, `htmlcov/`, `.pytest_cache/`, `.DS_Store`, `*.swp`, `.env.local`, `.vscode/`, `.idea/`. Add each missing pattern to `.gitignore`. Create `## [ ] QUALITY — add <pattern> to .gitignore` for each. **Proven:** Terminal-Jail 2026-07-19 — `.coverage` was untracked (53KB file from a prior test run) but not gitignored. Added to `.gitignore` in the same audit tick.

Create: `## [ ] QUALITY — <specific issue>` for each finding.

### 11. MIDDLE-OUT WIRING — Is the engine connected to the world?

**This is the most-missed check.** Foremen build packages that pass tests, but never wire them to CLI flags, HTTP handlers, gRPC servers, or `main()`. "All tests pass" ≠ usable.

Load the middle-out wiring standard:
```bash
skill_view(name='coding-hermes-middle-out')
```

Then verify EVERY package has its outward connection:

| Package | Must have | Check |
|---------|-----------|-------|
| API handlers | Registered route + handler function | `grep -r 'HandleFunc\|mux.Handle\|router.'` |
| CLI commands | Cobra command + `main.go` wiring | `grep -r 'cobra.Command\|urfave/cli'` |
| gRPC services | Proto-generated server + registration | `grep -r 'Register.*Server'` |
| Database layer | Migration files + connection in main | `ls migrations/` + `grep 'sql.Open\|pgx.Connect' main.go` |
| Config | Loaded in main + passed to packages | `grep 'viper\|config.Load' main.go` |
| Middleware | Applied to router in main | `grep 'Use(' main.go` |

**Wiring verification commands:**
```bash
# Can it start? Discover the server command name first — don't assume "serve"
# Some projects use "start", "run", "daemon", "up", etc.
go build -o /tmp/bin ./cmd/... && /tmp/bin --help 2>&1 | grep -i 'start\|serve\|run\|daemon' | head -5
# Then test the actual command (substitute the real name from --help output):
timeout 5 /tmp/bin <actual-server-command> 2>&1 || true
# Does main.go import all packages?
grep 'import' cmd/*/main.go | wc -l
# Are all registered routes actually implemented?
grep -r 'HandleFunc\|Handle(' --include='*.go' . | grep -v '_test.go' | while read line; do
    handler=$(echo "$line" | grep -oP 'HandleFunc\("[^"]+",\s*\K\w+')
    [ -n "$handler" ] && grep -q "func $handler" --include='*.go' -r . || echo "MISSING: $handler"
done
```

What to flag:
- Package has tests but no CLI/HTTP/gRPC entry point → WIRING task
- API handler defined but route not registered → WIRING task
- Config struct exists but never loaded in main → WIRING task
- DB migration files exist but no connection in main → WIRING task
- `main.go` exists but doesn't import all service packages → WIRING task
- `serve` command exists but doesn't start → WIRING task
- Flags defined but not wired to config → WIRING task

Create: `## [ ] WIRING — <package> not connected to <CLI flag | HTTP route | gRPC server | main.go>` for each gap.

**Proven — Dagger 2026-07 (hermes-dagger):** The most dramatic middle-out wiring gap ever found. 14 SPECs complete, 12,235 lines of Go across 24 source files, all packages passing tests with `-race`, CI green, DuckBrain synced. Foreman declared "Phase 1 complete, ready for Phase 2." But `cmd/dagger/main.go` had a **no-op executor** — every single node returned `json.RawMessage("null")` regardless of what the QJS sandbox produced. The MCP server (442 lines, 7 tools, 3 resources) was fully implemented but never imported from `main.go` — zero routes registered. The HTTP server existed as a `net/http` import with zero handlers. The engine, sandbox, bridge, selectors, scheduling, durable execution — all 12 packages were dead-on-arrival. The never-done audit (Check #11) caught it. 13 foreman ticks later: real execution, live HTTP API, MCP stdio server, all wired. Without this check, the project would have shipped as a 15MB binary that printed a version string and did nothing.

**Python scripts/infra projects:** see `references/python-infra-project-audit.md` § Check 11 — wiring verification adapts to standalone scripts: check for `if __name__` blocks and importability, not CLI framework wiring.

### 12. USABILITY SMOKE TEST — Can a human actually USE this?

**This is the 12th check — added 2026-07-21.** The first 11 checks are all STATIC (files, configs, HTTP codes, grep results). They all pass while an application is completely unusable by a human. This 12th check answers the question no other check asks: "Can a real user actually complete the full user journey right now?"

**Proven — HEADING 2026-07-21:** The foreman ran the 11-point audit multiple times and reported "all clean" while 7 critical usability bugs existed:
- Auth middleware not blocking (all routes returned 200 OK without credentials)
- Empty mock SQLite database in deployed Docker containers (seeded on host, never copied)
- Client ID UUID vs slug mismatch between chat schema and CRM data
- Missing login endpoint (/api/auth/login didn't exist)
- Export validation rejecting valid trip snapshot payloads
- Strike endpoint returning non-JSON (schema column name mismatch)
- Docker containers running stale images missing config/env vars

A single 15-minute USABILITY-001 walkthrough caught all 7. None of the 11 static checks caught any of them. All 11 had been marked "PASS" for multiple ticks. The project had 133 passing tests, zero lint errors, 4 ADRs, and CI/CD configured — completely green on all static checks while impossible to use.

**The check — unconditionally, on every audit cycle:**

1. **Deploy the app** — `docker compose up -d` (or equivalent). If Docker Compose isn't configured, that IS the first gap: create an INFRA task for it.

2. **Walk through the primary user journey:**
   - Can a user open the app? (verify HTML loads, not just HTTP 200)
   - Can they authenticate? (verify login endpoint exists AND works)
   - Can they perform the primary action? (search, create, query — the core workflow)
   - Can they see results? (verify response bodies contain real data, not just `[]` or errors)
   - Can they complete the full workflow end-to-end?

3. **Verify responses deeply, not just HTTP codes:**
   - 200 with empty body = FAIL
   - 200 with HTML instead of JSON = FAIL
   - 200 with incorrect schema = FAIL
   - 202 accepted but never completes = FAIL
   - 500 = FAIL (create task immediately)
   - 404 for expected routes = FAIL

4. **Verify seeded/mock data in the RUNNING instance:**
   - `docker compose exec <service> sqlite3 /app/db.sqlite "SELECT COUNT(*) FROM main_table"` — returns 0 when data was only seeded on host
   - Test queries must return actual rows, not empty sets

5. **Use lightweight tools:**
   - `curl` or Python `urllib` (not Playwright — that's a separate TEST check)
   - `docker compose exec` for container inspection
   - Keep it under 30 tool calls total

**Output:** Every broken step creates a `USABILITY-NNN` task with exact reproduction, expected vs actual behavior, HTTP response details, and Critical priority (blocks all user workflows). These go to the TOP of the execution order — nothing else matters until a real user can use the app.

**When to skip:** ONLY when Docker Compose isn't configured yet (create an INFRA task), the app has no user-facing surface (pure library), or the first sprint hasn't delivered a deployable artifact.

**Do not confuse with Check 7 (endpoint verification).** Check 7 verifies individual endpoints return something. Check 12 verifies a full user journey works end-to-end with real data in a deployed instance. They are different layers. A project can have all endpoints returning 200 and still fail every usability check.

For the full checklist with exact commands, deployment patterns, and failure classification, see `coding-hermes-foreman/references/never-done-12th-check-usability.md`.

Create: `## [ ] USABILITY — <broken step description>` for each failure. Available in `coding-hermes-foreman/references/never-done-12th-check-usability.md`.

### 13. E2E TESTING TICK — Has a real browser/CLI agent tested this?

**Added 2026-07-24.** The first 12 checks are static or human-walkthrough. This 13th check verifies that a dedicated AI testing agent has exercised the project through its real interfaces — browser, CLI, or API — and reported findings as tasks.

**This check is different from Check 7 (endpoint verification) and Check 12 (usability smoke test).** Check 7 verifies endpoints return correct HTTP codes. Check 12 verifies a human can complete a user journey. Check 13 verifies an AI testing agent has explored the project deeply and found bugs a human would miss.

**Proven — HEADING 2026-07-24:** Static checks 1-11 all passed for multiple ticks. Usability check (#12) found 7 critical bugs. But the Luna E2E testing agent found 10 MORE bugs that neither static checks nor the human walkthrough caught: WebSocket topic mismatch, ranked-option contract divergence, evacuation payload shape mismatch, combobox accessibility bug, dark-theme false positives, and 5 more. These were protocol-level and visual-regression bugs invisible to curl-based checks.

**The check:**

1. **Check if E2E-001 task exists on the board.** If it doesn't, create it immediately.

2. **Check if e2e-output/tasks.md exists** — has a testing agent run recently?
   ```bash
   ls e2e-output/tasks.md e2e-output/report.md 2>/dev/null
   ```

3. **If no E2E output exists:** trigger the E2E testing tick from the foreman loop (Step 1.5i):
   - Spawn Luna for browser-based projects (Next.js, React, web apps)
   - Spawn Step 3.7 Flash for CLI/API-only projects
   - The testing agent produces `e2e-output/report.md` + `e2e-output/tasks.md`
   - Inject tasks into the board

4. **If E2E output exists:** verify tasks were injected into the board. Check for:
   - P0/critical tasks that haven't been worked yet
   - Tasks marked `[x]` that should be re-verified
   - New regression gaps since the last E2E run

5. **Every 5-10 ticks:** re-trigger E2E testing. Code changes → new bugs → new tasks → self-improving loop.

**Testing agent model selection:**
| Project type | Model | Why |
|-------------|-------|-----|
| Browser/web apps | GPT-5.6 Luna | Vision, screenshots, DOM inspection, Playwright |
| CLI/API tools | Step 3.7 Flash | Fast, cheap, agentic — curl/httpie suites |
| Complex multi-service | DeepSeek V4 Pro | Multi-step reasoning across services |

**Do not confuse with other checks:**
- Check 7 = "does the endpoint return 200?"
- Check 12 = "can a human complete the user journey?"
- Check 13 = "has an AI testing agent explored deeply and created tasks from findings?"

Create: `## [ ] E2E — <gap>` if E2E testing hasn't run or findings haven't been injected.

## Idle Tick Protocol — When All 13 Checks Pass

**⚠️ Zombie tick detection first:** Before running the idle protocol, check if the foreman cron job is PAUSED. If `cronjob action='list'` shows `state: paused, enabled: false` but ticks keep arriving, you are a ZOMBIE tick — the scheduler daemon is spawning you via Fleet TOML `ApplyFleetConfig` upsert despite the paused cron. See `coding-hermes-foreman/references/zombie-idle-foreman-pattern.md` for the full detection → response → root-cause workflow. Do NOT run the 11-point audit on a zombie tick — run a minimal discovery sweep and BAIL EARLY.

When the audit finds zero gaps (all 11 checks pass), the foreman enters idle-tick mode. Follow this protocol:

### GitReins Task Store Sync — FIRST STEP when board appears empty

**This is the fastest, most objective fabrication detector.** A board that says all tasks [x] but GitReins has pending tasks is definitively fabricated — no need to reason about "maybe the tests ran" or "maybe the coverage was already there." The GitReins store is machine state; the board is human-written (by a foreman). When they disagree, GitReins is the ground truth.

**Run this BEFORE the full 11-point audit** — it takes 5 seconds and can surface 10+ falsely-closed tasks instantly. If GitReins shows pending tasks, the prior audit was shallow/fabricated and you should expect more gaps from the full 11-point run.

**Verification step before deletion:** Do NOT blindly delete GitReins tasks just because the board says [x]. The board may itself be wrong. For each pending GitReins task, verify the criteria are met in code:
- `ls <file>` — does the file exist?
- `grep <pattern>` — is the config/route/function actually present?
- `go test -cover ./<pkg>/` — does test coverage exist?

If criteria are genuinely met → delete from GitReins. If criteria are NOT met → the board task was falsely marked [x]; re-open it as `[ ]` on the board AND keep it in GitReins.

1. `mcp__gitreins__task_list(workdir=...)` — list all GitReins tasks
2. Compare against `.coding-hermes/tasks.md` — find "pending" GitReins tasks whose board counterpart is `[x]`
3. For each: verify the criteria are met in code, then delete from GitReins if genuinely done
4. For any where criteria are NOT met: re-open the board task as `[ ]`
5. Stage and commit `.gitreins/tasks.yaml` alongside the board update

**Proven:** Crier 2026-07-21 idle tick #2 — board claimed all 28 tasks [x] but GitReins had 10 pending. Code verification confirmed 9/10 genuinely done (deleted from store). CI-011 was NOT done — coverage reporting absent from .gitlab-ci.yml despite board claiming complete. Re-opened as a new task. Without this sync, a fabricated board would have persisted indefinitely.

See `references/gitreins-board-sync.md` for the full detection and fix workflow.

### Scheduler Health Check (BEFORE writing idle tick to board)

Daemon restarts revert API-set `CooldownS` values to the TOML default. Always verify:

```bash
curl -s http://127.0.0.1:9090/api/v1/projects/<project> | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'CooldownS={d[\"project\"][\"CooldownS\"]}, Enabled={d[\"project\"][\"Enabled\"]}')"
```

**⚠️ Scheduler project name mismatch:** The daemon's project name often differs from the repo name. Querying the wrong name returns `{"error":"project not found"}` — the daemon IS running, the name is just wrong. When you see "project not found", list all projects and filter: `curl /api/v1/projects | python3 -c "..." | grep -i <keyword>`. See `references/scheduler-project-name-mismatch.md` for the full detection and fix pattern. **Proven:** H3 Shim — 3 idle ticks logged "scheduler unreachable" when the daemon was always running. Correct name was `h3-shim-foreman`, not `h3-shim`.

| Finding | Action |
|---------|--------|
| CooldownS matches expected value | Proceed to idle-tick write |
| CooldownS reverted to lower value | Re-fix: `curl -X PUT ... -d '{"CooldownS":<expected>}'`. Note reversion count in board. 1st reversion = warning. 2+ reversions = escalate to Bane (foreman MUST NOT self-disable per Disable Authority). |
| Project is disabled | Do NOT re-enable. Write idle tick noting disabled state. Stop. |

**Root cause:** The scheduler daemon loads `CooldownS` and `Enabled` from the TOML config at startup. API `PUT` changes are in-memory only — they survive tick-to-tick but not daemon restarts. The durable fix is editing the TOML file, but that requires foreman access to the scheduler host config. Foremen without that access should re-fix via API and escalate persistent reversions.

**⚠️ In-flight cooldown reversion (no daemon restart):** Cooldown can also revert between ticks WITHOUT a daemon restart. When the daemon has multi-hour uptime but the cooldown drops from 43200s to 3600s or 900s between consecutive ticks, the reversion source is likely the scheduler daemon's own tick processing — `ApplyFleetConfig` upsert reloading the TOML default on each evaluation cycle. Detection: daemon `/api/v1/status` shows uptime longer than the interval between the last two ticks (e.g., 13h uptime but cooldown reverted 2 hours ago). This is NOT a restart reversion — it's a mid-flight config reload. The API PUT fix still works, but the reversion will repeat every evaluation cycle until the TOML is edited. **Proven:** coding-hermes-scheduler tick #74 (2026-07-21) — cooldown reverted to 3600s with 13h55m daemon uptime. No restart occurred. Re-fixed to 43200s via API PUT but pattern has repeated 4 times across ticks #71-74.

**PUT vs GET response format:** The scheduler API has two response shapes. GET `/api/v1/projects/<name>` wraps the project in `{"project": {...}}` — parse with `d["project"]["CooldownS"]`. PUT returns the project object flat at top level — parse with `d["CooldownS"]` directly. Using the GET parser on a PUT response throws `KeyError: 'project'`; the PUT succeeded, verify with a fresh GET instead. See `references/scheduler-put-vs-get-response-format.md`.

**Proven:** chimera-v2 2026-07-20 — cooldown reverted 14400s→1800s three times (ticks #6, #12, #14) after daemon restarts. All three re-fixed via API PUT. 2nd and 3rd reversions escalated to Bane. hermes-dagger 2026-07-20 — cooldown reverted 14400s→1800s after daemon restart (tick #53), 1st reversion — re-fixed via API PUT, warning tracked in board. Imhotep 2026-07-21 — 2nd reversion (tick #5), PUT response parsed with wrong key, re-fixed + escalated. — cooldown reverted 14400s→1800s three times (ticks #6, #12, #14) after daemon restarts. All three re-fixed via API PUT. 2nd and 3rd reversions escalated to Bane. hermes-dagger 2026-07-20 — cooldown reverted 14400s→1800s after daemon restart (tick #53), 1st reversion — re-fixed via API PUT, warning tracked in board.

### Idle Counter

Track consecutive idle ticks in the board. Write the counter to DuckBrain each tick:

```
**Idle tick #N — all 12 checks pass. No new tasks. Counter: N/7 (no action ≤2).**
```

At ≥3 consecutive idle ticks (with no task creation for 3 straight ticks), set cooldown to 14400s (4h). At ≥7 idle ticks, escalate to Bane with disable instructions. Never self-disable.

**Past cap (counter ≥8):** When the idle counter exceeds 7 and the scheduler keeps firing ticks despite escalation, continue running the full audit each tick. Escalate again. Track reversions. The foreman is in a holding pattern — Bane has been notified, the cooldown is at max, and the project is genuinely complete. Do NOT self-disable. Do NOT fabricate tasks to break the idle loop. The scheduler daemon should eventually honor the disable request or the cooldown will naturally space ticks to 12h+. **Proven:** coding-hermes-scheduler ticks #73-74 (2026-07-21) — counter went from 7/7 to 8/7 despite escalation at tick #73. Scheduler kept firing. Foreman ran full audit both ticks, re-fixed cooldown, escalated again. No self-disable.

### Commit Board Updates (Even During Idle Ticks)

The idle tick entry written to `tasks.md` IS a code change. Commit it. The standard idle-tick "Actions Taken" says "no code committed" — this is misleading when the board itself was modified. Replace "no code committed" with the commit hash after committing. **Proven:** hermes-dagger 2026-07-20 — tick #52 wrote the board update but never committed it (working tree showed `M .coding-hermes/tasks.md`). Tick #53 picked up both uncommitted changes. The board update is real code — commit it.

## The Infinite Loop

```
Board empty? → Run 11-point audit → Find gaps → Create tasks → Work tasks → Board empty? → Repeat
```

**The project is only done when ALL 12 checks pass with zero findings.** Until then, keep adding tasks.

## Language-Specific Command References

The commands in each check above are Go-centric examples. For other languages, load the corresponding reference:

- **TypeScript/Node:** `references/typescript-patterns.md` — tsc, vitest, npm outdated, TS-specific test gap detection, TS-aware quality checks
- **Rust:** Use `cargo test`, `cargo update --dry-run` (when `cargo outdated` is not installed), `cargo bench`. See pitfall in Check 3 for integration test counting. See **Check 5 Rust pitfall detection** above for stub/panic/empty-impl commands. See `references/rust-pitfall-hunt.md` for additional patterns.
- **C++:** Use `make -j4` or `cmake --build`. Check `external/` for bundled deps, `ls external/` and VERSION files for versions, `--gtest_list_tests` for test enumeration, `grep -c 'Benchmark\|BM_'` for benchmarks. Verify binary links with `make -j4`. See `references/cpp-project-audit.md` for the complete C++ adaptation of all 11 checks (test-gap detection, dep auditing, endpoint verification, wiring).
- **GDScript/Godot:** Game engine projects need full adaptation — no package manager, centralized tests, HACK/STUB are game mechanics not code smells, autoloads >1000 lines are normal, Hilo reports N/A. See `references/gdscript-godot-audit.md` for the complete 11-check adaptation, false-positive catalog, and boot verification patterns.
- **Python:** Use `pip list --outdated`, `pip-audit`, `pytest --cov`, `grep -rn 'def test_'`. For test-gap detection specifically, see `references/python-test-gap-import-detection.md` — the naive `find *.py ! -name '*_test.py'` approach fails when tests live in a separate `tests/` directory. Use import-based grep instead. **For infrastructure/scripts projects** (no web framework, standalone scripts), see `references/python-infra-project-audit.md` — covers adapted checks 3, 4, 7, 8, 9, 11, and Hilo umbrella repo behavior.

## Anti-Patterns

- **"Board is empty, project is complete"** — NEVER. Always run the audit.
- **"I checked last tick, nothing changed"** — checked last tick means you check AGAIN this tick. Code rots, deps age, specs drift.
- **"The tests pass so it's fine"** — tests passing ≠ complete. Specs, docs, deps, perf, pitfalls all need checking.
- **Self-pausing without running the audit** — NEVER self-pause before running all 12 checks.
- **"This is a maintenance project, not active"** — maintenance IS active. Continuous improvement never stops.
- **SELF-DISABLING (CRITICAL)** — NEVER call `PUT enabled=false` on your own project. NEVER auto-disable yourself. Only the scheduler daemon or an explicit human command may disable a project. If you detect you've been idle for many ticks, continue running the 11-point audit and creating improvement tasks — do NOT disable yourself.
- **Trusting the scheduler cooldown to stay at the set value (CRITICAL)** — NEVER assume the cooldown you set persists. The scheduler daemon loads `CooldownS` from TOML at startup — every daemon restart reverts API `PUT` values. Always verify the cooldown at the start of every idle tick (see Scheduler Health Check in Idle Tick Protocol above). A reverted cooldown means the project fires too frequently, burning tokens on unnecessary idle ticks. Track reversions — 2+ in a short window warrants escalation to Bane. **Proven:** chimera-v2 2026-07-20 — cooldown set to 14400s reverted to 1800s after daemon restart (twice, ticks #6 and #9).
- **Running the full 12-point audit via delegation (CRITICAL)** — NEVER delegate the audit to subagents. Delegation has a 600-second hard cap (`child_timeout_seconds` in config.yaml). Large repos (200+ files, C++ projects, monorepos) will time out every time with partial results. Small single-file projects may complete but it's not worth the risk. Instead, use the **trigger-injection pattern**: inject `## [ ] NEVER-DONE — Run coding-hermes-never-done 12-point audit` as a task on the board. The foreman picks it up on its next tick and runs the audit in its own session — no time cap, full tool access, built-in retries. This is the ONLY reliable way to run the audit at scale. **Proven:** 2026-07-19 — 38 projects audited via delegation; 7 small projects completed, 31 timed out. Injecting the trigger task took 3 minutes and every project got its audit on the next daemon tick.
- **Manual unpausing that bypasses supervisor/daemon guards** — When unpausing foremen, check if the scheduler daemon is alive on :9090 first. If the daemon is running, it handles foreman ticks — do NOT unpause cron jobs. The supervisor has guards for this but manual human action bypasses them. **Proven:** 2026-07-19 — 35 foremen manually unpaused while daemon was running, creating duplicate-tick chaos. Required immediate re-pause.
- **Shallow audit — running 1-2 checks and claiming all 11 passed (PRODUCER SIDE).** You are the foreman running the audit. Do not run `go build` and `go test`, find one failure, and declare "11-point audit passed" in your commit message. The remaining 9 checks require their own tool calls: `go list -u -m all` for deps, `grep` for stubs/TODOs, `find` for untested files, DuckBrain recall for memory sync, wiring verification, spec sampling, etc. **Every check must produce concrete tool output visible in the session transcript.** A check whose output is not in the transcript was not run. The commit message MUST list findings per-check, not a blanket "all clear." If only 3 checks found findings and 8 were silent, the 8 were skipped — not clear. **Proven:** Kobayashi-Maru idle tick #2→#3 (2026-07-19) — tick #2 claimed "11-point audit passed, add FIX-dist-test-timeout" (one finding from check 3 only). Tick #3 re-ran all 11 checks with concrete tool calls and found 7 real gaps: 8 stubs (check 5), 30+ outdated deps + DEPRECATED package (check 4), 0 DuckBrain memories (check 9), and only 3 of 11 checks had been actually run by tick #2. The "passed" claim was fabrication by omission — 8 checks were never executed.\n- **Trusting a prior tick's `[x] NEVER-DONE` claim (CRITICAL)** — NEVER trust a board entry that says the 11-point audit was completed by a prior tick. The audit is the last line of defense — if it was fabricated or incomplete, the board stays falsely empty and the project stagnates. ALWAYS run the audit fresh on every tick when the board is empty, regardless of what the prior tick claimed. Detection signals: CI is red but board says all checks passed, specs are stale but audit claimed they were updated, deps were claimed upgraded but `--outdated` still shows them. **Proven:** gitreins-poc 2026-07-19 — prior tick marked `[x] NEVER-DONE — Run 11-point self-improvement audit` as complete, but independent re-audit found: CI had 3 consecutive failures (5 LSP tests), 6/11 specs were stale (only 4 were updated, not all 11), and pydantic-core was still outdated despite being claimed as upgraded.

- **Board-GitReins discrepancy — the single fastest fabrication signal (CRITICAL).** When the board says all tasks [x] but GitReins `task_list` shows pending tasks, there is a gap — but it cuts BOTH ways. GitReins is machine state; the board is a foreman's claim. Run `mcp__gitreins__task_list(workdir=...)` on EVERY idle tick BEFORE the 11-point audit. If any GitReins tasks are pending but the board says [x], VERIFY EACH ONE AGAINST CODE before concluding anything. **Either the board is fabricated OR GitReins was never synced after legitimately completing the work.** Do not assume the board is wrong just because GitReins disagrees. Check file existence, test functions, dep versions, import paths. If the code confirms completion → GitReins is stale (sync it to complete). If the code confirms NOT done → the board was fabricated (re-open the task). **Proven (board fabricated):** Crier 2026-07-21 idle tick #2 — 10 GitReins tasks pending while board claimed all [x]. 9/10 genuinely done in code (deleted from store), 1 genuinely NOT done (CI-011, re-opened). **Proven (GitReins stale):** coding-hermes-scheduler tick #74 (2026-07-21) — 20 GitReins tasks pending while board claimed all [x]. Verified ALL 20 against code: every spec file existed, every test function present, every dep upgraded. Board was correct — GitReins store was simply never synced. 15/20 synced to complete in one tick.

- **Phantom gap detection — verifying prior-tick file-existence claims (CRITICAL).** When a prior tick's audit created tasks claiming files exist or don't exist, verify with git history before accepting them. Use `git log --all --diff-filter=A -- <path>` to check if a file was ever committed, `git show <commit>:<path>` to verify existence at a specific commit, and `ls` both CI config locations (`.github/workflows/*.yml` AND `.gitlab-ci.yml`) — board metadata saying "CI: X" may itself be wrong. See `references/phantom-gap-verification.md` for the full verification protocol, detection signals, and decision tree. **Proven:** Crier idle tick #3 (2026-07-21) — idle tick #2 fabricated both CI-011 (searched for `.gitlab-ci.yml` which doesn't exist — project uses GitHub Actions) and QUALITY-003 (claimed `specs/AGENTS.md` existed — `git log --all --diff-filter=A` proved it never did). Both were phantom gaps detected by git-history verification.

- **Creating tasks from unverified audit findings (CRITICAL — PRODUCER SIDE)** — NEVER write a `## [ ] TASK` to the board based on an audit check command without independently verifying the finding is real. The audit runs in a separate session with its own VIRTUAL_ENV, PATH, and git state — all three can differ from the foreman's environment. An audit finding that says "spec is stale," "dep is outdated," or "tool is missing" MUST be verified with a fresh read/command in the foreman's own session before creating a task. The verification should be a 2-second `grep`/`importlib.metadata.version()`/`which` call — not a full investigation. If the verification disproves the finding, mark it as false-positive and MOVE ON. Do not create a task. The full verification protocol and root-cause taxonomy is in `references/audit-false-positive-verification.md`. **CONSUMER SIDE:** When a foreman picks up an audit-created task in a later tick, it must also verify the task's premise before implementing — see `coding-hermes-foreman/references/verify-audit-created-task-premises.md`. **Proven (producer):** gitreins-poc 2026-07-19 — Tick 3 audit created 4 tasks (GR-085 through GR-088). All 4 were false positives: spec already current, README already current, pydantic-core already 2.47.0, ruff already installed. Root causes: VIRTUAL_ENV contamination (GR-087), bare-command-vs-venv-path (GR-088), stale file read (GR-085/086). Burned a full foreman tick on verification-only work. **Proven (consumer):** Kobayashi-Maru 2026-07-19 — TEST-untested-source-files claimed 20+ untested files. Directory-level check showed 3 of 6 packages already had tests. Re-audit saved implementing unnecessary tests.

- **Accepting fabricated root cause diagnoses from audit tasks (CRITICAL)** — When the audit creates a task with a SPECIFIC root cause claim (e.g., "deadlock at line 555," "goroutine leak in function X"), verify the claim against the source code BEFORE accepting the diagnosis. Common fabrication signals: deadlock claims involving `RLock()` (read locks allow concurrent access — structurally impossible), "blocks forever" claims for functions with `ctx.Done()` select paths (context cancellation guarantees exit), line numbers that don't match the claimed concurrency primitive. See `references/fabricated-root-cause-diagnosis.md` for the full verification protocol, fabrication signal table, and response matrix. **Proven:** Kobayashi-Maru 2026-07-19 — Check 3 created TEST-analytics-timeout claiming "RWMutex deadlock at dashboard.go:555." Code at line 543 uses `RLock()` — concurrent reads, no deadlock possible. Test passes 5/5 in 5.4-6.5s. Fabricated diagnosis, burned a foreman tick on verification.

## Disable Authority (THE ONLY WAY TO DISABLE A PROJECT)

Projects can be disabled by exactly two things and NOTHING else:

1. **Human command** — the project owner explicitly disables via API, dashboard, or direct DB change.
2. **Scheduler daemon** — only after a pattern of failures verified across 10+ consecutive timeouts spanning >24 hours, AND only after alerting the chat with a clear warning message like `⚠️ AUTO-DISABLE: <project> disabled after 10 consecutive timeouts`.

**Foremen MUST NOT self-disable.** If your project appears idle or dead:
- Run the 11-point audit
- Find improvement tasks
- If truly nothing to do: log "IDLE — maintenance mode" but stay ENABLED
- Let cooldown handle pacing — the scheduler will space you out naturally
- NEVER `PUT enabled=false` from within a foreman tick
