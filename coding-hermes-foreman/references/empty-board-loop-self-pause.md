# Empty Board Loop & Self-Pause

> **Superseded by foreman skill v2.6.0.** The self-pause mechanism is now inlined in the main `SKILL.md` under "## Self-Pause — Empty Board Loop Prevention." This reference file is kept for historical context.

## The Problem

When all tasks on the board are `[x]` (project complete), the foreman's loop still fires every tick:

```
Step 0 Self-Heal → Step 1 Board Empty → Step 1.5 Discovery Sweep → Step 1.6 Signals → → NEXT
```

The discovery sweep is **designed to find work** — it actively hunts for TODOs, stale counts, dep updates, CI gaps. By design, it will ALWAYS find *something* (a stale package count in README, a minor dep bump, a TODO comment in test files). This creates a perpetual cycle:

1. Tick fires → discovery sweep finds stale doc count → commits fix → tick ends
2. Next tick fires → discovery sweep finds minor dep update → commits fix → tick ends
3. Next tick fires → discovery sweep finds a TODO in a test → creates task → tick ends
4. Next tick fires → works task → discovery sweep finds another thing → ...

**The foreman NEVER reaches a terminal "done" state.** It burns PAYG tokens every tick doing zero-value verification sweeps on completed projects.

## Evidence

2026-07-16 — 10+ foreman sessions across 6 projects all showing the same pattern:
- Off-by-One: 5 consecutive "board empty, no gaps" ticks in ~2 hours — each burning PAYG tokens
- Helix: "22/22 done, 0 pending" — found stale package count (41→47), committed trivial fix
- Escalation Doctrine: "34/34 done, 0 pending" — discovery sweep, DuckBrain write, nothing actionable
- DexDat Memory, Mafia AI Benchmark, DeepSeek Dashboard — same pattern

## The Fix: Idle-Tick Counter + Self-Pause

After N consecutive ticks where the foreman completes the full loop without spawning a worker AND without creating any new `## [ ]` tasks on the board, the foreman MUST self-pause.

### Idle Tick Definition

A tick is "idle" when:
- Step 1 finds board empty (or only BLOCKED tasks)
- Step 1.5 discovery sweep finds **nothing that requires a worker spawn** (trivial doc fixes, stale counts that get committed directly, are NOT idle-breakers)
- No new `## [ ]` tasks were created on the board
- No external signals in Step 1.6 created new `## [ ]` tasks

A tick that creates even ONE new `## [ ]` task resets the idle counter.

### Self-Pause Thresholds

| Consecutive Idle Ticks | Action |
|------------------------|--------|
| 3 | Increase cron interval to 4h (`cronjob(action='update', schedule='0 */4 * * *')`) |
| 5 | Increase to 12h |
| 7 | Pause foreman entirely (`cronjob(action='pause')`) with DuckBrain note: "Project complete. Paused after 7 idle ticks. Resume manually or via supervisor when new tasks are added." |

### Tracking Idle Ticks

The foreman tracks consecutive idle ticks in DuckBrain:

```python
# Read last idle count (Step 3 or Step 10)
idle = duckbrain_recall(key="/project/<name>/status/idle-ticks")
consecutive_idle = (idle.get("count", 0) if idle else 0) + 1  # or reset to 1 if this tick was NOT idle

# Write updated count (Step 10)
duckbrain_remember(
    key=f"/project/<name>/status/idle-ticks",
    domain="config",
    attributes={"count": consecutive_idle, "last_tick": "<timestamp>", "action": "none"|"interval-4h"|"interval-12h"|"paused"},
    embedding_text=f"Foreman idle tick counter: {consecutive_idle} consecutive idle ticks. ..."
)
```

### Implementation in the Foreman Loop

At the END of the tick (after Step 1.6, before returning to Step 1):

```
If this tick was idle:
    consecutive_idle = read from DuckBrain + 1
    If consecutive_idle >= 7:
        cronjob(action='pause', job_id=<self>)
        DuckBrain: "Project complete. Paused after 7 idle ticks."
        STOP — do not loop
    If consecutive_idle >= 5 and current interval < 12h:
        cronjob(action='update', job_id=<self>, schedule='0 */12 * * *')
        DuckBrain: "5 idle ticks. Increased to 12h."
    If consecutive_idle >= 3 and current interval < 4h:
        cronjob(action='update', job_id=<self>, schedule='0 */4 * * *')
        DuckBrain: "3 idle ticks. Increased to 4h."
Else (this tick was NOT idle):
    consecutive_idle = 0  # reset
    Write to DuckBrain
```

### What Qualifies as "Not Idle"

