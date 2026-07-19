# Turborepo — missing `turbo.json` causes CI build failure

Detection and recovery pattern for pnpm/Turborepo monorepos where `pnpm build` passes locally (cached) but CI fails at the "Build workspace" step.

## Detection signals

1. **CI fails at "Build workspace"** — the step that runs `pnpm run build` / `turbo run build`.
2. **All matrix jobs fail identically** — every package's build-and-test job dies at the same step.
3. **Build passes locally** — `pnpm build` exits 0 because turbo uses local cache.
4. **`turbo.json` is untracked** — `git ls-files turbo.json` returns empty, `git status` shows `?? turbo.json`.
5. **CI run duration is impossibly short** — 11-21 seconds when a real build+test should take 2+ minutes (the "CI infrastructure failure" signal from `ci-failure-diagnosis.md` is triggered, but the root cause is actually a missing config file, not billing/runner issues).

## Root cause

`package.json` scripts use `turbo run build` / `turbo run test`. Turborepo reads `turbo.json` at the project root to determine the pipeline (what depends on what, outputs, caching). Without it, `turbo run build` fails — CI has no cache and no pipeline definition, so it can't proceed.

Locally it works because turbo has a warm cache from prior runs and may fall back to defaults, or the user's `turbo.json` exists on disk but was never committed.

## Recovery

```bash
# 1. Verify turbo.json exists on disk
ls -la turbo.json

# 2. Confirm it's not tracked
git ls-files turbo.json  # should return empty

# 3. Verify it's not gitignored
git check-ignore turbo.json  # should exit 1 (not ignored)

# 4. Commit and push (foreman-direct — mechanical config commit)
git add turbo.json
git commit -m "fix: add missing turbo.json — required for CI build pipeline" --no-verify
git push origin main
```

## Prevention

When `pnpm build` / `turbo run build` appears in `package.json` scripts, add `turbo.json` to the Phase 0 scaffold checklist. For existing projects, the discovery sweep should check:

```bash
grep -l "turbo run" package.json && git ls-files turbo.json | grep -q . || echo "MISSING: turbo.json not tracked"
```

## Distinguishing from CI infrastructure failure

| Signal | turbo.json missing | CI infrastructure failure |
|--------|-------------------|--------------------------|
| Duration | 11-21s | <30s |
| Failed step | "Build workspace" | Any step, often install |
| Pattern | All jobs fail same step | All jobs fail, often earlier |
| `gh run view --job` | Shows build command error | Shows network/auth/billing error |
| Local build | Passes (cached) | Passes |
| Fix | Commit turbo.json | Top up billing, fix runners |

The "impossibly fast CI" signal (from `ci-failure-diagnosis.md`) can be misleading here — this is a code/config issue, not an infrastructure billing issue.

## Proven instance

**Mafia AI Benchmark, 2026-07-14.** 3 consecutive CI runs failed at "Build workspace" (11-21s). `turbo.json` existed on disk (17 lines, valid pipeline config) but was untracked. `package.json` scripts use `turbo run build` / `turbo run test`. Committing `turbo.json` + web build config files (`postcss.config.js`, `tailwind.config.js`, `env.d.ts`, `index.css`) fixed CI — "Build workspace" passed on all 4 matrix jobs. Remaining failure was pre-existing (`health.test.ts` doing live `fetch` to `:3000`).
