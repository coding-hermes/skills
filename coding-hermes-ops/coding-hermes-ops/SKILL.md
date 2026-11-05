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

One fleet-wide lane, `fleet-ops-check`, reviews the whole census every 12h in a PROMPT session —
it reads the findings, decides which are real, and files rows. It is not a command lane: the four
utility command lanes are a fixed set of deterministic fixers, and judgement does not belong in
one of those. Each project's own `-ops` lane runs the census scoped to itself.

## The census

```bash
python3 ~/.hermes/scripts/fleet_ops_check.py                 # rollup + projects needing work
python3 ~/.hermes/scripts/fleet_ops_check.py --json          # machine report
python3 ~/.hermes/scripts/fleet_ops_check.py --project X     # one project family
python3 ~/.hermes/scripts/fleet_ops_check.py --alignment     # list families with no -ops lane
```

Exit 0 = clean, 1 = a runnable project has a gap. The report groups findings by check, then lists
only P1/P2 projects; a compliant project is deliberately silent.

**Read the `--json` shape before you filter it.** A per-project element is
`{family, kind, workdir, gaps[], lanes[], evidence{}}` and each gap is `{check, detail, severity}`.
There is no `.project` and no `.findings[]`, so a jq filter written against those names answers
`{"project": null, "findings": []}` — which reads exactly like a clean census. When a `--json`
probe comes back empty, print `.[0] | keys` and re-filter; an empty list from a guessed field path
is a lookup error, never evidence that the family is clean.

**Read the `kind` column before believing any finding.** Kinds are derived, not declared:

| kind | derived from | judged on |
|---|---|---|
| `service` | container/orchestration files, or a server entrypoint in the source | health, metrics, container, supervision, scheduling, backup, deploy doc |
| `cli` | `go.mod` + `cmd/`, or an executable package | deploy/install doc, release path |
| `library` | a package manifest and no entrypoint | deploy doc, CI |
| `docs` | no build manifest | nothing — correct for a spec corpus, a FALSE NEGATIVE for a shell toolkit (below) |
| `unresolved` | workdir does not exist | the workdir itself |

**Stand-in workdirs are the number-one false negative.** A lane row's `workdir` is often a board
holder under `~/.hermes/stand-in/` while the real repo is named by `repo_url` as `local:/path`.
The scanner resolves `repo_url` first for exactly this reason; if you write your own probe, do the
same or you will classify ten running services as docs and report them clean.

**The other false negative is the shell toolkit.** `docs` is derived purely from the absence of a
language manifest (`go.mod`, `package.json`, `pyproject.toml`, `setup.py`, `Cargo.toml`,
`requirements.txt`), so a repo that ships only `scripts/*.sh` — a node provisioner, an installer, an
operator CLI — classifies as `docs` and is judged on NOTHING, not even the deploy doc it usually
already has. Before accepting a clean `docs` verdict, count the family's scripts: two or more
executable `*.sh` under `scripts/`/`bin/` (or a `tests/selftest.sh` gate) means it is a toolkit and
its whole operational surface is unwatched.

**That hole is closed in the shipped classifier — check for the fix before re-filing the class.**
`classify()` derives a shell toolkit: at least two TRACKED `*.sh` under `scripts/` or `bin/` (depth
≤3), or a `tests/selftest.sh` gate, returns `cli` with `evidence.kind_basis = 'shell-toolkit:<n>'`
naming the script count. So a manifest-less repo that still reads `docs` while shipping scripts means
the LIVE script lost the patch — re-apply `patches/fleet-ops-shell-toolkit.patch` from the
code-factory repo (the versioned copy of an unversioned file) instead of minting a second P2 for the
same class. Read `kind_basis` beside `kind`: it is the basis the verdict was derived from. Probe,
from the repository root:

```bash
python3 ~/.hermes/scripts/fleet_ops_check.py --project <family> --json | jq -r '.[0].kind'
find <workdir>/scripts <workdir>/bin -maxdepth 2 -name '*.sh' -type f | wc -l
```

**The third is `library` on a repo whose services are standalone scripts.** A Python package
manifest plus no `cmd/` classifies as `library`, so a project that runs three long-lived units from
`scripts/<name>_server.py`-style entrypoints is judged only on deploy-doc/CI while its health,
metrics and supervision go unwatched. Never accept a `library` verdict without asking what the host
is actually running from that tree — the listeners are the ground truth, not the manifest:

```bash
ss -ltnp 2>/dev/null | grep -E ':(9092|9093|9391) '          # who is up, and from which pid
for p in $(pgrep -f '<workdir>/scripts/'); do tr '\0' ' ' < /proc/$p/cmdline; echo; done
```

