# golangci-lint v1 → v2 Config Migration

**Symptom:** CI lint job fails with `unsupported version of the configuration: ""` when `golangci-lint-action` uses `version: latest` (which resolves to v2.12.2+). Or v2 loads but immediately errors with `gofmt is a formatter` or `unknown linters: 'gosimple'`.

**Root cause:** golangci-lint v2.x changes the config schema significantly. Two tiers of failure:

| Tier | Error | Cause | Fix |
|------|-------|-------|-----|
| Simple | `unsupported version of the configuration: ""` | Missing `version: "2"` | Add `version: "2"` as first line |
| Full | `gofmt is a formatter`, `unknown linters: 'gosimple'`, schema validation errors on `issues.exclude-rules` | Config structure changed in v2 | Rewrite config to v2 schema |

## Full v2 Migration Checklist

### 1. Add `version: "2"` (required)
```yaml
version: "2"
```
Must be the first line. Without it, v2 rejects the entire config.

### 2. Move gofmt/goimports to `formatters` section
In v2, formatters (gofmt, goimports, golines) live in a separate top-level section:

```yaml
# v1 (removed):
linters:
  enable:
    - gofmt
    - goimports

# v2:
formatters:
  enable:
    - gofmt
    - goimports
  settings:
    gofmt:
      simplify: true
    goimports:
      local-prefixes:
        - github.com/example/project
```

If you keep them under `linters.enable`, v2 fails with `Error: gofmt is a formatter`.

### 3. Remove `gosimple` from linters.enable
In v2, `gosimple` was removed — its checks are part of `staticcheck`. Remove it from the enable list or v2 fails with `unknown linters: 'gosimple'`.

### 4. Move `issues.exclude-rules` to `linters.exclusions.rules`
In v2, exclusion rules moved from the `issues` section to `linters.exclusions`:

```yaml
# v1 (removed):
issues:
  exclude-rules:
    - path: _test\.go
      linters: [errcheck]

# v2:
linters:
  exclusions:
    rules:
      - path: _test\.go
        linters: [errcheck]
        text: "Error return value"   # see rule #5
```

Validate with: `golangci-lint config verify` — where v1 accepted `issues.exclude-rules`, v2 rejects it with `additional properties 'exclude-rules' not allowed`.

### 5. Exclusion rules require ≥2 fields
Each `linters.exclusions.rules` entry must have at least 2 of (`text`, `source`, `path`/`path-except`, `linters`). A rule with only `path` + `linters` fails with:
```
error in exclude rule #0: at least 2 of (text, source, path[-except], linters) should be set
```
**Fix:** always include `text` (a regex matching the issue text):
```yaml
- path: _test\.go
  linters: [errcheck]
  text: "Error return value"
```

### 6. Pre-existing staticcheck checks in v2
V2 enables several new staticcheck checks by default that v1 did not. These hit on existing codebases and must be suppressed if pre-existing:

| Check | Description | Prevalence |
|-------|-------------|------------|
| `QF1001` | Could apply De Morgan's law | Common in test assertions |
| `QF1002` | Could use tagged switch on arg | Common in CLI switch blocks |
| `QF1003` | Could use tagged switch | Common in if/else chains |
| `QF1008` | Could remove embedded field from selector | Common in Go struct access |
| `QF1012` | Use fmt.Fprintf instead of WriteString(fmt.Sprintf(...)) | **Very common** — hundreds of instances in CLI output builders |
| `ST1003` | Naming conventions | Project-style preferences |
| `ST1005` | Error strings should not end with punctuation | Common in multi-line error messages |
| `ST1016` | Methods on value vs pointer receiver | Pre-existing design choice |
| `ST1020` | Exported function missing doc comment | Pre-existing documentation gap |
| `ST1021` | Exported type missing doc comment | Pre-existing |
| `ST1022` | Exported method missing doc comment | Pre-existing |

**Fix:** suppress in `linters.settings.staticcheck.checks`:
```yaml
linters:
  settings:
    staticcheck:
      checks:
        - all
        - -QF1012  # WriteString(fmt.Sprintf(...)) — pre-existing across 100+ files
        - -ST1003  # Naming conventions — pre-existing
        - -ST1005  # Error strings punctuation — pre-existing
```

### 7. errcheck `exclude-functions` still works but use simple patterns
The `exclude-functions` format for errcheck still works in v2. Use function names directly:
```yaml
linters:
  settings:
    errcheck:
      exclude-functions:
        - fmt.Fprintln
        - fmt.Fprintf
        - fmt.Fprint
        - (io.Writer).Write
        - (net/http.Flusher).Flush
```

Note: method patterns with full package paths (e.g. `(*github.com/.../Type).Method`) may not suppress correctly in v2. Use path-based exclusions in `linters.exclusions.rules` instead for stubborn cases.

### 8. `golangci-lint config verify` is your friend
After any config change, validate before running lint on the full codebase:
```bash
golangci-lint config verify
# Exit 0 = valid, exit 3 = schema error with specific message
```
This catches structural errors quickly without running the full lint.

## Foreman Fix Strategy

The foreman can apply the **full v2 migration directly** (mechanical exception) — no worker needed. The changes are config-only:

1. `patch` the `.golangci.yml` with the `version: "2"` field
2. Rewrite the config to v2 schema (formatters, exclusions moved, etc.)
3. `golangci-lint config verify` to confirm
4. `golangci-lint run ./...` — expect initial failures from new default checks
5. Add staticcheck suppressions for all pre-existing check codes
6. Add errcheck `exclude-functions` for fmt.Fprint*/Close/Flush patterns
7. `golangci-lint run ./...` — target 0 issues
8. Commit

**Proven:** Helix 2026-07-16 — full migration from `.golangci.yml` v1 → v2 in a single foreman tick. `make all` (lint 0 issues + all tests PASS + build PASS) after migration. Commit `a144d65`.

## Template

A minimal working v2 `.golangci.yml` template:

```yaml
version: "2"
formatters:
  enable:
    - gofmt
    - goimports
  settings:
    gofmt:
      simplify: true
    goimports:
      local-prefixes:
        - github.com/example/project
run:
  timeout: 5m
  go: "1.22"
linters:
  enable:
    - errcheck
    - govet
    - ineffassign
    - staticcheck
    - unused
  settings:
    staticcheck:
      checks:
        - all
        - -QF1012  # pre-existing pattern noise
    errcheck:
      exclude-functions:
        - fmt.Fprintln
        - fmt.Fprintf
        - fmt.Fprint
        - (io.Writer).Write
        - (net/http.Flusher).Flush
  exclusions:
    rules:
      - path: _test\.go
        linters: [errcheck]
        text: "Error return value"
issues:
  max-issues-per-linter: 0
  max-same-issues: 0
```

See `templates/golangci-v2.yml` for a complete working example.
