# GitHub Pages Static-Site Verification — Discovery Sweep Pattern

## When to Use

The project is a static site (single HTML file, Jekyll/Hugo site, SPA build output) deployed via GitHub Pages. The discovery sweep's standard API-endpoint checks (`/health`, `/api/status`) don't apply — there's no backend server. The CI model is GitHub's built-in Pages deployment, not an action-based workflow.

## Detection

```bash
git remote -v
# → origin  https://github.com/<owner>/<repo>.git

# Check deployment URL from the project's README or GitHub Pages config
# Common patterns:
#   https://<owner>.github.io/<repo>/
#   https://<custom-domain>/

# No .github/workflows/ directory is NORMAL for built-in Pages
ls .github/workflows/ 2>/dev/null || echo "No workflows directory (built-in Pages)"
```

## Step 1.5b — Live Endpoint Check

For API projects:
```bash
curl -s http://localhost:<port>/health
curl -s https://<deployed-url>/api/status
```

For static HTML projects:
```bash
# HTTP check
curl -s -o /dev/null -w "HTTP %{http_code}" https://<owner>.github.io/<repo>/
# Expected: HTTP 200

# File size check (compare to local)
echo "Deployed: $(curl -s https://<owner>.github.io/<repo>/ | wc -c) bytes"
echo "Local:    $(wc -c < index.html) bytes"

# Byte-identity verification (most thorough)
LOCAL_MD5=$(md5sum index.html | awk '{print $1}')
DEPLOYED_MD5=$(curl -s https://<owner>.github.io/<repo>/ | md5sum | awk '{print $1}')
if [ "$LOCAL_MD5" = "$DEPLOYED_MD5" ]; then
    echo "✅ Byte-identical deployment"
else
    echo "⚠️ Deployed file differs from local — deployment may be stale"
fi
```

## Step 1.5e — CI Audit for Built-in Pages

GitHub Pages auto-deployment has NO workflow file. All deployment state is in `gh run list`:

```bash
# List recent deployments (all are "pages build and deployment")
gh run list -R <owner>/<repo> --limit 5

# Check if the LATEST commit is deployed
# Match deployment timestamps against commit timestamps
echo "Latest commit: $(git log -1 --format='%ai %s')"
echo "Latest deploy: $(gh run list -R <owner>/<repo> --limit 1 --json createdAt,conclusion --jq '.[0].createdAt')"
```

**Deployment staleness check:** If `gh run list` shows the last successful deployment predates the latest commit by more than a few hours, the Pages auto-deploy may be blocked (billing, Actions disable). Create `## [ ] INFRA — GitHub Pages deployment stale (<date>), commits since <commit>`.

## Step 1.5d — CDN Version Cross-Reference (instead of npm audit)

CDN-only projects have NO `package.json` or lockfile. Running `npm audit --production` produces `ENOLOCK` — this is expected, not an error worth investigating. Skip npm/pip security scanning entirely.

Instead, verify documentation matches the actual CDN imports:

```bash
# Extract CDN versions from HTML
grep -oP 'cdnjs\\.cloudflare\\.com/ajax/libs/[^/]+/\\K[0-9]+\\.[0-9]+\\.[0-9]+' index.html
grep -oP 'cdn\\.jsdelivr\\.net/npm/[^@]+\\K@[0-9]+\\.[0-9]+\\.[0-9]+' index.html

# Extract documented versions from README/SKILL.md
grep -oiP '[a-z.-]+ [0-9]+\\.[0-9]+\\.[0-9]+' README.md SKILL.md

# Cross-reference — every CDN version in HTML should appear in docs
```

If a CDN version was bumped in the HTML but docs weren't updated, create a `## [ ] DOC` task.

CDN-only projects also skip:
- `govulncheck` / `pip-audit` / `cargo-audit` (no local packages to scan)
- Dependency integrity checks (1.5e — no packages to verify)
- Build verification (1.5a — no build step, just validate the HTML file exists and has valid script/import tags)

## Step 1.5c — No Build Step

Single-file HTML projects have no build step, no test framework, no npm/node_modules. This is normal:

- `make build` → not applicable (skip)
- `npm test` → not applicable (skip)
- `npx tsc --noEmit` → not applicable (skip)

The discovery sweep should not flag "no build system" as a gap. Check only for actual TODO/FIXME/HACK in the HTML source.

## Workflow-Based Pages Deployment Detection

Not all Pages deployments use the built-in auto-deploy. Some projects use a workflow-based approach with `actions/configure-pages@v4`, `actions/upload-pages-artifact@v3`, and `actions/deploy-pages@v4`:

```bash
ls .github/workflows/pages.yml 2>/dev/null
# Detection: workflow file exists + check build_type
gh api repos/<owner>/<repo>/pages --jq '.build_type'
# → "workflow" (instead of "legacy" for auto-deploy)
```

Workflow-based Pages deployments upload raw files from a `path:` directory (e.g., `path: docs`). The workflow does NOT build or transform files — whatever is in the directory gets uploaded as-is.

## Critical: index.html Required for Root URL

**GitHub Pages does NOT render `index.md` to `index.html`.** When the `docs/` directory contains only `.md` files:

```bash
# deploy succeeds (all steps green) but root URL returns 404
curl -s -o /dev/null -w "HTTP %{http_code}" https://<owner>.github.io/<repo>/
# → HTTP 404

# individual .md files are served as raw text
curl -s -o /dev/null -w "HTTP %{http_code}" https://<owner>.github.io/<repo>/index.md
# → HTTP 200
```

**Fix:** create `docs/index.html` as a landing page with links to all doc files. Use a simple dark-themed HTML page matching GitHub's color scheme.

## Verification After index.html Fix

```bash
curl -s -o /dev/null -w "HTTP %{http_code}" https://<owner>.github.io/<repo>/
# → HTTP 200 ✅
```

## Common Pitfalls

- **Last deployment predates HEAD commit**: GitHub Pages auto-deploy can stall silently (billing, Actions disable). Always check timestamps.
- **Deployed file differs from local**: Someone pushed a stale branch or deployment failed silently. The MD5 check catches this.
- **CDN version drift**: README says Chart.js 4.4.1 but HTML loads 4.4.7. Common when dev bumps CDN URLs but forgets docs.
- **`gh run list` shows "cancelled" alongside "success":** Cancelled runs are normal — they're superseded by newer commits. Look at the latest successful run's created_at, not the cancelled ones.

## Proven

DeepSeek Dashboard — 2026-07-15: Single-file HTML dashboard (2,426 lines, Chart.js + JSZip + sql.js, GitHub Pages auto-deploy). Discovery sweep used MD5 byte-identity check to confirm deployment matches local (both `80b9c60a5b5267e589ece541ec433741`). No `.github/workflows/` directory (normal for built-in Pages). CDN versions cross-referenced and matched. Zero gaps found — board remained empty.
