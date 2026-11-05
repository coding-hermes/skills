# Fleet deploy and alignment runbook

Two stores hold the fleet's shape and they must agree:

| store | what it is authoritative for |
|---|---|
| `~/.hermes/coding-hermes/scheduler.db` (`projects`) | the live row: `enabled`, `command`, current cadence, namespace |
| `~/.hermes/fleet.toml` | the loader input: re-pinned into `projects` at daemon start |

A lane that exists only in the DB keeps running until the next daemon restart. A lane that exists
only in the TOML does not exist. A cadence written to one store and not the other is the fleet's
most common silent defect — it looks fixed, and it reverts.

## Adding a service to the fleet

```bash
# 1. lane family — cadence comes from the table, never from you
python3 ~/.hermes/scripts/fleet_lane_align.py --project <name> --roles ops --dry-run
python3 ~/.hermes/scripts/fleet_lane_align.py --project <name> --roles ops

# 2. write the block into fleet.toml (append-only; existing lines stay byte-identical)
python3 ~/.hermes/scripts/fleet_toml_sync.py --dry-run
python3 ~/.hermes/scripts/fleet_toml_sync.py

# 3. prove the two stores agree
python3 ~/.hermes/scripts/lane_cadence.py check

# 4. prove the ops surface
python3 ~/.hermes/scripts/fleet_ops_check.py --project <name>
```

`fleet_lane_align.py` refuses to invent a cadence, never flips `enabled` on an existing row (the
daemon's auto-disable for failure rate must survive a re-run), and repairs a retired-driver
`command` instead of leaving it in place.

`fleet_toml_sync.py` appends only. A previous generation of scripts re-serialized the whole file;
one of them cut a 691-row board to a single row, which is why the append-only rule exists.

## Canonical cadence (single source: `lane_cadence.py`)

| suffix | pin | role |
|---|---|---|
| `-foreman` | 6h | project primary (varies by ruling: 900s … 12h) |
| `-sync` | 6h | state reconciliation |
| `-qa` | 12h | quality sweep — ONE per project |
| `-ops` | 24h | operations sweep |
| `-pm` / `-releng` | 24h | planning / release engineering |
| `-dogfood` | 3d | real-use validation |
| `-docs` / `-readme` / `-review` / `-perf` | 7d | slow-moving artefacts |

This table IS the closed role set. A `-<role>-qa` composite (`-docs-qa`, `-readme-qa`, `-releng-qa`,
`-foreman-qa`, `-review-qa`, `-perf-qa`) is fabricated — a second QA beside the real `-qa`, or a QA
sweep of a README. Delete such rows in both stores; never create one to "match" a peer family, because
the peers carry them too and diffing against a peer inherits the defect. Group families by lane NAME
(role suffixes stripped, longest-first, only when the stripped stem is itself a registered row) —
grouping by workdir over-splits, since stand-in dirs are named per lane. Standing a host down onto a
subset of families (both stores written while the daemon is stopped, then a boot that must resurrect
nothing): `coding-hermes-lane-ops` → `references/fleet-stand-down.md`.

`lane_cadence.py check` exits 1 on drift. It also flags a row whose `cooldown_s` and
`cooldown_pin_s` disagree even when one of them is correct — that disagreement is ambiguity the
loader resolves however it likes, and it hid 38 enabled `-qa` lanes sitting at the primary
cadence.

## Repair, don't report

`lane_repair.py --apply` is the fixing lane: cadence drift is corrected in BOTH stores and
re-verified; a workdir problem becomes a brief for an agent instead of a scripted directory move
(a directory can legitimately be moving, renamed or re-modelled, and a move script that guesses
wrong destroys the only copy of something).

The same principle applies here: an ops finding that a script can fix, the script fixes. An ops
finding that needs judgement becomes a board row with acceptance criteria.

## Pitfalls, all observed on a live fleet

- **A policy regen can strip every pin.** A cooldown-policy script that regenerated
  `fleet.toml` from live DB values once removed `cooldown_pin_s` from 660 of 676 enabled lanes;
  the next restart re-pinned them to defaults and a lane family silently reverted to a 30m cadence
  twice in a day. Any generator must emit the pin alongside the cadence, and prefer the canonical
  value for a satellite over whatever the DB currently says.
- **`enabled` is not cosmetic.** A lane auto-disabled for a 91% failure rate still reads
  `enabled = true` in a stale TOML; the next restart resurrects it. When you disable a lane,
  disable it in both stores.
- **A family is one repository.** Different workdirs are only a defect when
  `git rev-parse --show-toplevel` agrees they are the same repo.
- **Suffix matching must be hyphen-delimited and longest-first**, or `9router-docs-qa` matches
  `-docs` and is classified as a primary.
- **Never re-serialize a file you only meant to edit one line of.** Append or patch; never
  round-trip.

## When the deploy is "done"

Not when the process starts. Done means: health answers, a metric moves, a log line lands, killing
the process brings it back, and the `-ops` lane will look again tomorrow. Anything less is a
process that happens to be running right now.
