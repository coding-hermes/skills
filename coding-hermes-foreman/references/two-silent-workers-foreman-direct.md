# Two-Silent-Worker → Foreman-Direct Pattern

When both the primary and first-fallback workers fail on the same task,
the foreman implements directly rather than burning through remaining buckets.

## Detection

Worker 1 fails silently or with review-diff. Worker 2 also fails. Two variants:

### Variant A — Both Silent (zero files from both)

Both workers produce no files on disk:
1. **Primary** (e.g., GLM-5.2 @ zai-glm): silent for 120+ seconds, no files.
2. **Fallback** (e.g., MiniMax-M3 @ minimax): same — silent, no files.

### Variant B — Silent + Partial (files from second worker)

First worker silent. Second worker writes PARTIAL work before getting stuck:
1. **Primary** (e.g., GLM-5.2): silent, zero files → kill.
2. **Fallback** (e.g., MiniMax-M3): writes some files to disk (struct changes,
   constructor updates, partial method bodies), then enters review-diff loop.
3. **File check**: `git diff --stat` shows modified files, but key pieces are
   missing (helper functions, secondary-file changes).

## Decision Flow

```
Worker 1 failed?
    ↓
Worker 2 spawned
    ↓
After 120-180s: check filesystem
    ├── No files on disk (Variant A) → KILL worker 2
    │   └── Foreman: implement everything directly
    │       → Skip worker 3 — if 2 different models failed, a 3rd likely will too
    │
    └── Files on disk + mtimes frozen + review-diff showing (Variant B) → KILL worker 2
        ├── `go build ./... && go vet ./...` on partial work
        ├── If compiles: identify what's missing from ACs
        ├── If missing pieces are mechanical (helpers, sync methods, boilerplate):
        │   → Foreman writes remaining pieces directly
        │   → One commit for worker's work + foreman's completion
        └── If build fails or missing pieces require design:
            → `git checkout` partial work, respawn or create subtask
```

## Decision: Stop Trying Buckets

After TWO consecutive failures from different providers:
- Do NOT try fallback 2 — if two different models failed, a third likely will too
- Do NOT respawn with the same model — confirmed failure pattern
- **Switch to foreman direct implementation** if:
  - The foreman has already loaded all necessary context (Steps 2-4)
  - The spec is structured enough (prose with clear struct/interface descriptions works)
  - For Variant B: the worker's partial work compiles and covers the structural changes

## Why This Works

The foreman has already:
1. Read the spec (Step 1)
2. Analyzed impact (Step 2 — Hilo)
3. Loaded DuckBrain context (Step 3)
4. Read the existing code to compile the worker prompt (Step 4)

The foreman has 80% of the context — and in Variant B, the worker proved it
understood the task by writing correct structural code. The remaining pieces
are mechanical completions of patterns the worker already established.

## Cost Comparison

| Path | Time | Tokens |
|------|------|--------|
| Worker succeeds on attempt 1 | 3-10 min | Prepaid bucket |
| Worker 1 fails → Worker 2 partial → foreman finish | 5-8 min | PAYG (foreman) |
| Worker fails → worker fails → worker 3 fails → foreman | 10-15 min | PAYG + wasted credits |

## Variant A — Proven

Helix REVIEW-QUEUE-01 (2026-07-14):
- GLM-5.2 @ zai-glm: 167s silent, zero files
- MiniMax-M3 @ minimax: 60s silent, zero files
- Foreman: implemented `pkg/review/queue.go` (573 lines), `queue_test.go` (320 lines),
  `cmd/helix/review.go` (+125 lines) in ~15 tool calls
- Build+vet+test green, guard PASS

Imhotep Normalization (2026-07-14):
- GLM-5.2 @ zai-glm: 180s silent, zero files (via `hermes -z`)
- kimi-k2.7 @ kimi-for-coding: 45s silent, zero files (via `hermes -z`)
- Both spawned with `hermes -z "$(cat file)"` — `hermes chat -q` failed first
  with shell escaping errors on the complex multi-section prompt
- Foreman: implemented normalization engine directly from axiom-level S05 spec:
  `pkg/models/taxonomy.go` (64 lines), `internal/normalizer/normalizer.go`
  (497 lines), `internal/normalizer/normalizer_test.go` (445 lines, 32+ tests)
- Also added `github.com/google/uuid` dependency via `go mod edit -require`
  (security scanner blocked `go get`)
- Build+vet+test green, guard PASS on first commit `4891b2d`
- Key insight: `hermes -z` is NOT a reliable fallback when `hermes chat -q`
  fails — both approaches can fail on complex prompts

## Variant B — Proven

Scheduler NS-005 (2026-07-14):
- GLM-5.2 @ zai-glm: 263s silent, zero files → killed
- MiniMax-M3 @ minimax: wrote `main.go` flag + `loop.go` struct/constructor/evaluate-branch
  (partial — missing `evalContext()` helper and `duckbrain.go` namespace sync)
  → review-diff loop at 314s → killed
- Foreman: wrote `evalContext()` (35 lines, DB queries following Loop patterns) +
  duckbrain.go namespace sync (70 lines, following `syncProjectStatuses` template)
- Build+vet+test green, guard PASS, committed `a77bf39` (3 files, +195/-31)

## When Variant B Applies vs. When It Doesn't

✅ **Foreman finishes when:**
- Worker wrote the structural code (struct fields, constructor, branching logic)
- Remaining pieces follow established patterns in the same file/package
- Missing pieces are mechanical: helper functions, sync methods, boilerplate
- Build already passes on the partial work

❌ **Do NOT finish when:**
- Worker's partial work doesn't compile
- Missing pieces require design decisions (new interfaces, data flow choices)
- You don't understand WHY the worker wrote what it wrote
- The task scope is unclear (the worker may have been confused too)