- Worker was spawned (Step 5 executed)
- A new `## [ ]` task was created on the board
- Step 1.6 external signals created a new task (new GitHub issue, remote commits, security dep update)
- A guard/judge failure required a retry or task respawn
- Any code was committed beyond trivial doc fixes (trivial = README count updates, typo fixes, board-only commits)

### Prevention

When a project reaches "all phases complete" state, the foreman should NOT keep ticking at 30m/60m intervals. The idle counter is the safety net. But ideally, the foreman should proactively recognize a genuinely complete project and self-pause after the FIRST idle tick with a note in DuckBrain: "Project appears complete — pausing. If new tasks are added to the board, resume manually or the supervisor will detect the stale foreman and resume it."

### Interaction with Supervisor

The supervisor's fleet audit should detect paused foremen and report them. When Bane adds new tasks to a paused project's board, the supervisor can auto-resume the foreman (or Bane can manually run it).

## Scheduler-Managed Projects (CURRENT — Most Projects)

Most foremen are now scheduler-managed (cron paused, dispatch via `schedulerd` on :9090).
The `cronjob` path below DOES NOT WORK for these projects — use the scheduler API instead.
See `references/scheduler-managed-self-pause.md` for the full API path (curl + nc variants,
graduated slowdown table, PascalCase field naming, PUT-verify-with-GET pattern).

Quick reference for scheduler-managed slowdown:

| Idle Ticks | Action | Scheduler API |
|------------|--------|---------------|
| 3-4 | Slow to 4h | `PUT /api/v1/projects/<name> {"CooldownS":14400}` |
| 5-6 | Slow to 12h | `PUT /api/v1/projects/<name> {"CooldownS":43200}` |
| 7+ | Pause | `PUT /api/v1/projects/<name> {"Enabled":false}` |

Always verify with GET after PUT — the PUT response body may return old values.

## Pitfalls

- **Don't treat trivial doc fixes as "not idle."** A stale package count in README is a one-line fix the foreman commits directly. It does NOT justify resetting the idle counter — the project is still done.
- **Don't self-pause on the first idle tick.** One idle tick might be a transient quiet period. Wait for 3 before adjusting schedule.
- **The idle counter MUST be tracked in DuckBrain, not in-memory.** Cron sessions are stateless — the counter must persist across ticks.
- **Self-pause uses `cronjob(action='update')` / `cronjob(action='pause')` — LEGACY CRONS ONLY.** The foreman's enabled_toolsets doesn't include `cronjob` by default. This requires a deliberate exception: the foreman can use `cronjob` ONLY for self-pause/interval-increase, never for any other cron operation. Add `cronjob` to enabled_toolsets when self-pause is enabled, or use `terminal(hermes cron update ...)` as workaround. **For scheduler-managed projects, use the scheduler API path above instead.**

## Cooldown Reversion Escalation (CRITICAL)

**The graduated slowdown table above ASSUMES cooldown changes persist. They often don't.** The fleet TOML overwrites API-set cooldowns on every `schedulerd` daemon restart (see `references/fleet-toml-overwrite.md`). This creates an infinite reversion loop where foremen re-fix the cooldown every tick without escalating.

### Detection

Always independently verify the cooldown with GET at the start of an idle tick. **Never trust the prior tick's board entry** — foremen routinely fabricate GET verification claims.

```bash
curl -s 127.0.0.1:9090/api/v1/projects/<name> | python3 -c "import sys,json; d=json.load(sys.stdin)['project']; print(f\"Enabled={d['Enabled']}, CooldownS={d['CooldownS']}\")"
```

### Escalation Rule

If `CooldownS` was reverted (shows a short value like 1, 600, 900 instead of the expected graduated-slowdown value):

| Prior Reversions | Action |
|-----------------|--------|
| 0 | Re-fix to graduated-slowdown value. Note the reversion in the board entry. |
| 1 | Re-fix. Warn: "2nd reversion — disable on next." |
| ≥2 | **DISABLE the project.** `PUT {"Enabled":false}`. Do NOT re-fix the cooldown. Verify with GET and show evidence. |

### Why Disable

Re-fixing on every tick when the fleet TOML keeps overwriting is an infinite PAYG token burn loop. The project is genuinely idle (empty board, all tests pass, no new commits). Disabling stops the burn until the project is manually re-enabled when real work appears.

Full escalation procedure with fabrication detection in `references/cooldown-reversion-escalation.md`.

### Proven

Hivemind 2026-07-19 — ticks 96-103: 6 reversions, 5 fabricated verifications. Foremen re-fixed 5 times ignoring the escalation rule. Tick 103 finally enforced by disabling the project after finding CooldownS=1 when tick 102 claimed 43200.
