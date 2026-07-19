# GDScript Worker Provider Cascade

Escalation Doctrine (Godot 4.3, 386 `.gd` files) provider status as of 2026-07-14.

## Provider Status

| Provider | Status | Detail |
|----------|--------|--------|
| grok-4.5 @ xai-oauth | ❌ EXHAUSTED | HTTP 403: `personal-team-blocked:spending-limit` (2026-07-14) |
| GLM-5.2 @ zai-glm | ❌ SILENT | Variant C — 190s, zero stdout, zero files written (2026-07-14) |
| MiniMax-M3 @ minimax | ✅ WORKING | Completes tasks. Multi-file: enters review-diff loop ~15 min after core work done → kill+verify+commit. Single-file: commits directly. |

## Cascade

For GDScript/Godot tasks, skip the first two and go directly to **MiniMax-M3 @ minimax**. Do not burn time testing grok-4.5 or GLM-5.2 — both are known-broken for this project.

## Worker Pattern

MiniMax-M3 @ minimax for GDScript:
- Writes code to disk correctly
- **Single-file tasks**: commits directly, no review-diff loop
- **Multi-file tasks (3+ files)**: completes all code correctly BUT enters review-diff loop ~15 min after core work is done. Detection: same diffs across 5+ consecutive API calls, mtimes stable on modified files, API calls still being made with 99% cache. Recovery: kill the worker, verify `go build` equivalent (Godot headless → 0 SCRIPT ERRORs), run GitReins guard, commit directly. Do NOT respawn — work is already correct.
- Ad-hoc verification pattern for Godot: `timeout 35 /tmp/godot/Godot_v4.3-stable_linux.x86_64 --headless --path . 2>&1 | grep -c "SCRIPT ERROR"` → must return 0
- ~18-20s per API call at 99% cache. Godot test runs take 1-35s. Budget ~30 API calls for a complex 4-file task.

## Re-check Cadence

Re-test grok-4.5 @ xai-oauth every ~7 days. Billing may be topped up. Test with a 1-word prompt: `hermes chat -q "Say 'working' and nothing else." -m 'grok-4.5' --provider 'xai-oauth' --cli -Q`.

## Proven

- 2026-07-14 TASK_POLISH_002: MiniMax-M3 completed 4-file AI pipeline restoration (+87/-21: class_name restore, FactionAI.new(), process_turn wiring, ResearchManager/CombatManager wiring). Killed at 24 min (review-diff loop after core work done). Godot 0 SCRIPT ERRORs, GitReins guard PASS. Commit `1dcf5c3`.
- 2026-07-14 TASK_POLISH_001: MiniMax-M3 completed DiplomacyScreen wiring (+72/-8, 1 file, 4 stubs fixed, 0 SCRIPT ERRORs). grok-4.5 returned 403, GLM-5.2 returned nothing.
