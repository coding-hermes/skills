# Starvation Diagnosis via Packer Logs (2026-07-31)

Three distinct "project hasn't ticked" root causes found in one session. Each
presented identically (enabled=1, valid-looking cooldown, no ticks for days)
but required a different fix. Diagnostic path documented here.

## The Diagnostic: Read the PACKER-SORTED Log Lines

The daemon logs every eval cycle's project ranking:

```
18:47:54 packer.go:135: PACKER-SORTED[0]: dexdat-memory urgency=105492.7 pri=10 last=02:53
18:47:54 packer.go:135: PACKER-SORTED[1]: <project> urgency=53677.1 pri=10 last=22:04
18:47:54 packer.go:163: PACKER: max concurrency reached (4), stopping
18:47:54 packer.go:204: PACKER: nothing packed — checked 1 projects, skipped budget=0 cooldown=0 already-running=0, total-running=4/4
```

**Interpretation:**
- A project MISSING from PACKER-SORTED entirely = excluded before sorting
  (namespace problem, decay=0 flat urgency, or disabled) — NOT waiting for a slot.
- A project PRESENT in the list but not spawned = waiting for concurrency
  (`max concurrency reached` / `total-running=4/4`) — healthy, just queued.
- `urgency` values: compare the starved project's urgency to peers. If it's
  ~10 while peers show thousands, decay_rate=0 is flattening it.

## Root Cause 1: Nonexistent Namespace (<project>)

- **Symptom:** enabled=1, cd=900s, valid priority, ZERO ticks since Jul 29.
- **DB:** `namespace_id='<project>'` — but `GET /api/v1/namespaces` returns only
  [backup, coding-hermes, data-cleanup, duckbrain-infra, monitoring].
- **Why:** the allocator only iterates registered namespaces; unknown
  NamespaceID = never considered.
- **Fix:** `PUT /api/v1/projects/<project> {"NamespaceID":"coding-hermes"}`.
- **Verify:** next eval shows the project in PACKER-SORTED near the top
  (urgency 53,624 for ~2 days elapsed at pri=10).

## Root Cause 2: decay_rate=0 (dexdat-memory + 8 others)

- **Symptom:** starved 87h, valid namespace, enabled=1, cd=900s, pri=10.
  Escalator fired `project starved: dexdat-memory — last tick 87h49m ago`
  every 5 min but allocator never picked it.
- **DB:** `decay_rate=0.0`.
- **Why:** urgency = pri × (1+elapsed/interval)^decay. decay=0 → exponent
  collapses to `pri × 1` = flat 10. Elapsed time ignored → never urgent.
- **Fix:** `PUT {"DecayRate":1.0}` → urgency jumped to 105,492 immediately
  and project took PACKER-SORTED[0].
- **Scope:** 9 projects had decay=0; all had been set by foremen treating
  "self-pause" as "set decay to 0". Only genuinely idle projects should
  carry decay=0 (with 0 pending board work verified).

## Root Cause 3: Case-Duplicate Ghost Entry (<project> vs <project>)

- **Symptom:** "<project>" enabled with cd=900s, zero ticks ever (5 days).
- **DB:** TWO rows, same workdir `~/<project>`:
  - `<project>` — created Jul 18, **661 ticks** Jul 18→29 all committed,
    self-paused at 43200s, deliver target set. THE REAL PROJECT.
  - `<project>` — created Jul 26 (8 days later), 0 ticks, no deliver. GHOST.
- **Why:** case-sensitive project names; a later API/foreman call registered
  the lowercase variant pointing at the same workdir.
- **⚠️ Query pitfall:** `WHERE project_name='<project>'` returns zero rows when
  the row is `<project>`. Use `WHERE lower(project_name) LIKE '%<project>%'`.
  An exact-case query produces the false conclusion "foreman never ran /
  logging is broken" — the logging was fine, the lookup was case-sensitive.
- **Fix:** disable the ghost (`PUT {"Enabled":false}`), keep the real entry.

## Fleet Audit Script Upgrades (shipped same session)

`~/.hermes/scripts/fleet-cooldown-audit.py` (cron "Fleet Cooldown Audit",
every 6h, no_agent, silent-when-clean) now checks THREE failure classes:

1. `DUPLICATE-WORKDIR` — 2+ enabled projects sharing a workdir
2. `DECAY-ZERO-STARVATION` — enabled project with decay_rate=0 AND pending
   board/gitreins work
3. `SLOW-COOLDOWN` — enabled project at ≥43200s cooldown with pending work
   (respects fleet.toml pinning — admin intent is not a problem)

Manual run: `python3 ~/.hermes/scripts/fleet-cooldown-audit.py`

## Order of Operations When "Project Hasn't Ticked"

1. `GET /api/v1/projects/<name>` — enabled? namespace? decay? cooldown?
2. `WHERE lower(project_name) LIKE` — case-insensitive tick lookup
3. Cross-check NamespaceID against `GET /api/v1/namespaces`
4. Read recent PACKER-SORTED lines — present-but-queued vs missing-entirely
5. Check decay_rate — flat urgency is silent starvation
6. Check for duplicate workdir rows (case variants)
