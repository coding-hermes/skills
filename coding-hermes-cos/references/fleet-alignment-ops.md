# Fleet alignment ops — working a lane cleanup worklist end to end

The operator periodically sends a batch alignment worklist ("X is missing lanes, delete A,
B, C, disable Y"). Work it in ONE scripted pass, never lane-by-lane by hand.

## 0. Backups first, non-overwriting

```
cp scheduler.db  backups/scheduler-db-pre-<tag>.snapshot   # skip if exists
cp fleet.toml    backups/fleet.toml.pre-<tag>
```

## 1. Census everything the operator named

One query over `projects` for every prefix/name mentioned. Do not guess what exists —
the operator misspells names (`dc-vacum` → `dc-vacuum`), and the fix is a `LIKE` census,
not a rename guess.

## 2. Classify each item before acting

- **Fixture residue** — `repo_url` of `example.com/*` or workdir `local:/tmp*`. These are
  old seeding-test lanes. DELETE (they burn ticks when enabled and confuse alignment),
  even if currently enabled — say so in the report.
- **Incomplete family** — count lanes against the 11-role template: foreman + qa, pm,
  sync, dogfood, perf, releng, review, docs, readme, ops. Mint the missing ones.
- **Case twins** — exact-case duplicates (`HEADING` vs `heading`) are reconciler-era
  drift. The owner decides which case is real when asked; when he already ruled (e.g.
  lowercase is the family), delete the twin INCLUDING lanes you minted for it earlier the
  same day, and own the mistake in the report.
- **Compound-role residue** — names like `<fam>-readme-qa` (a role glued onto a role)
  are lane-creation bugs. Delete.

## 3. Minting rules

- **Match the family's state, not your preference**: a disabled (dark/paused) family gets
  DARK mints (`enabled=0`, `disabled_by='api'`, a disable reason naming the family
  state). An enabled family gets enabled mints. Never wake a paused family by completing
  its template.
- Satellites take `admission_mode='cooldown'`; the API rejects non-tasks admission on
  lanes the validator classes as foremen — workdirs follow
  `~/.hermes/stand-in/<role>/<fam>` (`pm-lane` for pm).
- `projects.created_at`/`updated_at` are NOT NULL — stamp both on insert.
- After the SQL insert, re-assert the enabled flag via a full-field **API PUT** — the
  daemon flush clobbers SQL flag writes (see SKILL.md state-law pitfall).
- Renaming a lane (e.g. a pre-convention bare name → `<fam>-foreman`): update
  `projects.name`, rewrite `ticks.project_name`, and edit the `fleet.toml` block's `name`
  line — all three or the family reads as two.

## 4. Deletion rules

- Delete = remove from `projects`, remove `ticks` rows, remove the `fleet.toml`
  `[[projects]]` block (split the file on `(?=\n\[\[projects\]\])`, match the whole
  block's `name = "..."` line — never a substring), and delete any orphaned cron that
  exists only to serve the deleted family (card-manager crons: `hermes cron delete <id>`).
- boardctl create refuses duplicate ids — when filing an alignment row, take the next
  free id; the abort IS the safety.

## 5. fleet.toml consistency

fleet.toml carries only ENABLED lanes by regenerator design — 200+ disabled lanes absent
from it is normal, not data loss. After edits, `tomllib` parse-check and diff the name
set both ways (in-toml-not-db, in-db-not-toml-and-enabled must both be empty).

## 6. Verify and report

- Read back every mutation by count (`sum(enabled)` per touched family, deleted-name
counts = 0), never by the script's printout alone.
- Regenerate the owner dashboard:
  `python3 ~/.hermes/skills/coding-hermes-cos/scripts/lane_alignment_report.py` →
  `~/project-reviews/lane-alignment.html` — and send the file with the report. The owner
  reviews by clicking families open; a stale HTML he already downloaded is why a
  'still broken' reply can mean he is reading an old snapshot — re-send the current file.
- Duplicate-workdir warnings in the scheduler event log after minting are real findings
  (two enabled lanes on one tree = concurrent-writer hazard) — file them as a row, do not
  silently accept.

## 7. Model-pin sweeps (removing pins to let the router decide)

- **Find the ENFORCER before trusting any bulk state mutation.** A fleet-wide pin or flag
  sweep that ran once means nothing if a cron or script re-applies it hourly. Before
  sweeping: grep the cron list and the scripts dir for pin-enforce mechanisms, and confirm
  each one is disarmed (its target env empty) — otherwise the sweep silently reverts and
  the 'constant failures' come back.
- **Pin fields are read per-spawn, so direct SQL is safe for THEM** (`update projects set
  model='', provider=''`) — the daemon-flush clobber law applies to FLAG flips, not pin
  clears. Prefer this over full-field PUTs when the admission validator refuses the API
  route for some lane classes (a `-ops` lane with empty `admission_mode` 400s every PUT
  with an admission-law error; do NOT flip admission modes as a side effect of a pin
  sweep — file that as its own row).
- **Build PUT bodies with a self-learning bool set**: the first run's 400 error names each
  Go-typed bool field (`field updatesAlias.\w+ of type bool`) — grow the bool set from the
  errors and retry per lane instead of hand-guessing the whitelist up front.
- **Count pins per mode at census time** (enabled vs disabled separately): the enabled
  count is the failure generator; disabled-lane pins are a standby-wave decision for the
  owner, not part of the sweep.
