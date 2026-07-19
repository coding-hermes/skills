# TypeScript/pnpm Monorepo — Foreman Scaffold Pattern

## Detection
Project uses `pnpm-workspace.yaml` (or AGENTS.md says "pnpm workspace"), has
`tsconfig.json` files, and uses `@scope/package` naming.

## Phase 0 Scaffold — Foreman Can Do Directly

The foreman can create mechanical scaffold: directory tree, config files, stub
source files. No design decisions — just boilerplate.

### Directory Structure
```
packages/<name>/src/       # Shared packages
apps/<name>/src/app/       # Next.js (app router)
apps/<name>/src/           # Express/Node API
config/                    # YAML/JSON config files
```

### Root Files
- `pnpm-workspace.yaml`: `packages: ["packages/*", "apps/*"]`
- `package.json`: `"private": true`, scripts for `pnpm --parallel -r run <cmd>`
- `tsconfig.base.json`: `target: ES2022`, `module: ESNext`, `moduleResolution: bundler`, `strict: true`
- `.prettierrc`: project-wide formatting

### Package Template (shared library)
```json
{
  "name": "@heading/<name>",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "scripts": {
    "build": "tsc",
    "test": "echo 'No tests yet' && exit 0",
    "lint": "echo 'No lint yet' && exit 0",
    "clean": "rm -rf dist"
  },
  "dependencies": {
    "@heading/core": "workspace:*"
  }
}
```

### Package tsconfig
```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": { "outDir": "./dist", "rootDir": "./src" },
  "include": ["src"]
}
```

### Next.js Web App (`apps/web`)
- **package.json:** depends on `next`, `react`, `react-dom`, `@heading/core`
- **NO `rootDir` or `outDir` in tsconfig** — Next.js uses `noEmit: true` and generates `.next/types/` which falls outside `rootDir`. See pitfall below.
- **next.config.ts:** `export default { output: 'standalone' };`
- **layout.tsx:** Starts with `<html><body>`, no global styles needed initially

### Express API App (`apps/api`)
- **package.json:** depends on `express`, `cors`, `ws`, all `@heading/*` packages
- **dev script:** `tsx watch src/index.ts` (tsx for watch mode)
- **Explicit return type required** on factory functions (see pitfall below)

## Pitfalls

### Next.js tsconfig rootDir clash
**Symptom:** `next build` fails with "File '.next/types/app/layout.ts' is not under 'rootDir'."
**Cause:** Next.js auto-generates type declarations in `.next/types/` which is outside `src/`.
**Fix:** Remove `outDir` and `rootDir` from the web app's tsconfig. These are not needed with `noEmit: true`.
**Proven:** Heading 2026-07-15.

### Express 5 strict type inference (TS2742)
**Symptom:** `tsc` fails with "The inferred type of 'createApp' cannot be named without a reference to '.pnpm/@types+express-serve-static-core@...'."
**Cause:** Express's `Express` type comes from a deep transitive dependency; TypeScript can't name it in the public API.
**Fix:** Add explicit return type annotation: `import express, { type Express } from 'express';` then `export function createApp(): Express { ... }`.
**Proven:** Heading 2026-07-15.

### PNPM approve-builds for esbuild/sharp
**Symptom:** `pnpm install` exits 1 with `[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: esbuild, sharp`.
**Fix:** `pnpm approve-builds esbuild sharp` — these are needed for Next.js production builds.
**Proven:** Heading 2026-07-15.

### GitReins init uses `npm test` for pnpm workspaces
**Symptom:** `gitreins init` detects TypeScript but sets `test_command: npm test`.
**Fix:** Post-init, edit `.gitreins/config.yaml` to use `test_command: pnpm test`. Also add pipeline stages and evaluator caps appropriate for project size. See `.gitreins/config.yaml` template below.
**Proven:** Heading 2026-07-15.

### TypeScript "No tests yet" stub passes guard
**Symptom:** `gitreins guard` shows `✓ tests` even though no real tests exist.
**Cause:** Each package has `"test": "echo 'No tests yet' && exit 0"` — this exits 0.
**This is correct for Phase 0 scaffold.** Tests are added by workers in later phases. The guard verifies the test command succeeds — a stub that exits 0 is a valid placeholder. Do NOT create a task for "missing tests" — test tasks are already on the board.
**Proven:** Heading 2026-07-15.

## GitReins Config Template (TypeScript/pnpm)

```yaml
guards:
  secrets: true
  lint: false
  tests: true
  test_mode: full
  test_command: pnpm test
  static_analysis: false

pipeline:
  stages:
    - id: tier1
      parallel: true
      on: [pre-commit, pre-eval]
      steps:
        - id: guard
          type: script
          run: "gitreins guard"
          on_fail: block
    - id: tier2
      type: ai_eval
      on: [pre-eval]
      condition: "true"
      max_iterations: 25
      tools: [read_file, run_command, search_pattern, read_diff, sandbox]

evaluator:
  max_iterations: 25
  max_time: "5m"
  max_input_tokens: "0.1M"
  max_output_tokens: "0.2M"
  tool_call_weight: 0.1
  compaction_threshold: 0.90
  code_context_budget: 0.70

defaults:
  model: deepseek-v4-flash
  check_for_updates: true
```

## Verification Checklist (Phase 0 Scaffold)

- [ ] `pnpm install` — all workspace deps resolve
- [ ] `pnpm build` — all packages compile (tsc + next build)
- [ ] `pnpm test` — all stubs exit 0
- [ ] `gitreins guard` — Tier 1 PASS
- [ ] `hilo graph warm` — edges discovered
- [ ] `hilo graph stats` — no orphan warnings for non-test files
- [ ] `git push origin master` — remote exists and accepts
