# Per-Project Delivery Routing — Pitfalls & Debugging

## Symptom
All scheduler ticks deliver to the default thread (83996) instead of per-project threads.

## Root Cause: MultiPoolPacker doesn't populate Deliver

The scheduler has TWO packing code paths:
1. `Packer.Pick()` — non-namespace mode. Populates `PackedProject.Deliver` correctly.
2. `MultiPoolPacker.Pack()` — namespace mode (used when `--namespace-mode` is on). 
   Did NOT populate `PackedProject.Deliver` — the struct literal was missing the field.

Result: `SpawnedTick.Deliver` was empty, so `deliverOutput()` fell back to the default thread.

## Detection

```bash
journalctl -u coding-hermes-scheduler | grep "DELIVER.*83996"
```

If ALL ticks go to 83996 no matter the project, the `Deliver` field is not being populated.

## Fix (3 locations — all must match)

1. **`internal/database/models.go`** — add `Deliver string` to `Project` struct
2. **`internal/database/projects.go`** — add `deliver` to SELECT + Scan in `ListProjects()` and `ListProjectsByNamespace()`
3. **`internal/scheduler/multipool_packer.go`** — add `Deliver: pu.Project.Deliver` to the PackedProject literal in `Pack()`
4. **`internal/scheduler/packer.go`** — add `deliver` to the scored struct + scan + PackedProject population (already fixed)

## Delivery target format

```
telegram:-1003310984808:<thread_id>
```

Thread IDs are extracted from paused cron jobs' `deliver` field, matched by workdir.

## Key commit
`1a73db3` — "fix: populate Deliver field in MultiPoolPacker and database queries"
