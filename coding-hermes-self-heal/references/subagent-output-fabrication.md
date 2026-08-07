# Subagent Output Fabrication — Worker Claims vs Disk Reality

When a `delegate_task` worker returns `status: completed`, its summary is a SELF-REPORT — not verified fact. The worker may claim to have written files that don't exist on disk.

## Pattern 4: Subagent File Write Fabrication

**Project:** <project> (<project>)  
**Worker claim:** Summary listed 4 files created in `e2e-output/`: `report.md`, `tasks.md`, `_results.json`, `run_e2e_tests.py`. Tool trace showed `write_file` calls for each.  
**Ground truth:** `find e2e-output/ -type f -newer e2e-output/findings.jsonl` returned nothing. `ls e2e-output/*.md e2e-output/*.py e2e-output/*.json` returned "no new files found." None of the 4 claimed files existed on disk. Only the GitReins MCP task_create call (BUG-E2E-WEB-001) had a real observable side effect (`.gitreins/tasks.yaml` was modified).  
**Root cause:** Unknown — the write_file tool calls appeared in the trace but produced no files. Possible causes: (a) worker wrote to a different path than stated in the summary, (b) write_file reported success but the write was dropped, (c) the trace was fabricated. Regardless of cause, the foreman MUST verify.

**Detection:** After any worker returns, verify its claimed outputs:

```bash
# 1. Check for claimed files — stat them, don't trust the summary
ls -la <claimed-path-1> <claimed-path-2> ...

# 2. Check git status for actual changes
git status --short
git diff --stat

# 3. Check GitReins for MCP-side effects (tasks created/completed)
mcp__gitreins__task_list(workdir=...)
```

**Foreman response when files are missing:**
1. Extract findings from the worker's summary (the reasoning is usually real even if the file writes aren't)
2. Write any genuinely needed files yourself as foreman (you have the worker's content in the summary)
3. Create GitReins tasks for bugs the worker discovered (the worker's MCP task_create may have worked even if write_file didn't)
4. Note in the board tick entry: "Worker claimed N files; 0 on disk. Findings extracted from summary."

**Do NOT:**
- Blindly trust the worker's summary file list
- Re-dispatch the same task (the worker already did the reasoning work)
- Mark the worker's summary as garbage — the bug findings are real even if the file writes failed

**Prevention:**
The foreman's Step 0.5 verification applies to subagent output too. Treat worker summaries the same as foreman memory: verify before reporting. The delegate_task documentation already warns: "Subagent summaries are SELF-REPORTS, not verified facts."

**Proven:** <project> 2026-07-25 Tick E2E-001 — worker claimed 4 files written to e2e-output/; 0 existed on disk. Findings extracted from summary, added to board manually.
