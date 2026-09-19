# Fleet config: DB is the source of truth, fleet.toml is a mirror

**Policy (Bane 2026-09-19, verbatim intent):** "we want a fleet file but not
rewriting it all the time … that has led to a lot of issues and keeps changing
the underlying system that you're trying to run … we are not using the cooldown
as much since we have task mode."

## What changed

The old flow had **two competing authorities**:

1. Operator sets a cooldown via API PUT → scheduler DB has it.
2. `fleet-cooldown-policy.py --apply` ran "correction rules" (REDUCE/RAISE/
   PROMOTE/REVERT), PUT its own decisions back, then **regenerated fleet.toml
   from the API** — with a header that said "do not edit by hand".
3. Next daemon restart re-pinned every project **from fleet.toml** — silently
   reverting whatever the operator had set between regens.

Proven failures of that design: the hermes-dagger 900s pin reverted to 21600 on
a restart (twice, via two different paths); the regen dropped wave keys
(`wave_enabled`/`wave_tick_timeout`/`wave_workers_cap`) on any regen; h3/warpfs
anti-flood pins got clobbered 34 consecutive times before an ELEVATED_PINS
whitelist was bolted on.

## The new flow

```
API PUT (the only way to change pacing)
   └─> scheduler DB (single source of truth)
          └─> fleet-sync.py --write  (one-way mirror, atomic)
                 └─> ~/.hermes/fleet.toml   (read by daemon at startup)
```

- **`scripts/fleet-sync.py`** — mirrors live DB state into fleet.toml. Decides
  nothing, PUTs nothing. Emits every namespace field it finds
  (`admission_mode`, `load_gate`, `wave_*`, `model_chain`, `default_prompt`,
  caps) and every project pin (cooldown, adaptive floor/ceiling, model,
  provider, deliver, enabled). Dry-run by default; `--write` goes through
  tmpfile+rename.
- **`scripts/fleet-cooldown-policy.py --apply` is RETIRED** — it now exits 2
  with a pointer to fleet-sync.py. The dry-run *report* mode (no --apply) still
  works for audits.
- Task mode made the cooldown-era correction rules obsolete anyway: with
  `admission_mode = "tasks"` the board drives work; the clock only guards
  against hammering.

## Operating rules

1. **Cooldown/pacing change = one API PUT. Nothing else needed.** It survives
   restarts because the mirror re-reads the DB (run `fleet-sync.py --write`
   after batch changes, or on any schedule you like — the mirror is
   idempotent).
2. **Never hand-edit `~/.hermes/fleet.toml`** — it gets overwritten by the
   mirror. The one escape hatch is the `OVERRIDES` dict at the top of
   fleet-sync.py (checked, not decided — for "this pin must survive even a
   drifted DB").
3. **Fleet.toml on a *new* host is a bootstrap file, not policy.** Seed it with
   the projects you want created, boot the daemon, then treat the DB as
   authoritative from that point on.
4. **Audit = compare mirror to DB**: `python3 fleet-sync.py | diff - fleet.toml`
   — empty diff means file and DB agree.

## Migration for other deployments running the old script

```bash
# 1. retire the mutator (it fights operator PUTs)
python3 ~/.hermes/scripts/fleet-cooldown-policy.py --apply   # exits 2 after update

# 2. write the mirror once — captures whatever is true in YOUR db right now
python3 ~/.hermes/scripts/fleet-sync.py --write

# 3. restart the scheduler whenever convenient; pins now converge instead of fight
```
