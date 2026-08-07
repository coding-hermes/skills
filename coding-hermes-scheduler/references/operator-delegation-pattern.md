# Operator Delegation Pattern — Why the Operator Shouldn't Hand-Patch Go Code

**Session:** 2026-07-18, ~6 hours
**Context:** Debugging coding-hermes-scheduler stability (<project> not firing, duplicate spawns, OOM, deadlocks)
**Key quote (Bane):** "are you actually putting this work into the foreman task list letting a smart coding agent do the work and then benefit from the upgrades or are you constantly trying to manage this yourself knowing it is not your strong suite?"

## What Happened

The operator (Hermes Agent) spent ~6 hours making real-time Go code edits via terminal/patch tools to fix scheduler bugs. Each edit introduced a new bug:

| Edit | Intention | Side Effect |
|------|-----------|-------------|
| SlotPool `chan struct{}` semaphore | Concurrent spawn | Packer still queried DB → duplicates (rethinkdb ×7) |
| RunningSet via `l.spawner.RunningSet()` | Pass in-memory set | SlotPool bypasses spawner's active map → always empty |
| SlotFreed channel for event-driven eval | Zero-wait refill | No debounce → 1388 ticks in 5 minutes feedback loop |
| `UPDATE last_tick_completed=NULL` for all projects | Unstick stale projects | Flat urgency → packer picks alphabetically → <project> never runs |
| <project> weight 25→10 | Fit in budget | Already correct — urgency tie-breaking was the real issue |
| Service file copy | Deploy fix | Overwritten with broken version (pkill, wrong concurrency, wrong memory) |
| Port 9090 conflict | Restart daemon | 6-restart crash loop, systemd `Restart=always` made it worse |

## The Foreman Was Right There

The entire time, the `coding-hermes-scheduler` foreman was running on its own tick cadence. It has:
- Full Go toolchain (build, vet, test, lint)
- GitReins guard integration
- Access to all source files
- The task board at `.coding-hermes/tasks.md`
- Its own SDLC loop (self-heal → scan → implement → verify → commit)

If the operator had simply written the bugs as tasks on the board, the foreman would have fixed them correctly in 1-2 ticks with proper testing.

## Correct Pattern

```
Operator: identifies bug → writes clear task on board → commits → moves on
Foreman:  picks up task on next tick → analyzes → fixes → builds → tests → commits
Operator: verifies foreman's commits pass gates
```

**Task format:**
```markdown
### [ ] TASK-ID — Short description
**P:CRITICAL W:20**
**Symptom:** What the user sees (<project> never ticks)
**Root cause:** What we think is broken (sort ties + flat urgency)
**Fix direction:** What approach to take (urgency based on actual last_tick,
not created_at; update last_tick on all outcomes)
**Deliverable:** Go code change + test + commit
```

## When Hand-Patching IS Appropriate

- Emergency: daemon is down, fleet stopped, needs immediate restart
- Simple config: DB updates, project enable/disable, cooldown adjustments
- Architecture decisions: "use a channel semaphore, not DB queries"
- Task writing: putting items on the foreman's board
- Verification: checking the foreman's work is correct

## When to Task the Foreman

- Any code change spanning more than 1 file
- Any change requiring Go compilation
- Any change with race condition risk
- Any change to the service file
- Any new feature requiring tests