A listener whose `/proc/<pid>/cmdline` names the repo's own script disproves `library`; file the
kind-detection P2 with the pid/cmdline evidence and, until it is fixed, judge the family on the
`service` row set by hand — a clean rc=0 on a family with live listeners is the same lie as a
`docs` pass on a toolkit.

Census the class fleet-wide (the same `--json` run over every family) before filing: it is ONE
classifier hole with many victims, so the row quotes how many families sit in it — including the
scanner's own family when its workdir holds the scripts.

### Editing the census (or any unversioned fleet script) without losing history

`~/.hermes/scripts/` is not a git repository, so an in-place fix there has no history and no rollback.
A live script is still fixable — it just has to be made auditable in the same tick:

1. Prove no live writer before editing: `ps -eo pid,etime,args | grep '<script>' | grep -v grep`
   empty, plus the file's mtime. A script modified minutes before your tick is a concurrent writer —
   file the row instead of editing.
2. Copy the pristine file into tick scratch and record its sha256: that copy is both the diff base
   and the only way back.
3. Make the edit, then capture it in a versioned repo:
   `diff -u --label a/<file> --label b/<file> <pristine> <live> > <repo>/patches/<name>.patch`.
4. Prove the patch BOTH ways and quote both results: forward onto the pristine copy in a temp dir
   (`git apply --check`), and — durably, since it keeps working after the edit — reverse onto the
   LIVE patched file (`cd <script dir> && git apply --check --reverse <patch>`), which succeeds only
   when the live file equals the patched version.
5. Ship the regression arms next to the patch (`<repo>/patches/<name>.test.py`, target path as
   `argv[1]` defaulting to the live script). A repo whose gate cannot import a file outside the tree
   has nowhere else to put them, and the arms are what keep a silent regression from reading as a
   clean census.

## Checks and severities

| check | severity | meaning |
|---|---|---|
| `metrics` | P1 | a service with no prometheus/otel/statsd instrumentation: it can fail invisibly |
| `health` | P1 | no readiness/liveness surface in the entrypoint |
| `backup` | P1 | the project OWNS a datastore (migrations, schema, a db file) with no backup/restore path |
| `container` | P2 | a service with no Dockerfile/compose |
| `supervision` | P2 | no systemd unit, no deploy dir — restart policy undefined |
| `scheduling` | P2 | neither an orchestrator nor a supervisor: nothing restarts it |
| `deploy-doc` | P2/P3 | no DEPLOY/RUNBOOK/OPERATIONS doc — the deploy path is tribal; matched case-insensitively, so `docs/OPERATIONS.md` counts (a `deploy-doc` gap on a repo that HAS the doc means the live script predates the `exists_ci` fix) |
| `ci` | P3 | no CI pipeline in the repo |
| `lane-ops` | P3 | the family has no `-ops` lane (rolled up fleet-wide, never listed per project) |

A datastore is `migrations/`, `schema.sql`, `init.sql`, or an actual `*.db`/`*.duckdb` file. A
postgres *client* import is not a datastore — a service that talks to someone else's database has
nothing of its own to back up. Do not "fix" a `backup` finding by adding a backup script for data
the project does not own; correct the classification instead.

## Reconciling census findings before you file

The census is a lead generator, not a verdict list — every finding is a heuristic over the tree.
Classify each one before it becomes a board row, because a phantom P1 buries the real one and
comes back on every tick.

- **`backup` is the known false-positive class.** `owns_store` matches `migrations`, `schema.sql`
  and `init.sql` as a path component ANYWHERE under the root, so it fires on
  `.coding-hermes/board/schema.sql` — the foreman board's own schema — for every project that has
  a board. The canonical board is git-tracked JSONL, so there is nothing to back up.  Prove the hit (locate the path with `search_files (target='files')`, then `git ls-files <path>`),
  then refute the finding in the report and in any row
  you file. Never "fix" it by writing a backup script for data the project does not own.
- **A `*.db` in the repo root is not a datastore until a reader proves it.** Root-level
  `memory.db` / `dev.db` / `tasks.db` are often gitignored dev residue: `grep -rn '<name>'
  <source dirs>` returning zero hits plus `git check-ignore <path>` proves it. The action is then
  "delete the residue and note it in the ops doc", not "add a backup path".
- **A finding the project's kind cannot action is a refutation.** `container` on a PyPI/CLI
  deliverable, and `supervision`/`scheduling` on a viewer nobody deploys, would have the lane ask
  for a Dockerfile on a library. Refute them in the reconciliation and point at the row that owns
  the real decision.
