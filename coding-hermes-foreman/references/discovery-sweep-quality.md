# Discovery Sweep — Quality Rules

## Trivial item batching

When the discovery sweep finds multiple low-priority TODO stubs or comment cleanups:

- **Batch them into ONE task**, not one per file
- Group by type: "doc-stubs", "TODO-cleanup", "comment-fixes"
- A board with 5 separate `[STUB]` tasks for "TODO: implement X" is noise — the foreman will clear them all in one tick anyway
- Example: DexDat Memory sweep found 5 TODO stubs across 5 files. Created 5 separate tasks. Resolved all in one tick with 2 commits. Better: 1 task "Clean up TODO stubs across 5 files."

## Quality over quantity

- Max 5 new tasks per sweep regardless
- If more than 5 gaps found, pick the 5 most impactful
- Skip "trivial comment fix" tasks if the board already has 3+ pending — the next sweep will catch them
- Prioritize: broken CI > failing tests > missing features > stubs > cosmetic

## CI audit without `gh` CLI

Step 1.6's `gh run list` requires GitHub CLI to be authenticated. When it's not available:
- Check GitHub Actions via `curl -s https://api.github.com/repos/<org>/<repo>/actions/runs?per_page=3`
- Or skip CI audit entirely and note "gh CLI unavailable" in the output
- The foreman should NOT block on missing tooling — report the gap and continue

## Idle tick scope discipline

When the discovery sweep finds a pre-existing non-blocking code quality issue during an idle tick:

- **Note it, do NOT fix it.** Idle ticks are for discovering NEW work that moves the project forward. Pre-existing technical debt that doesn't block production (syntax quirks in generator scripts that don't affect output, minor formatting inconsistencies, comment typos) is scope creep.
- **Signal:** if fixing the issue causes cascading failures (test breakage, compilation errors), it's scope creep by definition. The current state was verified working — changing it during an idle tick introduces risk with no upside.
- **Pattern:** generator/auto-generated file has a syntax quirk that the runtime silently ignores. The committed output is hand-curated and correct. The foreman tries to "fix" the generator → generated output diverges → tests fail → multiple patches → working tree ends up reverted. Net result: 10+ tool calls burned, zero progress, idle tick still idle.
- **Correct action:** note in the tick report as "pre-existing, non-blocking" and move on. If it matters, file a task in the board for a future non-idle tick.
- **Proven:** H3 SDK TypeScript idle tick #2 (2026-07-18) — orphaned `case "object"` blocks in `generate-schemas.ts` exist in committed HEAD but don't affect operation (P5-04 verified). Attempted fix cascaded into 11 test failures and required full revert.
