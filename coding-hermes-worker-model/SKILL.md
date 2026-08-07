---
name: coding-hermes-worker-model
description: >-
  Worker model selection guide — analyze task requirements, match to model
  capabilities via DuckBrain benchmarks, pick the right provider, avoid
  anti-patterns. Extracted from coding-hermes-foreman.
version: 1.0.0
author: Bane + Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [coding-hermes, model-selection, worker, capability-based]
    related_skills:
      - coding-hermes-foreman
      - coding-hermes-worker
      - duckbrain-memory
      - model-intelligence
      - coding-hermes-map
---

> See [coding-hermes-map] for the full skill hierarchy and when to use each skill.

## Worker Model Selection — Capability-Based

**This section replaces the old language-based table.** The foreman picks workers based on what the TASK needs, not what language it's in.

### Step 0: Bane's Current Model Directive (2026-07-31)

**deepseek-v4-flash is the preferred model over deepseek-v4-pro** — flash received
an update in the last 24h that pro did NOT. Bane: "v4 flash is the model to be
using now it is better then v4 pro because there was an update to one of them in
last 24 hours but not the other." Use v4-flash for foreman AND worker dispatch
until benchmarks or Bane say otherwise. When a board row still names V4 Pro as
dispatch model, update it to V4 Flash (e.g., GAP-001 on hermes-canopy).

### Step 0.5: Recall Model Capabilities from DuckBrain (BEFORE picking)

```bash
duckbrain recall --namespace default --key /benchmarks/models/<model-id>
```

The AI Benchmark DB Updater cron populates this daily at 4 AM with pricing, benchmarks, context windows, strengths, and weaknesses for every model. Query the specific models you're considering for the task. Target keys:

| Model | Key |
|-------|-----|
| Your best reasoning model (>your-provider) | `/benchmarks/models/deepseek-v4-pro` |
| Your fast budget model (>your-provider) | `/benchmarks/models/deepseek-v4-flash` |
| Your batch processing model (>your-provider) | `/benchmarks/models/minimax-m3` |
| Your long-context model (>your-provider) | `/benchmarks/models/kimi-k3` |
| GLM-5.2 | `/benchmarks/models/glm-5.2` |
| Kimi K3 (fixed-price sub) | `kimi-for-coding` provider, model `k3`, base `https://api.kimi.com/coding/v1` |
| Your most capable Go model (>your-provider) | `/benchmarks/models/gpt-5.6-sol` |
| GPT-5.6 Terra | `/benchmarks/models/gpt-5.6-terra` |
| Grok-4.5 | `/benchmarks/models/grok-4.5` |
| Step-3.7 Flash | `/benchmarks/models/step-3.7-flash` |
| Tencent Hy3 | `/benchmarks/models/tencent-hy3` |

Each entry returns: tier, context window, pricing (input/output per 1M tokens), benchmarks (SWE-bench, Aider, etc.), and user sentiment.

### Step 5a: Analyze the Task

For each pending task, determine requirements:

| Requirement | Check | Models that handle it |
|------------|-------|----------------------|
| Long context (>100k) | Specs, refactors, multi-file | Your most capable Go model (>your-provider), Your batch processing model (>your-provider) (partial), Your long-context model (>your-provider) (partial) |
| Image processing | Screenshots, UI mockups, diagrams | Your most capable Go model (>your-provider), gpt-5.6-terra, grok-4.5 |
| UI/frontend work | HTML, CSS, JS, visual output | Your most capable Go model (>your-provider), Your batch processing model (>your-provider), hy3, Your long-context model (>your-provider) |
| Shell-heavy work | CI, infra, devops, scripting | step-3.7-flash, glm-5.2, Your best reasoning model (>your-provider) |
| Architecture design | System design, data models, APIs | Your most capable Go model (>your-provider), Your best reasoning model (>your-provider), Your batch processing model (>your-provider) |
| Go coding (complex) | Multi-file features/refactors | glm-5.2, Your batch processing model (>your-provider) |
| Go coding (bug fixes) | Single-file fixes, tests | Your long-context model (>your-provider), glm-5.2, Your batch processing model (>your-provider) |
| Python/TS general | Features, fixes | Your batch processing model (>your-provider), Your long-context model (>your-provider), glm-5.2 |
| Docs/specs | Structured writing | gpt-5.6-terra, step-3.7-flash |
| Mechanical work | Boilerplate, lint, format, test gen | step-3.7-flash, Your fast budget model (>your-provider) |

