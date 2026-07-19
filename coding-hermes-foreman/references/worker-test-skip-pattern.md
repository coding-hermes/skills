# Worker Test-Skip Pattern — Documenting Production Bugs

When a test-only worker discovers a production code bug that prevents clean
test execution, the worker should NOT modify production code. Instead, use
`t.Skip` with a diagnostic comment that explains the bug.

## Pattern

```go
func TestExample_WithData(t *testing.T) {
    t.Skip("SKIPPED: <component>.<function> has <specific bug> — production fix needed")
    // ... original test body (kept for reference when bug is fixed) ...
}
```

## Rules

1. **Never modify production code in a test-only task.** The task is "write tests",
   not "fix bugs." Production fixes need their own board task.
2. **The Skip message must be grep-able.** Include the exact file:line or function
   name so a future foreman can find and fix it.
3. **Keep the test body.** Don't delete the test code — a future fix task will need it.
   Comment it out or leave it below the Skip.
4. **Document the bug in the commit message AND the DuckBrain write.** The foreman
   should note it so the discovery sweep can find it later.

## Example (Proven)

**Bug:** `internal/dashboard/generator.go:101` scans `COUNT(*) int` into a `bool` field
(`RunningNow`). The modernc.org/sqlite driver cannot convert int→bool, causing the
query to hang indefinitely.

**Worker skip:**
```go
func TestGenerate_WithProjects(t *testing.T) {
    t.Skip("SKIPPED: dashboard.collect hangs due to int→bool Scan (generator.go:101) — production fix needed")
    // ... full test body below ...
}
```

**Commit:** `771affe fix: dashboard tests no longer hang on int→bool Scan bug`

**DuckBrain entry:** `/project/scheduler/concept/2026-07-12-generator-scan-bug` —
"generator.go:101 scans COUNT(*) (int) into FleetRow.RunningNow (bool). SQLite driver
cannot convert. Test skipped. Needs production fix: add a separate query or change
RunningNow to int."

**Proven:** Scheduler GAP-002 (2026-07-12) — MiniMax-M3 worker discovered the bug while
writing dashboard tests. Instead of timing out or modifying production code, it used
`t.Skip` with diagnostic comment. All other tests pass.
