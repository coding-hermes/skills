# MiniMax-M3 / gpt-5.6-terra / kimi-k3 Review-Diff Loop

MiniMax-M3, gpt-5.6-terra, and kimi-k3 all exhibit a review-diff loop behavior on multi-file Go, Python, JS/HTML/CSS, and TypeScript/Express tasks. The worker produces correct code within ~3-5 minutes then enters a loop of showing diffs and re-reviewing without committing. The code is almost always correct — the loop is about polish, not correctness.

## Detection
- Output shows repeated `review diff` blocks with small refinements
- Worker uptime exceeds 150s without committing
- Files exist on disk and `tsc` / `go build` passes
- git status shows unstaged or staged changes but no commit

## Recovery (same for all models)
1. Check if files exist and compile: `pnpm build` / `go build ./... && go vet ./...`
2. If green, kill the worker — the code is done
3. Restore any unrelated drift (`pnpm-lock.yaml`, `.vfs/graph/edges.jsonl`)
4. Stage intended files, run `gitreins guard`
5. If guard passes, commit directly
6. Do NOT respawn the same model — the loop is model-specific

## gpt-5.6-terra specifics
- On openai-codex provider: produces code faster (~3 min) than MiniMax-M3
- Review-diff loop is slightly shorter but just as persistent
- Code quality is consistently excellent — build-clean on first attempt
- Same kill-at-review-diff strategy works identically

## Proven instances
| Date | Project | Model | Task | Result |
|------|---------|-------|------|--------|
| 2026-07-12 | Consensus | MiniMax-M3 | CSS+HTML (1,596+144 lines) | 6min, killed, code correct |
| 2026-07-12 | Chimera v2 | MiniMax-M3 | 8 Python files | 9min, staged correctly |
| 2026-07-12 | Bunker WI-069 | MiniMax-M3 | 7 Go files (+925 lines) | 6min, unstaged |
| 2026-07-15 | H4F | MiniMax-M3 | Single-file Python (+95 lines) | 150s, killed, guard clean |
| 2026-07-16 | Hermes DAGger SPEC-003 | kimi-k3 | Multi-format selector (Go) | 487s, completed eventually |
| 2026-07-16 | Hermes DAGger SPEC-005 | MiniMax-M3 | bubblewrap sandbox (Go) | ~9min, 21 tests, completed |
| 2026-07-16 | Hermes DAGger SPEC-006 | MiniMax-M3 | DAG generation (Go) | ~5min, 13 tests, completed |
| 2026-07-16 | Hermes DAGger SPEC-007 | kimi-k3 | Bridge + MCP (Go, 4 files, 1,166 lines) | ~4min productive, 6+min review-diff, killed, guard clean, committed |
| 2026-07-18 | H3 umbrella P6-01 | MiniMax-M3 | HTML landing page (756 lines, dark theme, SVG diagram, JS tabs) | ~360s, killed after file verified correct, all 7 ACs met |
| 2026-07-18 | HEADING API-003 | gpt-5.6-terra | TypeScript/Express endpoint (+94 lines) | ~3min, review-diff, killed, build+guard clean |
| 2026-07-18 | HEADING API-004 | gpt-5.6-terra | TypeScript/Express + analytics router (+232 lines, 3 files) | ~3min, review-diff, killed, staged but uncommitted, build+guard clean |
| 2026-07-18 | HEADING API-005 | MiniMax-M3 | TypeScript/Express travel restrictions (+260 lines, 3 files) | ~5min, review-diff, killed, unstaged, build+guard clean |