**Large-file refactor tasks ("N files >500 lines" board rows): scope with the barrel-split pattern, then dispatch** — split the monolith into a module directory and keep the entry file as a one-line re-export (`export * from './<dir>/index.js'`) so every importer compiles untouched; singleton values defined in exactly ONE module and re-exported (identity preserved); shared types in types.ts break circular imports; REPO_ROOT path constants shift one dir deeper. This pattern makes a huge task verifiable in ONE worker pass (tsc across all importers + full package suite = proof of zero API change). Proven: wojons-mythos QUALITY-LF-001 (2,152L → 7 modules, 10 importers untouched, 2,072 tests green, glm-5.2). Full recipe + worker-prompt wording: `coding-hermes-foreman` → `references/large-file-barrel-split.md`.

### Step 5b: Pick Model (match requirements → capabilities)

1. **If image processing needed AND not Go** → Your most capable Go model (>your-provider) primary, grok-4.5 fallback
2. **If 150k+ context needed** → Your most capable Go model (>your-provider) primary, Your batch processing model (>your-provider) (partial) fallback
3. **If architecture/reasoning** → Your most capable Go model (>your-provider) primary, Your best reasoning model (>your-provider) fallback
4. **If spec/docs** → gpt-5.6-terra primary, step-3.7-flash fallback
5. **If Go complex** → glm-5.2 primary, Your batch processing model (>your-provider) fallback, Your long-context model (>your-provider) backup
6. **If Go bug** → Your long-context model (>your-provider) primary, Your batch processing model (>your-provider) fallback, glm-5.2 backup
7. **If Python/TS** → Your batch processing model (>your-provider) primary, Your long-context model (>your-provider) fallback, glm-5.2 backup
8. **If mechanical/fast** → step-3.7-flash primary, Your fast budget model (>your-provider) fallback
9. **If mixed/special** → Your batch processing model (>your-provider) (most versatile) primary
10. **All others** → Your batch processing model (>your-provider) → Your long-context model (>your-provider) → glm-5.2 cascade

### Step 5c: Provider Balance

Spread work across prepaid plans. Track in DuckBrain:

```bash
duckbrain recall --namespace coding-hermes --key /fleet/provider-usage
```

If your-budget-provider approaching exhaust → bias toward kimi-for-coding + zai-glm. If zai-glm exhausted → bias toward your-budget-provider + stepfun. Rotate to avoid lockouts.

### Anti-Patterns

- **Your most capable Go model (>your-provider) for Go coding:** Silently exits with zero output. Never send Go tasks to your-primary-provider.
- **Your long-context model + Your best reasoning model claiming full context:** Both degrade past ~128-200k despite claims.
- **GLM-5.2 on GDScript:** Silent (Variant C). Use Your batch processing model (>your-provider) instead.
- **Make/test parallelization > j4:** NEVER use `-j` higher than 4 for `make` or `go test -parallel`. A single `make -j16` on C++ projects (RethinkDB, etc.) saturates the entire machine with `-O3` compilations, choking all other foremen and workers. Maximum: `make -j4`, `go test -parallel 4`. If the project has an existing `-j` flag in its Makefile, override it. **Proven:** RethinkDB 2026-07-18 — one Your batch processing model (>your-provider) worker ran `make test -j16`, launched 237 C++ files at `-O3`, load hit 16.76, entire fleet stalled.

