#!/usr/bin/env python3
"""Fleet-wide GitReins judge config audit for all enabled scheduler projects.

Audits .gitreins/config.yaml evaluator sections and flags:
  - NO-CONFIG      — .gitreins/config.yaml missing entirely
  - WRONG-MODEL    — evaluator model != deepseek-v4-flash
  - LOW-ITER       — >200 source files but max_iterations < 100
  - LOW-TIME       — >500 source files but max_time != 30m

Usage:
  python3 gitreins-judge-fleet-audit.py /path/to/scheduler_projects.json
    (JSON from `curl -s --noproxy '*' http://127.0.0.1:9090/api/v1/projects`)
  python3 gitreins-judge-fleet-audit.py --scan ~
    (scan every dir under ~ for .gitreins/config.yaml)

Proven: 2026-07-31 — audited 34 enabled projects in one pass, flagged 4
(dexdat-core 808 files/50 iter, imhotep 205/30, mafia-ai-benchmark 281/50,
muster 591/50), GITREINS-JUDGE tasks injected on all 4 boards.
"""
import json, os, re, sys

def evaluate_workdir(wd):
    name = os.path.basename(wd.rstrip('/'))
    cfg = os.path.join(wd, '.gitreins', 'config.yaml')
    if not os.path.isfile(cfg):
        return (name, 'NO-CONFIG', '-', '-', 0)
    with open(cfg, errors='replace') as f:
        content = f.read()
    ev_model, ev_iter, ev_time = '-', '-', '-'
    # evaluator section first, then defaults section fallback
    for pattern in (r'evaluator:.*?(?:\n\S|\Z)', r'defaults:.*?(?:\n\S|\Z)'):
        m = re.search(pattern, content, re.S)
        if not m:
            continue
        section = m.group(0)
        mm = re.search(r'model:\s*["\']?([\w.\-/]+)', section)
        if mm and ev_model == '-':
            ev_model = mm.group(1)
        mi = re.search(r'max_iterations:\s*(\d+)', section)
        if mi:
            ev_iter = mi.group(1)
        mt = re.search(r'max_time:\s*["\']?([\w]+)', section)
        if mt:
            ev_time = mt.group(1)
    # count source files (skip vendored/build dirs)
    nfiles = 0
    skip = {'.git','node_modules','.venv','venv','target','dist','build','vendor','.coding-hermes','.hermes'}
    for root, dirs, files in os.walk(wd):
        dirs[:] = [d for d in dirs if d not in skip]
        for fn in files:
            if fn.endswith(('.go','.py','.ts','.tsx','.js','.rs','.cpp','.cc','.h','.c','.java','.rb','.gd','.sh')):
                nfiles += 1
        if nfiles > 3000:
            break
    flag = ''
    if ev_model == '-':
        flag = 'NO-EVALUATOR'
    elif ev_model != 'deepseek-v4-flash':
        flag = f'WRONG-MODEL({ev_model})'
    if nfiles > 200 and ev_iter.isdigit() and int(ev_iter) < 100:
        flag += ' LOW-ITER'
    # LOW-TIME: only when max_time is genuinely UNDER 30m for large codebases.
    # Higher values (45m, 12h) are fine — parse unit-aware, don't whitelist.
    if nfiles > 500 and ev_time not in ('-',):
        mm_t = re.match(r'(\d+)\s*m', ev_time)      # "25m" / "45 m"
        mh_t = re.match(r'(\d+)\s*h', ev_time)      # "12h"
        mins = None
        if mm_t:
            mins = int(mm_t.group(1))
        elif mh_t:
            mins = int(mh_t.group(1)) * 60
        elif ev_time.isdigit():
            mins = int(ev_time)
        if mins is not None and mins < 30:
            flag += ' LOW-TIME'
    return (name, flag or 'OK', ev_model, ev_iter, nfiles)

def main():
    workdirs = []
    if len(sys.argv) > 2 and sys.argv[1] == '--scan':
        base = sys.argv[2]
        for d in os.listdir(base):
            wd = os.path.join(base, d)
            if os.path.isdir(os.path.join(wd, '.gitreins')):
                workdirs.append(wd)
    elif len(sys.argv) == 2:
        with open(sys.argv[1]) as f:
            data = json.load(f)
        for p in data.get('projects', []):
            if not p.get('enabled', p.get('Enabled')):
                continue
            wd = p.get('workdir', p.get('Workdir', ''))
            if wd and not wd.startswith('/tmp'):
                workdirs.append(wd)
    else:
        print("Usage: gitreins-judge-fleet-audit.py <scheduler_projects.json> | --scan <dir>")
        sys.exit(1)

    print(f"{'Project':32s} {'Status':26s} {'Model':18s} {'Iter':6s} {'Files'}")
    flagged = []
    for wd in sorted(set(workdirs)):
        if not os.path.isdir(wd):
            continue
        name, status, model, it, files = evaluate_workdir(wd)
        print(f"{name:32s} {status:26s} {model:18s} {it:6s} {files}")
        if status != 'OK':
            flagged.append(name)
    print(f"\nFlagged {len(flagged)}: {', '.join(flagged) if flagged else 'none'}")

if __name__ == '__main__':
    main()
