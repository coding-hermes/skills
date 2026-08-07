---
name: coding-hermes-discovery
description: >-
  Discovery sweep for coding-hermes foremen — finds work when the board is empty.
  Ordered priority sweep: build integrity, live endpoints, spec alignment, CI audit,
  dependency vuln scan, dependency integrity, WebUI admin panel, E2E verification,
  real-world input pipeline test. Covers Go, Python, Node/TypeScript, and Rust stacks. Self-contained — loadable
  by any foreman cron job without needing the full foreman skill.
version: 1.0.0
author: Bane + Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [coding-hermes, discovery, foreman, sweep, dependency-check]
    related_skills:
      - coding-hermes-cron
      - coding-hermes-model-router
      - coding-hermes-never-done
      - hilo-usage
      - gitreins
      - prompt-foundry
      - duckbrain
      - webui
      - coding-hermes-map
  support_files:
    - references/cron-localhost-verification.md
    - references/gh-pages-static-site-verification.md
    - references/spec-audit-methodology.md
    - references/stale-count-discovery-patterns.md
    - references/gitlab-ci-audit.md
    - references/ci-failure-diagnosis.md
    - references/gh-pages-configure-failure.md
    - references/ci-non-triggering-diagnosis.md
    - references/supervisor-auto-pause-orphan-chain.md
    - references/gitreins-stale-task-cleanup.md
    - references/spec-hub-multi-repo-foreman.md
    - references/silent-import-failure-ci-pass.md
---

> See [coding-hermes-map] for the full skill hierarchy and when to use each skill.

# Discovery Sweep — Find Work When the Board Is Empty

When there's nothing to work on, FIND work. The sweep is ordered by priority — don't check CI until you've confirmed the build works.

**Model Router — task decomposition on first contact:** When a project is new or the board has only bootstrap tasks (INIT, SPEC, DOC, CI), load `coding-hermes-model-router` and decompose the project into a full task matrix. Score each task by priority, complexity, and required capabilities. Route each task to the cheapest model that works.

## 1.5a — Build Integrity Check

```bash
make build 2>&1 || go build ./... || cargo build || npm run build
```

Does the project build clean? If no, create `## [ ] BUILD — <broken component>`.

## 1.5b — Usability Testing (Live Endpoints)

If the project has live endpoints (APIs, UIs, services), hit them. **Do NOT stop at `/health`.** Health passes mean the server is running — not that the application works. Hit every role-specific route with real auth tokens.

### Step 1: Basic health check

```bash
curl -s http://localhost:<port>/health || echo "Not running"
curl -s https://<deployed-url>/api/status || echo "Not deployed"
```

### Step 2: Auth-required route verification (MANDATORY for multi-role apps)

For every role-specific dashboard/endpoint, login as each demo role and hit the route:

```bash
# Login as each role, extract token, hit their dashboard
TEACHER_TOKEN=$(curl -s -X POST http://localhost:<port>/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"teacher@demo.<project>.app","password":"<demo-pass>"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['accessToken'])")

STUDENT_TOKEN=$(curl -s -X POST http://localhost:<port>/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"student@demo.<project>.app","password":"<demo-pass>"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['accessToken'])")

# Hit EVERY dashboard route for EVERY role
curl -s -o /dev/null -w "Teacher dashboard: %{http_code}\n" \
  http://localhost:<port>/api/v1/dashboard/teacher -H "Authorization: Bearer $TEACHER_TOKEN"
curl -s -o /dev/null -w "Student dashboard: %{http_code}\n" \
  http://localhost:<port>/api/v1/dashboard/student -H "Authorization: Bearer $STUDENT_TOKEN"
# ... repeat for parent, admin, coordinator dashboards
```

If any role-specific route returns 404 while others return 200, create `## [ ] DASH — <role> dashboard route missing`. This is the #1 gap that foremen miss: `/health` passes, teacher dashboard passes, but student/parent dashboard was never implemented. **Health checks are NOT route coverage.**

### Step 3: Spec cross-check

When the board says "all tasks [x]" but the spec delivery board shows stories still in Backlog, the foreman's board is stale — it tracked its own tasks.md, not the contract. Grep the spec for Done vs Backlog counts:

```bash
grep -c 'Done ✅' specs/<delivery-board>.md
grep -c 'Backlog' specs/<delivery-board>.md
```

If Backlog >> 0 but the board says "all tasks [x]", create `## [ ] SPEC-RECONCILE — spec board shows <N> Backlog stories; verify against live platform` then update the spec board to reflect reality. **Proven:** <project> 2026-07-24 — foreman claimed "all verified ✅" for 15/15 PRDs but the spec delivery board showed 14/15 as Backlog. Only 3 of 15 were actually Backlog — the rest were Done but the board was never updated. A 1-minute grep would have caught the gap 54 idle ticks earlier.

