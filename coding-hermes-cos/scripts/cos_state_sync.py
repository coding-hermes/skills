#!/usr/bin/env python3
"""COS source-of-truth sync: kanban.db + scheduler.db + boards -> DuckBrain `cos` namespace.

Declared tables (SUPA-6, namespace `cos`):
  projects          - one row per FAMILY (lanes grouped by workdir)
  initiatives       - one row per kanban task (initiative card)
  initiative_events - append-only reconcile audit trail

Usage:
  cos_state_sync.py             # full sync (projects + initiatives + reconcile event)
  cos_state_sync.py --verify    # read back counts and print them

Upsert rule: PATCH ?pk=eq.<id> first; POST only when updated=0 (insert-only store).
"""
import hashlib
import json
import os
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCHED_DB = os.path.expanduser("~/.hermes/coding-hermes/scheduler.db")
KANBAN_DB = os.path.expanduser("~/.hermes/kanban.db")
TOKEN_FILE = os.path.expanduser("~/.duckbrain/cos-sync.token")
BASE = "http://127.0.0.1:3000/api/ns/cos/tables"
NS = "cos"

KANBAN_OPEN = ("triage", "ready", "in_progress", "blocked", "review", "parked")
BOARD_CLOSED = {"complete", "completed", "done", "closed", "cancelled", "canceled", "superseded"}


def token():
    with open(TOKEN_FILE) as f:
        return f.read().strip()


def req(method, path, body=None):
    r = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-API-Key": token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            data = resp.read()
            return resp.status, json.loads(data) if data else {}
    except urllib.error.HTTPError as e:
        if e.code == 429:  # rate limited: honor retryAfter, bounded retries
            delay = 1.5
            for _ in range(5):
                time.sleep(delay)
                try:
                    with urllib.request.urlopen(r, timeout=30) as resp:
                        data = resp.read()
                        return resp.status, json.loads(data) if data else {}
                except urllib.error.HTTPError as e2:
                    if e2.code != 429:
                        return e2.code, e2.read().decode()[:300]
                    delay *= 1.5
            return 429, "rate limited after retries"
        return e.code, e.read().decode()[:300]


def upsert(table, pk_col, pk_val, row):
    """PATCH by pk; insert when the row does not exist yet.
    Robust against the store's burst rate-limiting: a PATCH that fails for a
    non-404 reason (e.g. 429 slipping through, 5xx) is retried before the POST
    fallback, and a POST 409 (row exists after all) re-patches instead of dying
    — the sync must survive 599-row bursts, not crash on the 300th row."""
    for attempt in range(3):
        code, data = req("PATCH", f"/{table}?pk=eq.{pk_val}", row)
        if code == 200 and isinstance(data, dict) and data.get("updated", 0) > 0:
            return "patched"
        if code == 429:
            time.sleep(2.0 * (attempt + 1))
            continue
        if code in (500, 502, 503):
            time.sleep(1.5 * (attempt + 1))
            continue
        break
    time.sleep(0.05)
    code, data = req("POST", f"/{table}", row)
    if code in (200, 201):
        return "inserted"
    if code == 409:
        # row exists (PATCH missed or raced) — one final PATCH attempt
        code, data = req("PATCH", f"/{table}?pk=eq.{pk_val}", row)
        if code == 200:
            return "patched-after-409"
    raise RuntimeError(f"insert {table}/{pk_val} -> {code}: {data}")


