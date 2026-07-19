# Phased Migration Pattern — Don't Cut Over Blind

**Origin:** July 12, 2026 — coding-hermes scheduler migration.

## The Rule

**When deploying a new system that replaces an existing one, run both in parallel.**
Keep the old system running production workloads. Use the new system as a sandbox
with non-critical projects. Graduate workloads one at a time.

## The Anti-Pattern

1. Build new system → migrate everything → disable old system → hope it works.
2. Result: production goes silent, old crons are paused, you can't tell if either system is working.
3. User frustration: "Your moving my production building to a thing with minimal logging."

## The Correct Pattern

```
Phase 1: BUILD — Build the new system in isolation. Simulation testing, unit tests.
Phase 2: SHADOW — Run new system in parallel with old. New system manages a few
         low-stakes test projects. Old system handles everything else.
Phase 3: CANARY — Move ONE project from old to new. Monitor for 24h.
         Verify: ticks complete, outcomes correct, no double-spawning.
Phase 4: ROLL — Graduate 3-5 more projects. Monitor.
Phase 5: CUTOVER — When confidence is high (weeks, not hours), move remaining
         production projects. Keep old system as warm standby.

## Never Do This
- Pause all old crons immediately after migration
- Migrate 26+ projects in one batch
- Deploy without at least 1h of simulation testing first
- Skip the shadow/canary phases

## Signals You Violated This
- "keep the import crons on Hermes then the not important on the new stuff"
- "so you can play before etc and when we are good we transfer more workloads"
- Any phrase containing "you moved my production" or "put it back"