- **A P1 row is only executable if its cited authority is committed.** When a row names a spec or
  doc section as design authority, run `git ls-files <doc>` first: an UNTRACKED design authority
  is itself the finding — land it in its own commit inside the same tick, or the row cannot be run
  once the working tree is cleaned.
- **File one row per genuine gap**, with acceptance criteria the next tick can execute verbatim
  (a path that must exist, a `grep -c` with its expected count, a deletion that must report
  "No such file").

## Stand-in workdirs: resolve the real root, never "repair" the lane

An ops/pm lane's `workdir` is often `~/.hermes/stand-in/<role>/<project>` — not a git root, so the
foreman identity gate fails there by design. Resolve instead of standing down:
`readlink -f <standin>/.coding-hermes/board` usually names `<real-repo>/.coding-hermes/board`, and
the family's `-foreman` row in `scheduler.db` carries the registered `workdir`/`repo_url`. Run the
identity gate at that registered root, record both paths in the receipt, and leave the lane row
alone — a stand-in that mirrors a sibling role is a convention, not a defect, and
`fleet_lane_align.py` repairs cadence/command only (it will not re-point `repo_url`/`workdir` on
an existing lane, so a hand edit would be the only way and is not worth it).

**But measure the board before you call such a lane healthy.** Stand-in directories are created per
LANE, and most of them never get a board of their own: count `.coding-hermes` directories under
`~/.hermes/stand-in` against `tasks.jsonl` files inside them and the ratio is roughly 7:1 boardless
(377 directories, 53 boards on a mature fleet). A lane whose workdir holds no board is **board-blind**:
the scheduler's pending count at that path reads nothing, so admission cannot gate on work and the lane
fires on the clock forever. Grep the scheduler journal for `board-unreadable` before believing a family
is idle rather than merely unreadable, and treat a board-blind lane that still commits as productive by
accident, not by design.

The same directory also makes the lane **context-blind**: relative paths, `git`, and AGENTS.md/specs
discovery all resolve inside the scratch dir, so the lane only finds its project because the prompt
spells the absolute path out. Cost is real too — 6-7 GB and 150k+ files accumulate there.

The sanctioned forward shape (needs an owner decision, not an ops tick): give every lane the family
repo as its workdir, or a PERSISTENT per-lane worktree (`proj-wt-<project>-<role>` on branch
`lane/<project>/<role>`) refreshed before each tick, with evidence under
`.coding-hermes/evidence/<lane>/`. Persistent, not ephemeral per tick: a fresh worktree inherits no
gitignored files (`.venv`, `node_modules`, build caches), so an ephemeral tree repays the dependency
install on every tick — which is how a "clean isolation" change saturates the host it was meant to
protect.

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

## A clean census is not an uptime check

The census judges ARTIFACTS in the tree. It never asks whether the family's own lanes are running,
so a family can score rc=0 while every lane is dark — and an ops lane that stops at the rollup has
answered the wrong question. Add the uptime leg after the census, every tick:

- **Per-lane last-ok and failure class**, from the scheduler: one single-project GET per lane
  (`/api/v1/projects/<lane>`) or `ticks` in `~/.hermes/coding-hermes/scheduler.db`. A family where most
  lanes have no completed tick in the last day is a **P1 ops finding** even when every artifact check
  passes.
- **Group failures by CLASS, not by lane.** Twelve lanes failing on one error string is one outage
  with one owner, not twelve project defects. The class name is usually inside the error, but do NOT
  select the full column first: `ticks.error` embeds the router's entire decision document (matrix,
  ladder, deadline block, `_router_headers`) — several kilobytes per row — so a `select error` over
  twenty lanes dumps tens of kilobytes into the transcript and gets truncated before you can read it.
  Classify with a bounded projection in ONE query, then read one full error only when the class is
  still unknown:

  ```bash
  sqlite3 -json ~/.hermes/coding-hermes/scheduler.db "select project_name, id, status, outcome,
    spawned_at, completed_at, substr(error,1,90) as err_head
    from ticks where project_name like '<family>%' order by spawned_at desc limit 20"
  ```

  The same one query replaces N single-project GETs for the per-lane leg; keep the GET only when you
  need `latest_tick` fields the table does not carry.
- **Test the tempting mitigation before recommending it.** "Pin the lanes", "raise the cooldown",
  "disable the lane" are hypotheses: split the fleet (pinned vs unpinned, before vs after) and quote
  both sides. A mitigation that does not move the split is noise in the report.
