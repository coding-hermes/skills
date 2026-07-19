# Deploy Docs to GitHub Pages — Infrastructure Diagnosis

## Failure Signature

The `Deploy Docs to GitHub Pages` workflow fails at the "Setup Pages" step with:
```
X Setup Pages
X HttpError: Not Found
```

## Root Cause

The `actions/configure-pages@v4` action returns `HttpError: Not Found` when GitHub Pages is NOT configured for the repository. This is a **repository settings issue**, not a code or workflow issue.

## Required Fix (not automatable from CLI)

The repo must have Pages enabled in its Settings with the source set to "GitHub Actions":

1. Go to `https://github.com/<org>/<repo>/settings/pages`
2. Under "Source", select "GitHub Actions"
3. No code changes needed — re-run the workflow

## Classification

This is an **infrastructure failure**, not a code failure. Per `coding-hermes-foreman` Step 1.5e (CI infrastructure vs code failure classification):

- All workflows fail at the same infra step? → Infra issue
- Markdown-only commits fail identically to code commits? → Infra issue
- CI workflow `actions/configure-pages@v4` fails with `HttpError: Not Found`? → Infra issue

Do NOT create code-fix tasks for this. Create `## [ ] INFRA — configure Pages for <repo>` at most.

## Proof

| Date | Repo | Run | Step | Error |
|------|------|-----|------|-------|
| 2026-07-14 | gethilo/hilo | 29361215109 | Setup Pages | HttpError: Not Found |
| 2026-07-14 | gethilo/hilo | 29313502081 | Setup Pages | HttpError: Not Found |

Workflow: `.github/workflows/pages.yml` was correct (`permissions: pages: write`, `actions/configure-pages@v4`). The Pages configuration simply didn't exist at the repo level.
