# `~/.hermes/.env` Source Failure — Unquoted Value With Spaces

## The Problem

The Hermes `.env` file (`/home/kara/.hermes/.env`) contains a line like:

```
API_SERVER_MODEL_NAME=Hermes Agent
```

The value has a space, is unquoted, and lives alongside other shell-style
`KEY=value` lines. When the foreman wraps a worker spawn with the canonical
pattern:

```bash
set -a
source /home/kara/.hermes/.env
set +a
exec hermes chat -q "..." -m MiniMax-M3 --provider minimax --ignore-rules --cli -Q
```

bash tokenizes the unquoted `Hermes Agent` value, then tries to execute
`Agent` as a command. The wrapper exits with:

```
/home/kara/.hermes/.env: line 39: Agent: command not found
```

The `hermes chat` process never starts. The terminal tool reports exit 126.
The log contains **only** the "Agent: command not found" line — no
`⚠ Invalid model.max_tokens` warning (which is what successful spawns print),
no session_id, no output.

## Detection

| Signal | Meaning |
|--------|---------|
| Worker exit in <2 seconds | Source failed before `hermes chat` ran |
| Log shows ONLY `Agent: command not found` (one line) | bash error from `.env` parsing |
| No `session_id:` line in log | `hermes chat` never reached the LLM call |
| `terminal(background=true, notify_on_complete=true)` reports exit 126 | bash interpreter exited on the bad line |

## The Fix

**Path A — Wrapper script that parses the .env safely (proven pattern):**

Write a wrapper that reads the `.env` line by line and exports only valid
identifiers. This skips blank lines, comments, and any line where bash's
default tokenization would misbehave:

```bash
#!/bin/bash
# /tmp/run-<project>-worker.sh
cd /home/kara/<project>
while IFS= read -r line; do
  [[ "$line" =~ ^#.*$ ]] && continue
  [[ -z "$line" ]] && continue
  key="${line%%=*}"
  val="${line#*=}"
  if [[ "$key" =~ ^[A-Z_][A-Z0-9_]*$ ]]; then
    export "$key=$val"
  fi
done < /home/kara/.hermes/.env
exec hermes chat -q "$(cat /tmp/<project>-task.txt)" \
  -m <model> --provider <bucket> --ignore-rules --cli -Q \
  > /tmp/<project>-worker.log 2>&1
```

Then run via `terminal(background=true, notify_on_complete=true)`.

**Why this works:** `IFS= read -r` reads the whole line as-is (no word
splitting). The regex `^[A-Z_][A-Z0-9_]*$` ensures the key is a valid shell
identifier. Multi-word values are passed through verbatim — `export "KEY=val
with spaces"` correctly sets the environment variable.

**Path B — Strip the offending line before sourcing:**

```bash
set -a
source <(grep -v '^API_SERVER_MODEL_NAME=' ~/.hermes/.env)
set +a
hermes chat -q "..." ...
```

Brittle — breaks if more unquoted-with-space lines exist. Use Path A.

## Common Mistakes

- **`set -a; source ~/.hermes/.env` in a subshell or one-liner with
  `&&`/`;`** — same problem, even faster to fail (subshell can't recover).
- **Wrapping `source` in `bash -c "..."`** — the `.env` parser runs in the
  subshell only, then the subshell exits. Outer shell doesn't get the env.
  Use `.env` sourcing in the same shell that calls `hermes chat`.
- **Sourcing `~/.bashrc` or `~/.profile`** — these don't include
  `MINIMAX_API_KEY` etc. The .env file is the only source for those.

## Proven

**SpecLang 2026-07-13 — FIX-VALIDATE-002 worker spawn:**

- First 3 worker attempts failed silently in <2s with `Agent: command not
  found` (lines 39 of `/home/kara/.hermes/.env`).
- Each failed wrapper was followed by a retried wrapper using the same
  `set -a; source .env` pattern — every retry hit the same error.
- Diagnostic: `cat ~/.hermes/.env | sed -n '39p'` showed
  `API_SERVER_MODEL_NAME=Hermes Agent` — the space-containing value that
  bash tokenizes.
- Fix: wrote `/tmp/run-speclang-worker.sh` with the line-by-line parser
  pattern above, `chmod +x`, then spawned via `terminal(background=true,
  notify_on_complete=true)`.
- Worker (MiniMax-M3 @ minimax) started cleanly, produced session_id,
  wrote the parser fix to disk, exited after 145s.

## Related

- `references/hermes-chat-multiline-pitfall.md` — `-q` flag single-line
  argument constraint
- `references/cron-worker-spawn-blocked.md` — cron security timeout
  blocking spawns