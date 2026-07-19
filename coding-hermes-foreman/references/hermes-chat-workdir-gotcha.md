# `hermes chat -q` Workdir Gotcha — Spawned Agent Uses Own Config, Not Shell CWD

## Problem

When spawning a worker via `hermes chat -q`, the running Hermes agent (spawned by the chat command) uses its **own configured working directory**, NOT the terminal shell's `$PWD`. This means the `cd /home/kara/<project> && hermes chat ...` pattern from the foreman skill's Step 5 is **insufficient** — the shell CWD is correct for the terminal, but the spawned agent reads its own workdir from Hermes session config.

## Manifestation

The spawned agent reports that target files don't exist, even though they clearly exist on disk:

```
The current working directory /home/kara/helix is the [different project]...
No internal/api/handlers/websocket/ directory exists.
```

The foreman confirms the files exist:
```
$ pwd && ls internal/api/handlers/websocket/handler.go
/home/kara/helios-work
handler.go  (file exists)
```

But the spawned agent (running from its own workdir `/home/kara/helix`) can't see them.

**Another manifestation — `--workdir` flag rejected:** `hermes chat` does NOT accept a `--workdir` flag. Passing `--workdir /path/to/project` produces `error: unrecognized arguments: --workdir`. The correct approach is `cd /path/to/project` in the wrapper script, combined with absolute paths in the prompt. The spawned agent's session config determines its effective workdir; `cd` in the shell wrapper affects the parent shell but the spawned agent may still use its configured workdir.

## Root Cause

`hermes chat` creates a **new Hermes session** that starts in the workdir defined by its own session configuration. This is NOT the parent shell's CWD, even though `cd` was run in the parent shell before the `hermes chat` command. The `terminal(workdir=...)` parameter sets the terminal shell's CWD for the foreman's own reading/writing, but does NOT propagate to the `hermes chat` subprocess as a workdir override.

The spawned agent's session config may point to a different project entirely (e.g., `/home/kara/helix`) because that was the last session's workdir or a configured default.

## Fix

**Use absolute paths in the worker prompt.** The spawned agent can read files by absolute path regardless of its own workdir:

```bash
# DO NOT rely on relative paths in the prompt
hermes chat -q 'Modify /home/kara/helios-work/internal/api/handlers/websocket/handler.go ...'

# The prompt should explicitly state:
# "Your working directory is /home/kara/helios-work.
#  All file paths are relative to /home/kara/helios-work.
#  Use absolute paths when reading files."
```

**Passing the prompt from a file — `--prompt-file` does not exist.** The `-q` flag accepts a string, not a file path. To pass a prompt from a file, use command substitution:

```bash
# WRONG — --prompt-file flag does not exist
hermes chat -q --prompt-file worker_prompt.txt

# RIGHT — inline via command substitution
hermes chat -q "$(cat worker_prompt.txt)" --provider minimax --model minimax-m3
```

Large prompts (>100KB) may hit shell argument length limits; in practice C++ implementation prompts at ~4KB work fine. Proven: RethinkDB CDC-07 2026-07-19 — `--prompt-file` attempt failed with `error: argument -q/--query: expected one argument`; command substitution succeeded.

**Also set `terminal(workdir=...)`** for the foreman's own commands (git, hilo, go build) so they run in the correct project — this ensures the foreman's verification commands (`go build`, `git status`) see the right files even though the spawned agent doesn't.

## When It Matters

This issue affects ALL `hermes chat -q` worker spawns, regardless of model or provider. It's not specific to any worker model (GLM, MiniMax, Kimi, Grok). Every spawned agent that needs to read or modify project files MUST have absolute paths in its prompt.

The issue is invisible when the spawned agent's configured workdir happens to match the foreman's target project — which is often the case when the foreman is a dedicated cron for that project. It surfaces specifically when:
- The foreman manages multiple projects from one session
- The foreman's configured workdir differs from the target project
- A cron job's session config was set up for a different project first

## Proven

- **Helios 2026-07-16** — MiniMax-M3 @ minimax spawned with `cd /home/kara/helios-work && hermes chat ...` reported cwd as `/home/kara/helix`. All 3 worker attempts (glm-5.2 429, kimi-k2.7 silent exit, MiniMax-M3 workdir mismatch) failed to touch `internal/api/handlers/websocket/handler.go`. Foreman applied fixes directly via `patch` tool. 49 insertions, 23 deletions, 8/8 GitReins judge PASS.