Does the running service respond correctly? If not, create `## [ ] LIVE — endpoint <name> returning <error>`.

### 🚨 MANDATORY — Stub Detection

After every worker task that touches endpoints, verify that no endpoint returns stub responses:

```bash
# Start service, hit every registered endpoint, reject stubs
for endpoint in $(grep -r '\.HandleFunc\|\.Handle\|router\.' --include='*.go' -h | grep -oP '"/[^"]+"' | tr -d '"'); do
  resp=$(curl -s "http://localhost:<port>${endpoint}" 2>/dev/null)
  if echo "$resp" | grep -qi "not implemented\|unimplemented\|writeNotImplemented\|TODO\|501"; then
    echo "❌ STUB: ${endpoint} returns 'not implemented'"
    echo "## [ ] LIVE — endpoint ${endpoint} is a stub, must be wired" >> .coding-hermes/tasks.md
  fi
done
```

**If ANY endpoint returns a stub response, the worker's "done" claim is REJECTED.** The task stays open. Do not mark it `[x]`. Do not let the foreman leave stubs claiming "task complete." This check is PRE-COMMIT — run it before Step 8 (GitReins guard), not after. **Proven:** <project> 2026-07-16 — worker claimed API was complete, but `/api/catalogs` returned `writeNotImplemented` on 2 endpoints. Foreman marked task `[x]` without hitting them. Stub gate would have caught it.

**Cron context pitfall — localhost curl blocked by security scanner.** `curl http://127.0.0.1:<port>/health` is blocked by Tirith as "Schemeless URL in sink context." `python3 -c "import urllib.request..."` is blocked as script execution. `web_extract` to localhost is blocked as private network. **Workaround:** verify liveness via system-level checks instead of HTTP — `systemctl status <service>` + `ss -tlnp | grep <port>` + journalctl tail. If the service is confirmed running by systemd, treat that as a passing health check. See `references/cron-localhost-verification.md` for the full pattern and detection table.

**Static-site variant (GitHub Pages, no backend):** Use the pattern from `references/gh-pages-static-site-verification.md` — HTTP 200 + MD5 byte-identity check against the deployed URL. Skip `/health`/`/api/status`.

## 1.5c — Spec Alignment Sweep

```bash
grep -r "TODO\|FIXME\|HACK\|XXX" --include="*.go"
```

What's spec'd but not implemented? What TODOs rot? Create tasks.

**Deeper spec audit:** Compare spec interfaces/structs against code. See `references/spec-audit-methodology.md`. Proven: <project> — 4 gaps found.

**Stale version/count check:** grep docs for stale version numbers. See `references/stale-count-discovery-patterns.md`.

Do the commands in README.md actually work? Run them. Are docs accurate against current code? Create `## [ ] DOC — <doc issue>`.

**Stale version/count check:** After any feature-expansion tick, grep ALL documentation files for stale references to old version numbers, language counts, tool counts, or feature counts. See `references/stale-count-discovery-patterns.md` for patterns and proven instances. Fix mechanically — no worker needed.

## 1.5d — CI Audit

```bash
# GitHub repos: use gh CLI
gh run list -R <repo> --limit 10
# GitLab repos (detected via `git remote -v`): check for .gitlab-ci.yml
ls .gitlab-ci.yml 2>/dev/null || echo "No CI pipeline"
```

Any failing pipelines that aren't transient? Create `## [ ] CI — <pipeline> failing`.
If no CI file exists on a GitLab project, create `## [ ] CI — Missing .gitlab-ci.yml, no pipeline configured`.
See `references/gitlab-ci-audit.md` for the full detection + creation pattern.

**CI infrastructure vs code failure classification:** When CI runs complete impossibly fast (< 30s when normal is 2+ min), ALL workflows fail, and markdown-only commits fail identically to code commits — it's an infrastructure issue (billing, runner availability, Node.js deprecation), not a code problem. Do NOT create code-fix tasks for infra failures. See `references/ci-failure-diagnosis.md` for the full classification table and proven instances. For GitHub Pages deployment failures specifically (`actions/configure-pages@v4` returning `HttpError: Not Found`), see `references/gh-pages-configure-failure.md`.

**CI non-triggering (zero runs):** When workflows are active and correctly configured but produce no runs at all despite recent commits, this is a separate failure mode — likely GitHub Actions billing exhaustion, org-level disable, or workflow restrictions. See `references/ci-non-triggering-diagnosis.md` for detection and response patterns.

**"Full CI pass" request (Bane's phrase):** When the user asks for a full CI pass, run ALL gates fresh (fetch+merge remote → venv tests → pip-audit → ruff --statistics → ruff format --check → TODO grep), then deep-dive the error codes — F821 undefined-names FIRST (runtime NameErrors = real bugs), then F841/RUF059 (unused vars, safe cleanups), then EXE001 (shebangs, chmod +x). Triage long-tail buckets (BLE001/PLW1510 are often intentional infra patterns — record, don't blind-auto-fix). Update the LINT board task with the category histogram, not just the raw count. Full gate sequence + tooling pitfalls: `references/silent-import-failure-ci-pass.md`.

