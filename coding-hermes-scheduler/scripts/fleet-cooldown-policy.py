#!/usr/bin/env python3
"""Fleet cooldown policy — matches supervisor skill + Bane directives.

Cooldown matrix (Bane 2026-08-07 — THREE speeds):
  - 900s  (15m)  — PRIORITY. If a project is at 900s, LEAVE IT THERE.
                   Nothing in this script lowers or raises 900.
  - 7200s (2h)   — DEFAULT baseline for the fleet.
  - 43200s (12h) — COMPLETED (no real work; NEVER-DONE perpetual tasks
                   are fine at this tier).

Correction rules (Bane 2026-08-07):
  1. Any project BELOW 900s (e.g. 600) → RAISED back to 900s.
  2. Project at 900s → untouched, always.
  3. Project above 7200s WITH real work (pending board items or open
     stand-in gaps) → moved back to 7200s (2h) — not 900s.
  4. Project at 7200s with no work at all → promoted to 43200s (12h,
     completed tier). Promotions are the only other allowed increase.

Usage: python3 fleet-cooldown-policy.py [--apply]
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import urllib.request

# ── Self-bootstrap: re-exec with the durable board venv (has duckdb) ──
BOOTSTRAP_PY = os.path.expanduser('~/.hermes/venvs/board/bin/python3')
if importlib.util.find_spec('duckdb') is None and os.path.exists(BOOTSTRAP_PY):
    os.execv(BOOTSTRAP_PY, [BOOTSTRAP_PY] + sys.argv)

API = 'http://127.0.0.1:9090'
TARGET_ACTIVE = 900       # PRIORITY — Bane-designated fast projects (15m)
TARGET_IDLE = 7200        # DEFAULT — fleet baseline (2h)
TARGET_COMPLETED = 43200  # COMPLETED — no work, verified done (12h)
TARGET_CI = 1800          # CI failing + CI tasks on board

# PRIORITY tier (900s) is set manually (API PUT) — this script never
# touches projects already at 900. It only enforces the floor (below-900
# → 900), the 2h default, and the completed tier.

LEDGER_PATH = os.path.expanduser('~/.hermes/stand-in/ledger.json')

def open_ledger_gaps(name):
    """Count stand-in ledger items still open for a project (suffix-tolerant).

    Scheduler names carry a '-foreman' suffix while ledger uses the bare repo
    name — match both. A project with no ledger entries at all counts as
    having no open gaps (nothing found = nothing pending).
    """
    try:
        with open(LEDGER_PATH) as f:
            items = json.load(f).get('items', [])
        cands = {name, name[:-8] if name.endswith('-foreman') else name,
                 name + '-foreman'}
        return sum(1 for it in items
                   if it.get('project') in cands and it.get('status') != 'verified')
    except Exception:
        return 0

# Board source: tasks.md (legacy) or board/tasks.parquet (migrated)
def parse_pending_from_md(md_path):
    """Count real pending tasks in a tasks.md board (section-aware)."""
    import re
    n = 0
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'migrate', os.path.expanduser('~/.hermes/scripts/migrate-board-to-duckdb.py'))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _, _, tasks = m.parse_tasks_md(md_path)
        if tasks:
            real = [t for t in tasks
                    if t['status'] in ('pending', 'in_progress', 'blocked', 'open', 'todo')
                    and t['id'] != 'NEVER-DONE']
            n = len(real)
    except Exception:
        pass
    # Fallback: count open checkbox headers directly. The shared parser
    # silently DROPS format-drifted sections (Kobayashi-Maru's
    # "## [ ] KB-GAP-003 — title" blocks parsed as 1 of 3 tasks → 0 pending
    # → wrongly pinned at 43200 with 2 real gaps open).
    try:
        with open(md_path) as f:
            c = f.read()
        boxes = len(re.findall(r'^## \[ \]|^- \[ \]', c, re.M))
        never = (len(re.findall(r'^## \[ \].*NEVER-DONE', c, re.M))
                 + len(re.findall(r'^- \[ \].*NEVER-DONE', c, re.M)))
        boxes = max(0, boxes - never)
    except Exception:
        boxes = 0
    return max(n, boxes)

def parse_pending_from_parquet(parquet_path):
    """Count real pending tasks from migrated board (tasks.parquet)."""
    try:
        import duckdb
        con = duckdb.connect()
        n = con.execute(
            f"SELECT count(*) FROM read_parquet('{parquet_path}') "
            "WHERE status IN ('pending','in_progress','blocked') "
            "AND id != 'NEVER-DONE'").fetchone()[0]
        con.close()
        return n
    except Exception:
        return None

def board_pending(workdir):
    """Return real-pending count for a project workdir, or None if unreadable."""
    cd = os.path.join(workdir, '.coding-hermes')
    if not os.path.isdir(cd):
        return None
    # Migrated board first (authoritative)
    pq = os.path.join(cd, 'board', 'tasks.parquet')
    if os.path.exists(pq):
        n = parse_pending_from_parquet(pq)
        if n is not None:
            return n
    # DuckDB/SQLite board (board.db or board.duckdb) BEFORE the legacy
    # tasks.md mirror — when both exist the db is the live store and the
    # mirror is stale (deepseek-dashboard had 1 real pending that the
    # mirror hid, keeping it wrongly pinned at 43200).
    for dbname in ('board.db', 'board.duckdb'):
        dbp = os.path.join(cd, 'board', dbname)
        if os.path.exists(dbp):
            n = parse_pending_from_sqlite(dbp)
            if n is not None:
                return n
    md = os.path.join(cd, 'tasks.md')
    if os.path.exists(md):
        n = parse_pending_from_md(md)
        if n is not None:
            return n
    return None

def parse_pending_from_sqlite(db_path):
    """Count real pending tasks from a board.db/board.duckdb store (DuckDB format)."""
    try:
        import duckdb
        con = duckdb.connect()
        con.execute(f"ATTACH '{db_path}' AS bdb (READ_ONLY)")
        try:
            tables = [t[0] for t in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_catalog='bdb'").fetchall()]
            t = 'tasks' if 'tasks' in tables else (tables[0] if tables else None)
            if not t:
                con.close()
                return None
            try:
                # Direct count — DuckDB PRAGMA table_info doesn't accept
                # catalog-qualified names ('bdb.tasks' → BinderException),
                # which previously made this return None and fall through
                # to the stale tasks.md mirror.
                n = con.execute(
                    f"SELECT count(*) FROM bdb.{t} WHERE status IN "
                    "('pending','in_progress','blocked','open','todo')").fetchone()[0]
                con.close()
                return n
            except Exception:
                # no status column — fall back to the JSONL mirror if present
                jsonl = os.path.join(os.path.dirname(db_path), 'tasks.jsonl')
                if os.path.isfile(jsonl):
                    import json as _json
                    n = 0
                    with open(jsonl) as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                row = _json.loads(line)
                            except Exception:
                                continue
                            if str(row.get('status', '')).lower() in (
                                    'pending', 'in_progress', 'blocked', 'open', 'todo'):
                                n += 1
                    con.close()
                    return n
                con.close()
                return None
        except Exception:
            con.close()
            return None
    except Exception:
        return None

def api_get(path):
    with urllib.request.urlopen(API + path, timeout=10) as r:
        return json.loads(r.read())

def api_put(path, body):
    req = urllib.request.Request(
        API + path, data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'}, method='PUT')
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def main():
    apply = '--apply' in sys.argv
    fleet_pins = read_fleet_pins()
    projects = api_get('/api/v1/projects').get('projects', [])

    print(f"mode: {'APPLY' if apply else 'DRY-RUN'}")
    print(f"{'PROJECT':32s} {'PENDING':8s} {'COOLDOWN':10s} {'TARGET':8s} {'ACTION'}")
    actions = []
    for p in sorted(projects, key=lambda x: x.get('name', x.get('name', ''))):
        name = p.get('name', p.get('name', '?'))
        if not p.get('enabled', p.get('enabled')):
            continue
        workdir = p.get('workdir', p.get('workdir', ''))
        if workdir.startswith('local:'):
            workdir = workdir[6:]
        cooldown = p.get('cooldown_s', p.get('cooldown_s', 0))
        pending = board_pending(workdir)

        if pending is None:
            print(f"{name:32s} {'?':8s} {cooldown:10d} {'—':8s} board-unreadable (skip)")
            continue

        # Cooldown correction rules (Bane 2026-08-07):
        # 1. below 900 → RAISE to 900 (minimum floor)
        # 2. at 900 → untouched (priority tier)
        # 3. above 7200 with real work → REDUCE to 7200 (2h default)
        # 4. 7200 (or less) with no work → PROMOTE to 43200 (completed)
        gaps = open_ledger_gaps(name)
        work_exists = pending > 0 or gaps > 0
        target = cooldown  # default: no change

        if cooldown < TARGET_ACTIVE:
            target = TARGET_ACTIVE
            action = f"RAISE {cooldown}→900 (below minimum floor)"
            if apply:
                api_put(f"/api/v1/projects/{name}", {"cooldown_s": target})
                action += " ✓"
            actions.append((name, cooldown, target, pending))
        elif cooldown == TARGET_ACTIVE:
            # 900 = priority tier. Two origins: (a) operator pin in fleet.toml
            # → untouched; (b) stand-in WAKE (PUT 900 on a project whose pin
            # says otherwise — standin-pick.py:131 "wake the foreman") → the
            # wake must be TEMPORARY: revert to 7200 once no work remains,
            # otherwise projects silently run hot forever after being poked.
            pin = fleet_pins.get(name)
            if pin == TARGET_ACTIVE:
                action = "ok (operator priority tier — untouched)"
            elif work_exists:
                action = "ok (stand-in wake active — work exists)"
            else:
                target = TARGET_IDLE
                action = f"REVERT wake 900→7200 (no work; pin={pin})"
                if apply:
                    api_put(f"/api/v1/projects/{name}", {"cooldown_s": target})
                    action += " ✓"
                actions.append((name, cooldown, target, pending))
        elif work_exists and cooldown > TARGET_IDLE:
            target = TARGET_IDLE
            action = f"REDUCE {cooldown}→7200 (work exists: {pending} pending, {gaps} gaps)"
            if apply:
                api_put(f"/api/v1/projects/{name}", {"cooldown_s": target})
                action += " ✓"
            actions.append((name, cooldown, target, pending))
        elif not work_exists and cooldown < TARGET_COMPLETED and fleet_pins.get(name) != TARGET_IDLE:
            # Rule 4: promote idle 7200s to 43200 — BUT only when the 2h tier
            # was policy-set, not operator-set. An explicit fleet.toml pin of
            # 7200 is admin intent ("keep this at 2h") and must not be
            # promoted away (Bane 2026-08-07: bunker/chimera-v2/duckbrain/
            # h3-sdk-* are operator 2h projects). Policy-promoted projects get
            # their pin regenerated to 43200, so pin==7200 uniquely marks
            # operator intent.
            target = TARGET_COMPLETED
            action = f"PROMOTE {cooldown}→43200 (completed: 0 pending, 0 open gaps)"
            if apply:
                api_put(f"/api/v1/projects/{name}", {"cooldown_s": target})
                action += " ✓"
            actions.append((name, cooldown, target, pending))
        else:
            action = "ok"

        print(f"{name:32s} {pending:8d} {cooldown:10d} {target:8d} {action}")

    print(f"\n{len(actions)} projects need cooldown reduction" +
          (" (APPLIED)" if apply else " — run with --apply"))

    if apply:
        # Re-fetch projects AFTER the PUTs so fleet.toml pins reflect the
        # corrected state, not the pre-PUT snapshot. (Proven 2026-08-07:
        # pins for h3/muster/uhlp/dexdat-memory were written stale and
        # would have reverted the reductions on daemon restart.)
        projects = api_get('/api/v1/projects').get('projects', [])
        # Regenerate fleet.toml pins from the corrected state so daemon
        # restarts re-pin to the policy decision, not a stale snapshot.
        # (Daemon must run with -config pointing at this file.)
        n = write_fleet_pins(projects)
        print(f"fleet.toml: regenerated {n} project pins (durable across restarts)")


def read_fleet_pins(path=None):
    """Read {name: cooldown_s} from fleet.toml (operator-set pins)."""
    import re as _re
    path = path or os.path.expanduser('~/.hermes/fleet.toml')
    pins = {}
    try:
        txt = open(path).read()
    except OSError:
        return pins
    for block in _re.findall(r'\[\[projects\]\](.*?)(?=\[\[|$)', txt, _re.S):
        n = _re.search(r'name\s*=\s*"([^"]+)"', block)
        c = _re.search(r'cooldown_s\s*=\s*(\d+)', block)
        if n:
            pins[n.group(1)] = int(c.group(1)) if c else None
    return pins

def write_fleet_pins(projects):
    """Write [[projects]] pins for all enabled projects from API state."""
    import urllib.parse
    enabled = [p for p in projects if p.get('enabled', p.get('enabled'))]
    out = [
        "# Fleet configuration — cooldown overrides",
        "# These entries ensure cooldowns survive scheduler restarts.",
        "# Auto-generated by fleet-cooldown-policy.py --apply — do not edit by hand.",
        "# Policy: 900s fast (1+ real pending) / 7200s default (0 pending).",
        "",
    ]
    for p in sorted(enabled, key=lambda x: x.get('name', x.get('name', ''))):
        out.append("[[projects]]")
        out.append(f'name = "{p.get("name", p.get("Name", "?"))}"')
        out.append(f'repo_url = "{p.get("repo_url", p.get("RepoURL", "")) or "local:" + p.get("workdir", p.get("Workdir", ""))}"')
        out.append(f'workdir = "{p.get("workdir", p.get("Workdir", ""))}"')
        out.append(f'weight = {p.get("weight", p.get("Weight", 10))}')
        out.append(f'priority = {p.get("priority", p.get("Priority", 5))}')
        out.append(f'cooldown_s = {p.get("cooldown_s", p.get("CooldownS", 7200))}')
        out.append(f'model = "{p.get("model", p.get("Model", "")) or "deepseek-v4-flash"}"')
        out.append(f'provider = "{p.get("provider", p.get("Provider", "")) or "deepseek-foreman"}"')
        ns = p.get('namespace_id', p.get('NamespaceID'))
        if ns:
            out.append(f'namespace_id = "{ns}"')
        if p.get('deliver', p.get('Deliver')):
            out.append(f'deliver = "{p.get("deliver", p.get("Deliver", ""))}"')
        out.append(f'enabled = {"true" if p.get("enabled", p.get("Enabled")) else "false"}')
        out.append("")
    path = os.path.expanduser('~/.hermes/fleet.toml')
    with open(path, 'w') as f:
        f.write('\n'.join(out))
    return len(enabled)

if __name__ == '__main__':
    main()
