#!/usr/bin/env python3
"""Fleet lane-alignment report: every foreman family, every lane inside it, color-flagged.
Owner's rules: GREEN = foreman on + all satellites on; YELLOW = foreman on + missing sats,
or foreman off + some sats on, or satellites with no foreman lane; RED = family dark.
Reads the scheduler DB read-only; writes a self-contained HTML dashboard (dark, KPI cards,
filter box, <details> per family). Regenerate any time; a standing cron can wrap it."""
import sqlite3, html
from collections import defaultdict, Counter

c = sqlite3.connect('file:/home/kara/.hermes/coding-hermes/scheduler.db?mode=ro', uri=True)
c.row_factory = sqlite3.Row
rows = [dict(r) for r in c.execute(
    "select name, enabled, repo_url, workdir, parent, admission_mode, cooldown_s, "
    "disabled_by, substr(disabled_reason,1,120) dr from projects order by name")]

ROLES = ['-foreman', '-qa', '-pm', '-sync', '-dogfood', '-perf', '-releng', '-review',
         '-docs', '-readme', '-ops', '-cards', '-ci', '-upstream', '-standin', '-watch']
def family_role(name):
    low = name.lower()
    for r in sorted(ROLES, key=len, reverse=True):
        if low.endswith(r):
            return name[: -len(r)], r[1:].upper()
    return name, 'PRIMARY'

fam = defaultdict(list)
for r in rows:
    f, role = family_role(r['name'])
    fam[f].append({**r, 'role': role})

fams = []
for f, lanes in sorted(fam.items()):
    fm = next((l for l in lanes if l['role'] == 'FOREMAN'), None)
    sats = [l for l in lanes if l['role'] != 'FOREMAN']
    sats_on = [l for l in sats if l['enabled']]
    if fm is None:
        color, note = 'YELLOW', 'no foreman lane exists'
    elif fm['enabled'] and len(sats_on) == len(sats):
        color, note = 'GREEN', 'aligned'
    elif not fm['enabled'] and not sats_on:
        color, note = 'RED', 'family dark'
    else:
        color = 'YELLOW'
        note = ('foreman on, %d/%d satellites on' % (len(sats_on), len(sats))) if fm['enabled'] \
               else 'foreman off but %d satellite(s) on' % len(sats_on)
    fams.append({'family': f, 'color': color, 'note': note, 'foreman': fm, 'lanes': lanes})

cnt = Counter(f['color'] for f in fams)

def lane_html(l):
    st = 'on' if l['enabled'] else 'off'
    reason = html.escape(l['dr'] or '')
    return ('<div class="lane"><span class="dot %s"></span><code>%s</code>'
            '<span class="meta">%s · adm=%s · cd=%ss · by=%s %s</span></div>'
            % (st, html.escape(l['name']), l['role'], html.escape(l['admission_mode'] or ''),
               l['cooldown_s'], html.escape(l['disabled_by'] or '-'), reason and ('— ' + reason) or ''))

def fam_html(f):
    fm = f['foreman']
    fm_line = ('<code class="fm">%s</code>' % html.escape(fm['name'])) if fm else '<code class="fm none">(no foreman lane)</code>'
    lanes = ''.join(lane_html(l) for l in sorted(f['lanes'], key=lambda x: x['role']))
    return ('<details class="fam %s"><summary><span class="flag %s">%s</span>'
            '<span class="fname">%s</span><span class="fnote">%s · %d lanes, %d on</span></summary>'
            '<div class="body">%s</div></details>'
            % (f['color'].lower(), f['color'].lower(), f['color'], fm_line, html.escape(f['note']),
               len(f['lanes']), sum(1 for l in f['lanes'] if l['enabled']), lanes))

body = ''
for color in ('GREEN', 'YELLOW', 'RED'):
    body += '<h3 class="sec %s">%s families (%d)</h3>' % (color.lower(), color, cnt[color])
    body += ''.join(fam_html(f) for f in fams if f['color'] == color)

STYLE = '''body{background:#14161a;color:#d6d8dd;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:24px}
h1{font-size:20px;margin:0 0 4px}.sub{color:#8a8f98;font-size:12px;margin-bottom:18px}
.kpis{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap}
.kpi{border-radius:10px;padding:12px 18px;min-width:110px;background:#1d2026;border:1px solid #2a2e35}
.kpi b{display:block;font-size:26px}.kpi span{font-size:11px;color:#8a8f98;text-transform:uppercase;letter-spacing:.08em}
.kpi.G b{color:#4ade80}.kpi.Y b{color:#facc15}.kpi.R b{color:#f87171}
details.fam{background:#1d2026;border:1px solid #2a2e35;border-radius:8px;margin:6px 0}
details.fam summary{cursor:pointer;padding:9px 14px;display:flex;gap:10px;align-items:center;list-style:none}
details.fam summary::-webkit-details-marker{display:none}
.flag{font-size:10px;font-weight:700;padding:2px 8px;border-radius:99px;letter-spacing:.05em}
.flag.GREEN{background:#14532d;color:#4ade80}.flag.YELLOW{background:#713f12;color:#facc15}.flag.RED{background:#7f1d1d;color:#f87171}
.fname{font-weight:600;font-family:ui-monospace,monospace}.fnote{color:#8a8f98;font-size:12px;margin-left:auto;text-align:right}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:8px}
.dot.on{background:#4ade80}.dot.off{background:#555}
.lane{padding:5px 18px;border-top:1px solid #262a31;font-size:13px}
.lane code{color:#c4b5fd}.lane .meta{color:#8a8f98;font-size:11px;margin-left:10px}
code.fm{color:#7dd3fc;font-weight:600}
h3.sec{margin:22px 0 8px;font-size:14px;text-transform:uppercase;letter-spacing:.08em}
h3.sec.GREEN{color:#4ade80}h3.sec.YELLOW{color:#facc15}h3.sec.RED{color:#f87171}
input{background:#1d2026;border:1px solid #2a2e35;color:#d6d8dd;border-radius:8px;padding:8px 12px;width:280px;font-size:13px}'''

doc = ('<!doctype html><html><head><meta charset="utf-8"><title>Fleet Lane Alignment</title>'
       '<style>%s</style></head><body>'
       '<h1>Fleet Lane Alignment — source of truth: scheduler DB</h1>'
       '<div class="sub">%d lanes · %d families · GREEN=foreman on+all sats on · YELLOW=partial mismatch · RED=family dark</div>'
       '<div class="kpis">'
       '<div class="kpi G"><b>%d</b><span>green families</span></div>'
       '<div class="kpi Y"><b>%d</b><span>yellow families</span></div>'
       '<div class="kpi R"><b>%d</b><span>red families</span></div></div>'
       '<input id="q" placeholder="filter families…" oninput="for(const d of document.querySelectorAll(\'details.fam\')){d.style.display=d.textContent.toLowerCase().includes(this.value.toLowerCase())?\'\':\'none\'}">'
       '%s</body></html>'
       % (STYLE, len(rows), len(fam), cnt['GREEN'], cnt['YELLOW'], cnt['RED'], body))

out = '/home/kara/project-reviews/lane-alignment.html'
open(out, 'w').write(doc)
print('wrote %s (%d bytes) — %d G / %d Y / %d R of %d families' % (out, len(doc), cnt['GREEN'], cnt['YELLOW'], cnt['RED'], len(fams)))
