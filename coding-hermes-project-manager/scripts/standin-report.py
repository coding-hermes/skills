#!/usr/bin/env python3
"""standin-report.py — Build the Stand-In HTML report (what's been happening).

Reads three sources:
  1. DuckBrain coding-hermes namespace (JSONL on disk — survives HTTP degradation)
     - /stand-in/YYYY-MM-DD/<project> events (gap pushes, tasks written)
     - /fleet/projects/<name>/ticks/* recent tick entries (foreman activity)
  2. Scheduler API (cooldowns, enabled, last tick)
  3. Board files (tasks.md / tasks.jsonl) for pending counts

Output: ~/.hermes/stand-in/reports/stand-in-report-YYYY-MM-DD-HHMM.html
Also writes a LATEST.html pointer. Self-contained (inline CSS, no JS deps).
"""
import json, os, re, sys, time, urllib.request
from datetime import datetime, timezone

NS = '~/duckbrain/namespaces/coding-hermes'
OUT_DIR = os.path.expanduser('~/.hermes/stand-in/reports')
API = 'http://127.0.0.1:9090'

def read_jsonl_lines(path):
    """Yield parsed JSON lines from a JSONL file (tolerant of bad lines)."""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return

def duckbrain_entries(key_prefix=None, domain=None, month='2026-08'):
    """All entries in the coding-hermes namespace for a domain/month."""
    out = []
    if domain:
        domains = [domain]
    else:
        domains = [d for d in os.listdir(NS) if os.path.isdir(os.path.join(NS, d))]
    for d in domains:
        ddir = os.path.join(NS, d)
        mdir = os.path.join(ddir, month)
        if not os.path.isdir(mdir):
            continue
        for fn in os.listdir(mdir):
            if not fn.endswith('.jsonl'):
                continue
            for e in read_jsonl_lines(os.path.join(mdir, fn)):
                if key_prefix and not (e.get('key') or '').startswith(key_prefix):
                    continue
                out.append(e)
    return out

def scheduler_projects():
    try:
        with urllib.request.urlopen(API + '/api/v1/projects', timeout=8) as r:
            d = json.loads(r.read())
        return [norm(p) for p in d.get('projects', [])]
    except Exception:
        return []

_ALIAS = {'name': 'Name', 'repo_url': 'RepoURL', 'workdir': 'Workdir',
          'cooldown_s': 'CooldownS', 'decay_rate': 'DecayRate', 'model': 'Model',
          'provider': 'Provider', 'enabled': 'Enabled', 'created_at': 'CreatedAt',
          'updated_at': 'UpdatedAt', 'last_tick_started': 'LastTickStarted',
          'consecutive_failures': 'ConsecutiveFailures'}

def norm(p):
    """Scheduler API serves snake_case (spec S06); expose PascalCase aliases so
    downstream code keeps working regardless of API shape."""
    out = dict(p)
    for k, v in p.items():
        if k in _ALIAS and _ALIAS[k] not in out:
            out[_ALIAS[k]] = v
    return out

def board_pending(workdir):
    md = os.path.join(workdir, '.coding-hermes', 'tasks.md')
    if os.path.isfile(md):
        try:
            with open(md) as f:
                c = f.read()
            return c.count('- [ ]') + c.count('| [ ]') + c.count('⬜'), len(re.findall(r'\| ✅', c))
        except Exception:
            return -1, -1
    jl = os.path.join(workdir, '.coding-hermes', 'board', 'tasks.jsonl')
    if os.path.isfile(jl):
        pend = comp = 0
        for e in read_jsonl_lines(jl):
            if e.get('status') == 'pending':
                pend += 1
            if e.get('status') == 'complete':
                comp += 1
        return pend, comp
    return -1, -1

