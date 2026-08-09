#!/usr/bin/env python3
"""Check which coding-hermes cron jobs failed to fire on schedule.
Run by supervisor Phase 2A. Returns JSON with firing status per job.

Usage: python3 scripts/check-cron-firing.py [--json] [--stale-threshold-multiplier 2.0]
"""

import json, sys, os
from datetime import datetime, timezone, timedelta

JOBS_PATH = os.path.expanduser('~/.hermes/cron/jobs.json')
STALE_MULTIPLIER = 2.0  # Job is "stale" if delta > multiplier * expected interval

def parse_interval_minutes(schedule):
    """Extract expected interval in minutes from schedule dict."""
    kind = schedule.get('kind', '')
    if kind == 'interval':
        return schedule.get('minutes', 0)
    elif kind == 'cron':
        # Approximate: */15 → 15, */30 → 30, 0 */2 → 120, 0 */4 → 240
        expr = schedule.get('expr', schedule.get('display', ''))
        if '*/15' in expr: return 15
        if '*/30' in expr: return 30
        if '*/2' in expr or 'every 2h' in expr.lower(): return 120
        if '*/4' in expr or 'every 4h' in expr.lower(): return 240
        if '*/6' in expr or 'every 6h' in expr.lower(): return 360
        # Default: assume every hour for unknown cron expressions
        return 60
    elif kind == 'every':
        # Invalid kind — parse display
        display = schedule.get('display', '')
        import re
        m = re.search(r'(\d+)', display)
        return int(m.group(1)) if m else 0
    return 0

def main():
    with open(JOBS_PATH) as f:
        data = json.load(f)

    now = datetime.now(timezone.utc)
    results = []
    stale_count = 0
    never_count = 0
    disabled_count = 0

    for j in data.get('jobs', []):
        skills = [s if isinstance(s, str) else s.get('name', '') for s in (j.get('skills') or [])]
        if 'coding-hermes-cron' not in skills:
            continue

        name = j.get('name', '?')
        enabled = j.get('enabled', False)
        state = j.get('state', '?')
        lr = j.get('last_run_at')
        schedule = j.get('schedule', {})
        err = j.get('last_error')

        result = {
            'name': name,
            'enabled': enabled,
            'state': state,
            'last_run': lr,
            'schedule_display': j.get('schedule_display', '?'),
            'expected_minutes': parse_interval_minutes(schedule),
            'status': 'unknown',
            'issue': None
        }

        if not enabled:
            result['status'] = 'disabled'
            result['issue'] = j.get('paused_reason') or 'disabled'
            disabled_count += 1
        elif state in ('completed', 'paused'):
            result['status'] = 'stale_state'
            result['issue'] = f'state={state}'
            stale_count += 1
        elif lr is None:
            result['status'] = 'never'
            result['issue'] = 'never fired'
            never_count += 1
        else:
            lr_dt = datetime.fromisoformat(lr.replace('Z', '+00:00'))
            delta_h = (now - lr_dt).total_seconds() / 3600
            expected_m = result['expected_minutes']
            result['delta_hours'] = round(delta_h, 1)

            if expected_m > 0 and delta_h > (expected_m / 60) * STALE_MULTIPLIER:
                result['status'] = 'stale'
                result['issue'] = f'{delta_h:.1f}h since last run (expected every {expected_m}m)'
                stale_count += 1
            else:
                result['status'] = 'ok'

        if err:
            result['last_error'] = str(err)[:200]

        results.append(result)

    output = {
        'checked_at': now.isoformat(),
        'total': len(results),
        'ok': sum(1 for r in results if r['status'] == 'ok'),
        'stale': stale_count,
        'never': never_count,
        'disabled': disabled_count,
        'jobs': results
    }

    if '--json' in sys.argv:
        print(json.dumps(output, indent=2))
    else:
        print(f"Firing check: {output['ok']} OK, {output['stale']} stale, {output['never']} never, {output['disabled']} disabled")
        for r in results:
            if r['status'] != 'ok':
                print(f"  {'🔴' if r['status'] in ('stale','never') else '⚫'} {r['name']}: {r['issue']}")

    return 0 if stale_count == 0 and never_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
