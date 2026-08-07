# Starvation & Ghost Projects — Diagnosis Playbook (2026-07-31)

A project can be `Enabled=true` with a normal cooldown and STILL never tick.
The scheduler alerts "project starved" every 5 min but the packer never picks
it. Three root causes, all seen in production.

## 1. decay_rate=0 → permanent starvation (the big one)

Urgency formula: `priority × (1 + elapsed/interval)^decayRate`. With
`decayRate=0`, elapsed time is IGNORED — urgency stays flat at priority level
(~10) while every healthy project's urgency grows with age. The project
never wins the packer. **Proven:** dexdat-memory starved 87h with valid
namespace + 900s cooldown because decay_rate was 0 (a foreman set it as a
misapplied "self-pause").

- **Detect:** `GET /api/v1/projects` → find `Enabled=true` + `DecayRate=0`
  + pending board work. Check the daemon log `PACKER-SORTED[...]` — the
  project is absent or at the bottom regardless of elapsed time.
- **Fix:** `PUT /api/v1/projects/<name>` `{"DecayRate":1.0}`.
- **Guard (live since commit bc438e6):** the API now REJECTS
  `DecayRate <= 0` with HTTP 400 ("decay_rate must be > 0 (0 causes
  permanent starvation — urgency never grows)"). Foremen cannot starve
  themselves anymore.

## 2. Namespace issues → never scheduled

- `NamespaceID=None` → allocator skips the project entirely. **Proven:**
  `<project>` enabled 5 days, zero ticks, because namespace was NULL.
- `NamespaceID` pointing to a namespace that doesn't exist in the daemon
  (list via `GET /api/v1/namespaces`) → same effect. **Proven:** `<project>`
  was assigned namespace "<project>" which didn't exist.
- **Fix:** `PUT /api/v1/projects/<name>` `{"NamespaceID":"coding-hermes"}`.

## 3. Case-insensitive duplicate workdir → ghost project

Project names are case-sensitive but the daemon doesn't dedupe workdirs.
`<project>` and `<project>` pointing at the same dir = two project rows, one
does all the ticks, the ghost never fires. **Proven:** <project> had 661
committed ticks; `<project>` (same workdir, different case) had zero.

- **Detect:** query DB for projects sharing a workdir
  (`SELECT name FROM projects WHERE LOWER(workdir)=LOWER(?)`).
- **Fix:** delete/disable the ghost row (the one with no tick history).
- **Guard (live since commit bc438e6):** `CreateProject` now rejects a
  workdir already registered by an ENABLED project (HTTP 409). Disabled
  duplicates are still allowed (archived entries).

## Auto-heal

`~/.hermes/scripts/fleet-auto-heal.py` (cron every 6h, no_agent) detects
AND fixes all three: disables duplicate-workdir ghosts, restores
`DecayRate=1.0` on decay-zero starvation, resets 12h+ cooldowns to 900s
when pending work exists. Silent when healthy; prints what it fixed when
not. Respects `fleet.toml` pins (cooldown >= 43200 in fleet.toml = admin
intent, skipped). Keep it in sync with any new scheduler failure modes.

## Debugging workflow

Daemon log (`process log` on the schedulerd session) shows
`PACKER-SORTED[N]: <project> urgency=X pri=Y last=Z` per evaluation — the
single best tool for "why wasn't X picked". Compare a healthy project's
urgency vs the starved one; flat urgency ≈ decay=0.

## Board storage: Parquet → JSONL (INFRA-013)

`.coding-hermes/board/` exports were Parquet (binary, opaque, unmergeable,
force-added against `.gitignore:26` `.coding-hermes/`). Correct git-safe
pattern: keep `board.db` DuckDB as the ignored live store, export
`tasks.jsonl` / `events.jsonl` / `fixtures.jsonl` / `board.jsonl`
(line-per-record, diffable) as the git mirror, negate
`!.coding-hermes/board/*.jsonl` + `schema.sql` in .gitignore. DuckBrain
uses the same JSONL-for-git pattern.