def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    now = datetime.now(timezone.utc)
    stamp = now.strftime('%Y-%m-%d-%H%M')
    month = now.strftime('%Y-%m')

    # ── 1. Stand-in events from DuckBrain ──
    standin = duckbrain_entries(key_prefix='/stand-in/', domain='event', month=month)
    standin.sort(key=lambda e: e.get('timestamp', ''))
    # ── 2. Fleet tick entries from DuckBrain ──
    ticks = duckbrain_entries(key_prefix='/fleet/projects/', domain='event', month=month)
    tick_keys = [e for e in ticks if '/ticks/' in (e.get('key') or '')]
    # ── 3. Scheduler state ──
    projs = scheduler_projects()
    enabled = [p for p in projs if p.get('enabled')]
    paused = [p for p in enabled if (p.get('cooldown_s') or 0) >= 14400]
    # "Never ticked" — derive from DuckBrain tick logs (API LastTickStarted is unreliable):
    # /fleet/projects/<name>/ticks/* keys tell us which projects have actually run
    ticked_names = set()
    for e in tick_keys:
        # key like /fleet/projects/ring-runner/ticks/<tick-id> → ['', 'fleet', 'projects', 'ring-runner', ...]
        parts = (e.get('key') or '').split('/')
        if len(parts) >= 5 and parts[2] == 'projects':
            ticked_names.add(parts[3])
    never = [p for p in enabled if p['name'] not in ticked_names]

    # ── Build HTML ──
    rows = []
    for e in standin:
        ts = (e.get('timestamp') or '')[:16].replace('T', ' ')
        key = e.get('key', '')
        proj = key.rsplit('/', 1)[-1] if key else '?'
        attrs = e.get('attributes') or {}
        tasks = attrs.get('tasks_added', '?')
        verdict = attrs.get('verdict', '?')
        text = (e.get('embedding_text') or '')[:220]
        rows.append(f"""<tr>
<td class="mono">{esc(ts)}</td>
<td><b>{esc(proj)}</b></td>
<td><span class="tag {esc(verdict)}">{esc(verdict)}</span></td>
<td class="mono">{esc(tasks)}</td>
<td>{esc(text)}</td>
</tr>""")

    # Project table
    proj_rows = []
    for p in sorted(enabled, key=lambda x: x['name'].lower()):
        wd = p.get('workdir', '')
        pend, comp = board_pending(wd)
        cd = p.get('cooldown_s', 0)
        state = ('🔴 paused' if cd >= 14400 else '🟢 active' if cd <= 900 else '🟡 mid')
        lt = (p.get('LastTickStarted') or 'never')[:16].replace('T', ' ')
        pend_s = str(pend) if pend >= 0 else '?'
        proj_rows.append(f"""<tr>
<td><b>{esc(p['name'])}</b></td>
<td>{state}</td>
<td class="mono">{cd}s</td>
<td class="mono">{pend_s}</td>
<td class="mono">{esc(lt)}</td>
<td class="mono small">{esc(wd)}</td>
</tr>""")

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stand-In Fleet Report — {stamp}</title>
<style>
:root {{ --bg:#0f1115; --card:#171a21; --border:#262b36; --txt:#e6e9ef; --dim:#8b93a5; --grn:#3fb950; --ylw:#d29922; --red:#f85149; --blu:#58a6ff; }}
* {{ box-sizing:border-box; }}
body {{ background:var(--bg); color:var(--txt); font:14px/1.5 -apple-system,'Segoe UI',Roboto,sans-serif; margin:0; padding:24px; }}
h1 {{ font-size:22px; margin:0 0 4px; }}
h2 {{ font-size:16px; margin:28px 0 10px; border-bottom:1px solid var(--border); padding-bottom:6px; }}
.sub {{ color:var(--dim); margin-bottom:18px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin:14px 0; }}
.card {{ background:var(--card); border:1px solid var(--border); border-radius:8px; padding:12px; }}
.card .n {{ font-size:24px; font-weight:700; }}
.card .l {{ color:var(--dim); font-size:12px; text-transform:uppercase; letter-spacing:.5px; }}
table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--border); border-radius:8px; overflow:hidden; }}
th {{ text-align:left; color:var(--dim); font-size:11px; text-transform:uppercase; letter-spacing:.5px; padding:8px 10px; border-bottom:1px solid var(--border); }}
td {{ padding:8px 10px; border-bottom:1px solid var(--border); vertical-align:top; }}
tr:last-child td {{ border-bottom:none; }}
.mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12.5px; }}
.small {{ font-size:11.5px; color:var(--dim); }}
.tag {{ display:inline-block; padding:1px 8px; border-radius:10px; font-size:11px; font-weight:600; }}
.tag.gaps-found {{ background:#3a2a12; color:var(--ylw); }}
.tag.ok, .tag.verified, .tag.gap-free {{ background:#12291a; color:var(--grn); }}
.tag.woke, .tag.poked {{ background:#12263a; color:var(--blu); }}
.tag.clean {{ background:#12291a; color:var(--grn); }}
.green {{ color:var(--grn); }} .yellow {{ color:var(--ylw); }} .red {{ color:var(--red); }}
.note {{ color:var(--dim); font-size:12.5px; }}
</style></head><body>
<h1>🕵️ Stand-In Fleet Report</h1>
<div class="sub">Generated {now.strftime('%Y-%m-%d %H:%M UTC')} · human stand-in gap-pusher · logged in DuckBrain (<span class="mono">coding-hermes</span> ns)</div>

<div class="cards">
  <div class="card"><div class="n">{len(standin)}</div><div class="l">Stand-in runs</div></div>
  <div class="card"><div class="n">{len(enabled)}</div><div class="l">Enabled projects</div></div>
  <div class="card"><div class="n yellow">{len(paused)}</div><div class="l">Self-paused (≥4h)</div></div>
  <div class="card"><div class="n red">{len(never)}</div><div class="l">Never ticked</div></div>
  <div class="card"><div class="n">{len(tick_keys)}</div><div class="l">Foreman ticks logged</div></div>
</div>

<h2>Stand-In Gap Pushes (DuckBrain <span class="mono">/stand-in/</span>)</h2>
<table><thead><tr><th>Time</th><th>Project</th><th>Verdict</th><th>Tasks</th><th>Finding</th></tr></thead>
<tbody>
{''.join(rows) if rows else '<tr><td colspan="5" class="note">No stand-in runs logged yet this month.</td></tr>'}
</tbody></table>

<h2>Fleet State (scheduler :9090)</h2>
<table><thead><tr><th>Project</th><th>State</th><th>Cooldown</th><th>Pending</th><th>Last tick</th><th>Workdir</th></tr></thead>
<tbody>
{''.join(proj_rows)}
</tbody></table>

<div class="note" style="margin-top:18px">
Sources: DuckBrain JSONL (<span class="mono">{NS}/event/{month}/</span>) · scheduler API · project boards.
Stand-in writes tasks to boards → wakes paused foremen → foremen do the work. Gaps found are real user-perspective findings (docs, integration, UX, tests), not code-green checks.
</div>
</body></html>"""

    path = os.path.join(OUT_DIR, f'stand-in-report-{stamp}.html')
    with open(path, 'w') as f:
        f.write(html)
    latest = os.path.join(OUT_DIR, 'LATEST.html')
    with open(latest, 'w') as f:
        f.write(html)
    print(f"REPORT_WRITTEN: {path}")
    print(f"LATEST: {latest}")
    print(f"standin_events={len(standin)} enabled={len(enabled)} paused={len(paused)} never={len(never)} ticks_logged={len(tick_keys)}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
