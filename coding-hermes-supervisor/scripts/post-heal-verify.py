#!/usr/bin/env python3
"""Post-heal verification — run AFTER phase0-autoheal.py and enforce-foreman-models.py.

Checks for false positives:
1. Supervisor (id 55afdcd33d7f) still has correct model/provider
2. Non-foreman infra crons don't have model/provider set
3. All foremen have explicit enabled_toolsets (not null)
4. No foreman has delegation in enabled_toolsets (cronjob checked separately via extra-tool check — can be legit for self-pause)
5. All foremen have ALL 6 canonical toolsets (terminal, file, web, search, skills, memory)
   — NOT just search/skills/memory. Proven: totalstack-foreman 2026-07-14 had
   ['terminal','file','search','skills','memory'] missing 'web'; old check passed it silently.

Usage: python3 scripts/post-heal-verify.py
"""
import json, os

JOBS_PATH = os.path.expanduser("~/.hermes/cron/jobs.json")
with open(JOBS_PATH) as f:
    data = json.load(f)

issues = []

for j in data['jobs']:
    jid = j.get('id', '')
    name = j.get('name', '')
    skills = j.get('skills') or []
    is_supervisor = any('coding-hermes-supervisor' in str(s) for s in skills)
    is_foreman = any('coding-hermes-foreman' in str(s) for s in skills)
    is_cron = any('coding-hermes-cron' in str(s) for s in skills)

    # 1. Supervisor must be deepseek-v4-flash / opencode-go
    if is_supervisor:
        m = j.get('model')
        p = j.get('provider')
        if m != 'deepseek-v4-flash' or p != 'opencode-go':
            issues.append(f'SUPERVISOR {name} ({jid}): model={m}, provider={p} — SHOULD BE deepseek-v4-flash / opencode-go')

    # 2. Non-foreman infra crons must NOT have model/provider set
    if not is_foreman and not is_supervisor and is_cron:
        m = j.get('model')
        p = j.get('provider')
        if m or p:
            issues.append(f'INFRA-CRON {name} ({jid}): model={m}, provider={p} — should be null/null')

    # 3. Check enabled_toolsets on foremen — must have ALL canonical toolsets and no extras.
    #    Uses individual if checks (not elif) so ALL issues per foreman are reported, not just
    #    the first one found. Proven: 2026-07-17 — kobayashi-maru-foreman had cronjob in toolsets,
    #    old elif chain only reported cronjob, missed that toolsets also had non-canonical extras.
    CANONICAL = ["terminal", "file", "web", "search", "skills", "memory"]
    if is_foreman:
        et = j.get('enabled_toolsets')
        if et is None:
            issues.append(f'FOREMAN {name} ({jid}): enabled_toolsets=null — must be explicitly set')
        elif not isinstance(et, list):
            issues.append(f'FOREMAN {name} ({jid}): enabled_toolsets is {type(et).__name__} — expected list')
        else:
            if 'delegation' in et:
                issues.append(f'FOREMAN {name} ({jid}): enabled_toolsets has delegation (PROHIBITED)!')
            # cronjob is NOT checked here — it's caught by the `extra` check below and can
            # legitimately be present for self-pause support. Proven: 2026-07-25 — enforce
            # script canonical set is 6 items without cronjob; extra-tool check reports it.
            missing = [t for t in CANONICAL if t not in et]
            if missing:
                issues.append(f'FOREMAN {name} ({jid}): enabled_toolsets missing {missing}')
            extra = [t for t in et if t not in CANONICAL]
            if extra:
                issues.append(f'FOREMAN {name} ({jid}): enabled_toolsets has extra non-canonical tools: {extra}')

if issues:
    print(f"Post-heal verification FAILED — {len(issues)} issues:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    exit(1)
else:
    print("Post-heal verification PASSED — no issues.")