def iso(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def now_iso():
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def board_families():
    """Group scheduler lanes into families by workdir (fleet law: family = one board)."""
    con = sqlite3.connect(f"file:{SCHED_DB}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT name, admission_mode, enabled, workdir FROM projects").fetchall()
    con.close()
    fams = {}
    for name, admission, enabled, workdir in rows:
        wd = (workdir or "").rstrip("/")
        key = wd or f"no-workdir:{name}"
        f = fams.setdefault(key, {
            "workdir": wd or None, "lanes": [], "admission_modes": set(), "enabled": 0,
            "active_foreman": False, "has_foreman": False})
        f["lanes"].append(name)
        if admission:
            f["admission_modes"].add(admission)
        if enabled:
            f["enabled"] += 1
        # the operator 2026-11-16: the COS's default focus is ACTIVE FOREMEN, but
        # non-foreman projects are a legitimate category (more are coming) —
        # a family WITHOUT a foreman lane is recorded as 'no-foreman', not as
        # broken. Only a family whose foreman lane EXISTS but is disabled is
        # 'foreman-off' (a recoverable state, deep scan returns on enable).
        if name.endswith("-foreman"):
            f["has_foreman"] = True
            if enabled:
                f["active_foreman"] = True
    return fams


def family_rows():
    out = []
    fams = board_families()
    now = time.time()
    # pre-pass: assign family names. Within a basename collision group the
    # canonical repo workdir (outside ~/.hermes stand-in/sync dirs, shortest
    # path) wins the plain name; the rest get a hash-suffixed name.
    from collections import defaultdict
    from collections import Counter
    groups = defaultdict(list)
    for k in fams:
        base = os.path.basename(k) if k and not k.startswith("no-workdir:") else \
            k.replace("no-workdir:", "")
        groups[base].append(k)
    name_for = {}
    for base, keys in groups.items():
        def rank(k):
            internal = k.startswith(os.path.expanduser("~/.hermes/"))
            return (1 if internal else 0, len(k), k)
        ordered = sorted(keys, key=rank)
        for i, k in enumerate(ordered):
            if i == 0:
                name_for[k] = base
            else:
                name_for[k] = f"{base}-{hashlib.sha1(k.encode()).hexdigest()[:8]}"
    for key, f in sorted(fams.items()):
        board = Path(f["workdir"]) / ".coding-hermes" / "board" / "tasks.jsonl" if f["workdir"] else None
        board_path = str(board) if board else None
        open_rows = 0
        last_activity = 0.0
        # Focus law (the operator 2026-11-16): deep scan = active foreman. Three cases:
        #   active foreman            -> full depth (board parse + tick recency)
        #   foreman lane disabled     -> cheap row, status='foreman-off' (recoverable)
        #   NO foreman lane (legit)   -> cheap row, status='no-foreman'; mtime-only
        #                                activity (a stat, not a parse) so the
        #                                project still shows fresh vs stale
        if not f.get("active_foreman"):
            cheap_status = "foreman-off" if f.get("has_foreman") else "no-foreman"
            last_mod = None
            if board and board.exists():
                try:
                    last_mod = board.stat().st_mtime
                except OSError:
                    last_mod = None
            out.append({
                "project": name_for[key],
                "kind": ",".join(sorted(f["admission_modes"]) or ["prompt"]),
                "status": cheap_status,
                "admission_mode": (sorted(f["admission_modes"]) or ["prompt"])[0],
                "workdir": f["workdir"],
                "board_path": board_path,
                "lane_count": len(f["lanes"]),
                "lanes": sorted(f["lanes"]),
                "open_rows": None,
                "last_activity_at": iso(last_mod) if last_mod else None,
                "updated_at": now_iso(),
            })
            continue
        if board and board.exists():
            last_activity = board.stat().st_mtime
            try:
                for line in board.read_text().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    st = str(row.get("status", "")).lower()
                    if st and st not in BOARD_CLOSED:
                        open_rows += 1
            except OSError:
                pass
        # scheduler tick recency for these lanes (string-typed ISO col; LIKE both forms)
        try:
            con = sqlite3.connect(f"file:{SCHED_DB}?mode=ro", uri=True)
            lanes = f["lanes"]
            q = ("SELECT MAX(created_at) FROM ticks WHERE project_name IN (%s)"
                 % ",".join("?" * len(lanes)))
            v = con.execute(q, lanes).fetchone()[0]
            con.close()
            if v:
                try:
                    t = datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
                    last_activity = max(last_activity, t)
                except ValueError:
                    pass
        except sqlite3.Error:
            pass
        age_h = (now - last_activity) / 3600 if last_activity else None
        status = "unknown" if age_h is None else (
            "active" if age_h < 48 else "idle" if age_h < 24 * 14 else "stale")
        # kind: from admission_mode of the family's foreman lane + suffix census
        kinds = sorted(f["admission_modes"]) or ["prompt"]
        suffixes = sorted({ln.rsplit("-", 1)[-1] for ln in f["lanes"] if "-" in ln})[:8]
        fam_name = name_for[key]

        out.append({
            "project": fam_name,
            "kind": ",".join(kinds),
            "status": status,
            "admission_mode": kinds[0],
            "workdir": f["workdir"],
            "board_path": board_path,
            "lane_count": len(f["lanes"]),
            "lanes": sorted(f["lanes"]),
            "open_rows": open_rows,
            "last_activity_at": iso(last_activity) if last_activity else None,
            "updated_at": now_iso(),
        })
    return out


def kanban_db_paths():
    """Every kanban source: one DB per board plus the legacy shared DB."""
    boards = Path(os.path.expanduser("~/.hermes/kanban/boards"))
    found = sorted(p for p in boards.glob("*/kanban.db")) if boards.is_dir() else []
    return [(p.parent.name, p) for p in found] + [("default", Path(KANBAN_DB))]


def kanban_initiatives():
    out = []
    for board, db_path in kanban_db_paths():
        if not db_path.exists():
            continue
        out.extend(_board_initiatives(board, db_path))
    return out


def _board_initiatives(board, db_path):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    tasks = [dict(r) for r in con.execute(
        "SELECT id, title, body, assignee, status, priority, created_at,"
        " completed_at, consecutive_failures, last_failure_error,"
        " current_run_id, branch_name, workspace_path, result FROM tasks").fetchall()]
    links = {}
    for r in con.execute("SELECT parent_id, child_id FROM task_links").fetchall():
        links.setdefault(r["parent_id"] if "parent_id" in r.keys() else r[0], []).append(
            r["child_id"] if "child_id" in r.keys() else r[1])
    con.close()
    out = []
    for t in tasks:
        tid = t["id"]
        ev = {}
        if t.get("current_run_id"):
            ev["current_run_id"] = t["current_run_id"]
        if t.get("branch_name"):
            ev["branch"] = t["branch_name"]
        if t.get("workspace_path"):
            ev["workspace"] = t["workspace_path"]
        if t.get("result"):
            ev["result"] = str(t["result"])[:500]
        # project: leading [tag] in the title, else null (COS reconcile fills it)
        project = None
        title = t["title"] or ""
        if title.startswith("[") and "]" in title:
            project = title[1:title.index("]")]
        out.append({
            "initiative_id": tid,
            "title": title,
            "project": project,
            "status": t["status"],
            "priority": t["priority"] or 0,
            "body": (t["body"] or "")[:8000],
            "child_ids": links.get(tid, []),
            "blocker": t.get("last_failure_error"),
            "consecutive_failures": t.get("consecutive_failures") or 0,
            "evidence": ev,
            "assignee": t.get("assignee"),
            "created_at": iso(t["created_at"]),
            "updated_at": now_iso(),
            "closed_at": iso(t["completed_at"]),
        })
    return out


def sync():
    counts = {}
    for row in family_rows():
        counts["projects"] = counts.get("projects", 0) + 1
        upsert("projects", "project", row["project"], row)
    for row in kanban_initiatives():
        counts["initiatives"] = counts.get("initiatives", 0) + 1
        upsert("initiatives", "initiative_id", row["initiative_id"], row)
    event = {
        "event_id": f"reconcile-{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "initiative_id": None,
        "ts": now_iso(),
        "kind": "reconcile",
        "detail": {"projects": counts.get("projects", 0),
                   "initiatives": counts.get("initiatives", 0)},
        "actor": "cos_state_sync.py",
    }
    req("POST", "/initiative_events", event)
    return counts


def verify():
    for t in ("projects", "initiatives", "initiative_events"):
        code, data, total = req2("GET", f"/{t}?count=exact&limit=1")
        print(f"{t}: {total} rows (http {code})")


def req2(method, path, body=None):
    """Same as req() but also returns the X-Total-Count header."""
    r = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-API-Key": token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            data = resp.read()
            return resp.status, json.loads(data) if data else {}, resp.headers.get("X-Total-Count")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300], None


if __name__ == "__main__":
    if "--verify" in sys.argv:
        verify()
    else:
        print(json.dumps(sync()))
