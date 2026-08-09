#!/usr/bin/env python3
"""Fix foreman models, repeat format, and schedule format — no LLM, no exceptions.
Run every 4h via cron. Reads jobs.json, fixes foremen not on deepseek-foreman,
int-format repeat fields, and string-format schedules.
Excludes supervisor (identified by name containing 'supervisor').
Backs up jobs.json before every change."""
import json, os, shutil, re
from datetime import datetime

JOBS_FILE = os.path.expanduser('~/.hermes/cron/jobs.json')

def backup():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = JOBS_FILE + '.bak.' + ts
    shutil.copy2(JOBS_FILE, bak)
    return bak

def main():
    with open(JOBS_FILE) as f:
        data = json.load(f)

    fixes = []
    bak = backup()

    for j in data['jobs']:
        name = j.get('name', '')
        workdir = j.get('workdir')
        skills = j.get('skills', [])
        # Exclude supervisor and non-foremen
        is_foreman = (
            workdir
            and any('coding-hermes' in str(s) for s in skills)
            and 'supervisor' not in name.lower()
        )
        if not is_foreman:
            continue

        # Rule 1: provider must be deepseek-foreman
        if j.get('provider') != 'deepseek-foreman':
            j['provider'] = 'deepseek-foreman'
            fixes.append(f'{name}: provider → deepseek-foreman')

        # Rule 2: model must be deepseek-v4-flash (Bane 2026-07-31 — flash is
        # the better model; v4-pro no longer used. See worker-model skill Step 0.)
        model = j.get('model', '')
        if model != 'deepseek-v4-flash':
            j['model'] = 'deepseek-v4-flash'
            fixes.append(f'{name}: model {model} → deepseek-v4-flash')

        # Rule 3: repeat must be dict format
        repeat = j.get('repeat')
        if isinstance(repeat, int):
            j['repeat'] = {'times': None, 'completed': 0}
            fixes.append(f'{name}: repeat int → dict format')

        # Rule 4: schedule must be dict format
        sched = j.get('schedule')
        if isinstance(sched, str):
            m = re.match(r'every\s+(\d+)m', sched)
            if m:
                minutes = int(m.group(1))
                j['schedule'] = {'kind': 'interval', 'display': sched, 'minutes': minutes}
            else:
                j['schedule'] = {'kind': 'interval', 'display': sched, 'minutes': 120}
            fixes.append(f'{name}: schedule {sched} → dict format')

    if fixes:
        with open(JOBS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f'[{datetime.now().isoformat()}] Fixed {len(fixes)} foremen:')
        for fix in fixes:
            print(f'  {fix}')
    else:
        print(f'[{datetime.now().isoformat()}] No fixes needed')

if __name__ == '__main__':
    main()
