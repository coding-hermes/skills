#!/usr/bin/env python3
"""Urgency ranking probe — replicates the scheduler packer's selection math.

Run:  python3 urgency_rank.py [namespace] [limit]
Prints enabled projects sorted by urgency exactly as the MultiPoolPacker
scores them, so you can see WHERE a project sits in the queue and why it
never gets selected. DB: ~/.hermes/coding-hermes/scheduler.db.

Config replicated from schedulerd defaults: min-interval 20m, max-interval
24h, num-levels 10 (ratio = 72). Override with env vars MIN_I / MAX_I / NLVL.
"""
import sqlite3, os, sys, math
from datetime import datetime, timezone

MIN_I = float(os.environ.get("MIN_I", 1200.0))      # 20m
MAX_I = float(os.environ.get("MAX_I", 86400.0))     # 24h
NLVL = int(os.environ.get("NLVL", 10))
ratio = MAX_I / MIN_I
NS = sys.argv[1] if len(sys.argv) > 1 else "coding-hermes"
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 20

def interval(p):
    p = max(1, min(p, NLVL))
    return MAX_I / (ratio ** ((p - 1) / (NLVL - 1)))

def urgency(prio, decay, now, last, created):
    elapsed = (now - last).total_seconds() if last else (now - created).total_seconds()
    if elapsed < 0:
        elapsed = 0
    base = 1.0 + elapsed / interval(prio)
    if base < 1.0:
        base = 1.0
    return prio * (base ** decay)

db = os.path.expanduser("~/.hermes/coding-hermes/scheduler.db")
con = sqlite3.connect(db)
now = datetime.now(timezone.utc)

lastcomp = {}
for r in con.execute("SELECT project_name, MAX(completed_at) FROM ticks WHERE status != 'running' GROUP BY project_name"):
    try:
        lastcomp[r[0]] = datetime.fromisoformat(r[1].replace("Z", "+00:00"))
    except Exception:
        pass

rows = con.execute(
    "SELECT name, weight, priority, cooldown_s, decay_rate, created_at, enabled, namespace_id "
    "FROM projects WHERE enabled=1 AND namespace_id=?", (NS,)).fetchall()

scored = []
for name, w, p, cd, decay, created, en, ns in rows:
    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except Exception:
        created_dt = now
    u = urgency(p, decay, now, lastcomp.get(name), created_dt)
    scored.append((u, name, w, p, decay, cd, lastcomp.get(name)))

scored.sort(reverse=True)
print(f"{'URGENCY':>8} {'NAME':32s} w  p  decay  cd  last_tick")
for u, name, w, p, decay, cd, last in scored[:LIMIT]:
    lt = last.strftime("%m-%d %H:%M") if last else "NEVER"
    print(f"{u:8.1f} {name:32s} {w:2d} {p:2d} {decay:5.1f} {cd:5d} {lt}")
con.close()
