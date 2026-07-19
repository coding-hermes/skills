---
name: never-done
description: Foreman self-improvement loop — empty board means find more work, not stop
version: 1.0.0
category: software-development
---

# Never Done — Continuous Self-Improvement

**Core principle:** An empty board does NOT mean the project is done. It means the foreman hasn't looked hard enough. The foreman's job is continuous improvement — find gaps, add tasks, fix them, repeat. Never declare victory.

## When This Skill Loads

Load this skill when:
- The board has 0 pending tasks (all `[x]`)
- Or the foreman is about to mark the last task `[x]`
- Or the board has been empty for 2+ consecutive ticks

## The 10-Point Self-Improvement Audit

Run this audit EVERY tick when the board is empty or nearly empty. Each pass creates new tasks. The loop is infinite — there is always something to improve.

### 1. SPEC ALIGNMENT — Do specs match reality?

```bash
# Compare spec files against actual code
for spec in specs/*.md specs/**/*.md; do
    [ -f "$spec" ] || continue
    # Extract interface signatures, data models, API endpoints from spec
    # Check if they exist in actual code
done
```

What to check:
- Every interface in spec exists in code
- Every endpoint in spec returns the documented shape
- Every data model field in spec is present in code
- Every error path in spec is handled in code
- Every config value in spec is used in code

Create: `## [ ] SPEC — <specific gap>` for each mismatch.

### 2. DOC COVERAGE — Are docs complete?

```bash
# Check for undocumented files, missing README sections
find . -name '*.go' -o -name '*.py' -o -name '*.ts' | while read f; do
    # Check if file has doc comments, is referenced in docs
done
```

What to check:
- Every public function has a doc comment
- README covers setup, usage, API, configuration
- CONTRIBUTING.md exists and is accurate
- Architecture decisions are documented in DuckBrain
- API docs match actual endpoints (run curl against live server)

Create: `## [ ] DOC — <gap>` for each missing piece.

### 3. TEST GAPS — What isn't tested?

```bash
# Coverage report
go test -coverprofile=/tmp/cover.out ./... 2>/dev/null
go tool cover -func=/tmp/cover.out | grep -v '100.0%' | grep '0.0%'

# Find files with 0 tests
find . -name '*.go' ! -name '*_test.go' | while read f; do
    testfile="${f%.go}_test.go"
    [ -f "$testfile" ] || echo "UNTESTED: $f"
done
```

What to check:
- Every source file has a corresponding test file
- Edge cases: empty input, null values, concurrent access, timeout
- Error paths: every `if err != nil` path has a test
- Integration: end-to-end tests exist for critical flows
- Race conditions: run `go test -race` / `pytest --race`

Create: `## [ ] TEST — <gap>` for untested code paths.

### 4. PACKAGE UPGRADES — Are deps current?

```bash
# Go
go list -u -m all | grep '\['
# Python
pip list --outdated 2>/dev/null
# Node
npm outdated 2>/dev/null
# Rust
cargo outdated 2>/dev/null
```

What to check:
- Security advisories for current versions
- Breaking changes in available upgrades
- Deprecated packages that need replacement
- Go version in go.mod vs latest stable

Create: `## [ ] DEPS — <package> from <old> to <new>` for each upgrade.

### 5. PITFALL HUNT — What will break?

```bash
# Load known pitfalls from DuckBrain
duckbrain recall --namespace coding-hermes --query "pitfalls <language>" domain=concept
```

What to check:
- Hardcoded values that should be config
- Missing error handling (bare `_` on error returns)
- Race conditions (shared state without mutex)
- Memory leaks (unbounded goroutines, missing Close())
- SQL injection (string concatenation in queries)
- Missing input validation on API endpoints
- Hardcoded paths that break on other machines

Create: `## [ ] PITFALL — <specific vulnerability>` for each finding.

### 6. PERFORMANCE AUDIT — Is it fast enough?

```bash
# Go benchmarks
go test -bench=. -benchmem ./... 2>/dev/null
# Profile hot paths
go test -cpuprofile=/tmp/cpu.out -bench=. 2>/dev/null
```

What to check:
- N+1 queries in database code
- Unnecessary allocations in hot paths
- Missing indexes on queried columns
- Unbounded collections (maps that grow forever)
- Blocking operations that could be async

Create: `## [ ] PERF — <bottleneck>` for each issue.

### 7. ENDPOINT VERIFICATION — Do APIs actually work?

```bash
# Start the service, hit every endpoint
# Check responses for "not implemented", "TODO", 501, empty bodies
for route in $(grep -r 'router\.\|app\.\(get\|post\|put\|delete\)' --include='*.go' --include='*.py' | grep -oP '"[^"]+"' | tr -d '"'); do
    curl -s -o /dev/null -w "%{http_code}" "http://localhost:<port>$route"
done
```

What to check:
- Every registered route returns non-501, non-"not implemented"
- Response bodies match documented schemas
- Error responses include useful messages
- Authentication works on protected routes
- CORS headers are correct