- **Dedupe against the OWNING board before filing.** Fleet-wide outage classes are usually already
  pending on the board of the component that owns them (router/complexity → task-router; admission,
  cooldown, auto-disable → the scheduler; key/balance → the provider row). Search that board for the
  class keywords first. If it is filed, contribute a stronger fixture to that row — a family-level
  view, exact counts, a re-runnable probe — instead of minting a second id: that is liveness
  confirmation, and a second row splits the closure.
- **Write the lane evidence outside the repo.** An ops lane's registered workdir is often the project
  checkout itself; write `<lane>-<date>-evidence.md` into the family staging dir
  (`~/.hermes/stand-in/<family>-lane/`) and keep the repo untouched while siblings share it.

Query recipes, the census shape and the attribution table: `references/lane-uptime-and-outage-triage.md`.

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
- **Reading `rc=0` as "the family is fine".** rc follows the checks; a misclassified family has no
  checks to run. Read the `kind`, then read the family's uptime.
- **Filing one fleet-wide outage on every project board.** One class, one row, on the board of the
  component that owns it. Project boards get the fixture, not the id.
- **A lane-config field that every sibling lane shares.** Before filing "lane X is missing field F",
  census F across the family's own scheduler rows: `sqlite3 -json … "select name,parent,enabled,
  admission_mode from projects where name like '%-ops'"`. When the majority of peers carry the same
  empty/default value (`parent=""` on every `<family>-ops` lane, for instance), that is the deploy
  path's convention, not a per-lane defect — filing it splits a class that belongs to whoever owns
  the loader, and the next tick re-files it. Report it as a convention observation, or file nothing.

## A re-fired ops tick implements the row its first run filed

An ops tick is one-shot work under a fixed tick id, and the scheduler can re-fire the same id after
the first execution is killed mid-tick. Prove whether this tick already ran from the surfaces that
carry the id, in this order:

1. **The lane evidence file.** `grep -rl '<tick-id>' ~/.hermes/stand-in | head` finds
   `<family>-lane/<lane>-<date>-evidence.md`; its closeout section names the row the first pass
   filed, the commit, the verdict dir and the memory record id.
2. **The filed row's own `reasoning`.** First-pass rows quote their own tick id
   (`… measured by the <lane> tick <tick-id>`). Slurp the board — an unslurped filter runs once per
   input line and cannot index a row:
   `jq -s -r '.[]|select(((.reasoning//"")|tostring)|contains("<tick-id>"))|.id' <board>/tasks.jsonl`
3. **The DuckBrain record the evidence names.** `jq -r '.key, (.embedding_text // .content // "")' <file>`.

Then split the result: work the earlier pass CLOSED gets verified plus an addendum, never
re-implemented or re-judged; work it merely FILED — a still-pending row naming this tick id — is THIS
execution's task: implement that row additively on the published tip and do not re-do the commits
already pushed.

**Neither the board event log nor the tick's own scheduler row can prove absence.** A board whose
writer stores a minimal `{"status":"complete"}` detail answers empty to
`jq -r 'select((.detail // "")|tostring|contains("<tick-id>"))|.id' <board>/events.jsonl` even when
the first pass filed the row, published its verdict bundle and pushed — and an empty hit reads
exactly like "no prior execution". Likewise a re-fired tick still shows `status=running` with
`last_tick_completed` empty after a first pass that landed commits. Use both only to CORROBORATE a
filing you already found by row id, never to conclude the tick is fresh. Never attribute a tick with
`sqlite3 ~/.hermes/state.db "… where content like '%<tick-id>%'"`: that scan over the message table
times out, and a timeout reads as "no prior execution".

A memory key alone may not be enough to detect your own receipt: `/…/<date>`-scoped keys replace
each other and the content of an earlier pass can name only the date. **Put the tick id in the
CONTENT of every receipt you write**, and when you supersede, name the prior record id — otherwise
the next execution of a re-fired tick cannot prove it already ran from the ledger, and re-derives
(or worse, duplicates) the whole filing.

## Definition of done for an ops tick

1. Census run, exit code read (not assumed) — and the `kind` read too: a `docs` verdict on a shell
   toolkit is a finding, not a pass.
2. Lane uptime read for the family: every lane's last completed tick age and its failure class
   quoted. A dark lane set is a P1, filed or linked to the owning row.
3. Every P1 either fixed with proof, or filed as a board row naming the evidence and the
   acceptance criteria.
4. Any lane-family defect repaired through `fleet_lane_align.py` (both stores), never by hand.
5. The next tick's census shows the finding gone or the row linked — no silent re-reporting of
   the same item tick after tick.