**Bucket exhaustion handling:** When a primary bucket returns 429/resource_exhausted, immediately switch to the first fallback. When that exhausts, switch to the second. If ALL buckets for a task type are exhausted, create `## [ ] INFRA — prepaid buckets exhausted for <task-type>, need new provider or billing top-up` and skip that task.

**For spec-writing phases with 3+ independent files, spawn workers in parallel.** See `references/parallel-spec-worker-spawning.md`. GPT-5.6-terra on your-primary-provider handles concurrent sessions — 9 workers completed in ~7 minutes vs ~70 serial.

## Worker spawn command (exact invocation)

Foremen spawn workers as background `hermes chat` sessions (board dispatch events record the PID):

```bash
cd <repo> && hermes chat -q "$(cat /tmp/<task>_prompt.txt)" -m <model> --provider <provider> -Q
```

via terminal(background=true). `-q "$(cat prompt)"` feeds the self-contained worker prompt (write it with write_file FIRST — the prompt is the whole job: workers have zero conversation context), `-m`/`--provider` pick the worker model (e.g. `-m hy3 --provider custom:opencode-go`, `-m gpt-5.6-luna --provider openai-codex`, `-m glm-5.2 --provider zai-glm`), `-Q` quiet mode prints only the final response.

**⚠️ Check the repo's established worker provider FIRST — do NOT default to the main PAYG provider.** Board audit events record the model+provider used for prior workers in that repo. <project> convention: `deepseek-v4-flash --provider deepseek-foreman` (a separate keyed provider), NOT the main `deepseek` PAYG provider. Spawning with the wrong provider means kill + respawn (proven: <project> tick 106, 2026-08-03). Read the last 2-3 board audit events (or DuckBrain `/project/<name>/status` `tick_N` attributes) for the established pairing before writing the spawn command.

Required prompt sections: verified current state (facts with line numbers — "do not re-verify"), required design, the gitreins ACs verbatim, pitfalls (files the worker must NOT touch, no npm install, no push, no `gitreins task complete`), exact verification commands, and commit instructions with the `Addresses <task-id>` convention + Co-authored-by trailer. After spawn, record the PID in the board dispatch event and poll with process(action='poll')/wait. **Proven:** hermes-canopy UI-08 (hy3 @ opencode-go, PID 2004677) and UI-09 (gpt-5.6-luna @ openai-codex, PID 2831952), Ticks 127-128.

**The foreman monitors the background process.** Check for completion every ~60 seconds. If the worker hasn't finished within 15 minutes, check the log. If stuck, kill and retry with a different model on a different provider. A stuck worker is usually a model-specific issue — switching models resolves it.

**Two commit patterns — foreman-commit vs worker-direct-commit:**

The worker spawn prompt (from Step 4) includes commit instructions. Workers that follow those instructions will commit directly before exiting. When this happens:

| What changes | Foreman-commit (skill default) | Worker-direct-commit (common reality) |
|---|---|---|
| Steps 5-6-7-8 order | Foreman runs guard → judge → commit | Worker commits → foreman verifies post-commit |
| Guard runs on | Staged (pre-commit) changes | Already-committed state → "No files staged" is normal |
| Judge | Runs against staged diff | Typically skipped for trivial fixes; post-hoc judging risks false negatives |
| Foreman's role | Gates the commit | Verifies commit quality, pushes, updates board |

**When the worker commits directly, the foreman still:**
1. **Build+vet+test verification FIRST** — run `go build ./... && go vet ./... && go test ./... -count=1 -short` (or language equivalent). This catches syntax errors, import bugs, and test failures that `gitreins guard` may miss because the guard runs on committed state while the working tree can still have issues. Do NOT skip this step — it catches real bugs (e.g., GLM-5.2 double-import syntax errors) that the guard's `go_build` check passes over.
2. **Verify the commit exists and is correct** (`git log --oneline -1`, `git show --stat HEAD`).
3. **Run `gitreins guard` post-commit** — secrets check is still valuable even on verified code.
5. Push (`git push origin $(git branch --show-current)`).
5. **Update the board**.

