# Scheduler Bugs Found Through Simulation — July 12, 2026

Three critical bugs were found through simulation testing before hitting production. These are
the kind of bugs that simulation-first development catches. All three were in the scheduler core
path and would have silently broken the fleet.

---

## Bug 1: Urgency Formula Reversed

**What:** Priority 10 (highest) mapped to 160-hour intervals. Priority 1 (lowest) mapped to 5-minute intervals.

**Root cause:** `interval = minInterval * ratio^position` — multiplying by ratio makes intervals
grow with priority, but higher priority should mean SHORTER intervals.

**Fix:** `interval = maxInterval / ratio^position`

**Detection:** Simulation showed low-priority projects (priority 1) always picked before high-priority
projects (priority 9). Priority ordering appeared reversed in packer output.

**Lesson:** The geometric priority-to-interval mapping must be `max / ratio^position`, not
`min * ratio^position`. Verify with boundary tests: ComputeInterval(10) == minInterval,
ComputeInterval(1) == maxInterval.

---

## Bug 2: COALESCE Cooldown Trap

**What:** All newly-created projects were blocked by cooldown on their first tick.

**Root cause:** Packer query used `COALESCE(last_tick_completed, created_at)`. For projects
with NULL `last_tick_completed` (never run), the COALESCE returned `created_at`. The cooldown
check `now - lastCompleted < cooldownDur` was always true for fresh projects because
`created_at` was within the cooldown window.

**Fix:** Read `last_tick_completed` as raw NULL. Only enforce cooldown when the value is
explicitly set (non-NULL). Fresh projects with no prior tick pass through.

**Detection:** Simulation showed 0 projects packed despite 12 enabled. PACKER debug log showed
"skipped budget=0 cooldown=12". Debugging revealed all 12 were cooldown-skipped.

**Lesson:** Never COALESCE a nullable `last_completed` field with `created_at` for cooldown
enforcement. Use separate NULL semantics: NULL = never run = no cooldown.

---

## Bug 3: Sim Spawner Bypass

**What:** Simulated ticks completed but `last_tick_completed` was never updated on the
project row. Cooldowns had no effect across simulation ticks.

**Root cause:** `SimSpawner.Spawn` wrote tick rows directly via SQL, bypassing
`LifecycleTracker.Complete`, which is the only function that updates `last_tick_completed`.

**Fix:** Added `UPDATE projects SET last_tick_completed = ? WHERE name = ?` to
`SimSpawner`'s completion goroutine, mirroring the lifecycle behavior.

**Detection:** Simulation showed the same 5 projects every tick across 10 ticks,
even after all 12 projects had completed a simulated run. Cooldowns weren't cycling.

**Lesson:** Any spawner implementation (real or simulated) must update
`last_tick_completed` on the project row when a tick completes. Otherwise cooldowns
are ineffective. Test this with multi-tick simulations.