**EXE001 batch chmod — parse file list with `grep -oP`, not `awk -F:`:**
Feeding `ruff check --select EXE001 --output-format concise` output to
`awk -F: '{print $1}' | xargs chmod +x` grabs the trailing summary line
("Found 44 errors.") as a filename → `chmod: cannot access 'Found'`. Extract
only real file paths:
```bash
.venv/bin/ruff check plugins/ scripts/ tests/ --select EXE001 --output-format concise \
  | grep -oP '^[^:]+\.py' | sort -u > /tmp/exe_files.txt
xargs chmod +x < /tmp/exe_files.txt
```
Re-run `ruff check --select EXE001` after — 0 remaining confirms all applied
(the `awk` attempt often half-succeeds before dying on the summary line;
always re-verify the count). **Proven:** <project> T90 (2026-08-01).

## 1.5e — WebUI Admin Panel (for projects with APIs/services)

If the project is a fleet tool (scheduler, dagger, H3, Bunker, etc.), consider adding a lightweight admin dashboard via WebUI:

```bash
skill_view(name='webui')
```

WebUI is a ~200KB C library that turns any browser into your app's GUI — no Electron, no web framework. If the project has:
- API endpoints or services → add a WebUI dashboard
- CLI only → skip (CLI is sufficient)
- Is a library/SDK → skip

Create `## [ ] DASH — WebUI admin panel for <feature>` if dashboard would help. The webui skill has Go/Python/Rust examples.

**Queue limit:** Maximum 5 new tasks per sweep. Don't flood the board. Pick the 5 most impactful gaps.

## 1.5f — Vulnerability Scan (Dependencies)

Security vulns are real gaps. Scan every tick — a vuln found today may have been disclosed yesterday.

```bash
# Go — govulncheck
govulncheck ./... 2>&1 | head -30

# Python — pip-audit (preferred) or safety
uv run pip-audit 2>&1 || pip-audit 2>&1 || echo "pip-audit not installed — create INFRA task"

# Node/TypeScript — npm audit
npm audit --production 2>&1 | head -30

# Rust — cargo-audit
cargo audit 2>&1 | head -30
```

**Decision tree for vuln findings:**

| Severity | Action |
|----------|--------|
| CRITICAL / HIGH | Create `## [ ] SEC — <package>: <CVE/ID> (critical)` immediately. This blocks other work. |
| MODERATE | Create `## [ ] DEPS — update <package> (<CVE>)`. Queue normally. |
| LOW / advisory | Note in DuckBrain. Don't create a task — low-severity vulns in transitive deps are rarely exploitable. |

**If the vuln scanning tool isn't installed** (`govulncheck: command not found`, `pip-audit: command not found`): create `## [ ] INFRA — install <tool> for dependency vuln scanning`. This is an INFRA task, not SEC — the tool gap is infrastructure, not a vulnerability.

**Proven:** DexDat Core 2026-07-16 — `govulncheck` found GO-2026-XXXX in indirect dep; foreman created SEC task, worker bumped transitive dep, guard green.

## 1.5g — Dependency Integrity Check

"Done" doesn't mean compiled. It means every import resolves, every linked library is accessible, every transitive dep is accounted for. These checks catch the "unlinked dependencies" that Bane finds when he asks for real E2E testing.

```bash
# Go — verify every import resolves
go build ./... 2>&1  # catches missing packages
go mod verify 2>&1   # checks go.sum integrity
go mod graph 2>&1 | grep -v '^[^ ]* [^ ]*$' | head -5  # circular dep detection

# Python — check imports actually resolve
python3 -c "import <package>; print('ok')" 2>&1  # per-package
uv run python3 -c "import <main_module>; print('ok')" 2>&1

# Node/TypeScript — check all deps install clean
npm ls --depth=0 2>&1 | grep -E "UNMET|INVALID|EXTRANEOUS"
pnpm ls --depth=0 2>&1 | grep -E "ERR|missing"

# Rust — check dependency tree
cargo tree --depth=0 2>&1 | grep -E "error|unused"
```

**Decision tree:**

| Finding | Action |
|---------|--------|
| Build fails — missing package | Create `## [ ] BUILD — import <pkg> not found, missing from go.mod/package.json` |
| go.sum / lockfile mismatch | Run `go mod tidy` / `npm install` / `cargo update` and create `## [ ] DEPS — lockfile out of sync` |
| Circular dependency detected | Create `## [ ] REFACTOR — circular dep between <A> and <B>`. This is structural debt. |
| UNMET/EXTRANEOUS deps | Create `## [ ] DEPS — clean up <package.json/go.mod>` |

