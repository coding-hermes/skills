# Hermes Cron Internals

## Architecture

Hermes cron is NOT Linux cron. It's an in-process Python scheduler (`cron/scheduler.py`) running inside the Hermes gateway.

```
Every ~60s: scan jobs.json
  → is next_run_at <= now?
  → is job NOT in _running_job_ids (in-memory dict)?
  → spawn LLM session (full agent with tools, skills, context)
  → add job_id to _running_job_ids
  → wait for agent to finish (blocks)
  → deliver output (Telegram/Discord/etc)
  → remove from _running_job_ids
  → update next_run_at in jobs.json
```

## Key Differences from Linux Cron

| Linux Cron | Hermes Cron |
|-----------|-------------|
| Forks a process, forgets it | Spawns LLM session, waits for completion |
| Job takes 1ms or 1hr — doesn't matter | Job takes 30min → blocks next 2-3 ticks |
| 50 years of hardening | ~2000 lines of Python |
| All state on disk (crontabs) | Running state in-memory (`_running_job_ids`) |
| One broken job = one broken job | One broken job schema = entire scheduler crashes |
| Delivery: stdout → mail | Delivery: separate HTTP call after agent finishes |
| Concurrency: fork and forget | Concurrency: check `_running_job_ids`, skip if found |

## Why Foreman Ticks Get Missed

1. **Blocking completion:** A foreman taking 30+ minutes blocks all scheduled ticks during that window. At 15m cadence, 2-3 ticks are skipped because the job is still "running."

2. **In-memory locking:** `_running_job_ids` is a Python dict, not persistent. If the gateway process restarts (crash, update, LSP memory patch), ALL running jobs become zombies. The scheduler sees no `_running_job_ids` entries and starts new jobs, but the old sessions are still consuming tokens/cost somewhere.

3. **No backpressure:** `_running_job_ids` only tracks whether a job ID is active — not whether the agent is actually making progress. A stuck agent (infinite loop, hung tool call) holds the lock indefinitely.

4. **Schema fragility:** A single malformed entry in `jobs.json` (wrong `repeat` type, missing `expr`, invalid `kind:every`) can crash the ENTIRE scheduler. All 121 jobs stop.

## Delivery Thread-Stripping

When a cron job is created in a Telegram group thread (e.g., thread 83996 within chat -1003310984808), `deliver: "origin"` should resolve to `telegram:-1003310984808:83996`. But the scheduler resolves it to `telegram:-1003310984808` — stripping the thread ID.

Even setting `deliver: telegram:-1003310984808:83996` explicitly doesn't always work. The delivery log (`agent.log`) still shows `delivered to telegram:-1003310984808` without `:thread_id`. The content is sent but lands in the Home channel, not the thread.

**Impact on foremen:** Foreman cron output becomes invisible to Bane. The foreman completes successfully, produce real work (commits, spec writing, worker spawns), but Bane never sees the report. He only knows it ran from the cron list or agent.log.

**Workaround:** When the foreman detects its delivery went to Home channel (check agent.log), it must re-summarize its work to the human in the current turn. The cron delivery mechanism for group threads is unreliable.

## How the Scheduler Platform Fixes This

The coding-hermes scheduler (Go binary, `schedulerd`) sits in front of Hermes cron:

- **Process tracking:** Real OS PIDs, not in-memory dicts. A restarted scheduler reaps orphan processes.
- **Timeouts:** 30-minute hard timeout per foreman spawn. No infinite holds.
- **SQLite state:** All state on disk. No in-memory dicts to lose.
- **Single trigger cron:** One `no_agent` cron hits the scheduler API. The scheduler manages 33+ projects. If the trigger cron fails, only one job is affected.
- **Dashboard:** Per-project tick history, session IDs, outcomes — visible without agent.log grep.
