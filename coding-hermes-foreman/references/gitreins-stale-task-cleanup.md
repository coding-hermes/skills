# GitReins Stale-Task Cleanup

When a worker commits directly (worker-direct-commit path) without running `gitreins task complete`, or when an earlier tick skipped the GitReins judge due to timeout, `.gitreins/tasks.yaml` can accumulate tasks still marked `in_progress` whose code is already committed and verified.

## Detection

```bash
grep -c "status: in_progress" .gitreins/tasks.yaml
```

If > 0, identify each stale task by reading the task ID from the line just above the `in_progress` status.

## Cleanup

For each stale task, two paths:

### Path A — MCP `task_complete` (preferred for already-verified tasks)

The MCP tool bypasses the evaluator re-run, which saves time and avoids false negatives from admin-only diffs:

```
mcp_gitreins_task_complete(id="<task-id>", workdir="/home/kara/<project>")
```

Use this when the task criteria are already verified by build + tests + guard and you just need the status updated. The MCP path returns `passed: true, tier1_passed: true, tier2_verdict: null` — the Tier 2 evaluator doesn't run, so there's no risk of false negatives from examining the wrong diff.

### Path B — CLI `gitreins task complete` (audit trail needed)

When you need a full Tier 2 verdict with per-criterion evidence:

```bash
cd /home/kara/<project> && timeout 120 gitreins task complete <task-id>
```

Runs the evaluator which examines the **current commit's diff**. **CAUTION:** If the current commit only contains administrative changes (board updates, config syncs), all criteria may incorrectly FAIL because "no relevant code was changed." See the three-branch decision tree in `coding-hermes-cron:references/post-hoc-evaluator-false-negative.md`.

## MCP Timeout Behavior

MCP `task_complete` can time out at **300s** on large codebases even when the evaluator succeeds. The evaluator writes `completed_at` to `.gitreins/tasks.yaml` BEFORE the transport timeout hits — so the operation succeeds despite the `TimeoutError`.

**After any MCP timeout on `task_complete`:**
```bash
# Check if it actually succeeded
grep -A2 "id: <task-id>" .gitreins/tasks.yaml | grep completed_at
```

If `completed_at` is present → success, nothing to do.
If `completed_at` is NOT present → genuine failure; fall back to CLI or manual patch.

**⚠️ Duplicate-key collision:** After a timeout, the MCP may have already written `completed_at`. If you then `patch()` to add another one, you'll get two `completed_at` lines and a YAML `Map keys must be unique` error. **Always re-read the file** after a timeout before patching. See `references/gitreins-mcp-task-complete-partial-success.md`.

## Double-Timeout Fallback — Both MCP and CLI Hang

When the LLM evaluator is unreachable (missing API key, provider down, network partition),
both Path A (MCP `task_complete`) and Path B (CLI `gitreins task complete`) will hang
until their respective timeouts fire — 300s for MCP, 120s for `timeout`-wrapped CLI.
This burns 7+ minutes on a single stale task.

**Fast recovery — restore state file from git:**
```bash
git checkout -- .gitreins/tasks.yaml .gitreins/config.yaml 2>/dev/null
rm -f .gitreins/config.yaml.bak .gitreins/tasks.yaml.bak 2>/dev/null
```

This is the same pattern used in Step 0 self-heal. It discards the stale `in_progress`
state without trying to complete the task through the evaluator. The task's work is
already committed — the `.gitreins/tasks.yaml` file is local MCP-managed state, not
project source. Clearing it is safe.

**When to use this fallback vs retrying:**
- Task work is committed + verified → use `git checkout` restore. Don't retry.
- Task work is NOT yet committed → stash the task state, commit the work separately, then restore.
- Evaluator is intermittent (sometimes works) → try CLI once with 60s timeout. If it hangs again, restore.

**Proven:** Kobayashi-Maru 2026-07-18 — `todo-episode-stream-501` was `in_progress` but work was
committed at `4b64eff` + marked `[x]` on the board. MCP `task_complete` timed out at 300s,
CLI `timeout 120 gitreins task complete` also timed out (LLM evaluator unreachable). Foreman
restored state with `git checkout -- .gitreins/tasks.yaml` — tick completed without evaluator.

## Companion Reference

For the broader case of GitReins tasks with no corresponding board entry (including external validation tasks), see `references/gitreins-task-board-alignment.md`.

## When to Use Which

| Scenario | Path | Reason |
|----------|------|--------|
| Task criteria verified by build+test+guard | A (MCP) | No evaluator needed — just update status |
| Task needs official PASS/FAIL audit trail | B (CLI) | Need file:line evidence per criterion |
| Current commit is admin-only (board, config) | A (MCP) | CLI evaluator will false-negative on admin diffs |
| No prior PASS exists + feature code is in repo | A (MCP) | CLI evaluator examines wrong diff; force re-judge against feature commit instead |

## Proven

- **H4F 2026-07-15:** `langfuse-per-friend` was `in_progress` for 2+ days despite code committed at `0ec935a` with all tests passing. MCP `task_complete` resolved it instantly — returned `passed: true`, status changed to `complete`.
- **H4F 2026-07-16:** Same task re-emerged as `in_progress` (stale from prior tick). MCP `task_complete` timed out at 300s but succeeded — `completed_at` was written before the timeout. Agent's follow-up `patch()` created a duplicate `completed_at` line (YAML LSP error). Fixed by removing the duplicate. See `references/gitreins-mcp-task-complete-partial-success.md`.