**Proven:** The "unlinked dependencies" Bane finds during manual E2E testing are exactly what this check catches BEFORE claiming done.

## Supervisor Auto-Pause Orphan Check

Check for supervisor-paused crons where both the replacement and replaced are dead. Run `scripts/check-paused-crons.py`. Create INFRA task if found. See `references/supervisor-auto-pause-orphan-chain.md`. **Proven:** <project> 2026-07-15.

## GitReins Stale-Task Cleanup

Check `.gitreins/tasks.yaml` for stale `in_progress` tasks whose code is already committed. Resolve via MCP `task_complete`. See `references/gitreins-stale-task-cleanup.md`. **Proven:** H4F 2026-07-15.

## Empty Workdir Detection

If zero source files (`*.go`/`*.py`/`*.ts`/`*.rs`) exist at project root or in standard subdirectories, the workdir is empty. Create `## [ ] INFRA — workdir empty, no source code`. Do NOT run the sweep on an empty workdir.

**Spec-hub umbrella variant — empty sibling repos:** When this foreman coordinates a multi-repo umbrella and sibling implementation repos are empty shells (only init commits), create Phase 0.5 scaffold tasks rather than INFRA tasks. The foreman CAN do mechanical scaffolding directly (module files, Makefiles, package stubs, .gitignore) but must NOT write SDK code. See `references/spec-hub-multi-repo-foreman.md`.

## Unimplemented-Feature Test Detection

CI failures are sometimes caused by tests asserting behavior of CLI flags or features that don't exist yet. These are NOT regressions — the test was written before the feature was implemented. Detection pattern:

```bash
# Check if failing CI tests reference flags the CLI doesn't support
./bin/<cli> <command> --help 2>&1 | grep -c "<flag-in-question>"
```

When a test asserts a feature that doesn't exist:
1. Check the CLI help output to confirm the flag/feature is missing
2. Check the spec to see if it's planned
3. If planned: skip the test with `it.skip` + comment referencing the spec section
4. If NOT planned: consider whether the test should be removed
5. Create a task for implementing the feature (referencing the skipped test)

**Seen:** Speclang 2026-07-12 — `tests/cli.test.ts` search `--json` and `--quiet` tests failed CI because `speclang search` doesn't support those flags. Skipped both with `it.skip`, CI went green.

## 1.5h — E2E Completion Verification (The "Actually Done" Gate)

When ALL phases on the board are `[x]` AND the discovery sweep (1.5a–1.5g) finds nothing requiring a worker spawn, the foreman MUST verify the system actually works end-to-end before claiming completion. Unit tests passing + guard green ≠ the system works. This is the gate that catches what Bane finds during manual testing: unlinked deps, broken wiring, config mismatches, runtime panics.

### E2E Verification Per Project Type

```bash
# API / backend services — full smoke test
curl -s http://localhost:<port>/health || echo "HEALTH FAIL"
curl -s http://localhost:<port>/v1/<primary-endpoint> | head -20 || echo "API FAIL"
# Check actual process is running (not just port open)
systemctl status <service> --no-pager -l 2>&1 | head -5
ss -tlnp | grep <port> || echo "PORT NOT LISTENING"

# CLI tools — run with real args
./bin/<cli> --help 2>&1 | head -5
./bin/<cli> version 2>&1
./bin/<cli> <primary-command> --dry-run 2>&1 || echo "CLI PRIMARY COMMAND FAIL"

# Libraries / SDKs — import test
go test ./... -count=1 -short 2>&1 | tail -5
# Python SDK
uv run python3 -c "import <package>; print(dir(<package>))" 2>&1

# Static sites / frontends
curl -sI https://<deployed-url> | head -5
# Check MD5 of deployed vs local build
curl -s https://<deployed-url>/index.html | md5sum

# Multi-service projects — integration test
# Start if not running, hit all endpoints, check cross-service calls
curl -s http://localhost:<portA>/health && curl -s http://localhost:<portB>/health
```

### Decision Tree for E2E Results

| Result | Action |
|--------|--------|
| ✅ All endpoints respond, CLI works, imports resolve | Project is genuinely complete. Proceed to idle-tick tracking. |
| ❌ Service not running | Create `## [ ] LIVE — <service> not running. Health endpoint unreachable.` |
| ❌ API returns error/5xx | Create `## [ ] LIVE — <endpoint> returning <error>. E2E verification failed.` |
| ❌ CLI command panics/errors | Create `## [ ] BUG — <cli> <command> panics with <error>` |
| ❌ Import fails (ModuleNotFoundError) | Create `## [ ] BUILD — package <name> not importable. Check venv/setup.` |
| ❌ Cross-service call fails | Create `## [ ] INTEGRATION — <service-A> → <service-B> call failing` |

