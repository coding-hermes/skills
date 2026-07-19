# MCP `task_complete` Timeout-But-Success Pattern

## Problem

When resolving stale GitReins `in_progress` tasks via `mcp_gitreins_task_complete`, the MCP call
can time out at 300s on large codebases (the evaluator re-runs inside `task_complete`). The agent
sees a `TimeoutError` and assumes the operation failed — but the evaluator may have already written
the `completed_at` timestamp to `.gitreins/tasks.yaml` before the transport timed out.

## Detection

After a `TimeoutError` from `mcp_gitreins_task_complete`:

```bash
grep -A2 "id: <task-id>" .gitreins/tasks.yaml | grep completed_at
```

If `completed_at` exists, the operation SUCCEEDED despite the timeout. The task is now `complete`.

If `completed_at` does NOT exist, the operation genuinely failed — fall back to CLI or manual patch.

## Recovery

### Case A: MCP succeeded (completed_at present)
- The task was correctly marked `complete` — no further action needed
- Do NOT add another `completed_at` via `patch()` — you'll get a duplicate-key YAML error

### Case B: MCP failed (no completed_at)
- Fall back to CLI: `timeout 180 gitreins task complete <id>` (requires DEEPSEEK_API_KEY)
- If CLI also times out: patch `tasks.yaml` directly to set `status: complete` + add `completed_at` timestamp
- Commit the patched `tasks.yaml`

## Duplicate-Key Collision (MCP + Manual Patch)

When you call `mcp_gitreins_task_complete` AND also `patch()` the file to add `completed_at`,
you can end up with TWO `completed_at` lines. This happens because:

1. MCP `task_complete` writes `completed_at` to the file before timing out
2. Agent reads the file (sees `in_progress` state from before the MCP write)
3. Agent patches to add `completed_at` — but the file already has one from step 1
4. Result: `completed_at: '...'` appears twice, YAML LSP complains `Map keys must be unique`

**Fix:** After any MCP timeout, re-read the file FIRST before patching. If `completed_at` is
already present, do nothing — the task is resolved.

**Proven:** H4F 2026-07-16 — `langfuse-per-friend` task. MCP `task_complete` timed out at 300s
but wrote `completed_at: '2026-07-16T12:24:42.496501+00:00'`. Agent's subsequent `patch()` added
a second `completed_at: '2026-07-16T10:48:00.000000+00:00'`. Fixed by removing the duplicate.
