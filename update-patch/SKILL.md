---
name: update-patch
description: >-
  Use when running or maintaining the weekly update-and-patch lane that
  injects UPD-* dep-audit rows onto fleet boards. Covers the deterministic
  cron, the board-append rules, and how foremen execute the injected tasks.
version: 1.0.0
author: Hermes curator
platforms: [linux]
metadata:
  hermes:
    tags: [coding-hermes, cron, board, injection, deps, audit, scheduler, weekly]
    related_skills:
      - coding-hermes-jsonl-board-append
      - coding-hermes-scheduler
      - coding-hermes-foreman
      - coding-hermes-supervisor
    support_files:
      - scripts/update-patch-injector.py
---

# update-patch — weekly UPD-* board-injection lane

Deterministic weekly cron lane (NO LLM, NO dagger). Every run appends ONE open
board task row — `UPD-<YYYYMMDD>-<project>` — to each ENABLED scheduler
project whose workdir carries a JSONL-canonical board
(`.coding-hermes/board/tasks.jsonl`), then git-commits the board file per
repo. The per-project foreman executes the row multi-step on its next tick —
the owner's *cron-injects-board-rows* doctrine (safer than building a new
DAGger pipeline per lane). The row tells the foreman to audit dependencies,
bump + patch vulnerable/outdated packages in small commits, and run tests.

## When to use

- Registering, re-running, or debugging the weekly update-and-patch lane.
- A cron tick or foreman asks where an `UPD-*` row came from, or whether one
  may be injected.
- Maintaining the injector script or moving it between hosts.

## Where it lives and how to run it

- **Canonical copy:** this skill's `scripts/update-patch-injector.py` in the
  public `coding-hermes/skills` repo. Portable: it resolves `$HERMES_HOME`
  (default `~/.hermes`) at runtime — no absolute paths, no secrets.
- **Deployment shim:** `~/.hermes/scripts/update-patch-injector.py` is a thin
  shim that `exec`s the repo copy (falling back to the local mirror
  `~/.hermes/skills/update-patch/scripts/update-patch-injector.py`). Keep the
  shim filename stable so cron specs never break.
- **Run it:**
  ```bash
  python3 <repo>/update-patch/scripts/update-patch-injector.py --dry-run
  python3 <repo>/update-patch/scripts/update-patch-injector.py --dry-run --project my-project
  python3 ~/.hermes/scripts/update-patch-injector.py            # live (weekly)
  ```
  `--dry-run` prints what would be injected and writes NOTHING anywhere (no
  board edit, no commit, no log line).
- **Env knobs:** `UPDATE_PATCH_API_BASE` (default `http://localhost:9090`),
  `UPDATE_PATCH_BACKOFF_S` (default 60 — connection-retry sleep; lower to 1
  only for tests), `HERMES_HOME`, `UPDATE_PATCH_CO_AUTHOR` (board-commit
  trailer; the public copy ships empty = no trailer; deployments that want the
  private co-author convention set it).

## Weekly cron pattern

Register ONE deterministic job (no LLM prompt — a plain command job):

```
schedule: weekly
command:  /usr/bin/python3 ~/.hermes/scripts/update-patch-injector.py
workdir:  $HOME
```

- Every enabled scheduler project whose workdir has a board `tasks.jsonl` gets
  one row per run; projects without a board, or with an already-open `UPD-*`
  row, are skipped (idempotent — safe to re-run).
- A **closed** `UPD-*` row does NOT block the next weekly row.
- The row date is UTC (at UTC-05, a run between 00:00–04:59 local carries the
  next UTC date) — matches the fleet/scheduler convention.

## How the foreman executes injected UPD-* rows

Injected rows are ordinary open board work (same semantics as
`pm-injected-board-rows`): on its next tick the project foreman sees the open
row and executes it — do not bounce injected rows back.

Row shape: `id=UPD-<date>-<project>`, open status (board's own open-state
vocabulary), `priority=P2`, `complexity=3`,
`capability_tags=['deps','patch','audit']`, `source='update-and-patch'`, and a
multi-step directive in `reasoning` (also mirrored into `detail` only on
boards whose rows already carry a `detail` key).

Expected multi-step execution:

1. **Audit** dependencies for outdated/vulnerable versions — per stack:
   `govulncheck` / `go list -u -m all`, `npm audit`, `pip-audit`,
   `cargo audit`, etc.
2. **Bump + patch in SMALL commits** — one dependency or one vulnerability
   class per commit.
3. **Run tests after each step.**
4. **Commit each small step** and close the row when the audit + patches are
   done (normal board lifecycle; the next weekly run then injects a fresh row).

## Board-append convention it relies on

- Boards are **JSONL-canonical and git-tracked**
  (`.coding-hermes/board/tasks.jsonl`); `board.db` / `*.parquet` are untracked,
  rebuildable caches and are NEVER written by the injector.