**Judge decision:** For trivial/single-line fixes (test assertion changes, typo fixes, config updates), skip the post-hoc judge — it runs against an admin-only diff and produces false negatives (documented in the `gitreins` skill). For multi-file features, create a GitReins task pre-commit and run `gitreins judge <id>` against the feature commit. **Proven:** Kobayashi-Maru 2026-07-12 — worker committed 3-line test fix; foreman verified tests pass, ran guard post-commit (secrets clean), pushed, skipped judge.

**Paired dispatch — one worker for two tightly-related tasks (between serial and bankai):** When two board tasks are two halves of ONE feature (e.g. "log per-hop latency" + "report latency percentiles", or two stubs that share the same new deps), dispatch them to ONE worker in a single prompt instead of two serial ticks or two parallel workers. **The coupling criterion matters more than priority/size — P0 pairs are the highest-value pairing.** Two P0 bugs that are sequential hits on the same code path (fixing A alone leaves A's own regression test failing on B's bug) pair exactly like small P3 features: same file cluster, one worker, one GitReins task, one judge pass. Requirements for pairing: (1) same file cluster or adjacent files (no worker-conflict risk), (2) same model/provider sensible for both, (3) both dispatchable (deps met), (4) combined scope still fits one worker session. The prompt must explicitly say: dispatch both tasks, make N clean commits (one per task, each `Addresses <task-id>`), run the full test suite once at the end. Foreman side: create ONE GitReins task covering both criteria sets, mark both board rows in_progress at dispatch, complete both with their own commit hashes, judge once. Saves a full tick + context reload; avoids the double-guard overhead of two workers. **Proven:** h3-shim tick #149 (2026-07-31) — OBS-IMPL-02 (hop logging) + OBS-IMPL-03 (latency percentiles) paired; worker made 2 clean commits (57af986, af67358), +12 tests (239/239), one judge PASS, both board rows completed in one board commit f8ed851. **Second instance:** <project> tick 26 (2026-07-31) — E2E-STUB-002 + E2E-STUB-003 paired because both add the same go.mod deps (starlark + wazero); sequential work, two clean commits, one guard run. **P0 instance:** dexdat-memory tick #64 (2026-08-01) — DOGFOOD-001 + DOGFOOD-002 paired (both P0: SQLite lookups never seeded + missing idempotency_key — two halves of the fresh-install write path; the 001 regression test literally exercises 002's column). One worker (deepseek-v4-flash), one commit 55a9cc76 (+216/−20), one judge PASS 7/7, both board rows completed in one board commit. **Auth-deadlock P0 instance:** helios tick #155 (2026-08-03) — BUG-AUTH-ROUTE-PREFIX + BUG-SQLITE-SESSION-SCAN paired (two halves of one auth/session deadlock; E2E verification of A alone was impossible without B). One worker (k3 @ kimi-for-coding — Go-bug-fix primary per the capability table), 2 clean commits 7473a39/acc2f61 (+373/−49 incl. +252 test lines), worker ran its own live E2E battery (fresh sqlite via SQLITE_PATH + migrate, alt port, curl loop), one gitreins task helios-155-auth-session, one judge PASS 7/7, both board rows completed in one board commit. k3 proved strong on paired Go bug work: honest reporting of pre-existing blockers (users-table schema drift, migrate `--db` CLI parse bug), no go.mod contamination, no hallucinated imports.

## Kimi Fixed-Price Subscription

When the user has a fixed-price Kimi subscription, use `kimi-for-coding` provider with `k3` model. See **[references/k3-fixed-price-sub.md](references/k3-fixed-price-sub.md)** for config details, available models, and pitfalls.

## Bankai — Aggressive Parallel Fix Sweep

When the user says "bankai", dispatch ALL pending tasks in one parallel batch, recover from timeouts, commit everything, and re-audit. See **[references/bankai-pattern.md](references/bankai-pattern.md)** for the full cycle, timeout recovery, and GitReins integration pattern.
