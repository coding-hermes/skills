# Operational CLI Batch Tasks — Foreman Execution Pattern

When a board task requires running a CLI command rather than writing code, the foreman IS the executor. These tasks follow the same shortened loop as investigation tasks (Steps 5-7 skipped), but the Step 4 deliverable is an execution plan + the actual command invocation, not an investigation report.

## Detection Signals

- Task description contains a CLI command to run (e.g., `mythos batch environment`, `npm run build`, `./bin/tool migrate`)
- Task operates on a different repo than the foreman's workdir (cross-repo execution)
- No code changes expected — the task produces artifacts (images, DB migrations, reports), not source files
- Task board has explicit env-var instructions (e.g., `MYTHOS_PROJECTS_PATH=/path`)

## Execution Pattern

```
Step 0 → Step 1 → Step 2 (skip — no code) → Step 3 (skip — no code context) 
    → Step 4 (execution plan: what command, what env vars, what repo)
    → LAUNCH: terminal(background=true, notify_on_complete=true) 
    → MONITOR: process(action='wait', timeout=60) in a loop
    → Step 8 (commit board update) → Step 10 (DuckBrain write) → Step 1.6
```

## Background Process Monitoring

For long-running CLI commands (image generation, batch processing), use the background pattern:

```bash
# Launch in background with notification
terminal(background=true, notify_on_complete=true, timeout=1200)
```

Then monitor in a loop:
```python
# Poll with 60s timeouts — the wait will return partial output on timeout
process(action='wait', session_id='<id>', timeout=60)
# Repeat until "Progress: X completed, 0 remaining" or similar completion signal
```

## Hang-After-Output Recovery

**Symptom:** The CLI prints a completion summary (e.g., "Batch complete: 19/20 jobs completed") but the process doesn't exit. `process(action='poll')` shows `status: running` indefinitely.

**Recovery:**
1. Check the log with `process(action='log')` — confirm all output has been produced
2. Verify the artifacts exist on disk (e.g., `find /path -name "*.png" -mmin -5 | wc -l`)
3. `process(action='kill')` to terminate the hung process
4. Proceed with board update — the work is done

**This is NOT a failure.** Some CLI tools (especially Node.js processes with event-loop listeners, open DB connections, or HTTP keepalives) don't exit cleanly after producing all output. Killing after confirming output is complete is the correct recovery.

**Proven:** Mythos 2026-07-14 — `mythos batch environment` printed "Batch complete: 19/20 jobs completed" then hung. All 19 PNGs confirmed on disk (5-7 MB each). Kill + proceed to board update.

## Cross-Repo Execution

When the CLI command operates in a different repo:

```bash
cd /home/kara/<other-repo> && export VAR=value && node packages/cli/dist/index.js batch <type> --yes
```

The foreman's workdir remains `<foreman-repo>` for the board update and commit. The execution happens in the other repo via `cd` prefix. No git operations happen in the execution repo — the foreman only commits board updates to its own repo.

## Env Var Handling

For `.env` files with sensitive values, export only the needed vars explicitly rather than sourcing the whole file:

```bash
export OPENROUTER_API_KEY="$(grep OPENROUTER_API_KEY .env | cut -d= -f2-)"
export MYTHOS_PROJECTS_PATH="/path/to/projects"
```

This avoids the `set -a; source .env` pitfall where unquoted space-containing values break shell parsing (see `references/hermes-env-sourcing-pitfall.md`).
