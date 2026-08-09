#!/usr/bin/env python3
"""Verify jobs.json schedule integrity after edits.
Run this after ANY jobs.json modification to catch:
- Invalid 'kind' values ('every' instead of 'interval')
- Cron schedules missing 'expr' key (crashes scheduler)
- Interval schedules missing 'minutes' key
- schedule.kind/schedule.display mismatches with schedule_display
- Model/provider drift on pinned projects
"""
import json, sys

JOBS_PATH = '~/.hermes/cron/jobs.json'
PINNED = {
    # NOTE: helios and hilo were intentionally rebalanced 2026-07-06 per inventory
    # (budget foreman model per §helios-dual-model). The old pinned values
    # (gpt-5.5 / glm-5.2) were wrong for budget foremen. Current pinned targets
    # reflect the inventory's documented intent. If live config shows v4-pro instead
    # of v4-flash, that's also valid per the foreman model rule.
    "helios-coding-hermes-foreman":  ("custom:opencode-go", "deepseek-v4-flash"),
    "hilo-foreman":                  ("custom:opencode-go", "deepseek-v4-flash"),
    "Bunker Coding Hermes":          ("kimi-for-coding", "kimi-for-coding"),
    "speclang-ci-foreman":           ("minimax", "MiniMax-M3"),
    "mythos-coding-foreman":         ("xai-oauth", "grok-4.3"),
}

with open(JOBS_PATH) as f:
    data = json.load(f)

errors = []

for j in data['jobs']:
    name = j.get('name', j.get('id', '?'))
    s = j.get('schedule', {})
    kind = s.get('kind', 'unknown')
    
    # Check 1: 'every' is an invalid schedule kind (old Hermes format)
    if kind == 'every':
        errors.append(f"INVALID KIND 'every': {name} (id={j['id']}) — should be 'interval' with 'minutes' field")
    
    # Check 2: cron schedules need 'expr'
    if kind == 'cron' and 'expr' not in s:
        errors.append(f"MISSING expr: {name} (id={j['id']}) — scheduler will crash")
    
    # Check 3: interval schedules need 'minutes'
    if kind == 'interval' and 'minutes' not in s:
        errors.append(f"MISSING minutes: {name} (id={j['id']}) — interval schedule without duration")
    
    # Check 4: schedule.display should match schedule_display
    if s.get('display') and j.get('schedule_display'):
        if s['display'] != j['schedule_display']:
            errors.append(f"MISMATCH: {name} schedule.display='{s['display']}' != schedule_display='{j['schedule_display']}'")
    
    # Check 5: pinned projects
    if name in PINNED:
        exp_prov, exp_model = PINNED[name]
        if j.get('provider') != exp_prov or j.get('model') != exp_model:
            errors.append(f"PINNED VIOLATION: {name} = {j.get('provider')}/{j.get('model')} (should be {exp_prov}/{exp_model})")

if errors:
    print(f"❌ {len(errors)} SCHEDULE ERRORS:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("✅ All schedules valid — no expr gaps, no mismatches, no pinned violations")
    sys.exit(0)
