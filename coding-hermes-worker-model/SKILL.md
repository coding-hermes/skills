---
name: coding-hermes-worker-model
description: >-
  Worker model selection guide — analyze task requirements, match to model
  capabilities via DuckBrain benchmarks, pick the right provider, avoid
  anti-patterns. Extracted from coding-hermes-foreman.
version: 2.0.0
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

### Step 0: Read the Operator's Current Model Directive (LIVE — never hardcode)

The operator may set a fleet-wide default model directive. It is POLICY with an
expiry trigger ("until benchmarks or the operator say otherwise") — which means
it ROTATES. Never trust a directive embedded in any skill file, board row, or
memory note; re-read the live one:

1. `coding-hermes-config` (loaded first) — the operator's current
   foreman/worker default model + provider.
2. `duckbrain recall --namespace coding-hermes --key /fleet/model-directive`
   — dated directive with owner + revisit trigger, if one is set.
3. If a board row names a model that contradicts the live directive, the LIVE
   directive wins — update the row (Portability Law, coding-hermes-skill-authoring).

### Step 0.5: Recall Model Capabilities from DuckBrain (BEFORE picking)

```bash
duckbrain recall --namespace default --key /benchmarks/models/<model-id>
```

The AI Benchmark DB Updater cron populates this daily at 4 AM with pricing, benchmarks, context windows, strengths, and weaknesses for every model. Query the specific models you're considering for the task. Target keys:

**Enumerate the fleet's role buckets from the config skill** (which providers
and role-assignments the operator actually pays for), then recall each
candidate model's live benchmark row:

```bash
duckbrain recall --namespace default --key /benchmarks/models/<model-id>
```

The AI Benchmark DB Updater cron populates this daily with tier, context
window, pricing (input/output per 1M tokens), benchmarks (SWE-bench, Aider,
etc.), and user sentiment for every model. Candidate model IDs come from the
config skill and the benchmark index (`duckbrain list_keys --namespace
default --prefix /benchmarks/models/`) — NEVER from a table in this file
(Portability Law: answers rot; procedures don't).

### Step 5a: Analyze the Task

For each pending task, determine requirements:

| Requirement | Check | Which bucket handles it (resolve bucket → today's model via Step 0.5) |
|------------|-------|----------------------------------------------------------------------|
| Long context (>100k) | Specs, refactors, multi-file | reasoning bucket (verify actual context window in the benchmark row — claims lie past ~200k) |
| Image processing | Screenshots, UI mockups, diagrams | vision-capable bucket (check the benchmark row's strengths) |
| UI/frontend work | HTML, CSS, JS, visual output | frontend bucket |
| Shell-heavy work | CI, infra, devops, scripting | fast/cheap bucket |
| Architecture design | System design, data models, APIs | reasoning bucket |
| Language-heavy coding (Go/Py/TS) | Multi-file features, bug fixes | coding bucket — verify with the benchmark row's SWE-bench/Aider tier |
| Docs/specs | Structured writing | writing bucket |
| Mechanical work | Boilerplate, lint, format, test gen | fast/cheap bucket |

Buckets are DEFINED here; the model filling each bucket is CONFIG (Step 0.5).
This table survives model churn; a table of model IDs would not.

**Large-file refactor tasks ("N files >500 lines" board rows): scope with the barrel-split pattern, then dispatch** — split the monolith into a module directory and keep the entry file as a one-line re-export (`export * from './<dir>/index.js'`) so every importer compiles untouched; singleton values defined in exactly ONE module and re-exported (identity preserved); shared types in types.ts break circular imports; REPO_ROOT path constants shift one dir deeper. This pattern makes a huge task verifiable in ONE worker pass (tsc across all importers + full package suite = proof of zero API change). Proven: wojons-mythos QUALITY-LF-001 (2,152L → 7 modules, 10 importers untouched, 2,072 tests green, glm-5.2). Full recipe + worker-prompt wording: `coding-hermes-foreman` → `references/large-file-barrel-split.md`.

### Step 5b: Pick Model (match requirements → capabilities)

Resolve the task's requirement (Step 5a) to a ROLE BUCKET, then pick
primary → fallback → backup from today's bucket assignments (config skill):

1. Image processing needed → vision bucket
2. 150k+ context needed → reasoning bucket (verify real context window)
3. Architecture/reasoning → reasoning bucket
4. Spec/docs → writing bucket
5. Language-heavy complex coding → coding bucket
6. Mechanical/fast → fast bucket
7. Mixed/special → coding bucket (most versatile)
8. All others → coding → writing → fast cascade

Tie-breakers within a bucket: covered-by-subscription > cheaper per 1M >
faster > newer. If a bucket's primary returns 429/exhausted, drop to the
bucket's next entry; when a whole bucket is dead, file
`INFRA — bucket exhausted for <task-type>` and skip that task.

### Step 5c: Provider Balance

Spread work across prepaid plans. Track in DuckBrain:

```bash
duckbrain recall --namespace coding-hermes --key /fleet/provider-usage
```

Bias toward the prepaid plans with remaining headroom (read each provider's
usage from the config skill's provider list + its usage page). Rotate before
lockout: when a plan nears its cap, move its share to the next prepaid plan
with headroom. Never bias toward a provider BY NAME from this file — by
headroom from the live usage numbers.

### Anti-Patterns

- **Any single model becoming the fleet's Go default:** models that silently
  exit with zero output on a task class are recorded per-model in
  `references/pitfalls.md` — check it before first dispatch of an unfamiliar
  model on a new task class, and ADD your finding there after a silent-exit.
- **Context-window claims:** treat any model's claimed window past ~128k as
  unverified until a real long-context job lands; degrade is common.
- **Model-vs-language surprises (e.g. silent failure on GDScript):** the
  first dispatch of any model on an UNUSUAL language is a probe, not a
  production run — watch stdout/files for the first minutes (see
  references/two-silent-workers-foreman-direct.md).
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

**The foreman monitors the background process.** Check for completion every ~60 seconds. If the worker hasn't finished within 15 minutes, check the log. If stuck,
kill and retry with a different model from the NEXT bucket entry (a different
provider by construction). A stuck worker is usually a model-specific issue —
switching buckets resolves it. After a stuck-worker event, append the model +
task shape to `references/pitfalls.md` so the next foreman doesn't re-learn
it (registry, not memory).

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