Create: `## [ ] API — <endpoint> returns stub/error` for each failure.

### 8. CI/CD HEALTH — Does CI pass?

What to check:
- Latest CI run status (pass/fail)
- If failing: classify as code vs infrastructure
- Coverage trends over last 5 runs
- Lint warnings that have been ignored
- Build time trends (is it getting slower?)

Create: `## [ ] CI — <specific failure>` for CI issues.

### 9. DUCKBRAIN SYNC — Is knowledge current?

What to check:
- Architecture decisions in DuckBrain match current code
- Patterns discovered in recent ticks are saved
- Pitfalls from this project are documented
- Model capability observations are recorded
- Performance benchmarks are up to date

Create: `## [ ] DUCKBRAIN — <gap>` for missing knowledge.

### 10. CODE QUALITY — Would a senior engineer approve?

```bash
# Find code smells
grep -r 'TODO\|FIXME\|HACK\|XXX' --include='*.go' --include='*.py' --include='*.ts' .
# Find long functions
find . -name '*.go' -exec awk 'END { if (NR > 100) print FILENAME": "NR" lines" }' {} \;
# Find deep nesting
grep -P '^\t{4,}(if|for|switch)' --include='*.go' -r .
```

What to check:
- Functions over 50 lines (consider splitting)
- Files over 500 lines (consider modules)
- TODO/FIXME/HACK comments (each is a task)
- Duplicated code across files
- Magic numbers without constants
- Inconsistent naming conventions

Create: `## [ ] QUALITY — <specific issue>` for each finding.

### 11. MIDDLE-OUT WIRING — Is the engine connected to the world?

**This is the most-missed check.** Foremen build packages that pass tests, but never wire them to CLI flags, HTTP handlers, gRPC servers, or `main()`. "All tests pass" ≠ usable.

Load the axiom spec standard:
```bash
skill_view(name='axiom-implementation-specs')
```

Then verify EVERY package has its outward connection:

| Package | Must have | Check |
|---------|-----------|-------|
| API handlers | Registered route + handler function | `grep -r 'HandleFunc\|mux.Handle\|router.'` |
| CLI commands | Cobra command + `main.go` wiring | `grep -r 'cobra.Command\|urfave/cli'` |
| gRPC services | Proto-generated server + registration | `grep -r 'Register.*Server'` |
| Database layer | Migration files + connection in main | `ls migrations/` + `grep 'sql.Open\|pgx.Connect' main.go` |
| Config | Loaded in main + passed to packages | `grep 'viper\|config.Load' main.go` |
| Middleware | Applied to router in main | `grep 'Use(' main.go` |

**Wiring verification commands:**
```bash
# Can it start?
go build -o /tmp/bin ./cmd/... && timeout 5 /tmp/bin serve 2>&1 || true
# Does main.go import all packages?
grep 'import' cmd/*/main.go | wc -l
# Are all registered routes actually implemented?
grep -r 'HandleFunc\|Handle(' --include='*.go' . | grep -v '_test.go' | while read line; do
    handler=$(echo "$line" | grep -oP 'HandleFunc\("[^"]+",\s*\K\w+')
    [ -n "$handler" ] && grep -q "func $handler" --include='*.go' -r . || echo "MISSING: $handler"
done
```

What to flag:
- Package has tests but no CLI/HTTP/gRPC entry point → WIRING task
- API handler defined but route not registered → WIRING task
- Config struct exists but never loaded in main → WIRING task
- DB migration files exist but no connection in main → WIRING task
- `main.go` exists but doesn't import all service packages → WIRING task
- `serve` command exists but doesn't start → WIRING task
- Flags defined but not wired to config → WIRING task

Create: `## [ ] WIRING — <package> not connected to <CLI flag | HTTP route | gRPC server | main.go>` for each gap.

**Proven:** Dagger/Crier 2026-07 — 12 packages passed tests, zero wired to `dagger serve`. Foreman marked "done." Bane found: no `main.go`, no `cmd/`, no HTTP listener, no CLI. Engine running in a vacuum. This check catches that BEFORE declaring done.

## The Infinite Loop

```
Board empty? → Run 10-point audit → Find gaps → Create tasks → Work tasks → Board empty? → Repeat
```

**The project is only done when ALL 10 checks pass with zero findings.** Until then, keep adding tasks.

## Anti-Patterns

- **"Board is empty, project is complete"** — NEVER. Always run the audit.
- **"I checked last tick, nothing changed"** — checked last tick means you check AGAIN this tick. Code rots, deps age, specs drift.
- **"The tests pass so it's fine"** — tests passing ≠ complete. Specs, docs, deps, perf, pitfalls all need checking.
- **Self-pausing without running the audit** — NEVER self-pause before running all 10 checks.
- **"This is a maintenance project, not active"** — maintenance IS active. Continuous improvement never stops.