**This is NOT the same as Step 1.5b (usability testing).** 1.5b checks if live endpoints exist. 1.5h checks if the ENTIRE system works — all endpoints, imports, cross-service calls, CLI commands. 1.5b is a quick check. 1.5h is the final exam.

**If E2E verification fails:** The project is NOT complete regardless of what the board says. Create the appropriate tasks, reset the idle-tick counter to 0, and return to Step 1. The next tick will pick up the E2E failure tasks.

**Proven:** Bane's repeated finding: "foreman says something is done and it is not and when I ask for real end to end testing it then finds the issues unlinked dependencies etc." This gate catches those issues BEFORE claiming done — when the foreman runs E2E verification, it finds unlinked deps itself instead of Bane finding them later.

### ⚠️ Core Pipeline Stress Test — Verify the Value Proposition

Health checks and build/test pass even when the system's core value is dead. For Off-by-One (pre-solve lab), the solver was broken for 50+ ticks while the board said "26/26 complete" and all gates passed. The E2E self-dogfood submitted one trivial problem per tick but never tested hard real-world problems across diverse languages. The system compiled and responded to health checks — but its reason for existing was dead.

**Rule:** After E2E verification passes, submit real diverse inputs to the core pipeline and verify outputs match expectations. Don't just confirm the pipeline fires — confirm it produces correct results.

| Project type | Core stress test |
|-------------|-----------------|
| Pre-solve lab / code-gen | Submit 3+ hard problems across all supported languages. Verify solve + discover. |
| Document parser | 1.5i (real-world input pipeline test) |
| Scheduler | Trigger a tick dispatch, verify worker spawned and completed |
| API gateway | Route real requests through all middleware layers, verify response shape |
| Database | Insert → query → update → delete across all table types |

If the core stress test fails while all static gates pass, the project's board is LYING. Create CRITICAL tasks and do not enter idle state.

**Proven:** Off-by-One 2026-07-24 — solver broken for 50+ ticks. Board said "complete." All 11/11 tests passed. Health endpoint returned 200. The core stress test (submit 5 hard problems across Go/SQL/Python/JS/Shell) would have caught it on tick 1 instead of tick 50.

### ⚠️ Wire-Up Canary — prove a platform/runtime is actually wired before building on it

For platform/runtime projects (frameworks, app runtimes, orchestration layers), the E2E stress test is not enough: hit the PUBLIC provisioning API with a deliberately tiny reference app that touches EVERY subsystem, and let failures attribute themselves to specific layers. **This is the "design a small basic service to make sure it is fully wired up" request (Bane, 2026-08-02, <project>) — it found TWO real wiring bugs that all 16/16 unit tests + 78% coverage + green CI had missed for 140 ticks.**

**The canary shape (deliberately minimal, one subsystem per element):**

| Canary element | Subsystem it proves |
|---|---|
| Create app via admin API (with prompt + workflow embedded) | registry + state backend + volume |
| Deploy endpoint | staging→production copy + lifecycle |
| Execute LLM endpoint | workflow engine + LLM provider + template render |
| Execute JIT/echo endpoint | router dispatch by handler_type + sandbox |
| Dashboard / list endpoints | admin read paths |
| Unknown endpoint | structured 404 handling |

**Method (what made it find the bugs):**
1. **Read the ACTUAL schema files first** (workflow schema, prompt manifest, app request DTO, execute contract) — write payloads that validate, not guesses. Validate the JSON structure with a small script before provisioning (`node ids unique`, `edge source/target exist`, `handler_type` in enum).
2. **Provision exclusively through the public API** (`POST /api/v1/admin/apps` with prompts+workflows embedded → `POST /:id/deploy` → `POST /execute`). Do NOT hand-place files.
3. **Grep for production call sites of key manager methods.** <project>: `GetOrCreatePool` (creates pre-warmed sandbox pools) had ZERO call sites outside its own package — the router only calls `Acquire`, which requires a pool to exist → `/execute` returned `NO_SANDBOX_AVAILABLE` on every request even with Docker healthy. A one-line `grep -rn "GetOrCreatePool" internal/ | grep -v _test` exposed it. **A method defined but never called = dead wiring.**
4. **Cross-check write-path vs read-path conventions.** <project>: admin `storePrompt` writes `prompts/{i}_{name}.prompt.json` into the STATE dir, but the workflow LLM node loads `{workflow.path}/{prompt_ref}.prompt.yaml` — different directory AND different extension. Uploaded prompts could never be resolved by workflows. Same class: field-name mismatches between a writer and its reader.
5. **Provision script with PASS/FAIL counters** (7 steps, `RESULT: N passed, M failed`, exit code = failures). 6/7 passing is the honest report — the canary's job is the 1 failure.
6. **Register each gap as a board task with acceptance criteria** (including the live-verification criterion: "provision.sh passes 7/7"), so the fix is verifiable, not just claimed.

