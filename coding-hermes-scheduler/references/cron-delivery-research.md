# Hermes Cron Delivery Pipeline — Research Notes

Findings from reading `~/.hermes/hermes-agent/cron/scheduler.py` (2026-07-17).

## Key Finding: Cron Runs AIAgent In-Process, Not Subprocess

**The Hermes cron system does NOT spawn `hermes chat` as a subprocess.** It runs the agent in-process inside the Python cron scheduler. This is why the coding-hermes-scheduler couldn't match cron delivery by just removing `--cli` — the fundamental execution model is different.

## Execution Path

```
run_one_job(job)                                  # cron/scheduler.py:3399
  → run_job(job)                                  # :2487
      → AIAgent(prompt)                           # imports from run_agent.py
      → runs full conversation loop in Python
      → returns (success, full_output, final_response, error)
  → save_job_output(job_id, output)               # :3477
  → _deliver_result(job, final_response)          # :3515
      → _resolve_delivery_targets(job)            # :1229
      → _send_to_platform(content, platform, ...) # from tools/send_message_tool.py
      → wraps with "Cronjob Response: {name}\n(job_id: {id})" if cron.wrap_response is true
```

## Delivery Format

```
Cronjob Response: {job_name}
(job_id: {job_id})
-------------

{agent's final response}

To stop or manage this job, send me a new message (e.g. "stop reminder {job_name}").
```

Configurable via `cron.wrap_response` in `config.yaml` (default: true).

## Delivery Target Resolution (`_resolve_delivery_targets`, :1229)

- Parses `job["deliver"]` field
- Supported formats:
  - `"origin"` — deliver to the chat that created the job
  - `"local"` — no delivery, save output only
  - `"all"` — fan out to all connected channels
  - `"platform:chat_id:thread_id"` — specific target (e.g., `telegram:-1003310984808:83996`)
  - Comma-separated: `"origin,all"` delivers to origin + every channel

## Scheduler vs Cron — Execution Model Comparison

| | Scheduler (Go) | Cron (Python) |
|---|---|---|
| Agent execution | `exec.Command("hermes", "chat", "-q", ...)` | `AIAgent(prompt)` in-process |
| Output capture | `io.TeeReader` → `bytes.Buffer` | Return value of `run_job()` |
| Delivery | `http.Post` → api.telegram.org | `_send_to_platform()` → Hermes gateway |
| Session tracking | SQLite ticks table | Hermes SessionDB |
| Skill loading | `-s` CLI flags | System prompt injection |
| Concurrent safety | `sync.RWMutex` | File lock + `_running_job_ids` set |

## Implications for Scheduler

1. **Can't call `_deliver_result()` from Go** — it's Python in-process. The scheduler's `deliver.go` uses raw Telegram HTTP API as a workaround.
2. **Hermes-native delivery path** would require calling the Hermes API server's send endpoint or MCP `send_message` tool. Not implemented — the raw Telegram API works and is simpler.
3. **`hermes chat -q -Q` output is stdout-only** — the final response is printed to stdout with session_id, but no delivery routing. Adding `--source` might route through the gateway, but `-q` (non-interactive) may bypass gateway routing regardless.
4. **`--cli` pitfall** — the `--cli` flag (global Hermes flag, not a chat subcommand flag) forces an interactive prompt_toolkit REPL, contradicting `-q` (non-interactive). Was present in scheduler spawn args from initial implementation; removing it was correct.
