# Foreman Self-Alignment Prompt

Run this prompt against any coding-hermes foreman cron to bootstrap it into the new skill architecture. The foreman will read all updated skills, detect changes, self-correct its configuration, and produce a result.

## Usage

```
hermes cron list  # find the foreman's job_id
cronjob(action="run", job_id="<id>")
```

Or run independently:

```
hermes chat -q "$(cat ~/.hermes/skills/coding-hermes-foreman/references/self-alignment-prompt.md)"
```

## Prompt

```
You are a coding-hermes foreman. Your skills have been completely rebuilt. Read and align.

LOAD THESE SKILLS IN ORDER:
1. coding-hermes-north-star — understand the 3-tier architecture, your role, and your escalation path
2. coding-hermes-cron — understand the canonical cron shape, provider rules, and infrastructure protections  
3. coding-hermes-foreman — this is YOUR skill. It has been rewritten from a checklist into a full 12-step SDLC delivery loop

AFTER READING, ANSWER THESE QUESTIONS:
1. What changed in how you spawn workers? (Hint: delegate_task is no longer correct)
2. What provider must you ALWAYS use? Why?
3. What is the ordered discovery sweep? When do you run it?
4. What is Step 1.6 and why does it matter?
5. What do you do when a worker's prepaid bucket returns 429?
6. When should a guard failure NOT block your commit?

THEN:
- Run `hermes cron list` and verify your OWN cron configuration matches the canonical shape in coding-hermes-cron
- If your provider is NOT deepseek-foreman (PAYG), fix it immediately with `hermes cron edit <your_id> --provider deepseek-foreman`
- If your skills array does NOT include coding-hermes-foreman, fix it with `hermes cron edit <your_id> --skill coding-hermes-foreman --skill coding-hermes-cron --skill hilo-usage --skill gitreins`
- Run your next tick and produce a result. Deliver it here. Show me you understand the new system.
```

## Expected Self-Corrections

Foremen running this prompt should detect and fix:

1. **Provider drift** — foreman on opencode-go (prepaid) instead of deepseek-foreman (PAYG)
2. **Skill array stale** — still loading old `coding-hermes` instead of `coding-hermes-foreman`
3. **schedule.expr missing** — cron-kind jobs without `expr` field
4. **kind: "every"** — legacy format that needs conversion to `kind: "interval"`
5. **state: "completed"** — job finished but not reset to `scheduled`
6. **Worker spawn pattern** — should use `hermes chat -q` not `delegate_task`

## Validation

After alignment, verify with:

```bash
hermes cron list | grep -A8 "<foreman-name>"
```

Expected:
- Provider: deepseek-foreman
- Skills: coding-hermes-foreman, coding-hermes-cron, hilo-usage, gitreins
- State: scheduled
- Schedule.expr: present (not null/empty)
