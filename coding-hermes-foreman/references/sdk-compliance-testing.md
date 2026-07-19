# SDK Compliance Testing in Discovery Sweeps

When the project is an SDK implementing a protocol spec (e.g., H3, OpenAPI, gRPC), the discovery sweep's Step 1.5b (usability testing) takes a different form: run the **protocol compliance test battery** against the SDK's example harness. This validates the implementation against the spec, not just whether a service responds.

## When to Use

**Detection signals:**
- The project's spec mentions a compliance test battery (e.g., `h3-test` from `get-h3/shim`)
- The README or AGENTS.md says "Must pass X before release"
- The project parent monorepo has a `shim/` or `test-battery/` directory
- The project is one of several SDK implementations (Go, Python, TypeScript) for the same protocol

## Pattern — Local Testing

```bash
# 1. Build the example harness
go build -o /tmp/sdk-example examples/name/main.go

# 2. Start it in background
/tmp/sdk-example &  # via terminal(background=true)

# 3. Verify health
curl -s http://localhost:9191/v1/health

# 4. Run the compliance test battery
/path/to/shim/.venv/bin/test-battery --endpoint http://localhost:9191
```

## Pattern — CI Log Investigation (No Local Run)

When you CAN'T run the tests locally (missing toolchain, cross-repo setup), investigate via CI logs:

### Step 1: Identify the compliance job

```bash
# Get the latest run ID
gh run list -R owner/repo --limit 1 --json databaseId --jq '.[].databaseId'

# Find the compliance job within that run
gh run view RUN_ID -R owner/repo --json jobs --jq '.jobs[] | {name, conclusion, databaseId}'
```

The test battery's unit-test job (same repo) may PASS while the compliance job (cross-repo, runs against external harness) FAILS. These are separate jobs — don't assume the run log shows compliance results.

### Step 2: Get compliance job output

```bash
# gh run view --log shows ALL jobs (verbose, mixed output)
# Use --job for targeted output:
gh run view --job JOB_ID -R owner/repo --log 2>&1 | tail -80
```

Key line to grep for: the compliance test summary block:
```
  Health & Protocol                   6/7  ❌ FAILED
  Process Basic Flows                 6/8  ❌ FAILED
  Decision Types                      6/6  ✅ PASSED
  ...
  TOTAL                               40/43  FAILED
```

### Step 3: Cross-reference with source code

The test battery source (in the shim repo) maps category scores to specific test functions:

- Health & Protocol = `test_1_1` through `test_1_7`
- Process Basic Flows = `test_2_1` through `test_2_8`
- Decision Types = `test_3_1` through `test_3_6`
- Result Handling = `test_4_1` through `test_4_7`
- Error & Edge Cases = `test_5_1` through `test_5_10`
- Stress & Performance = `test_6_1` through `test_6_5`

Read the actual test assertions in the test battery source to understand expectations, then cross-reference with the harness source (in the SDK repo) to identify which fields are missing or wrong. Check BOTH:

1. The harness implementation (does it set the required fields?)
2. The SDK type definitions (do the structs even have the fields?)

### Step 4: Document exact failures

When done, the board entry should include:

- Exact test function names that fail
- Root cause per test (field missing? wrong value?)
- File + line number where the fix belongs
- Whether fix is in the harness or the SDK types

Example board update format:

```
- [x] Specific failing tests identified:
  - test_1_4_health_capabilities: harness Health() doesn't set Capabilities field
  - test_2_4_process_text_finished_false: harness always returns Finished=true
  - test_2_8_process_preserves_history: harness doesn't include History in Decision
- [ ] CROSS-REPO ACTION: sdk-go foreman must fix (3 changes to examples/echo/main.go)
```

## Interpreting Partial Scores

A partial score is NOT a failure — it's diagnostic data. The score breakdown by category reveals exactly which protocol layers are implemented and which need work:

| Score pattern | Meaning | Task to create |
|---|---|---|
| Health (6/7) + Errors (8/10) pass, Process (0/8) fails | SDK types + HTTP layer correct; example harness too simple for full agent loop | `## [ ] TEST` for conformance test harness |
| All categories near zero | SDK HTTP server broken or protocol mismatches | `## [ ] BUG` — investigate JSON schema alignment |
| Health fails but Process passes | Health endpoint missing capabilities or version fields | `## [ ] FIX` — minor HealthResponse gap |
| 40+/43 overall | SDK is protocol-compliant; remaining failures are edge cases | `## [ ] TEST` for specific edge case handling |

## h3-test Specifics

For H3 SDK projects, the test battery lives at `get-h3/shim`:
- **Binary:** `shim/.venv/bin/h3-test`
- **Source:** `shim/src/h3_shim/test_battery.py`
- **Categories:** Health & Protocol (7), Process Basic Flows (8), Decision Types (6), Result Handling (7), Error & Edge Cases (10), Stress & Performance (5) = 43 total
- **Flags:** `--endpoint URL`, `--json` (machine-readable output)
- **Prerequisites:** Python venv with `hermes-h3-shim` installed (`make install` in the shim dir)

## What Tasks to Create

Based on test battery results, create targeted tasks:

1. **Health gaps (score 6/7):** Minor — check capabilities array, version strings, transport field
2. **Process flow gaps (score 0/8):** Major — need conformance test harness implementing full tool_call -> result -> text -> end agent loop
3. **Error handling gaps:** Check error codes match spec, proper JSON error response format
4. **If all pass (>38/43):** Create doc task noting compliance score, flag remaining edge cases

**Maximum 2 tasks from compliance testing** — don't create a task per failed category. Bundle related failures:
- Health + Error gaps -> one `FIX` task
- Process + Decision + Result gaps -> one `TEST` task for conformance harness

**BLOCKED tasks:** When the root cause is in ANOTHER repo (harness-side, not test-battery-side), mark the task as BLOCKED with explicit cross-repo action items. The foreman commits only the board update — no code change in its own repo. The board entry must include enough detail that the other foreman can execute the fix without re-investigating.

## Proven

- **H3 Go SDK 2026-07-15:** Echo harness scored 14/43 (health 6/7, errors 8/10, process 0/8, decisions 0/6, results 0/7, stress 0/5). Created 2 tasks: TEST (conformance harness) and EXAMPLE (consensus integration). Health + error handling confirmed correct; process flow needs full agent loop.
- **H3 Shim 2026-07-18:** CI compliance job 40/43 against sdk-go echo harness. 3 failures identified via CI log extraction + cross-referencing test battery source with echo harness source. All 3 root causes in sdk-go's `examples/echo/main.go` (HealthResponse missing Capabilities, OnProcess always returning Finished=true, Decision missing History echo). Task marked BLOCKED on sdk-go foreman with 3 specific fix locations documented. Board-only commit (`cc72826`), no shim code change needed.

## Related

- **`cross-repo-compliance-test-fix.md`:** When a single compliance test fails and the fix requires changes in BOTH the SDK repo AND the test battery repo (because the test reads from a field path that doesn't match the protocol spec). Proven: H3 QV-GAP-01 (2026-07-18).
