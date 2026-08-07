# Scheduler API Pitfalls

These are real bugs discovered across 150+ foreman ticks. Know them before you claim a fix is done.

## Cooldown Silent-Failure (15+ ticks wasted)

**Symptom:** Foreman claims "cooldown restored to 43200s via PUT API" but next tick finds it at 900s.

**Root cause:** The PUT API field name is `CooldownS` (camelCase). Using `cooldown_s` (snake_case) is silently accepted with HTTP 200 — the API ignores the unknown field and returns the UNCHANGED value. The foreman reads the response, sees 200, and claims success.

**Fix:** Always use `{"CooldownS": 43200}` — camelCase. Always verify with GET after PUT. If GET shows the old value, your field name is wrong.

**Detection:** After every PUT, run a GET on the same project immediately. If `CooldownS` didn't change, the PUT was a no-op. Do NOT claim success without this verification.

## Cooldown Reversion Patterns (Multiple Root Causes)

| Cause | How to Detect | Fix |
|-------|--------------|-----|
| Silent PUT no-op (wrong field name) | GET after PUT shows old value | Use `CooldownS` not `cooldown_s` |
| Daemon restart → schema default | Check daemon PID changed since last tick | Systemd restart resets; re-PUT after startup |
| autoSlowdown 3600s cap | Cooldown reverts to ≤3600 | autoSlowdown caps above-cap cooldowns on PRODUCTIVE reclassify |
| DecayRate auto-escalation | Cooldown drifts downward without restart | Set `DecayRate=0` via PUT API |
| curl blocked by security scanner | PUT returns 200 but no change | Use Python `urllib.request` or Go client, not curl |

## applyFleetConfig Is Create-Only

`ApplyFleetConfig` skips existing projects. It does NOT overwrite cooldowns, models, or providers. Any cooldown reversion during a running daemon is NOT caused by fleet.toml re-application.

## autoSlowdown Output Scanner Bug

`spawn.go:332` — the scanner goroutine returns immediately after finding `session_id:` in stdout. `io.TeeReader` only writes data the scanner reads. The LLM's full response (containing "IDLE"/"VERDICT:" patterns autoSlowdown needs) is never captured. autoSlowdown is functionally dead for exec-spawned projects. Fixed in commit `1e7c4d4` (Jul 24) by changing `return` to `continue`.
