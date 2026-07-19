# Go Lint Fix Patterns — Foreman-Direct Mechanical Cleanup

This document covers common golangci-lint issue categories and the safe, proven fix
patterns for each. These are mechanical fixes the foreman can apply directly
(Exception #2: mechanical cleanup).

## Fix Patterns by Linter

### gocritic: unlambda
**Issue:** `RunE: func(cmd *cobra.Command, args []string) error { return someFunc(cmd, args) }`  
**Fix:** `RunE: someFunc`  
**Pitfall:** Only works when the wrapper function matches the `RunE` signature exactly
(`(cmd *cobra.Command, args []string) error`).

### gocritic: captLocal
**Issue:** `func foo(L *lua.LState)` — parameter `L` is capitalized.  
**Fix:** Rename parameter to lowercase: `func foo(lState *lua.LState)`  
**CRITICAL:** Must rename ALL references to the parameter within the function body.
Watch for inner closures that shadow the parameter with their own `L` — those
stay as-is (they're separate scope). Only rename the outer function's references.

### gocritic: exitAfterDefer
**Issue:** `os.Exit(m.Run())` in `TestMain` after `defer os.RemoveAll(...)`  
**Fix:** Add `//nolint:gocritic // TestMain must call os.Exit` comment.  
Do NOT restructure `TestMain` — the pattern is idiomatic.

### gocritic: assignOp
**Issue:** `x = x / 2`, `x = x + y`  
**Fix:** `x /= 2`, `x += y` — straightforward operator substitution.

### gosimple: S1000 — single-case select
**Issue:** `select { case <-ch: return }`  
**Fix:** `<-ch; return` or just `<-ch` if the function returns after.

### gosimple: S1009 — nil check before len()
**Issue:** `if x != nil && len(x) > 0`  
**Fix:** `if len(x) > 0` — `len()` returns 0 for nil maps/slices.

### gosimple: S1017 — conditional TrimPrefix
**Issue:** `if strings.HasPrefix(s, "/") { s = s[1:] }`  
**Fix:** `s = strings.TrimPrefix(s, "/")` — unconditional, same result.

### gosimple: S1023 — redundant return
**Issue:** `return` statement at end of function where `<-ch` already blocks.  
**Fix:** Remove the redundant `return`.

### errcheck: deferred cleanup (CI lint — exclude-list pattern)

**Issue:** `golangci-lint run ./...` flags deferred cleanup calls as unchecked:
```go
defer os.RemoveAll(tmpDir)   // flagged: Error return value not checked
defer db.Close()             // flagged: Error return value not checked
```

**Fix (test/setup code):** Add the functions to `.golangci.yml`'s `errcheck.exclude-functions` list
instead of using `_ =` or `//nolint` on every call site. These are intentionally
unchecked — deferred cleanup where there is nothing useful to do with the error:

```yaml
linters:
  settings:
    errcheck:
      exclude-functions:
        - os.RemoveAll
        - (*database/sql.DB).Close
        - (*database/sql.Rows).Close
        - (io.ReadCloser).Close
```

**Decision tree:**
| Pattern | Fix |
|---------|-----|
| Deferred in `main()`, `TestMain`, or setup helpers | Add to `.golangci.yml` exclude-functions list |
| Deferred in test subtests | Same — test teardown is not error-recoverable |
| Direct calls where error matters | Fix with proper error handling |
| Rare one-off function | `//nolint:errcheck` on that line |

**Why the exclude list is better:** (1) Single config change vs N `//nolint`
directives. (2) New deferred cleanup calls in other files won't trigger new lint
failures. (3) The `_ = func()` pattern is noise.

**Proven:** coding-hermes scheduler (2026-07-17) — `os.RemoveAll` and `db.Close`
in `cmd/schedulerd/test_verify.go`. Added both to exclude list → 0 issues.
Commit `2abf7e1`.

### errcheck: deferred `os.Remove` in production code — log-and-continue

**Issue:** `defer os.Remove(f.Name())` in production code (not test setup).
```go
f, err := os.CreateTemp("", "chtick-*.txt")
if err != nil { return }
defer os.Remove(f.Name())   // flagged: Error return value not checked
```

**Fix:** Wrap in an anonymous func that logs the error:
```go
defer func() {
    if err := os.Remove(f.Name()); err != nil {
        log.Printf("cleanup temp file %s: %v", f.Name(), err)
    }
}()
```

**Why NOT the exclude-list:**
- Production code needs to surface cleanup failures (disk full, permissions).
- The exclude-list is for test/setup teardown where failures are noise.
- A bare `_ = os.Remove(...)` hides the failure with no trace.

**Why NOT a nolint comment:**
- A single deferred `os.Remove` in production warrants error logging.
- The log line provides observability that would otherwise be lost.

**Proven:** Scheduler `deliver.go:36` (2026-07-18) — `defer os.Remove(f.Name())`
flagged by golangci-lint v2.12.2 errcheck. Wrapped with error logging.

### errcheck: `io.Closer.Close()` in a context-cancellation goroutine

**Issue:** `stdout.Close()` inside a goroutine that fires when a context expires.
```go
go func() {
    <-scanCtx.Done()
    stdout.Close()    // flagged: Error return value not checked
}()
```

**Fix:** Suppress with `_ =`:
```go
go func() {
    <-scanCtx.Done()
    _ = stdout.Close()    // closing a pipe on context expiry — nothing to do on error
}()
```

**Why `_ =` is correct here:**
- The goroutine's sole purpose is to unblock `scanner.Scan()` via pipe closure.
- If `Close()` fails, the pipe may be already closed or the process already dead.
- There is no meaningful recovery action — logging would be noise at shutdown.
- Unlike a deferred cleanup in production code (where error logging matters),
  this is a one-shot context-cancellation signal with no caller to report to.

**Decision: `_ =` vs error logging vs exclude-list**

| Context | Fix | Rationale |
|---------|-----|-----------|
| Deferred cleanup in tests | `.golangci.yml` exclude-list | Teardown — noise if flagged |
| Deferred cleanup in production | Log-and-continue wrapper | Observability matters |
| goroutine shutdown path | `_ =` | No caller, no recovery possible |
| Direct call where error matters | Proper error handling | Contract enforcement |

**Proven:** Scheduler `spawn.go:181` (2026-07-18) — `stdout.Close()` in a
context-cancellation goroutine. Suppressed with `_ =`.

### errcheck: `http.Response.Body.Close()` in HTTP client code

**Issue:** `defer resp.Body.Close()` — golangci-lint errcheck flags the unchecked
error return from `Close()`. This is the single most common errcheck hit in any
Go code that makes HTTP calls.

```go
resp, err := g.httpClient.Do(req)
if err != nil {
    return err
}
defer resp.Body.Close()   // flagged: Error return value not checked
```

**Fix:** Wrap in an anonymous func that discards the error:
```go
defer func() { _ = resp.Body.Close() }()
```

**Why NOT the exclude-list for `io.ReadCloser.Close`:**
Adding `io.ReadCloser.Close` to the errcheck exclude-functions list is TOO BROAD.
`http.Response.Body` is an `io.ReadCloser` but there are other ReadClosers where
you genuinely want the error checked (file handles, pipes). The exclude-list
entry would suppress ALL ReadCloser.Close calls across the entire codebase.

**Why `_ =` inline (not a defer wrapper) does not work:**
`_ = resp.Body.Close()` without `defer` closes the body BEFORE it is read.
Must be `defer func() { _ = resp.Body.Close() }()`.

**Decision table for `Close()` errcheck fixes:**

| Pattern | Fix | When |
|---------|-----|------|
| `defer resp.Body.Close()` (HTTP) | `defer func() { _ = resp.Body.Close() }()` | Always — standard Go idiom |
| `defer os.RemoveAll(dir)` (test) | Add to `.golangci.yml` exclude-list | Test teardown |
| `defer db.Close()` (test) | Add to `.golangci.yml` exclude-list | Test teardown |
| `defer os.Remove(f)` (prod) | `defer func() { log if err }()` | Production observability |
| `pipe.Close()` in goroutine | `_ = pipe.Close()` | Shutdown, no caller |

**Proven:** Scheduler `gateway_client.go:98` and `gateway_client.go:129` (2026-07-18) —
two occurrences in FEAT-003's gateway client. Fixed with defer-wrapping in commit
`e880786`.

### errcheck: unchecked return in test setup

**Issue:** `http.Post(url, ct, body)` — return values (resp, error) completely unchecked.
Common in test files where the call is setup/fire-and-forget.

**Fix:** Add error checking with `:=` — NOT `=`:
```go
_, err := http.Post(ts.URL+"/v1/process", "application/json", strings.NewReader(body))
if err != nil {
    t.Fatalf("POST /v1/process (setup): %v", err)
}
```

**Pitfall — `=` vs `:=` scoping:** When the function has no prior `err` declaration,
`_, err =` fails with "undefined: err". Use `_, err :=` to declare `err` in the
current scope. **Proven:** H3 Go SDK LINT-S01 (2026-07-15).

### noctx: bare http.Get
**Issue:** `resp, err := http.Get(url)`  
**Fix:** Use cobra command context when available:
```go
req, err := http.NewRequestWithContext(cmd.Context(), "GET", url, nil)
if err != nil {
    return fmt.Errorf("failed to create request: %w", err)
}
resp, err := http.DefaultClient.Do(req)
```
**Pitfall:** The function must have access to `cmd *cobra.Command`. If not available,
use `context.Background()`.

### staticcheck: SA4006 — unused value
**Issue:** `plugin, err := pm.Get("name")` — `plugin` never used before reassignment.  
**Fix:** Use `_, err := pm.Get("name")` for the first call. If the same variable is
redeclared later with `=` (not `:=`), change that to `:=`.

### staticcheck: SA4031 — nil check never true
**Issue:** `if registry == nil { ... }` after `registry := &Thing{...}`  
**⚠️ DANGER — do NOT remove the nil check or change to different assertion without
reading the full test.**  
**Pitfall:** Removing the nil check can break the test if the test body is the
only thing verifying the construction. The `//nolint:staticcheck` approach is
safer:
```go
if registry == nil { //nolint:staticcheck // SA4031: canary check
    t.Error("expected non-nil registry")
}
```
**Why not fix it differently?** Attempts that broke the test:
- `if len(registry.functions) == 0` — map is always empty after make(), fails test
- `if registry.functions == nil` — make() always returns non-nil, same problem
- Removing the check entirely — test becomes a no-op, loses the canary

### stylecheck: ST1003 — wrong capitalization
**Issue:** `func starlarkHttpFunc` → should be `func starlarkHTTPFunc`  
**Fix:** Rename the function AND search for ALL callers — test files, registrations,
closures. Miss one caller and the build breaks.

## golangci-lint v2 Schema Migration

When CI linter version upgrades to v2, the `.golangci.yml` config must be migrated
from v1 to v2 schema. v2 has a completely different configuration structure.

**Symptom:** CI lint job fails with "unsupported version of the configuration"
or v2 ignoring v1-format settings.

**v1 → v2 schema changes:**

| v1 key | v2 key |
|--------|--------|
| `linters-settings:` | `linters.settings:` |
| `linters:` | `linters.enable:` |
| `exclude-rules:` | `linters.exclusions.rules:` |
| `issues.exclude-rules:` | `linters.exclusions.rules:` |
| `run:` | (removed — use CLI flags) |

**Required top-level field:** `version: "2"` — required by golangci-lint >= v2.

**formatters section (new in v2):**
```yaml
formatters:
  enable:
    - gofmt
    - goimports
  settings:
    gofmt:
      simplify: true
    goimports:
      local-prefixes:
        - github.com/coding-hermes
```

**Pitfall — local-prefixes:** Must be an array in v2, not a string:
```yaml
# v2 (correct):
local-prefixes:
  - github.com/coding-hermes

# v1 format (will be ignored in v2):
local-prefixes: github.com/coding-hermes
```

**Pitfall — unused linters:** v2 may reject linter names it doesn't recognize.
Remove `gosimple` (merged into staticcheck) and any unused linters when migrating.

**CI workflow updates when bumping linter:**
- `golangci-lint-action@v6` → `@v7` (for v2)
- `GO_VERSION` may need bumping — v2 binaries built with newer Go

**Runtime detection:**
```bash
golangci-lint --version | head -1
# v1: "golangci-lint has version 1.64.8"
# v2: "golangci-lint has version 2.12.2"
```
If v2 but `.golangci.yml` has no `version: "2"`, add it first.
This single line often fixes the "unsupported version" error.

**Proven:** coding-hermes scheduler CI-001/CI-002 (2026-07-16) — 5 commits
of iterative fixes across v2 schema, local-prefixes array, gosimple removal,
and errcheck/gofmt cleanup.

### golangci-lint: Go toolchain version mismatch (binary too old)

**Issue:** golangci-lint binary refuses to run when go.mod targets a Go version
newer than the binary was built with:

```
Error: can't load config: the Go language version (go1.24) used to build
golangci-lint is lower than the targeted Go version (1.26.5)
```

**Root cause:** go.mod has `toolchain go1.26.5` (or `go 1.26`), but the
golangci-lint prebuilt binary (e.g., v1.64.8) was compiled with go1.24.
golangci-lint enforces that its own toolchain version is >= the project's.

**Fix — Option A (preferred):** Use `install-mode: goinstall` in CI so the
linter is built against the local toolchain, not downloaded as a prebuilt binary:

```yaml
- name: Set up Go
  uses: actions/setup-go@v5
  with:
    go-version: "1.26"         # Must match go.mod toolchain

- name: golangci-lint
  uses: golangci/golangci-lint-action@v6
  with:
    version: latest
    args: --timeout=3m
    install-mode: goinstall    # Build from source with local Go
```

**Why goinstall:** Avoids the prebuilt binary entirely. A `go install` build
uses the local `go` binary (setup-go's 1.26) so the compiled golangci-lint is
always version-compatible. Slightly slower CI (compilation time) but immune to
binary mismatch.

**Fix — Option B:** Pin a golangci-lint version known to be built with a Go
version >= the project's target. Check golangci-lint release notes for the
Go version used in each release's build.

**Fix — Option C (not recommended):** Downgrade go.mod `go` directive to match
the prebuilt binary's Go version. This constraints the project to an older
toolchain just to satisfy a linter — wrong trade-off.

**When this hits:** Any Go project using a `toolchain` or `go` directive that
is newer than golangci-lint's build toolchain. Common when:
- Project adopts a brand-new Go release (1.26, 1.27, etc.)
- golangci-lint prebuilt binaries lag behind the latest Go release
- CI uses `install-mode: binary` (the default for golangci-lint-action)

**Detection:** CI lint job fails with exit code 3. The exact error message
contains "lower than the targeted Go version". Not a code quality issue —
the code itself can lint fine, but the linter binary can't start.

**Proven:** H3 Go SDK (2026-07-18) — 3 consecutive CI failures on main.
go.mod had `toolchain go1.26.5`, golangci-lint v1.64.8 built with go1.24.
Fix: bumped lint job setup-go 1.23→1.26, install-mode→goinstall. Commit f11cc18.

## General Workflow

1. Get the full lint output: `golangci-lint run ./... 2>&1`
2. Categorize issues by linter type
3. For each file, read the surrounding context (5-10 lines around the issue)
4. Apply fixes with `patch` tool
5. After ALL fixes: `go build ./... && go vet ./...` — catches syntax errors
6. Run affected tests: `go test ./<pkg>/... -count=1 -short`
7. Re-run lint to confirm issues are resolved

## Gotchas

- **Local lint may show fewer issues than CI** — even with identical golangci-lint
  version. CI runs a broader scan. Always verify against CI output, not local.
- **Renaming a function requires finding ALL callers** — test files, registration
  maps, closure references. Use `grep -rn "oldName" --include="*.go" .` before renaming.
- **SA4006 fix may require a follow-up `:=` change** — when you change the first
  occurrence from `x, err := ...` to `_, err := ...`, the next occurrence must
  change from `x, err = ...` to `x, err := ...` (new declaration).
- **Inner closure parameters shadow outer ones** — in Go, `func(L *lua.LState) int`
  inside a function with parameter `lState *lua.LState` creates a NEW `L` variable.
  Only rename the OUTER function's references.
- **Removing an unused method may cascade to unused imports** — when the removed
  method was the sole user of an imported package (e.g., `fmt.Sprintf` inside
  `decisionID()`), the package import becomes unused. After removing the method,
  run `go vet ./...` to check for "imported and not used" errors, then remove
  the now-unused import. **Proven:** H3 Go SDK LINT-S01 (2026-07-15).