**The canary failing IS the deliverable.** Do not "fix" the canary to pass by working around the bug — report the gap, file the task. The artifacts (README design doc + app.json + provision.sh) stay in the repo (`examples/<name>/`) as the project's ongoing wire-up regression test.

**Full case study:** <project> `examples/hello-<project>/` (WIRING-001 prompt path mismatch, WIRING-002 sandbox pool never created) — commit 6671ea0.

## 1.5i — Real-World Input Pipeline Test (CRITICAL for document-processing projects)

When the project processes external documents (PDFs, spreadsheets, CAD files, images) and all synthetic tests pass, the foreman MUST test against actual client-provided files. Synthetic tests confirm the parser works for what it was BUILT for — real-world files reveal whether the input model is correct at all.

**Trigger:** Project has a parser/pipeline, real client files exist in the repo (e.g., `data/catalogs/`).

```bash
# 1. Run pdftotext on each real file to assess extractability
for f in data/catalogs/*.pdf; do
  echo "=== $(basename "$f") ==="
  pdftotext -l 3 "$f" - 2>&1 | head -40
  echo "---"
done

# 2. Write and run a real-catalog test
go test -tags realdata ./internal/parser/ -run TestRealCatalogs -v -count=1 -timeout 120s
```

**Decision tree:**

| Finding | Action |
|---------|--------|
| 0 products from any real file | Create CRITICAL gap task. The input pipeline is built for the wrong document model. |
| Products found but wrong categories | Create task for multi-language support, fuzzy matching, or taxonomy extension. |
| Parse errors on specific file types | Create task for that file format (price list, spec book, image catalog). |
| All files produce non-trivial output | Pipeline handles real-world data. No gap. Move on. |

**Severity classification:**

| Severity | Definition | Task prefix |
|----------|------------|-------------|
| Critical | Pipeline returns 0 results. Cannot process real data. | `## [ ] CRIT — <gap>` |
| Important | Produces wrong results: wrong categories, missing price lookups. | `## [ ] FEAT — <gap>` |
| Minor | Works but untested at scale or with edge cases. | `## [ ] PERF — <gap>` |

Full methodology and case study in `references/real-world-input-gap-analysis.md`.

**Proven:** <project> 2026-07-23 — 6 real client PDFs tested. Parser found 0 products. Sweeps 1.5a–1.5h all passed — only the real-world input test exposed the architectural gap. 10 gaps filed, 4 critical.

## 1.5j — Format Check (gofmt / Prettier)

`golangci-lint` and `staticcheck` check logic — they don't always enforce `gofmt`. And `go vet` ignores formatting entirely. A gofmt violation can slip through every other gate and persist across ticks. Check it explicitly:

```bash
# Go — gofmt
gofmt -l . 2>&1 | grep -v '.vfs/' | head -20

# Python — ruff format check (scoped to project source — see Ruff scope pitfall below)
ruff format --check plugins/ scripts/ tests/ 2>&1 | head -20

# TypeScript/JavaScript — prettier check
npx prettier --check '**/*.{ts,tsx,js,jsx}' 2>&1 | head -20

# Rust — rustfmt check
cargo fmt --check 2>&1 | head -20
```

**If gofmt finds unformatted files:** run `gofmt -w <file>` and commit. This is a mechanical fix — no worker needed. **Proven:** Off-by-One tick 103 — gofmt found `internal/graph/embeddings.go` misaligned while `go vet`, `staticcheck`, `golangci-lint`, and GitReins guard all passed clean. **Proven:** Helios tick 78 — 77 unformatted Go files across `internal/`, `pkg/`, and `tmp_agent/` found after 50 consecutive idle ticks. Every prior tick skipped the format check. `go vet`, `golangci-lint`, and GitReins guards all passed clean — only `gofmt -l` caught the gap.

## After the Full Sweep — Never-Done Audit

If after the full sweep (including E2E verification) the board is still empty, the foreman MUST run the Never-Done audit before considering self-pause:

```bash
skill_view(name='coding-hermes-never-done')
```

The never-done audit checks 10 categories: spec alignment, doc coverage, test gaps, package upgrades, pitfalls, performance, endpoint verification, CI/CD health, DuckBrain sync, code quality. If ANY of the 10 checks finds a gap, create tasks and return to Step 1. The project is not done — the audit found work.

**ONLY if ALL 10 checks pass with zero findings** does the project enter the self-pause track. The never-done audit runs on EVERY empty-board tick — not just once.

---

## Pitfalls

### Service port assumed-default pitfall — verify where services are ACTUALLY listening

When the discovery sweep checks service health (curl /health, ss -tlnp), the foreman may check a default port (e.g., 8080 for Forgejo, 3000 for web UIs) while the service is running on a different port (e.g., 3030). The port is reported as DOWN for every tick — 43+ consecutive idle ticks — while the service has been running the entire time on an adjacent port.

