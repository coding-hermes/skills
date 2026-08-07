# Timeout/Cooldown Alignment — v3.7 Design

**Session:** 2026-07-19  
**Trigger:** rethinkdb spawn→timeout→spawn loop, ASCE disabled by timeout pipeline  
**Bane directive:** "timeout means try again soon, not back off forever"

## Design Principle

```
timeout = LONG (2h)      — let jobs finish
cooldown = SHORT (15min) — re-fire fast after completion
timeout = LOG + ALERT    — never change cooldown
timeout = NEVER DISABLE   — project stays active regardless of history
```

## What Changed

| v3.6 (broken) | v3.7 (fixed) |
|---------------|-------------|
| timeout 1800s | timeout 7200s (2h) |
| timeoutBackoff doubles cooldown | timeout does NOT touch cooldown |
| timeout silent (log only) | deliverAlert sends ⚠️ to chat |
| autoSlowdown cap 4h→1h, 2x multiplier | cap 1h, 1.5x multiplier |
| autoSlowdown detects "IDLE TICK" string | detects "VERDICT: ... IDLE" line |

## Timeout Pipeline (v3.7)

```
Tick times out after 7200s
  → log.Printf("TIMEOUT: %s — project stays active, normal cooldown applies")
  → if delivery target set: deliverAlert(target, project, tickID, reason)
     → "⚠️ project timed out — timeout after X\nTick: Y"
     → hermes send → Telegram
  → Project cooldown: UNCHANGED
  → Next eval: project eligible immediately (if cooldown expired)
  → No penalty, no disable, no backoff
```

## Auto-Slowdown (gentle)

```
IDLE detected (VERDICT: ... IDLE in output)
  → Multiply cooldown by 1.5x (not 2x)
  → Cap at 3600s (1h)
  → Produtive tick (VERDICT: ... PRODUCTIVE) → reset to 600s

IDLE escalation path (1.5x):
  600 → 900 → 1350 → 2025 → 3037 → 3600(cap)

vs old 2x path:
  600 → 1200 → 2400 → 4800(cap-was-14400)

New path reaches cap in 5 idle ticks, old reached it in 3.
5× idle × 1h cap = worst case 5h gap, not permanent.
```

## Detection (VERDICT-based)

Old: `strings.Contains(text, "IDLE TICK")` — fragile, depends on exact formatting
New: `strings.Contains(text, "VERDICT:") && strings.Contains(text, "IDLE")` — structured

The foreman always outputs a VERDICT line. This is more reliable and doesn't
depend on arbitrary formatting conventions.

## Systemd Configuration (production)

```
ExecStart=.../schedulerd --tick-timeout 7200s --max-concurrent 10 --min-interval 30s
```

The systemd unit AND code default are aligned at 7200s. Verify:
```bash
grep "tick-timeout" /etc/systemd/system/coding-hermes-scheduler.service
# Must show: --tick-timeout 7200s
```

## Tests Enforcing This

| Test | What It Guards |
|------|---------------|
| TestTimeout_DoesNotBackOff | Cooldown ≤ 900 after timeout — no backoff |
| TestTimeout_AlertIsDelivered | ⚠️ + tick ID in alert message |
| TestAutoSlowdown_CapAtOneHour | 3600s cap verified |

## GitReins Enforcement

`RULE-NO-TIMEOUT-BACKOFF` (10 criteria):
1. tick-timeout ≥ 7200s in code default AND systemd
2. No TimeoutBackoff function exists
3. Timeout outcome does NOT modify cooldown
4. deliverAlert includes ⚠️ and tick ID
5. Auto-slowdown uses 1.5× multiplier
6. Auto-slowdown cap is 3600s
7. Productive resets cooldown to 600s
8. Tests exist for all of the above
9. No project auto-disabled anywhere in scheduler logic

Run: `gitreins evaluate --id RULE-NO-TIMEOUT-BACKOFF`
