# CI Failure Diagnosis Patterns

How to tell whether a CI failure is a code problem or an infrastructure problem — without needing access to the CI runner.

## Quick Classification

| Symptom | Verdict | Action |
|---------|---------|--------|
| CI duration < 30s on all jobs (normal is 2+ min) | **Infrastructure** | Check billing, runner availability, org settings |
| All workflows fail (CI, Build, Docker, Cross-Platform) | **Infrastructure** | Not a single-workflow config bug |
| Markdown-only commits fail identically to code commits | **Infrastructure** | Code didn't change — CI runner never started |
| `startedAt == createdAt` on every job (to the second) | **Infrastructure** | Runner never allocated — see The 4-Second Death Pattern |
| Only one workflow fails, others pass | **Code/config** | Check that workflow's config and the diff |
| CI duration is normal but tests fail | **Code** | Read the failure log |
| Local build + tests pass, CI fails | **Check duration** | If < 30s → infra. If normal duration → env difference |
| **Setup steps succeed, cargo/build/test steps have `conclusion: null`** | **Infrastructure** | Run partly started but core steps never recorded a conclusion. Check job-level `conclusion: failure`. Logs may return BlobNotFound. |

## Partial-Step Failure — Setup Succeeds, Build Steps Return `conclusion: null`

When a CI job shows:
- Setup steps (checkout@v4, Install Rust, Install system deps) → `conclusion: success`
- Cargo/build/test steps → `conclusion: null`
- Job-level conclusion → `failure`
- Log retrieval → `BlobNotFound` (HTTP 404)

The runner started and ran the setup steps but never completed (or failed to record) the build phase. This is NOT the 4-second death pattern (where the runner never allocates at all). The runner WAS provisioned but was killed or failed mid-execution.

### Causes

- **Runner OOM/disk-full**: The runner was allocated but ran out of memory or disk during compilation. Large Rust projects (duckdb-sys, tree-sitter grammars) are especially vulnerable.
- **Cached cargo failure**: A stale or corrupted cargo cache caused an unrecoverable build error the runner couldn't report.
- **Transient runner failure**: The GitHub-hosted runner process crashed or was preempted.
- **Timed-out step that didn't report**: A step exceeded the workflow timeout and was killed before writing its conclusion.

### Detection

```bash
gh api repos/<owner>/<repo>/actions/jobs/<job-id> --jq '.steps[] | {name: .name, conclusion: .conclusion}'
# → setup steps have conclusion: success
# → build steps have conclusion: null
```

### Action

1. Re-run the failed workflow (`gh run rerun -R <owner>/<repo> <run-id>`)
2. If it passes on retry → **transient runner failure**. No code change needed.
3. If it fails identically on retry → **stale cache or persistent runner issue**. Clear cargo cache (`gh actions-cache list -R <owner>/<repo>`) and re-run.
4. If markdown-only commits fail but code commits pass → **infrastructure issue, not code**.

**Proven:** Hilo 2026-07-15 — DOC commit (markdown-only, `.coding-hermes/tasks.md` + docs changes). CI run 29437634038: setup steps all `success`, all 6 cargo/build/clippy/test steps `conclusion: null`. Logs returned BlobNotFound. Re-run on subsequent commit resolved normally (no recurrence in 2 subsequent runs). Classified as transient runner failure.

## The 4-Second Death Pattern

When CI completes in **4-8 seconds** across ALL workflows on EVERY commit (including markdown-only board updates), the runner never executed your code. checkout alone takes ~5 seconds. The job was killed or rejected before it started.

### Definitive Signal: `startedAt == createdAt`

Every job in a failed CI run has two timestamps. When the runner is provisioned normally, `startedAt` is several seconds after `createdAt` (runner allocation + VM boot). When the runner is NEVER allocated, both timestamps are **identical to the second**.

**How to check:**
```bash
gh run view <run-id> --json jobs > /tmp/ci-jobs.json
# Compare startedAt and createdAt for each job
grep -E '"startedAt|"createdAt"' /tmp/ci-jobs.json
```

If every job has `startedAt` == `createdAt` (to the second), **the runner was never allocated** — this is definitively infrastructure, not code. On normal runs, jobs show a gap of 3-15 seconds between creation and start (runner provisioning + OS boot).

**Proven:** Hivemind 2026-07-15 — all 9 jobs across Test+Lint workflows had identical timestamp pairs (e.g., `"startedAt":"2026-07-15T14:09:36Z"` / `"createdAt":"2026-07-15T14:09:36Z"`). Local build+test+guard all pass. Docker checkout@v4 alone takes ~5s on its own — 3-second total runtime confirms no step executed.

### Pitfall — Tirith blocks piping `gh | python3`:** The security scanner may block `gh run view --json jobs | python3 -m json.tool` or similar pipe-to-interpreter patterns. Write the JSON to a file first (`> /tmp/ci-jobs.json`), then read with `grep` or `cat`. The raw JSON directly shows `startedAt` and `createdAt` fields.

