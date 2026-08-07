# Migrating Cron Jobs to the Scheduler

## Detection

Find cron jobs that should move to the scheduler:

```bash
python3 -c "
import json
with open('~/.hermes/cron/jobs.json') as f:
    data = json.load(f)
for j in data['jobs']:
    name = j.get('name','')
    skills = str(j.get('skills',[]))
    paused = j.get('paused_at')
    enabled = j.get('enabled',True)
    # Only show active, non-paused crons
    if enabled and not paused:
        print(f'{j[\"job_id\"][:16]:16s} {name:40s} {j.get(\"schedule\",\"?\"):30s} skills={skills[:60]}')
"
```

## Two Migration Paths

### Path A: Standard Foreman (most projects)

If the cron loads `coding-hermes-foreman` + `coding-hermes-cron`, it's a standard foreman. Register it:

```bash
curl -X POST http://127.0.0.1:9090/api/v1/projects \
  -H 'Content-Type: application/json' \
  -d '{"Name":"my-project","RepoURL":"local:~/my-project",
       "Workdir":"~/my-project","Weight":10,"Priority":5,
       "CooldownS":900,"Deliver":"telegram:-1003310984808:THREAD_ID",
       "NamespaceID":"coding-hermes"}'
```

Then enable and pause the cron.

### Path B: Custom Skill / Non-Foreman (specialized tasks)

If the cron uses a non-foreman skill (e.g., `<project>-e2e-flows`, browser tester, data pipeline), use a **custom command**:

```bash
curl -X POST http://127.0.0.1:9090/api/v1/projects \
  -H 'Content-Type: application/json' \
  -d '{"Name":"<project>-e2e","RepoURL":"https://github.com/<project>/<project>",
       "Workdir":"~/<project>","Weight":10,"Priority":5,
       "CooldownS":3600,"Deliver":"telegram:-1003310984808:50253",
       "Command":"hermes chat -q \"Load skill <project>-e2e-flows. Execute one flow per tick.\""}'

# Enable (create API doesn't set Enabled=true)
curl -X PUT http://127.0.0.1:9090/api/v1/projects/<project>-e2e \
  -H 'Content-Type: application/json' \
  -d '{"Enabled":true}'
```

**Important:** The scheduler's create-project API doesn't set `Enabled=true` on creation. You must enable it via PUT after creation. The `NamespaceID` is also required when `--namespace-mode` is on.

**Custom command format:** `hermes chat -q "Load skill <skill-name>. <prompt>."`

The scheduler will spawn this via `exec.Command` (not HTTP gateway) because custom command projects bypass the gateway path. This is acceptable for low-frequency jobs (every 1-2 hours).

**Pitfall:** Custom-command projects that use browser or terminal-heavy skills (`<project>-e2e-flows`, `browser-e2e-tester`) still spawn `hermes chat` subprocesses — they can't use the HTTP gateway path. Weigh this against the frequency: every 120m is fine; every 5m would cause duplication overhead.

## Post-Migration Verification

```bash
# 1. Verify cron is paused
python3 -c "import json;d=json.load(open('~/.hermes/cron/jobs.json'));j=[x for x in d['jobs'] if x['job_id']=='<JOB_ID>'][0];print(f'enabled={j.get(\"enabled\")} paused_at={j.get(\"paused_at\")}')"

# 2. Verify scheduler has the project
curl -s http://127.0.0.1:9090/api/v1/projects/<PROJECT_NAME> | python3 -m json.tool | grep -E "Name|Enabled|CooldownS|Last"

# 3. Wait for next eval cycle (up to min_interval + cooldown)
sleep 120

# 4. Check if tick was spawned
curl "http://127.0.0.1:9090/api/v1/ticks?limit=5" | python3 -m json.tool | grep <PROJECT_NAME>

# 5. If no tick after 5 minutes, force eval
curl -X POST http://127.0.0.1:9090/api/v1/evaluate
```

## Proven Migrations (2026-07-18)

| Cron | Scheduler Project | Path | Result |
|------|-------------------|------|--------|
| h3-foreman-bootstrap (every 5m) | h3 (600s cooldown) | A | Active |
| <project> Browser E2E Tester (every 120m) | <project>-e2e (3600s cooldown) | B | Active |
| <project>-foreman (every 30m) | <project> (900s cooldown) | A | Active |
| <project>-foreman (every 30m) | <project> (900s cooldown) | A | Active |
| helix-foreman (every 30m) | helix (600s cooldown) | A | Active |
| <project>-foreman (every 60m) | <project> (7200s cooldown) | A | Active |