- **Append-only deep copy of the board's LAST row** — preserves each board's
  exact canonical key set and serialization style (compact vs spaced,
  `ensure_ascii` on/off), so key-set-uniformity canaries (e.g. MP-GAP-015)
  stay green. Never rewrite the file; never write a header/`board.jsonl`
  (scheduler-family topology-B boards in `coding-hermes-jsonl-board-append`
  terms).
- Lifecycle/provenance fields are overridden; dispatched/worker result fields
  are nulled; `attempts`/line counters reset.
- Commit per repo: `git add -- .coding-hermes/board/tasks.jsonl` ONLY, then
  `commit --no-verify` with identity
  `totalwindupflightsystems <totalwindupflightsystems@gmail.com>` and a
  `Co-authored-by:` trailer only when `UPDATE_PATCH_CO_AUTHOR` is set.
  **NO push** — the local commit is pushed by the project foreman on its next
  tick (several projects have no remote at all).
- The append is verified by re-parsing the last line before committing; a
  failed project is logged and skipped without aborting the run.

## Dependencies

This skill operates on three external systems. Each must exist and be
verifiable before the lane can run (owner rule: skills declare the repos they
depend on).

### 1. `coding-hermes/scheduler` repo + running daemon (project enumeration)

- **Why:** source of truth for enabled projects + workdirs
  (`GET {API_BASE}/api/v1/projects`, Bearer `API_SERVER_KEY` from
  `~/.hermes/.env`), the namespace table, and fleet config.
- **Find it:** canonical repo `https://github.com/coding-hermes/scheduler`
  (local fleet clone under `~/coding-hermes-scheduler/…`); daemon API at
  `http://localhost:9090`; sqlite at `~/.hermes/coding-hermes/scheduler.db`;
  fleet config `~/.hermes/fleet.toml` (repo ships `fleet.example.toml`).
- **Verify:** `curl -s http://localhost:9090/api/v1/health`; or read-only
  `sqlite3 ~/.hermes/coding-hermes/scheduler.db
  "SELECT count(*) FROM projects WHERE enabled=1"`.
- **Fallback behavior:** API unreachable after 3 connection attempts (60s
  backoff) → read-only sqlite fallback (`SELECT name, workdir, enabled FROM
  projects WHERE enabled=1`). HTTP errors (4xx/5xx) are NOT retried.

### 2. JSONL-canonical board convention (injection targets)

- **Why:** the lane appends rows to each project's
  `.coding-hermes/board/tasks.jsonl` and commits that one file.
- **Find it:** inside any scheduler-enabled project workdir; conventions are
  documented by the `coding-hermes-jsonl-board-append` skill.
- **Verify:** `git -C <project-workdir> ls-files .coding-hermes/board/` shows
  `tasks.jsonl` (tracked); last line parses as JSON
  (`tail -1 …/tasks.jsonl | python3 -m json.tool >/dev/null`).

### 3. hermes-agent cron system (lane trigger)

- **Why:** fires the weekly job that runs the injector.
- **Find it:** cron job store `~/.hermes/cron/jobs.json` (job runs the
  `~/.hermes/scripts/update-patch-injector.py` shim weekly); run history in
  `~/.hermes/cron/output/update-patch-injector.log` (live runs only — one
  summary line each).
- **Verify:** the job entry exists with schedule `weekly`; the log's latest
  line shows `mode=live … errors=0` (or an explained error); the shim target
  (repo copy or local mirror) exists and `--dry-run` succeeds.

## Portability checklist (cold-agent discovery)

- [ ] No absolute paths in this skill or its script — `$HERMES_HOME` /
  `~/.hermes` resolved at runtime.
- [ ] No secrets or real names — API key is read from the env file at
  runtime; org identity only; co-author trailer via env var.
- [ ] Script is stdlib-only Python 3, deterministic, executable from any
  checkout (`python3 update-patch-injector.py --dry-run`).
- [ ] Cron spec, foreman execution steps, board-append rules, and dependency
  verification are all documented in this file alone.
- [ ] Script docstring documents row-shape, idempotency, namespace
  registration, and schema-safety rationale.

## Pitfalls

- `--dry-run` writes nothing — always run it first (and check the log mtime
  is untouched as proof).
- Default `UPDATE_PATCH_BACKOFF_S=60` makes a dead-API run take ~2 min before
  the sqlite fallback; that is intentional for production (mandate), so don't
  "fix" it — use the env knob only for one-off tests.
- The commit subject contains an em dash (`—`); keep UTF-8 intact.
- Do not rewrite a board file in place and never touch `board.db`/parquet —
  JSONL is authoritative and git-tracked.
- Do not add the co-author name into this public repo — the private trailer
  belongs in `UPDATE_PATCH_CO_AUTHOR` at the deployment layer only.
