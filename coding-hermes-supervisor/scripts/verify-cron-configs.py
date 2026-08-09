#!/usr/bin/env python3
"""Ad-hoc verification script for coding-hermes-supervisor changes.
Run after applying config fixes to confirm all crons are correctly configured
AND operationally healthy (did they fire on schedule?).

Usage: python3 scripts/verify-cron-configs.py [--check-skills] [--check-firing] [--jobs-path ~/.hermes/cron/jobs.json]
"""
import json, os, sys, argparse, re
from datetime import datetime, timezone, timedelta

HOME = os.path.expanduser('~')
DEFAULT_JOBS = os.path.join(HOME, '.hermes/cron/jobs.json')

REQUIRED_SKILLS = ['coding-hermes', 'coding-hermes-cron', 'hilo-usage']
EXCLUDE_CRONS = ['Coding Hermes Supervisor']

# Foreman models that are correct for inspection work
FOREMAN_MODEL_OK = [
    ('deepseek', 'deepseek-v4-pro'),       # PAYG inspection model
    ('custom:opencode-go', 'deepseek-v4-flash'),  # Budget idle model
    ('custom:stepfun', 'step-3.7-flash'),          # Specialty
]

# Coding models that should NOT be used for foreman inspection
CODING_MODELS_FOREMAN_BAD = {
    'glm-5.2', 'MiniMax-M3', 'gpt-5.5', 'gpt-5.4',
    'kimi-for-coding', 'grok-4.3', 'grok-4.1', 'grok-4'
}

# Pinned projects — foreman models set by Bane, don't flag
PINNED = [
    'helios-coding-hermes-foreman',
    'hilo-foreman',
    'Bunker Coding Hermes',
    'speclang-ci-foreman',
    'mythos-coding-foreman',
]


def parse_expected_interval_seconds(schedule):
    """Estimate the expected interval in seconds from a schedule dict."""
    kind = schedule.get('kind', '')
    if kind == 'cron':
        expr = schedule.get('expr', schedule.get('display', ''))
        # Rough heuristic for common cron expressions
        if '*/15' in expr or '* * * * *' in expr and '*/15' in expr:
            return 15 * 60
        if '*/30' in expr:
            return 30 * 60
        if '*/2 * * * *' in expr or '0 */2' in expr:
            return 120 * 60
        if '*/4 * * * *' in expr or '0 */4' in expr:
            return 240 * 60
        if '*/6 * * * *' in expr or '0 */6' in expr:
            return 360 * 60
        # Default for cron: check if hourly-ish
        return 60 * 60
    elif kind == 'interval':
        minutes = schedule.get('minutes', 60)
        return minutes * 60
    return 60 * 60  # fallback


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--jobs-path', default=DEFAULT_JOBS)
    parser.add_argument('--check-skills', action='store_true', default=True)
    parser.add_argument('--check-firing', action='store_true', default=True)
    parser.add_argument('--check-schema', action='store_true', default=True)
    parser.add_argument('--check-foreman-model', action='store_true', default=True)
    args = parser.parse_args()

    with open(args.jobs_path) as f:
        data = json.load(f)

    errors = []
    passes = []
    now = datetime.now(timezone.utc)

    coding_crons = [
        j for j in data['jobs']
        if any('coding-hermes' in (s if isinstance(s, str) else s.get('name', ''))
               for s in j.get('skills', []))
        and j.get('name') not in EXCLUDE_CRONS
    ]

    print(f"Found {len(coding_crons)} coding-hermes crons to verify\n")

    for j in sorted(coding_crons, key=lambda x: x.get('name', '')):
        name = j.get('name', '?')
        prov = j.get('provider')
        model = j.get('model')
        wd = j.get('workdir')
        sk = j.get('skills', [])
        sk_names = [s if isinstance(s, str) else s.get('name', '') for s in sk]
        sched = j.get('schedule', {})
        sched_display = j.get('schedule_display', '?')
        enabled = j.get('enabled', False)
        state = j.get('state', '?')
        last_run = j.get('last_run_at')
        last_error = j.get('last_error')

        issues = []

        # === SCHEMA HEALTH (highest priority — prevents scheduler crashes) ===
        if args.check_schema:
            kind = sched.get('kind', '')
            if kind == 'cron' and 'expr' not in sched:
                issues.append('CRITICAL: cron schedule missing "expr" key — crashes scheduler')
            if kind == 'every':
                issues.append('CRITICAL: kind="every" is invalid — silent failure')
            if kind == 'interval' and 'minutes' not in sched:
                issues.append('CRITICAL: interval schedule missing "minutes" key')
            if kind not in ('cron', 'interval', 'once'):
                issues.append(f'CRITICAL: unknown schedule kind="{kind}"')

        # === OPERATIONAL: DID IT FIRE? ===
        if args.check_firing and enabled:
            if last_run:
                try:
                    lr = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                    expected_s = parse_expected_interval_seconds(sched)
                    delta_s = (now - lr).total_seconds()
                    if delta_s > expected_s * 3:
                        issues.append(f'MISSED FIRES: last run {delta_s/3600:.1f}h ago, expected every {expected_s/60:.0f}m')
                    elif delta_s > expected_s * 2:
                        issues.append(f'LATE: last run {delta_s/3600:.1f}h ago, expected every {expected_s/60:.0f}m')
                except Exception:
                    issues.append(f'Cannot parse last_run_at: {last_run}')
            else:
                issues.append('NEVER FIRED: last_run_at is null')

        # === STATE ===
        if not enabled:
            paused_reason = j.get('paused_reason', '')
            if paused_reason:
                issues.append(f'DISABLED (intentional): {paused_reason[:60]}')
            else:
                issues.append('DISABLED (no reason — may be accidental)')
        elif state == 'completed':
            issues.append('state=completed — job finished and will not run again')

        # === FOREMAN MODEL CHECK ===
        if args.check_foreman_model and name not in PINNED:
            if model and model in CODING_MODELS_FOREMAN_BAD:
                issues.append(f'FOREMAN WASTE: {prov}/{model} is a coding model used for inspection — should be deepseek/deepseek-v4-pro')

        # === PROVIDER/MODEL ===
        if not prov:
            issues.append('missing provider')
        if not model:
            issues.append('missing model')
        if not wd:
            issues.append('missing workdir')

        # === SKILLS ===
        if args.check_skills:
            missing_skills = [s for s in REQUIRED_SKILLS if s not in sk_names]
            if missing_skills:
                issues.append(f'missing skills: {",".join(missing_skills)}')
            if 'opencode-containers' in sk_names:
                issues.append('has opencode-containers (should only be on Axiom crons)')

        # === LAST ERROR ===
        if last_error:
            err_short = str(last_error)[:80]
            issues.append(f'last_error: {err_short}')

        status = '✅' if not issues else '❌'
        print(f"  {status} {name:<40s} prov={prov or '!':<20s} model={model or '!':<24s} sched={sched_display:<15s} enabled={enabled}")
        if issues:
            for i in issues:
                print(f"     ⚠  {i}")
            errors.append(f"{name}: {'; '.join(issues)}")
        else:
            passes.append(name)

    print(f"\nPASS: {len(passes)}  FAIL: {len(errors)}")
    if errors:
        print("\nIssues found:")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    else:
        print("  ✅ All crons properly configured and operationally healthy.")
        sys.exit(0)


if __name__ == '__main__':
    main()