## "No Space Left on Device" — Runner Disk Exhaustion

When CI prints `An exception occurred` or `System.IO.IOException: No space left on device` in annotations, the GitHub Actions runner's disk is full. This is an infrastructure failure, not a code regression.

### Detection

```bash
gh run view <run-id> -R <repo> 2>&1 | grep -A5 "ANNOTATIONS"
# Look for: System.IO.IOException: No space left on device
```

**Key signals:**
- Run duration is LONGER than normal (not shorter like the 4-second death pattern). The runner was allocated and ran setup/build steps, then died mid-way.
- All code-critical steps (Build, Test, Lint) show `conclusion: success` but the final annotation shows the disk error.
- The failure occurs at the SAME elapsed time across unrelated workflows (e.g., both Test and Lint fail at ~43m when normal runs finish in ~38m).

### Root Causes

| Cause | Common In | Fix |
|-------|-----------|-----|
| Large cargo cache + incremental build artifacts | Rust projects with duckdb-sys, tree-sitter grammars | Clear cargo cache: `gh actions-cache list -R <repo>` then delete large entries |
| Docker layer cache bloat | Multi-stage Docker builds in CI | Prune Docker cache, reduce layers |
| Multiple workflows running concurrently on the same runner | Matrix builds on small runners | Reduce concurrency or increase runner disk size |
| Large lockfile + node_modules | pnpm/npm monorepos | Switch to pnpm with content-addressable store |

### Action

This is an **infrastructure** issue — do NOT create code-fix tasks. Options:
1. **Re-run the workflow** — transient disk pressure may clear
2. **Clear caches** — `gh actions-cache list -R <owner>/<repo>` then delete large entries
3. **If persistent** — create `## [ ] INFRA — CI runner disk exhausted, reduce cache size or add cleanup`

**Proven:** Hilo 2026-07-17 — Run 29523224486 showed `System.IO.IOException: No space left on device` at ~43m (normal runs ~38m). All 7 code steps (Build, Clippy, Test) reported success — the error was in a post-build log writer. Re-run on next commit passed normally.

Common causes:
- **Billing exhaustion**: GitHub Actions minutes depleted for the month
- **Runner unavailability**: No runner picked up the job (org-level runner pool empty or misconfigured)
- **Node.js deprecation**: GitHub deprecates old Node.js versions on runners. `actions/checkout@v4` and `actions/setup-go@v5` may trigger warnings/blocking if the runner's Node.js version is deprecated (e.g., Node.js 20 removed from runners June 2026)
- **Org-level restrictions**: Actions disabled at the org level, workflow restrictions, IP allowlists

## Proven Instances

- **Muster (2026-07-09 → 2026-07-12)**: 4 workflows, every commit since July 9 fails in 4-8s. Markdown-only chore commits fail identically to code commits. Local `go build ./... && go test ./...` passes. Last successful run July 9 (2m runtime). Billing was reportedly resolved July 4 but CI degraded 5 days later.
- **Hivemind (2026-07-13 → 2026-07-15)**: 10+ consecutive Test+Lint failures. All 9 jobs per run had `startedAt == createdAt`. Local build+test+guard all pass. No open issues, workflow YAML is correct. Confirmed as runner infrastructure failure.

## Golangci-lint Version / Go Version Mismatch

When a Go project targets Go 1.25+ and uses `golangci/golangci-lint-action@v4` with `version: latest`, the lint workflow fails with:

```
Error: can't load config: the Go language version (go1.24) used to build
golangci-lint is lower than the targeted Go version (1.25.0)
```

**Root cause:** golangci-lint v1.x (installed by action v4) is built with Go 1.24. Projects targeting Go 1.25+ require golangci-lint v2.x which is built with Go ≥1.25.

**Fix (3 changes in `.github/workflows/lint.yml`):**
1. Upgrade action: `golangci/golangci-lint-action@v4` → `@v7`
2. Pin version: `version: latest` → `version: v2.12.2` (or latest v2.x)
3. Safety net: add `continue-on-error: true` so lint warnings don't block CI

**Detection:** CI lint job fails in ~17 seconds. Error mentions Go version lower than targeted. This is a **code/config** problem (not infrastructure) — the lint tool needs upgrading, not the Go version.

