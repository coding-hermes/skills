import json
with open('~/.hermes/cron/jobs.json') as f:
    data = json.load(f)
jobs = data.get('jobs', data if isinstance(data, list) else [])
for j in jobs:
    skills = j.get('skills', [])
    name = j.get('name', '?')
    eid = j.get('id', '?')
    enabled = j.get('enabled', True)
    has_ch = any('coding-hermes' in str(s) for s in skills)
    if has_ch or (not enabled and has_ch):
        pid = j.get('provider', '?')
        model = j.get('model', '?')
        sched = j.get('schedule', {})
        sched_display = j.get('schedule_display', '?')
        wd = j.get('workdir', '?')
        lst = j.get('last_status', '?')
        sched_kind = sched.get('kind', 'N/A')
        sched_display_inner = sched.get('display', 'N/A')
        print(f'{eid}|{enabled}|{pid}|{model}|{sched_display}|{wd}|{lst}|name={name}|skills={skills}|schedule={{kind:{sched_kind},display:{sched_display_inner}}}')
