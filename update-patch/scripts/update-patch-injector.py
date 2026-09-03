#!/usr/bin/env python3
"""
update-patch-injector.py — 'update-and-patch' weekly board-injection lane
=========================================================================
Deterministic cron lane (NO LLM, NO dagger). Every run appends ONE open board
task row (UPD-<YYYYMMDD>-<project>) to each ENABLED scheduler project whose
workdir carries a JSONL-canonical board (.coding-hermes/board/tasks.jsonl),
then git-commits the board file per repo. The per-project foreman executes the
row on its next tick, multi-step — the owner's cron-injects-board-rows
doctrine (safer than building a new DAGger pipeline per lane).

Design decisions (all deterministic, stdlib-only):
- Project enumeration: GET {API_BASE}/api/v1/projects (Bearer API_SERVER_KEY
  from ~/.hermes/.env). Retry ONLY on connection-class errors, up to 3
  attempts with 60s backoff between attempts (mandate). Any final API failure
  (connection or HTTP) falls back to READ-ONLY sqlite on
  ~/.hermes/coding-hermes/scheduler.db (SELECT name, workdir, enabled FROM
  projects WHERE enabled=1). Env test knobs: UPDATE_PATCH_API_BASE (default
  http://localhost:9090), UPDATE_PATCH_BACKOFF_S (default 60).
- Row shape: APPEND-ONLY, deep-copy of the board's LAST tasks.jsonl row
  (guarantees the board's own canonical key set + serialization style —
  compact vs spaced, ensure_ascii on/off), then override lifecycle/provenance
  fields. NEVER rewrite the file; never touch board.db/parquet (untracked
  caches; JSONL is authoritative — ref coding-hermes-jsonl-board-append).
- 'detail' adaptation: the mandated task row carries a long directive TITLE
  and a multi-step note. Scheduler-family boards (schema.sql tasks table, e.g.
  my-project/muster) have NO 'detail' column — 31 canonical keys — and
  my-project enforces key-set uniformity (MP-GAP-015 task_keys_uniform), so a
  stray 'detail' key would corrupt the board. Therefore the multi-step note is
  written to the row's 'reasoning' field (and to 'detail' ONLY on boards whose
  last row actually carries a 'detail' key, e.g. legacy dagger-era rows).
- id: UPD-<YYYYMMDD>-<project> with the date in UTC (fleet/scheduler
  convention; at UTC-05 a run between 00:00-04:59 local carries the next UTC
  date). Project name verbatim from the scheduler (e.g. UPD-20260903-my-project).
- status: board's open-state convention detected from existing rows
  (pending/in_progress/todo/open — pick most frequent, tie-break in that
  order; fallback 'pending'); worker_status mirrored the same way. Closed set
  (complete/done/closed/cancelled/canceled) never counts as open.
- Idempotency: skip a project if it already carries an open row whose id
  starts with 'UPD-' (parsed-id match, not substring — consensus tick #295
  class). Closed UPD-* rows do NOT block a new weekly row.
- priority P2 / complexity 3 (fleet DEPS-audit precedent: P2 for deps),
  capability_tags ['deps','patch','audit'] where the key exists.
- Commit: git -C <workdir> add -- .coding-hermes/board/tasks.jsonl ONLY, then
  commit --no-verify with author/committer 'totalwindupflightsystems
  <totalwindupflightsystems@gmail.com>' and a body trailer taken from the
  $UPDATE_PATCH_CO_AUTHOR env var (deployments set it to the fleet co-author;
  the public copy ships empty = no trailer). NO push (local commit; foreman
  ticks push; several projects have no remote). Non-git workdirs are logged
  as errors and skipped.
- Log: one summary line appended to
  ~/.hermes/cron/output/update-patch-injector.log (live runs only; --dry-run
  writes nothing anywhere).

Namespace registration (schema-safety investigation, 2026-09-02):
A scheduler namespace row 'update-and-patch' was investigated and created
additively in the scheduler sqlite (namespaces table):
  INSERT INTO namespaces (id, weight, reserved, hard_cap, enabled,
    description, created_at, updated_at, default_prompt, max_concurrent,
    model_chain) VALUES ('update-and-patch', 5, 0, 20, 1, 'Weekly update &
    patch board-injection lane (deterministic cron, no dagger) — UPD-* rows',
    <utc>, <utc>, '', 1, '');
Why this is schema-safe (not risky):
- namespaces has no triggers and no CHECK constraints; id is the only unique
  key (sqlite_autoindex_namespaces_1); there is no FK FROM namespaces.
- Inbound FKs (projects.namespace_id, namespace_ticks.namespace_id) are both
  NO ACTION toward namespaces.id — an added row cannot invalidate existing
  references; nothing references the new id until something opts in.
- The scheduler reads namespaces generically (GET /api/v1/namespaces mirrors
  the table, incl. default_prompt/model_chain columns) and only schedules
  ticks for projects grouped under a namespace — 'update-and-patch' has zero
  projects, so no ticks can spawn from it (namespace_ticks allocation rows
  for it would simply read allocated=0, like the dormant backup/duckbrain-
  infra namespaces).
- House precedent: pm (2026-09-01) and qa (2026-09-01) namespace rows were
  inserted ad hoc with no migrations-table entry; migrations 17-21 cover DDL
  only. A row insert is not a schema migration.
Usage: python3 update-patch-injector.py [--dry-run] [--project NAME ...]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request

def _hermes_home() -> str:
    """$HERMES_HOME, else ~/.hermes — portable; no absolute paths in this file."""
    return os.environ.get("HERMES_HOME") or os.path.join(
        os.path.expanduser("~"), ".hermes")


_HERMES_HOME = _hermes_home()
ENV_FILE = os.path.join(_HERMES_HOME, ".env")
SCHEDULER_DB = os.path.join(_HERMES_HOME, "coding-hermes", "scheduler.db")
LOG_FILE = os.path.join(_HERMES_HOME, "cron", "output",
                        "update-patch-injector.log")
DEFAULT_API_BASE = "http://localhost:9090"

TITLE = ("Weekly package update & patch audit: check deps for outdated/"
         "vulnerable versions, bump + patch as needed, run tests, commit "
         "small steps")
PRIORITY = "P2"
COMPLEXITY = 3
CAPABILITY_TAGS = ["deps", "patch", "audit"]

AUTHOR_NAME = "totalwindupflightsystems"
AUTHOR_EMAIL = "totalwindupflightsystems@gmail.com"
# Trailer for the board commits; deployments set UPDATE_PATCH_CO_AUTHOR to
# the fleet co-author. Public copy ships empty (no trailer) on purpose.
CO_AUTHOR = os.environ.get("UPDATE_PATCH_CO_AUTHOR", "").strip()

OPEN_STATES = ("pending", "in_progress", "todo", "open")
CLOSED_STATES = ("complete", "done", "closed", "cancelled", "canceled")


def utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def read_api_key() -> str:
    """Read API_SERVER_KEY from the Hermes env file. Never print it."""
    with open(ENV_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("API_SERVER_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def fetch_projects_api():
    """GET /api/v1/projects with retry on connection errors (3x / backoff)."""
    base = os.environ.get("UPDATE_PATCH_API_BASE", DEFAULT_API_BASE).rstrip("/")
    backoff = int(os.environ.get("UPDATE_PATCH_BACKOFF_S", "60"))
    key = read_api_key()
    url = f"{base}/api/v1/projects"
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    last_err = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            projects = payload.get("projects", payload if isinstance(payload, list) else [])
            return "api", projects
        except urllib.error.HTTPError as exc:  # non-retryable: auth/route/etc.
            return "api-error", f"HTTP {exc.code} from {url}"
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            if attempt < 3:
                print(f"[update-patch-injector] api attempt {attempt}/3 failed "
                      f"({last_err}); retrying in {backoff}s", file=sys.stderr)
                import time
                time.sleep(backoff)
    return "api-error", last_err or "unknown connection error"


def fetch_projects_sqlite():
    """Read-only fallback over the scheduler sqlite."""
    con = sqlite3.connect(f"file:{SCHEDULER_DB}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT name, workdir, enabled FROM projects ORDER BY name"
        ).fetchall()
    finally:
        con.close()
    return [{"name": n, "workdir": w, "enabled": bool(e)} for n, w, e in rows]


def fmt_like(sample: str, now: _dt.datetime) -> str:
    """Format `now` (UTC) to mirror the timestamp style of `sample`."""
    if not sample:
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")
    frac = ".%f" if re.search(r"(?<=:\d{2})\.\d+", sample) else ""
    stripped = sample.strip()
    if "T" in stripped and stripped.endswith("Z"):
        return now.strftime(f"%Y-%m-%dT%H:%M:%S{frac}Z")
    if "T" in stripped:
        out = now.strftime(f"%Y-%m-%dT%H:%M:%S{frac}")
        m = re.search(r"[+-]\d{2}:\d{2}$", stripped)
        return out + (m.group(0) if m else "")
    if " " in stripped:
        return now.strftime(f"%Y-%m-%d %H:%M:%S{frac}")
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def detect_open_state(rows) -> str:
    """Most frequent open vocabulary in the board; fallback 'pending'."""
    counts: dict[str, int] = {}
    for row in rows:
        st = (row.get("status") or "").strip().lower()
        if st in OPEN_STATES:
            counts[st] = counts.get(st, 0) + 1
    if not counts:
        return "pending"
    best = OPEN_STATES[0]
    for st in OPEN_STATES:
        if counts.get(st, 0) > counts.get(best, 0):
            best = st
    return best


def detect_open_worker_state(rows) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        st = (row.get("worker_status") or "").strip().lower()
        if st in OPEN_STATES:
            counts[st] = counts.get(st, 0) + 1
    if not counts:
        return "pending"
    best = OPEN_STATES[0]
    for st in OPEN_STATES:
        if counts.get(st, 0) > counts.get(best, 0):
            best = st
    return best


def read_rows(board_path: str):
    """Parse all non-blank JSONL lines; returns (rows, raw_lines)."""
    rows, lines = [], []
    with open(board_path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            lines.append(line)
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append(None)
    return [r for r in rows if r is not None], lines


def has_open_upd_row(rows) -> str | None:
    """Return the id of an existing OPEN UPD-* row, or None."""
    for row in rows:
        rid = row.get("id")
        if not isinstance(rid, str) or not rid.startswith("UPD-"):
            continue
        st = (row.get("status") or "").strip().lower()
        if st not in CLOSED_STATES:
            return rid
    return None


def build_row(project_name: str, rows, lines, now: _dt.datetime):
    """Deep-copy last row; override to a fresh open UPD-* task row."""
    base = dict(rows[-1])
    last_line = lines[-1]
    last_row = rows[-1]
    open_state = detect_open_state(rows)
    worker_state = detect_open_worker_state(rows)

    def ts_for(key: str) -> str:
        sample = last_row.get(key)
        return fmt_like(sample if isinstance(sample, str) else "", now)

    new_id = f"UPD-{now.strftime('%Y%m%d')}-{project_name}"
    reasoning = (
        f"Injected by update-and-patch weekly lane ({now.strftime('%Y-%m-%dT%H:%M:%SZ')} "
        "UTC). Foreman may multi-step this row: (1) audit dependencies for "
        "outdated/vulnerable versions (govulncheck / go list -u -m, npm audit, "
        "pip-audit, cargo audit, etc. per stack); (2) bump + patch in SMALL "
        "commits (one dep or one vulnerability class per commit); (3) run tests "
        "after each step; (4) commit each small step and close this row when the "
        "audit + patches are done."
    )
    base["id"] = new_id
    base["title"] = TITLE
    base["status"] = open_state
    if "priority" in base:
        base["priority"] = PRIORITY
    if "complexity" in base:
        base["complexity"] = COMPLEXITY
    if "capability_tags" in base:
        base["capability_tags"] = CAPABILITY_TAGS
    if "worker_status" in base:
        base["worker_status"] = worker_state
    if "reasoning" in base:
        base["reasoning"] = reasoning
    if "detail" in base:  # boards whose schema/rows carry a detail key
        base["detail"] = reasoning
    for key in ("dispatched_at", "completed_at", "exit_code", "commit_hash",
                "files_changed", "guard_result", "ci_result", "worker_summary",
                "blocked_reason", "review_notes", "blocked_since", "foreman_note"):
        if key in base:
            base[key] = None
    if "attempts" in base:
        base["attempts"] = 0
    if "lines_added" in base:
        base["lines_added"] = 0
    if "lines_removed" in base:
        base["lines_removed"] = 0
    if "source" in base:
        base["source"] = "update-and-patch"
    if "created_at" in base:
        base["created_at"] = ts_for("created_at")
    if "updated_at" in base:
        base["updated_at"] = ts_for("updated_at")
    if "ts" in base:
        base["ts"] = ts_for("ts")

    style = {
        "ensure_ascii": "\\u" in last_line,
        "separators": (",", ":") if ", " not in last_line else None,
    }
    return new_id, base, style


def commit_board(workdir: str, new_id: str, date_str: str) -> str:
    """git add (board file only) + commit. Returns short sha or raises."""
    env = dict(os.environ)
    env["GIT_AUTHOR_NAME"] = AUTHOR_NAME
    env["GIT_AUTHOR_EMAIL"] = AUTHOR_EMAIL
    env["GIT_COMMITTER_NAME"] = AUTHOR_NAME
    env["GIT_COMMITTER_EMAIL"] = AUTHOR_EMAIL
    board_rel = ".coding-hermes/board/tasks.jsonl"
    subprocess.run(
        ["git", "-C", workdir, "add", "--", board_rel],
        check=True, capture_output=True, text=True, env=env,
    )
    subject = f"board: inject {new_id} — weekly update & patch audit ({date_str})"
    cmd = ["git", "-C", workdir, "commit", "--no-verify", "-m", subject]
    if CO_AUTHOR:
        cmd += ["-m", f"Co-authored-by: {CO_AUTHOR}"]
    proc = subprocess.run(
        cmd, check=True, capture_output=True, text=True, env=env,
    )
    head = subprocess.run(
        ["git", "-C", workdir, "rev-parse", "--short", "HEAD"],
        check=True, capture_output=True, text=True, env=env,
    )
    return head.stdout.strip()


def append_line(path: str, line: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would be injected; write nothing")
    ap.add_argument("--project", action="append", default=[],
                    help="only process this project (repeatable)")
    args = ap.parse_args()

    now = utcnow()
    date_str = now.strftime("%Y-%m-%d")
    mode = "dry-run" if args.dry_run else "live"

    src, projects = fetch_projects_api()
    if src == "api-error":
        print(f"[update-patch-injector] API failed ({projects}); "
              "falling back to read-only sqlite", file=sys.stderr)
        projects = fetch_projects_sqlite()
        src = "sqlite-fallback"
    elif src == "api":
        src = "api"

    wanted = set(args.project)
    projects = sorted(
        (p for p in projects if p.get("enabled") and p.get("workdir")),
        key=lambda p: p["name"],
    )
    if wanted:
        projects = [p for p in projects if p["name"] in wanted]
        missing = sorted(wanted - {p["name"] for p in projects})
        if missing:
            print(f"[update-patch-injector] WARNING: requested projects not "
                  f"found/enabled: {', '.join(missing)}", file=sys.stderr)

    injected, skipped, errors = [], [], []
    for proj in projects:
        name, workdir = proj["name"], proj["workdir"]
        board_path = os.path.join(workdir, ".coding-hermes", "board", "tasks.jsonl")
        if not os.path.isfile(board_path):
            skipped.append((name, "no board tasks.jsonl"))
            continue
        try:
            rows, lines = read_rows(board_path)
            if not rows or not lines:
                skipped.append((name, "empty board (no row to mirror)"))
                continue
            existing = has_open_upd_row(rows)
            if existing:
                skipped.append((name, f"open UPD-* row exists: {existing}"))
                continue
            new_id, row, style = build_row(name, rows, lines, now)
            if args.dry_run:
                print(f"[dry-run] WOULD INJECT {new_id} -> {board_path}\n"
                      f"          status={row.get('status')!r} "
                      f"worker_status={row.get('worker_status')!r} "
                      f"priority={row.get('priority')!r} "
                      f"complexity={row.get('complexity')!r}\n"
                      f"          title={row.get('title')}")
                injected.append((name, new_id, "dry-run"))
                continue
            with open(board_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, **style) + "\n")
            # verify the append landed and parses
            with open(board_path, encoding="utf-8") as fh:
                last = [l for l in fh.read().splitlines() if l.strip()][-1]
            landed = json.loads(last)
            assert landed.get("id") == new_id, "append verification failed"
            sha = commit_board(workdir, new_id, date_str)
            print(f"[update-patch-injector] injected {new_id} @ {sha} "
                  f"({name})")
            injected.append((name, new_id, sha))
        except Exception as exc:  # per-project isolation: keep the run going
            errors.append((name, f"{type(exc).__name__}: {exc}"))
            print(f"[update-patch-injector] ERROR {name}: "
                  f"{type(exc).__name__}: {exc}", file=sys.stderr)

    summary = (f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')} update-patch-injector "
               f"mode={mode} source={src} projects={len(projects)} "
               f"injected={len(injected)} skipped={len(skipped)} "
               f"errors={len(errors)}")
    if injected:
        summary += " ids=" + ",".join(f"{i[1]}@{i[2]}" for i in injected)
    print(summary)
    if not args.dry_run:
        append_line(LOG_FILE, summary)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
