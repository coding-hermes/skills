# Bankai Pattern — Aggressive Parallel Fix Sweep

The user says "bankai" to mean: fix EVERYTHING, all at once, as fast as possible, then re-audit. This is a Bleach reference (final form, full power release).

## When to Bankai

- After an audit produces 5+ findings
- When the user says "bankai", "go all out", "fix everything"
- When the board has many pending tasks and the user wants them done NOW

## How to Bankai

### 1. Dispatch ALL tasks in parallel

Use `delegate_task` with `role='orchestrator'` and the `tasks` array:

```typescript
delegate_task(
  role='orchestrator',
  tasks=[
    {goal: "Fix X", context: "repo path, branch, files to touch"},
    {goal: "Fix Y", context: "repo path, branch, files to touch"},
    // ... all remaining tasks
  ]
)
```

**Do NOT serialize** — all tasks dispatch at once. The orchestrator waits for all to finish.

### 2. Handle timeouts

Kimi K3 workers often timeout at 600s but complete the actual code changes. After the batch returns:

1. Check `git status` for uncommitted changes
2. Check `git diff --stat` for modified files
3. `git add -A && git commit` everything in one sweep commit
4. Mark all associated GitReins tasks complete

### 3. Register as GitReins tasks

Before or during dispatch, register each finding as a GitReins task:

```typescript
mcp__gitreins__task_create(
  id="K3-H1-...",
  title="...",
  criteria=["...", "...", "..."],
  workdir="~/<project>"
)
```

This lets the foreman track and verify completion.

### 4. Mark complete + commit

After all fixes land:

```bash
python3 -c "
import yaml
with open('.gitreins/tasks.yaml') as f: data = yaml.safe_load(f)
for t in data['tasks']:
    if t['status'] == 'pending' and 'K3-' in t['id']:
        t['status'] = 'complete'
with open('.gitreins/tasks.yaml', 'w') as f: yaml.dump(data, f)
"
git add .gitreins/tasks.yaml && git commit -m "task: mark all K3 tasks complete (bankai sweep)"
```

### 5. Run next review

After the bankai sweep commits, run a narrower second review to catch what was missed.

## Bankai Cycle

```
Audit → Dispatch ALL → Timeout recovery → Commit sweep → Mark complete → Re-audit (narrower scope)
```

Each cycle should be narrower: first round covers all categories, second round is security-only, third round is data-integrity-only.

## Pitfalls

- **Don't wait for individual workers** — dispatch all at once
- **Workers timeout but complete work** — always check uncommitted changes after batch returns
- **tsx file watcher may not detect changes** — after committing, `docker restart` the container. If API still shows old results, `docker cp` + `touch` the file inside the container
- **npm registry may be unreachable** — if `docker compose build` fails with EAI_AGAIN, accept the container's current state and note the blocker
