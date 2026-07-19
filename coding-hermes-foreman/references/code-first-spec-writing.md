# Code-First Spec Writing — Documenting Existing Implementations

When a spec task lands on the board but the corresponding code already exists (written from prose-level DuckBrain context by a prior tick), the spec worker's role shifts from "define what should exist" to "document what exists while identifying gaps." This is the **code-first** variant of spec writing, distinct from the **spec-first** pattern where the spec precedes any implementation.

## When This Pattern Applies

- A spec task (SPEC-SXX) is the next pending item on the board
- `git log --oneline -10` shows a recent commit that implemented the corresponding feature
- OR `grep` of the codebase finds the feature already exists on disk
- The task description says "from SPEC-SXX OpenAPI" or "from SPEC-SXX schema" but the spec file doesn't exist yet

**Detection:** Before spawning a worker for a spec task, check `git log --oneline -20` and `grep` the codebase. If the feature code exists, you're in code-first mode.

## Worker Prompt Adjustments

The worker prompt for code-first specs needs 3 additional instructions beyond the standard `spec-worker-prompt-pattern.md`:

### 1. Read Existing Code First
```
**CRITICAL:** The implementation already exists at `<file-path>`. 
Read it FIRST before writing the spec. The spec documents the INTENDED
contract — but you must understand the existing code to identify gaps.
```

### 2. Document the Contract, Not the Bugs
```
The spec describes the INTENDED API contract, not the current behavior.
If the code has bugs (wrong JSON field names, broken path dispatch),
document the CORRECT contract and note the gap in a separate section.
Do NOT encode the bug into the spec just because the code does it.
```

### 3. Add a Conformance Gap Section
```
After the spec body, add a section "N. Implementation Conformance" that
lists gaps between the spec contract and the current implementation.
Format each gap as: "**Gap:** <what the spec says> — *Actual:* <what the code does>"
```

## Identifying Gaps — What to Look For

Common code-first gaps that workers find (proven on Scheduler SPEC-S06):

| Gap Type | Detection Pattern | Example |
|----------|------------------|---------|
| Missing JSON tags | Go structs without `json:"..."` tags emit PascalCase field names | `Name` in JSON instead of `name` |
| Path dispatch bugs | URL parsing that splits on `/` without stripping the API prefix | `/api/v1/projects/alpha` → `parts[0]="api"` |
| Missing validation | No required-field checks on create/update endpoints | Accepting empty project names |
| Response shape drift | Response fields don't match the data model spec from a prior SPEC | `budget_total` vs `budget_used` naming inconsistency |
| Missing endpoints | Spec (or DuckBrain contract) lists endpoints the code doesn't implement | DELETE endpoint in contract but not in code |

## Verification (Code-First Specific)

In addition to the standard spec verification:
1. **Gap completeness:** Does the spec note at least the obvious gaps (JSON tags, path dispatch)?
2. **Contract fidelity:** Do the OpenAPI schemas match the PRIOR specs (S02 data model), not just the current code?
3. **Forward utility:** Can the NEXT task (API implementation from this spec) use the OpenAPI YAML as a build target?

## Post-Spec: Creating Fix Tasks

The gaps identified by the spec worker should become tasks on the board. For SPEC-S06, the two gaps discovered should become:
```
## [ ] FIX — Add JSON tags to database models (from SPEC-S06 gap #1)
- Add `json:"name"` tags to all fields in internal/database/models.go
- Add `json:"repo_url"` etc. matching the snake_case contract in SPEC-S06 §3
- Verify: all JSON responses use snake_case field names

## [ ] FIX — Fix project path dispatch (from SPEC-S06 gap #2)
- handleProjectByID currently splits full URL path; must strip /api/v1/ prefix
- Fix: use strings.TrimPrefix or route-relative path extraction
- Verify: GET /api/v1/projects/alpha resolves project name "alpha" correctly
```

## Proven Results

| Project | Spec | Code Existed Since | Lines | Gaps Found | Worker Model | Commit |
|---------|------|--------------------|-------|-----------|-------------|--------|
| Scheduler | SPEC-S06 REST API | cadc05b (prior tick) | 438 | 2 (JSON tags, path dispatch) | gpt-5.6-sol @ openai-codex | 43c1442 |