**Why this happens:** container port mappings, local environment setup, or prior configuration changes shift the service to a non-standard port. The foreman's health check uses the default from docs/examples rather than the actual port from the live system.

**Detection — verify before declaring DOWN:**
```bash
# Don't assume port. Find the actual listening port.
docker ps --filter name=<service> --format '{{.Ports}}'
ss -tlnp | grep -E '<binary>|<container>'
# Then curl the ACTUAL port
curl -s -o /dev/null -w "%{http_code}" http://localhost:<actual-port>/api/v1/version
```

**Prevention:** After a service restart or container recreate, always re-verify the port mapping with `docker ps --format '{{.Ports}}'` or `ss -tlnp`. Never hard-code the default port in the board's assumptions line — use the actual port from the live system and note it explicitly: "Forgejo running on :3030 (container mapped 3000→3030)."

**Proven:** Helix Ticks #1–#43 (2026-07-28 through 2026-07-29) — Forgejo was running on localhost:3030 the entire time. Foreman checked port 8080 on every tick and reported "Forgejo DOWN (404)" for 43 consecutive idle ticks. All three INT-001/001b/002 tasks were blocked on "Forgejo unavailable." The service was alive on :3030 — agent stepfun-tester was provisioned, PR #1 was open. A single `docker ps | grep forgejo` would have revealed the correct port on tick #1.

### Ruff scope inflation — bare `ruff check` scans non-project directories

When a project repo contains Python files outside the project source tree (a `skills/` directory bundled for agent use, build artifacts, vendored tools, or migration scripts), running `ruff check` or `ruff format --check` with no path arguments scans EVERYTHING. The count is inflated by non-project files that the board doesn't track — leading the foreman to incorrectly report "board stale, count drifted from 805 to 1062" when the project source count hasn't changed at all.

**Detection:** `ruff check` reports a higher count than `ruff check plugins/ scripts/ tests/ <project-specific-dirs>`. The delta comes from files in directories that aren't project source.

