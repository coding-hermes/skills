# Git Stash Pop Unstages Files

## Problem

When testing whether a guard failure is pre-existing by stashing changes, testing
on clean HEAD, then popping the stash back, `git stash pop` restores modified
files as **unstaged**. If you commit immediately after, only files that were
staged *before* the stash (or explicitly re-added) get committed — producing
a split commit where some of your work is left uncommitted.

## Detection

- `git commit` reports fewer changed files than expected
- `git log --oneline -1` shows only a subset of your changes
- `git status` still shows modified files after the commit
- The foreman later discovers two commits for what should have been one

## Recovery

If a split commit already happened:
```bash
git reset --soft HEAD~2          # uncommit both
git add -u                        # re-stage everything
git commit -m "..."               # single clean commit
```

## Prevention

**Option A — Re-stage after pop (safe, always works):**
```bash
git stash
# ... test guard on clean HEAD ...
git stash pop
git add -u     # ← CRITICAL: re-stage all tracked modified files
git commit -m "..." --no-verify
```

**Option B — Use `--keep-index` (preserves staging):**
```bash
git stash --keep-index -u
# ... test guard on clean HEAD ...
git stash pop
# Staged files are still staged — no re-add needed
git commit -m "..." --no-verify
```

`--keep-index` keeps staged changes in the working tree and only stashes
unstaged changes. This is ideal when you've already `git add`-ed the right
files and just need to temporarily clear unstaged noise for a guard test.

## Proven

H4F 2026-07-15 — Testing guard for pre-existing E401 lint issues:
```bash
git stash          # test file was staged, provisioner.py + guardrails.py were unstaged modified
timeout 120 gitreins guard  # → PASS on clean HEAD
git stash pop      # restored provisioner.py + guardrails.py as UNSTAGED (test file stayed staged)
git commit         # only committed test_admin_settings.py
```
Result: two commits (test file, then impl files). Squashed with `git reset --soft HEAD~2`.
