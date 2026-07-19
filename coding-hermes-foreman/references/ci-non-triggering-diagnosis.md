# CI Non-Triggering Diagnosis

When CI workflows are active and correctly configured but produce **zero runs**, this is a distinct failure mode from "CI runs but tests fail."

## Detection Pattern

```bash
# 1. Check recent CI runs
gh run list -R <owner>/<repo> --limit 20 --branch main

# 2. Check which workflows are active
gh workflow list -R <owner>/<repo>

# 3. Check workflow triggers (push events)
grep -A5 "on:" .github/workflows/*.yml | grep -E "push|pull_request" -A2

# 4. Check recent commits on the branch
git log --oneline -10
```

## Symptom

- Active workflows listed in `gh workflow list`
- Workflow YAML has correct `push: branches: [main, master]` triggers
- Multiple recent commits exist on the target branch
- `gh run list` returns zero runs (or only very old runs, e.g. dependency graph updates)
- No CI activity correlates with the recent commits

## Root Cause

This is almost always an **infrastructure issue**, not a code problem:

1. **GitHub Actions billing exhausted** — org/account has run out of minutes or credits
2. **Actions disabled at org level** — organization owner disabled Actions for the repo or org
3. **Workflow restrictions** — org-level workflow permissions block the workflow from running
4. **Branch protection bypass** — the branch name doesn't match the workflow's branch filter (e.g. workflow targets `main` but branch is `master`)

## Response

**Do NOT create code-fix tasks.** This is an infrastructure issue. Create:

```
## [ ] [INFRA] CI not triggering — workflows active but zero runs since <date>
```

The foreman cannot fix GitHub billing or org settings. Flag it and move on.

## Proven Instances

| Date | Repo | Commits | Last CI Run | Likely Cause |
|------|------|---------|-------------|--------------|
| 2026-07-13 | dexdat/dexdat-memory | 9 on master since Jul 11 | Jul 3 (Dependency Graph only) | Billing/runner availability |
