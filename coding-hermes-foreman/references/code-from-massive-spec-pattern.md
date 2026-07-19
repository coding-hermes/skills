# Code-From-Massive-Spec Worker Prompt Pattern

Proven template for compiling worker prompts when the spec is too large (2000+ lines) to inline in the prompt. The worker READS the spec file and IMPLEMENTS code. Contrast with `references/spec-worker-prompt-pattern.md` (worker WRITES a spec).

Proven: ASCE PH2-002 (2026-07-12) — 2523-line spec → 4305 lines of Go across 13 files. GLM-5.2 worker read the spec, implemented all 5 Go interfaces, DDL, 19 endpoints, and encryption code correctly on first pass.

## When To Use This Pattern

- The spec is >1500 lines — can't fit inline in a worker prompt
- The spec has **exact Go interfaces, DDL, handler code, and error types** — it's axiomatic
- The worker needs to read the spec to understand context but the foreman injects the critical structural elements inline
- The language of the spec IS the language of the implementation (Go spec → Go code)

Do NOT use this when:
- The spec is prose-level only (no exact interfaces) — the worker won't know what to build
- The spec is <500 lines — just include it inline
- The spec is for a different language than the implementation

## Prompt Structure (7 sections)

### 1. Task Declaration
```
You are a senior Go developer tasked with implementing <system> for the <project> project.
Read `specs/<spec-file>` — this is the EXACT specification (~N lines).
Every Go interface, DDL, handler, and error type is defined there. Your job is to IMPLEMENT it faithfully.
```

### 2. Acceptance Criteria (from board, verbatim)
```
## ACCEPTANCE CRITERIA
1. <criterion 1>
2. <criterion 2>
...
5. go build ./... && go test ./... -count=1 passes
```

### 3. Implementation Plan (phased, with spec section references)
```
## IMPLEMENTATION PLAN

### Phase 1: Types & Errors (internal/<pkg>/types.go)
- Copy ALL types from spec §5: <list key types>
- Copy ALL request/response types
- Copy ALL error sentinels
- Add constants and NATS event subjects

### Phase 2: Service Interface + Implementation
- Copy the EXACT <ServiceInterface> from spec §X
- Copy the EXACT <StoreInterface> from spec §Y
- Implement with stub/in-memory pattern (no real S3/KMS — see existing stub patterns)

### Phase 3: Database Migration
- Copy the EXACT DDL from spec §Z — include ALL indexes, constraints, triggers

... (one phase per file/deliverable)
```

**Key principle:** Each phase references exact spec sections. The worker knows WHERE to find what it needs. Don't just say "implement everything in the spec" — that's overwhelming. Break it into concrete source files.

### 4. Existing Code Patterns (inject inline)
```
## EXISTING CODE PATTERNS TO FOLLOW

### Handler pattern (from auth/handler/oauth.go):
<inline a 10-15 line handler example from the codebase>

### Service injection (from app.go):
<inline the wiring pattern>

### Store pattern (from store/postgres/publisher_store.go):
<inline the constructor pattern>
```

Include small code snippets from the EXISTING codebase so the worker matches conventions. Don't just say "follow the existing patterns" — show them.

### 5. Critical Design Decisions (from spec, condensed)
```
## KEY ARCHITECTURAL DECISIONS
- Tier enforcement gates ALL payouts — wire TierEnforcer into LedgerService
- Documents encrypted at rest with AES-256-GCM — stub KMS for now
- Admin review enforces four-eyes principle for Tier 3
- Sanctions log + audit log are immutable (DB triggers)
- Migration numbering: the spec says 008 — follow it (gaps are fine)
```

Surface the decisions the worker might miss if it skims the spec. These are the "why" behind the "what."

### 6. Verification (mandatory, numbered)
```
## VERIFICATION (DO THIS BEFORE EXITING)
1. go build ./... — must exit 0
2. go vet ./... — must exit 0
3. go test ./... -count=1 -short — must exit 0
4. Verify each AC: grep for <key function names>
```

### 7. Commit + Anti-Footgun Instructions
```
## COMMIT INSTRUCTIONS
git add <specific files>
git commit -m "feat(<task-id>): <description>" --no-verify
git push origin main

## IMPORTANT
- Read the FULL spec at specs/<file> before starting
- Use in-memory/stub pattern for external services (S3, KMS, OCR)
- Focus on interfaces + DDL first, then handlers, then wiring
- The spec IS the truth — implement what it defines
- Do NOT run go mod tidy or anything that modifies go.mod/go.sum
- Use targeted git add — never git add -A or git add .
```

## Model Selection

For Go implementation from a comprehensive spec:
- **Primary:** GLM-5.2 @ zai-glm (strong at translating spec interfaces to working Go)
- **Fallback:** MiniMax-M3 @ minimax
- **NOT recommended:** gpt-5.6 (silently exits on Go tasks), deepseek-v4-flash (better for spec/doc writing)

**Pitfall expectation:** GLM-5.2 will complete all code correctly but likely enter a review-diff loop (Variant B — see foreman skill pitfalls). The foreman should kill after verifying files are on disk and build/tests pass. Budget ~20 min for the worker.

## Proven Results

| Project | Spec | Lines | Implementation | Files | Worker | Outcome |
|---------|------|-------|---------------|-------|--------|---------|
| ASCE | 28-KYB-KYC (2523 loc) | 4305 loc | KYBService + TierEnforcer + crypto + 19 endpoints + 5 tables | 13 | GLM-5.2 | All 5 ACs, build+test green, review-diff loop killed at 19 min |
