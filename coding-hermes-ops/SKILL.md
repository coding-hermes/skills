---
name: coding-hermes-ops
description: Use when a lane must cover OPERATIONS — containers, orchestration, metrics, alerts, supervision, backup, deploy paths — or when new work is being deployed to the fleet and its ops surface would otherwise go unwatched.
---

# coding-hermes-ops

QA asks *"does it do what it claims?"*. Ops asks *"does anything keep it running, and would we
know if it stopped?"* A project can pass every test and still ship with no health endpoint, no
metrics, no restart policy and no deploy path — and no lane ever says so, because no lane owns
that question. This skill is the owner.

**Doctrine, in one line:** derive what a project IS from evidence in its tree, then judge only the
ops surfaces that kind of project actually needs. A docs repo needs no k8s; a service needs health,
metrics, supervision and a backup path. Getting this wrong is how an ops check becomes noise.

## The lane family

`<project>-ops` — a PROMPT lane on a 24h cadence (`lane_cadence.py` owns the number). It is a
normal lane: it wakes an agent, the agent runs this skill against its project, and it files or
fixes what it finds. It is **not** a shell command lane and must never be given a
`*-scheduler-tick.sh` command (those drivers are retired; the API's `isRetiredCommand` gate
refuses them, and writing one with raw sqlite bypasses the gate and silently converts the lane
into a dead script).

One fleet-wide census lane, `fleet-ops-check`, runs the scanner every 12h and stays silent when
the fleet is clean.

## The census

```bash
python3 ~/.hermes/scripts/fleet_ops_check.py                 # rollup + projects needing work
python3 ~/.hermes/scripts/fleet_ops_check.py --json          # machine report
python3 ~/.hermes/scripts/fleet_ops_check.py --project X     # one project family
python3 ~/.hermes/scripts/fleet_ops_check.py --alignment     # list families with no -ops lane
```

Exit 0 = clean, 1 = a runnable project has a gap. The report groups findings by check, then lists
only P1/P2 projects; a compliant project is deliberately silent.

**Read the `kind` column before believing any finding.** Kinds are derived, not declared:

| kind | derived from | judged on |
|---|---|---|
| `service` | container/orchestration files, or a server entrypoint in the source | health, metrics, container, supervision, scheduling, backup, deploy doc |
| `cli` | `go.mod` + `cmd/`, or an executable package | deploy/install doc, release path |
| `library` | a package manifest and no entrypoint | deploy doc, CI |
| `docs` | no build manifest | nothing — a spec corpus has no uptime |
| `unresolved` | workdir does not exist | the workdir itself |

**Stand-in workdirs are the number-one false negative.** A lane row's `workdir` is often a board
holder under `~/.hermes/stand-in/` while the real repo is named by `repo_url` as `local:/path`.
The scanner resolves `repo_url` first for exactly this reason; if you write your own probe, do the
same or you will classify ten running services as docs and report them clean.

## Checks and severities

| check | severity | meaning |
|---|---|---|
| `metrics` | P1 | a service with no prometheus/otel/statsd instrumentation: it can fail invisibly |
| `health` | P1 | no readiness/liveness surface in the entrypoint |
| `backup` | P1 | the project OWNS a datastore (migrations, schema, a db file) with no backup/restore path |
| `container` | P2 | a service with no Dockerfile/compose |
| `supervision` | P2 | no systemd unit, no deploy dir — restart policy undefined |
| `scheduling` | P2 | neither an orchestrator nor a supervisor: nothing restarts it |
| `deploy-doc` | P2/P3 | no DEPLOY/RUNBOOK/OPERATIONS doc — the deploy path is tribal |
| `ci` | P3 | no CI pipeline in the repo |
| `lane-ops` | P3 | the family has no `-ops` lane (rolled up fleet-wide, never listed per project) |

A datastore is `migrations/`, `schema.sql`, `init.sql`, or an actual `*.db`/`*.duckdb` file. A
postgres *client* import is not a datastore — a service that talks to someone else's database has
nothing of its own to back up. Do not "fix" a `backup` finding by adding a backup script for data
the project does not own; correct the classification instead.

## Deploying new work to the fleet

Adding a service to the fleet has an ops half that is easy to skip. Do it in this order — the
runbook with the exact commands and pitfalls is `references/fleet-deploy-and-alignment.md`:

1. **Lane family.** `fleet_lane_align.py --project <name> --roles ops` creates or repairs the
   lane from the canonical table. Never hand-write a cooldown.
2. **Both stores.** `fleet_toml_sync.py` appends the block to `fleet.toml`. The daemon re-pins
   from that file on restart, so a lane that exists only in `scheduler.db` loses its cadence at
   the next restart, and a lane that exists only in the file does not run at all.
3. **Cadence.** `lane_cadence.py check` must pass. If the family genuinely needs a different pin,
   change it in the table once — not in the creator, not in the DB by hand.
4. **Ops surface.** Run the census for the project and file the P1s as board rows with acceptance
   criteria; do not leave them as prose in a report.
5. **Prove it live.** A deploy is not done when the process starts. Health answers, a metric
   moves, a log line lands, and the thing restarts after a kill — see
   `references/observability-minimums.md`.
6. **Watch it.** An `-ops` lane exists from that moment, so the surfaces are re-checked on a
   cadence instead of being checked once by a human who then forgets.

## Container and orchestration work

`references/containers-and-orchestration.md` covers the docker/k8s specifics: healthcheck vs
readiness, resource limits, restart policy choices, why a compose file without `restart:` is a
P2, and the fleet rule that a containerised lane must not depend on host state it cannot see.

## Anti-patterns this skill exists to stop

- **"It's deployed" without a metric.** A service nobody can see failing is not deployed; it is
  unreported. P1 by default.
- **A report instead of a row.** Findings that live in a chat message or an HTML page are lost at
  the next context window. File board rows with acceptance criteria.
- **Adding a lane family by hand.** Every family created outside `fleet_lane_align.py` has
  arrived with a hardcoded cooldown, a retired command, or `enabled=1` flipped over the daemon's
  auto-disable.
- **Judging a docs repo by service rules.** 81 of the fleet's 87 families are docs/spec repos;
  flagging them for missing metrics is how the real P1 on a service gets buried.
- **Trusting `workdir`.** Resolve `repo_url` first. Stand-in directories exist by design.
- **Ops as a one-time audit.** An audit fixes today. The lane is what keeps it fixed.

## Definition of done for an ops tick

1. Census run, exit code read (not assumed).
2. Every P1 either fixed with proof, or filed as a board row naming the evidence and the
   acceptance criteria.
3. Any lane-family defect repaired through `fleet_lane_align.py` (both stores), never by hand.
4. The next tick's census shows the finding gone or the row linked — no silent re-reporting of
   the same item tick after tick.
