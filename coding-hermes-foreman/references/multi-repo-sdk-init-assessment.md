# Multi-Repo SDK INIT Assessment Pattern

When a per-SDK foreman (not the umbrella coordinator) ticks for the first time on a scaffold-only SDK sub-repo, use this assessment checklist. The spec lives in sibling repos — the foreman must read across the parent directory.

**Proven:** H3 Go SDK (2026-07-14) — sdk-go foreman INIT assessment, 8 stub files, spec in `../h3/specs/`, protocol schemas in `../protocol/schemas/v1/`.

## Detection Signals

- `go.mod` exists with module path and Go version, but zero dependencies (`require` block missing or empty)
- All `.go` files are package declarations — no structs, interfaces, functions, or methods
- `go build ./...` and `go test ./...` pass trivially (no code, no tests)
- `make build`, `make test` work but produce nothing
- `git log --oneline` shows 1-3 scaffold commits (init, scaffold, config)
- The parent directory (`../`) contains sibling repos: `h3/` (specs), `protocol/` (schemas), `sdk-python/`, `sdk-typescript/`, `shim/`

## INIT Assessment Checklist

### 1. Read the umbrella AGENTS.md FIRST
```bash
cat ../AGENTS.md
```
This tells you the dependency chain, foreman topology, and which sibling repos hold what. The umbrella AGENTS.md is the map.

### 2. Read the spec from the sibling spec repo
```bash
ls ../h3/specs/
cat ../h3/specs/04-SDK-Libraries.md   # or whatever spec covers this SDK
cat ../h3/specs/01-Overview-Architecture.md  # for context
```
The spec contains the exact Go interfaces, structs, HTTP endpoints. Grade it for axiomatic quality — if it has exact interfaces + DDL + error paths, the foreman CAN implement directly from it.

### 3. Read the protocol schemas from the sibling protocol repo
```bash
ls ../protocol/schemas/v1/
cat ../protocol/schemas/v1/common.json
cat ../protocol/schemas/v1/decision.json
cat ../protocol/schemas/v1/process-request.json
```
These are the source of truth for wire-format types. The SDK's `protocol/types.go` must match these exactly.

### 4. Audit project structure against spec
Check each item in the spec's package structure table:
- Directories exist on disk? 
- Files named correctly?
- Any implementation or all stubs?

### 5. Audit dependencies
```bash
cat go.mod
```
Does the project need external deps? The spec may reference packages not in go.mod (e.g., `uuid` for DecisionID generation).

### 6. Check sister SDKs for maturity baseline
```bash
ls ../sdk-python/src/ 2>/dev/null
ls ../sdk-typescript/src/ 2>/dev/null
```
Are they at the same scaffold level or further along? This sets expectations — don't over-implement relative to sister SDKs.

### 7. Check DuckBrain namespace
```python
duckbrain_list_keys(prefix="/project/sdk-<lang>/", maxDepth=3)
```
If empty, seed with INIT findings + project config. This is the foreman's Step 10 deliverable.

### 8. Audit missing project infrastructure
- README.md? 
- `.github/workflows/ci.yml`?
- `.gitreins/config.yaml` properly configured?
- `.gitignore` covers binaries, Hilo, IDE?

### 9. Check module path against spec
The `go.mod` module path may differ from the spec's stated module path. Flag this discrepancy explicitly — it needs resolution before any `go get` / import statements are written.

## Board Restructuring

The INIT board typically has vague tasks like `INIT`, `SPEC`, `DOC`, `TEST`, `CI`. Replace with concrete, phased implementation tasks drawn from the spec:

```
## [x] INIT — (completed by this assessment)
## [ ] SPEC — Verify 1:1 alignment, resolve discrepancies
## [ ] CORE-S01 — Protocol types from JSON Schema
## [ ] CORE-S02 — Harness interface + HTTP handler
## [ ] CORE-S03 — Testbed (MockHermes + assertions)
## [ ] DOC-S01 — README + examples
## [ ] CI-S01 — GitHub Actions
```

Each task must list specific files, acceptance criteria, and reference the spec section.

## DuckBrain Seeding

After assessment, seed the namespace with at least two entries:
1. **Events entry** (`/project/<name>/events/<date>-init`) — comprehensive assessment findings
2. **Config entry** (`/project/<name>/config/status`) — go version, module path, dependency status, phase ordering, spec location

## What NOT to do

- **Don't spawn a worker for INIT** — this is the shortened investigation loop (Steps 5-7 skipped). The foreman IS the investigator.
- **Don't create an INFRA task for "empty workdir"** — stub files ≠ empty. The scaffold was intentional.
- **Don't write implementation in the INIT tick** — the board must be structured first. SPEC comes before CORE.
- **Don't change the module path without confirmation** — note the discrepancy, don't resolve it unilaterally.
