# Dummy Project Testing Pattern

## When to use
When you need to test the scheduler's real-world timing, concurrency, weight-budget
packing, and cooldown behavior WITHOUT burning LLM tokens or touching production
projects.

## How it works
1. Create a directory of dummy "projects" — each is a shell script that mimics a
   foreman tick (outputs session_id, sleeps for a duration, prints fake build steps).
2. Register them in the scheduler DB with a custom `Command` field pointing to the
   shell script.
3. When the scheduler spawns the project, it execs the script directly instead of
   `hermes chat -q`.
4. The script's stdout is parsed for `session_id: <id>`, same as real foremen.
5. Outcomes are recorded as real ticks — completed/failed/timeout based on exit code.

## Dummy script template
```bash
#!/bin/bash
# Place in /tmp/dummy-projects/<name>/foreman.sh
DURATION=${1:-5}
echo "session_id: dummy-$(basename $(dirname $0))-$(date +%s)-$$"
echo "$(date -Iseconds) [$0] Foreman tick started — sleeping ${DURATION}s..."
sleep "$DURATION"
echo "$(date -Iseconds) [$0] Build step 1: lint — PASS"
sleep 1
echo "$(date -Iseconds) [$0] Build step 2: test — PASS"
echo "$(date -Iseconds) [$0] Foreman tick complete — 2 commits, 3 files changed"
exit 0
```

## Registration
```bash
curl -X POST http://127.0.0.1:9090/api/v1/projects \
  -H 'Content-Type: application/json' \
  -d '{"Name":"dummy-alpha","Workdir":"/tmp/dummy-projects/alpha","Weight":30,"Priority":9,"CooldownS":60,"Enabled":true,"Command":"bash /tmp/dummy-projects/alpha/foreman.sh 8"}'
```

## Test scenarios this enables
- **Weight budget exhaustion**: Set up projects totaling >100 weight, verify only N pack
- **Concurrency capping**: 12+ projects, max-concurrent=6, verify only 6 run
- **Cooldown rotation**: Short cooldowns (5-30s), run multiple evals, verify different projects each tick
- **Starvation detection**: Low-priority projects with long intervals — verify they eventually run
- **Timeout handling**: Script with `sleep 9999` — verify scheduler marks as timeout after spawn timeout
- **Failure recovery**: Script exits 1 — verify scheduler marks as failed, retries on next interval
- **Disable/enable at runtime**: PUT to disable a project mid-fleet, verify it drops out

## Key difference from --simulate mode
- `--simulate` generates synthetic ticks instantly with randomized outcomes
- Dummy projects spawn REAL processes with REAL timing → tests actual spawner/wait loop
- Use simulation for schema/data tests, dummy projects for timing/concurrency tests

## Built-in verification: `--test-verify N`
The scheduler ships with a self-contained correctness verifier:
```
./bin/schedulerd --test-verify 5
```
- Creates a temp DB, registers a 7-project test fleet with known weights/priorities/sleeps
- Runs N evaluation cycles with real spawning (shell scripts, not simulated)
- Checks 6 invariants: no hangs, full coverage, budget capping, no dupes, session IDs, priority ordering
- Exit 0 = all pass, exit 1 = failures found
- Temp DB cleaned on exit. Use for pre-commit hooks, CI smoke, idle-time health checks.

## Pitfall: splitCommand destroys shell quoting
When registering projects with `Command: "bash -c 'echo session_id: ...; sleep 5; ...' "`,
the naive `splitCommand()` function breaks the single-quoted script into separate args.
Result: the script fragment executes as `echo 'echo'` (wrong) and no session_id appears.
**Fix**: detect `bash -c` prefix in spawn.go and pass the script string directly to
`exec.Command("bash", "-c", script)` without splitting. Do not run shell one-liners through
splitCommand.

## Pitfall: trailing comma after sed-driven column rename
When replacing a two-column CREATE TABLE (e.g. `min_interval` + `max_interval`) with a single
column (`cooldown_s`), the leftover trailing comma after the last column causes SQLite syntax
error "near ')'". After any sed-driven schema edit, verify no trailing comma before `)`.
