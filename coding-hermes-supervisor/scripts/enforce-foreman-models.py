#!/usr/bin/env python3
"""Enforce foreman model rules — no LLM, no exceptions.
All foremen → deepseek-v4-flash @ deepseek-foreman PAYG provider.
Bane directive 2026-07-24: no more v4-pro split at any schedule speed.
Run every 30m via cron (no_agent=true)."""
import json, sys, os, re
from datetime import datetime, timezone

JOBS_FILE = os.path.expanduser('~/.hermes/cron/jobs.json')

def get_schedule_minutes(job):
    """Extract minutes from schedule dict or string. Returns None if unknown."""
    sched = job.get('schedule', {})
    if isinstance(sched, dict):
        mins = sched.get('minutes')
        if mins is not None:
            return mins
        # Try to parse from cron expr: */30 → 30, 0 */2 → 120
        expr = sched.get('expr', '')
        m = re.search(r'\*/(\d+)', expr)
        if m:
            return int(m.group(1))
        m = re.search(r'\*/(\d+)\s', expr)
        if m:
            return int(m.group(1)) * 60
    elif isinstance(sched, str):
        m = re.search(r'every\s+(\d+)m', sched)
        if m:
            return int(m.group(1))
        m = re.search(r'every\s+(\d+)h', sched)
        if m:
            return int(m.group(1)) * 60
    return None

def main():
    with open(JOBS_FILE) as f:
        data = json.load(f)

    CANONICAL_TOOLSETS = ["terminal", "file", "web", "search", "skills", "memory"]
    PROHIBITED = {"delegation"}

    fixes = []
    for j in data['jobs']:
        name = j.get('name', '')
        skills = j.get('skills', [])
        if 'coding-hermes-foreman' not in skills:
            continue

        provider = j.get('provider', '')
        model = j.get('model', '')
        schedule_mins = get_schedule_minutes(j)

        # Rule 0: enforce canonical toolsets (null → set, prohibited → strip, missing → add, extras → remove)
        et = j.get('enabled_toolsets')
        if et is None or not isinstance(et, list):
            j['enabled_toolsets'] = list(CANONICAL_TOOLSETS)
            fixes.append(f'{name}: enabled_toolsets {et} → canonical')
        else:
            new_et = [t for t in et if t not in PROHIBITED]
            for t in CANONICAL_TOOLSETS:
                if t not in new_et:
                    new_et.append(t)
            new_et = [t for t in new_et if t in CANONICAL_TOOLSETS]
            if new_et != et:
                j['enabled_toolsets'] = new_et
                fixes.append(f'{name}: toolsets {et} → {new_et}')

        # Rule 4: normalize skills array to canonical
        CANONICAL_SKILLS = ["coding-hermes-foreman", "coding-hermes-cron", "hilo-usage", "gitreins"]
        if skills != CANONICAL_SKILLS:
            j['skills'] = list(CANONICAL_SKILLS)
            fixes.append(f'{name}: skills {skills} → canonical')

        # Rule 1: provider must be deepseek-foreman
        if provider != 'deepseek-foreman':
            j['provider'] = 'deepseek-foreman'
            fixes.append(f'{name}: provider {provider} → deepseek-foreman')

        # Rule 2: ALL foremen use V4 Flash (Bane directive 2026-07-24)
        target_model = 'deepseek-v4-flash'

        if model != target_model:
            j['model'] = target_model
            fixes.append(f'{name}: model {model} → {target_model}')

        # Rule 3: schedule must be dict format
        s = j.get('schedule', {})
        if isinstance(s, str):
            if s.startswith('every '):
                m = re.search(r'every\s+(\d+)m?', s)
                mins = int(m.group(1)) if m else 30
                j['schedule'] = {'kind': 'interval', 'display': s, 'minutes': mins}
            else:
                j['schedule'] = {'kind': 'cron', 'display': s, 'expr': s}
            j['schedule_display'] = s
            fixes.append(f'{name}: schedule string → dict')

    if fixes:
        with open(JOBS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f'[{datetime.now(timezone.utc).isoformat()}] Fixed {len(fixes)} items:')
        for fix in fixes:
            print(f'  {fix}')
    else:
        print(f'[{datetime.now(timezone.utc).isoformat()}] All foremen correct — no changes needed')

if __name__ == '__main__':
    main()