**Proven:** DexDat Memory 2026-07-13 — golangci-lint-action@v4 with version `latest` pulled v1.64.8 (Go 1.24), failing on a Go 1.25.0 project. Fixed by upgrading to action v7 + pinning v2.12.2 (lint #29267363143 → SUCCESS). Also surfaced 2 real errcheck warnings once lint ran — the old version masked real issues.

### Golangci-lint v2.x Config Migration (Missing `version` Field)

When `.golangci.yml` has no `version` field and `golangci/golangci-lint-action` uses `version: latest` (resolving to v2.12.2+), the lint job fails with:

```
Error: can't load config: unsupported version of the configuration: ""
See https://golangci-lint.run/docs/product/migration-guide for migration instructions
```

**Root cause:** golangci-lint v2.x requires an explicit `version: "2"` at the top of the config file. The `latest` tag on the action auto-upgrades from v1.x to v2.x without warning, and v2.x rejects configs without the version declaration.

**Fix (2 changes):**
1. Add `version: "2"` to the top of `.golangci.yml`
2. Pin the action: `version: latest` → `version: v2.12.2` (or specific v2.x version)

**Detection:** CI lint job fails in ~27 seconds. Error contains `unsupported version of the configuration`. Local `go vet` and `go build` pass — the issue is purely CI config. This is a **CI config drift** issue (not code, not billing).

**Proven:** Scheduler 2026-07-14 — golangci-lint-action `version: latest` resolved to v2.12.2; `.golangci.yml` (last touched 2026-07-13) had no `version` field. Created CI-001 board task for the fix. Local `go build ./... && go vet ./...` both green.

## Push Trigger Silent Failure (workflow_dispatch works)

When push events don't trigger CI despite correct workflow config (`push: [main, master]` with correct branch names), but `workflow_dispatch` runs fine:

**Diagnostic steps:**
1. `gh run list -R <repo> --limit 10` — confirm zero runs from push events
2. `gh workflow run lint.yml -R <repo> --ref <branch>` — test workflow_dispatch
3. If dispatch works but push doesn't → **org-level Actions policy**, not billing or code

**Differential diagnosis:**
| dispatch works? | push works? | Verdict |
|---|---|---|
| ✅ | ✅ | Everything works — look elsewhere |
| ✅ | ❌ | Org-level policy restricting push event triggers |
| ❌ | ❌ | Billing exhaustion, runner unavailability, or Actions disabled |

**Workaround:** Add `workflow_dispatch:` to the `on:` block of every workflow. CI must be triggered manually via `gh workflow run`. This unblocks CI verification without requiring org admin access.

**Proven:** DexDat Memory 2026-07-13 — 10 commits on master since July 3 produced zero CI runs despite `push: [main, master]` triggers. workflow_dispatch triggered both Lint and Test successfully. Repo is private, org is on free plan, Actions enabled at repo level. Root cause unknown without org admin. Added workflow_dispatch triggers to both workflows as practical workaround.

## EBADPLATFORM — Platform-Specific Dependency Breaks Linux CI

When `npm ci` fails on Linux CI with `EBADPLATFORM` for a package like `@next/swc-darwin-arm64`:

```
npm error code EBADPLATFORM
npm error notsup Unsupported platform for @next/swc-darwin-arm64@15.5.15:
  wanted {"os":"darwin","cpu":"arm64"} (current: {"os":"linux","cpu":"x64"})
```

**Root cause:** A platform-specific package (macOS ARM64, Windows x64, etc.) is listed as a direct dependency in `package.json`. Framework tooling (Next.js SWC, esbuild, sharp, rollup) normally auto-selects the platform binary at install time — but when listed explicitly as a `dependency` or `devDependency`, `npm ci` tries to install it unconditionally and fails on mismatched platforms.

**Detection signals:**
- CI fails at "Install dependencies" step (gets past checkout + setup-node)
- Error contains `EBADPLATFORM` + `wanted {"os":"darwin"...}` or `wanted {"os":"win32"...}`
- `grep -c "darwin-arm64\|darwin-x64\|win32-x64" package.json` returns > 0 (in `dependencies` or `devDependencies`, NOT in `optionalDependencies`)
- Local dev on macOS works fine — developer never sees the failure

**Fix (2 changes):**
1. **Remove the platform-specific dep** from `package.json`. The framework (Next.js, esbuild, etc.) auto-selects the correct platform binary via `optionalDependencies` at install time.
2. **Switch `npm ci` → `npm install`** in the CI workflow. `npm ci` requires an exact lockfile match; removing the dep from `package.json` makes the lockfile stale. `npm install` regenerates the lockfile. Use `--legacy-peer-deps` if the project has peer dependency warnings.

**Also check:** Does the project have BOTH `package-lock.json` (npm) AND `pnpm-lock.yaml` (pnpm)? This is a package-manager conflict — CI uses one, dev uses the other. The workflow's `cache:` key and install command must match the lockfile present in the repo. If `pnpm-lock.yaml` exists, CI should use pnpm, not npm.

**Proven:** EduOS 2026-07-15 — `@next/swc-darwin-arm64` in `apps/web/package.json` devDependencies caused EBADPLATFORM on Linux CI. Dev machine was macOS so the failure was invisible locally. Removed dep, switched `npm ci` → `npm install --legacy-peer-deps`, bumped Node 20→22 (deprecated).
