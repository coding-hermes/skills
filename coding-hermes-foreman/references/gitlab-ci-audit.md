# GitLab CI Audit — Discovery Sweep Pattern

## Problem

The foreman discovery sweep (Steps 1.5e, 1.6) uses `gh run list -R <repo>` for CI audit. On GitLab-hosted projects, this returns HTTP 404 because `gh` only works with GitHub.

## Detection

```bash
gh run list -R <repo> --limit 5
# → failed to get runs: HTTP 404: Not Found
```

## Root Cause

The project is hosted on GitLab, not GitHub. Confirm with:

```bash
git remote -v
# → origin  git@gitlab.readydedis.com:<org>/<repo>.git
```

## CI Audit for GitLab Projects

GitLab CI audit is file-existence based since there's no `glab` CLI equivalent for run lists:

```bash
# Check if CI pipeline file exists
ls .gitlab-ci.yml 2>/dev/null || echo "No .gitlab-ci.yml"
```

If no CI pipeline file exists, create `## [ ] CI — Missing .gitlab-ci.yml, no pipeline configured` on the board.

GitLab CI status can be checked via the web UI at `https://gitlab.readydedis.com/<org>/<repo>/-/pipelines` but automated API access requires a GitLab PAT (usually not configured). The file-existence check is sufficient for discovery sweep purposes.

## Creating a GitLab CI Pipeline

Basic Go project template:

```yaml
stages:
  - build
  - vet
  - test
  - lint

variables:
  GO_VERSION: "<from go.mod>"
  GOMODCACHE: $CI_PROJECT_DIR/.go/pkg/mod

cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - .go/pkg/mod/

before_script:
  - go version

build:
  stage: build
  image: golang:${GO_VERSION}-alpine
  script: go build ./...

vet:
  stage: vet
  image: golang:${GO_VERSION}-alpine
  script: go vet ./...

test:
  stage: test
  image: golang:${GO_VERSION}-alpine
  script: go test ./... -race -count=1 -short

lint:
  stage: lint
  image: golangci/golangci-lint:v2.1-alpine
  allow_failure: true
  script: golangci-lint run ./...
```

This is a foreman-direct task (config file, no worker needed). Use the shortened loop.

## Proven

ASCE 2026-07-14 — `gh run list` returned 404; `git remote -v` confirmed GitLab hosting; `.gitlab-ci.yml` did not exist; foreman created it directly (commit `6eaddcb`).
