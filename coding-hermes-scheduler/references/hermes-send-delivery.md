# Hermes Gateway Delivery via `hermes send`

## Problem

The scheduler (`schedulerd`) spawns `hermes chat -q -Q` as a subprocess. `hermes chat -q` is
stdout-only — it does NOT route through Hermes' gateway delivery pipeline. This meant scheduler
ticks produced output but never reached Telegram (or any other platform).

The cron system (`cron/scheduler.py`) avoids this by running the agent IN-PROCESS via `AIAgent`,
then calling `_deliver_result()` → `_send_to_platform()` to deliver output through the gateway.

## Solution: `hermes send`

`hermes send` is Hermes' CLI tool for routing text through the gateway to any configured platform.
It reuses the gateway's credentials from `~/.hermes/.env` + `~/.hermes/config.yaml` — no platform
code, no raw APIs, no bot tokens needed in the scheduler.

```
hermes send --to <target> --subject "<header>" --file <path>
```

### Target format

| Format | Example | Meaning |
|--------|---------|---------|
| Platform only | `telegram` | Home channel for that platform |
| Platform:chat | `telegram:-1003310984808` | Specific chat |
| Platform:chat:thread | `telegram:-1003310984808:83996` | Specific chat + thread |
| Discord channel | `discord:#ops` | Discord channel |
| Signal number | `signal:+15551234567` | Signal recipient |

### Exit codes

- `0` — delivered successfully
- `1` — delivery or backend error
- `2` — usage error

## Architecture in the Scheduler

```
schedulerd → hermes chat -q -Q → io.TeeReader splits stdout:
                                    ├── scanner goroutine: extracts session_id
                                    └── bytes.Buffer: accumulates full output
           → tick completes
           → deliverOutput() writes output to temp file
           → exec.Command("hermes", "send", "--to", target, "--file", tmp)
           → Hermes gateway routes to correct platform/chat/thread
```

## What NOT to do

**Do NOT use raw Telegram HTTP API.** The scheduler's initial delivery implementation
(`deliver.go` v1) hardcoded the bot token and called `api.telegram.org/bot<token>/sendMessage`
directly. This:

1. Only works for Telegram (breaks for Discord, Signal, Slack users)
2. Requires storing the bot token in the scheduler code
3. Bypasses Hermes' multi-platform delivery layer
4. Creates a different code path for every platform

`hermes send` eliminates all four problems.

## Per-Project Delivery Targets

Each project's `deliver` column stores its target from the paused cron jobs.

**Backfill process:** See `references/deliver-backfill-from-cron.md` for the workdir-matching
pattern used to extract 29 per-project Telegram thread IDs from paused cron jobs (2026-07-18).

```sql
SELECT name, deliver FROM projects WHERE deliver != '';
-- ASCE → telegram:-1003310984808:12
-- Hivemind → telegram:-1003310984808:59430
-- Speclang → telegram:-1003310984808:17441
-- etc. (30 projects mapped)
```

## Cron vs Scheduler Delivery Comparison

| | Cron | Scheduler (HERMES SEND) |
|---|---|---|
| Agent runs | `AIAgent(prompt)` in Python | `hermes chat -q -Q` subprocess |
| Output capture | `run_job()` captures response | `io.TeeReader` → `bytes.Buffer` |
| Delivery | `_deliver_result()` → `_send_to_platform()` | `hermes send --to <target> --file <tmp>` |
| Header | `Cronjob Response: <name>` | `🤖 Scheduler Tick: <project> [<tick-id>]` |
| Platforms | All (gateway) | All (gateway) |