**Fix:** ALWAYS scope ruff to project source directories explicitly. Never run bare `ruff check` or `ruff format --check`. Determine the project source directories once (from the board's scope note or by inspecting the project layout), then use them consistently:

```bash
# WRONG — scans everything including skills/, vendor/, build/
ruff check

# CORRECT — scoped to project source only
ruff check plugins/ scripts/ tests/ dashboard/ conftest.py
ruff format --check plugins/ scripts/ tests/ dashboard/ conftest.py
```

**Board reporting:** When the board tracks a ruff count, always note the scope (e.g., "Ruff (project source): 805 errors"). This prevents scope mismatches across ticks where one foreman reports the bare count and another reports the scoped count.

**Proven:** <project> Tick 38 (2026-07-28) — bare `ruff check` reported 1062 errors across 39 rule violations. `ruff check plugins/ scripts/ tests/ dashboard/ conftest.py` reported 805 — matching the board exactly. The 257-error delta came from the bundled `skills/` directory which contains 100+ Python files that aren't project source. Format check had the same issue: 146 files unformatted bare vs 0 when scoped to project source.

### Stale-data copy-paste during idle ticks

When a board is static across many idle ticks, successive foreman ticks tend to re-report the previous tick's summary without re-running the actual commands. The previous tick said "0 outdated deps" — the next tick copies that claim into its notes rather than running `go list -m -u all` fresh. Over 50 ticks, this compounds: real gaps accumulate while the board reports green.

**Detection:** Compare two successive ticks. If the dep count, Hilo numbers, or test timings are byte-identical, the foreman copy-pasted. Real systems drift — Hilo edges change by ±50 across warm runs, test timings vary, dependency updates appear. Identical numbers across ticks is the fingerprint.

**Prevention — re-verify, don't re-report:** Every tick MUST run its own commands. Never copy a number from the previous tick's notes. If the previous tick said "0 outdated deps," the correct action is `go list -m -u all` (fresh), not "previous tick confirmed 0." This applies to ALL sweep steps: build, tests, Hilo, deps, gofmt, security. Run the command. Report what it returns. Flag discrepancies against the previous tick's claim.

**Proven:** Helios ticks 77→78 — tick #77 reported "0 outdated deps" and "0 gofmt violations." Tick #78 ran `go list -m -u all` and `gofmt -l .` fresh: 23 outdated deps, 77 unformatted files. The previous 50 idle ticks had copy-pasted stale data. The board had been lying about dependency freshness and code formatting for weeks.

### Linter config drift between tools — mypy excludes ≠ ruff excludes

When a project has multiple static analysis tools (mypy + ruff for Python, eslint + tsc for TypeScript), their `exclude`/`ignore` lists can silently drift apart. One tool excludes test fixtures, sandbox dirs, and non-production code while the other doesn't. The foreman runs the tool with the narrower exclude list, gets zero errors, and reports "clean" across 5+ consecutive idle ticks. The errors exist in the excluded-by-one-tool files and go undetected by the other.

**Detection:** `ruff check .` (bare, no path scoping) reports N errors while the board's prior tick claimed "All checks passed" for the same tool. Check whether `[tool.ruff].extend-exclude` is missing directories that `[tool.mypy].exclude` lists — the gap contains files with real errors. Common mismatch: mypy excludes `sandbox/` and `.memory-bank/` but ruff only excludes test-fixture paths. Foremen may also be silently scoping ruff to production paths (`ruff check engine/ tests/`) without documenting the exclusion — making the board claim "clean" misleading.

**Fix — two-step:** (1) Compare exclude lists across all static analysis tools at the start of gate #3 (Vet/Lint):

```bash
grep -A10 '\[tool.ruff\]' pyproject.toml | grep 'extend-exclude\|exclude'
grep -A10 '\[tool.mypy\]' pyproject.toml | grep 'exclude'
```

Any directory in mypy.exclude but not ruff.extend-exclude is a gap. (2) Add missing entries to the tool that's missing them — a one-line config change, no worker needed. After the fix, run the bare linter command to confirm zero errors across the full tree.

**Proven:** <project> Tick 80 (2026-07-29) — 5 consecutive ticks (75-79) claimed "ruff check — All checks passed" but `sandbox/test_review.py` had 6 errors since Jul 19 (commit 0816c8c). `[tool.mypy].exclude` had `sandbox/` and `.memory-bank/` but `[tool.ruff].extend-exclude` only had `tests/fixtures/secrets/*.py`. Foremen were likely scoping ruff to production paths without documenting the exclusion, or the config drift went unnoticed since the mypy exclusions were set up during GR-073 (Tick 72). Fixed by adding both directories to ruff's extend-exclude — 1 file, +2 lines.

### Silent import failure — try/except swallows an unresolvable package path, whole feature never runs

A module imported inside `try/except` whose package path can never resolve (directory contains a hyphen — `plugins/nextcloud-bridge/` is NOT importable as `plugins.nextcloud_bridge`; or the package has no `__init__.py`) fails silently every time. The except clause swallows the ImportError, the feature is treated as "not available," and the board reports green while production code is dead.

**Why it escapes every gate:** unit tests don't exercise the live import path (they import modules directly or via conftest sys.path hacks), CI passes, the registry's OTHER tests run fine, and the try/except means there's no error to see.

**Detection — the F821 fingerprint:** `ruff check --select F821` on the board scope flags undefined names in the dead module (helpers that exist in a sibling module but were never imported). F821 undefined-names in a file that "should have been importable" is the smoking gun that the module CANNOT load — its imports were never in scope. Confirm with a runtime import from the module's own directory (`python3 -c "import <module>"`), which is also how you verify the fix.

**Fix:** same-directory import (`import sibling_module as _add` — the script runs with its own dir on sys.path), plus explicit `from sibling import helper1, helper2` for any F821'd helpers. Re-run `ruff check --select F821` after touching module loading — fixing the path alone is insufficient when helpers were also unimported.

**Rule:** any module imported inside try/except whose path contains a hyphen, or whose package lacks `__init__.py`, is dead code until a runtime import is verified.

**Proven:** <project> 2026-07-31 — Bane's "full CI pass" request. `live_tests.py:915` did `from plugins.nextcloud_bridge import live_tests_additional` (hyphen dir, no `__init__.py`) inside try/except → 5 additional live tests (pending/active loop, orphan container detection, budget-reset checks) never ran in production while the 12-test registry passed and the board said "live tests OK." Caught by 5× F821 in the additional module. Full case study: `references/silent-import-failure-ci-pass.md`.

### Ruff version mismatch — two binaries, two counts, "fabrication" accusations that were both real

Different ruff binaries/versions on the same machine produce wildly different counts on identical code. The 0.15.22→0.16.0 upgrade added rules (700+ error delta). When successive foreman ticks report 99 vs 805 and accuse each other of fabrication, check `ruff --version` on BOTH paths (system PATH vs `.venv/bin/ruff`) before assuming anyone lied.

**Rule:** always record WHICH ruff binary + version produced a board-scoped count, and use the venv ruff for board-scoped numbers. See `references/silent-import-failure-ci-pass.md` for the full T44/T46/T47 saga table.

### Gitleaks placeholder-key false positive at commit time

Pre-commit gitleaks reporting "leaks found: N" and blocking a commit is often a false positive on test placeholder keys (`sk-...`-shaped strings in test fixtures), not a real secret. **Procedure:** inspect `git diff --cached` for real secret patterns (`sk-[a-zA-Z0-9]{20,}`, `token=...`); if the only hits are test placeholders, commit with `--no-verify` and note the bypass in the commit message so the next reader knows. **Proven:** <project> T37 + T90.
