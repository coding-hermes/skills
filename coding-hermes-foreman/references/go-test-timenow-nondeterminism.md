# Go Test `time.Now()` Non-Determinism — CI-Only Failures

## Pattern

Go tests that use `time.Now()` to compute reference dates are non-deterministic
across CI runners with different clocks or timezones. The test passes locally on
the foreman's machine but fails on CI because `time.Now()` returns a different
day or time.

## Detection

1. CI test failure shows weekday/date mismatch in assertion
2. Same test passes locally: `go test -count=1 -run <TestName>`
3. Test setup includes `now := time.Now()` or relative date math from it
4. Assertion compares against a specific weekday string or date

**Example CI failure:**
```
miner_test.go:395: expected Monday in time pattern title, got "Elevated incident rate on Tuesday"
```

## Root Cause

```go
// NON-DETERMINISTIC — depends on when/where CI runs
func TestDiscoverTimeBasedPatts(t *testing.T) {
    now := time.Now()                          // varies per runner
    monday := now.AddDate(0, 0, -int(now.Weekday())+1)  // computed from now
    // ... create incidents on monday ...
    // assertion expects "Monday" in title
}
```

When the CI runner's `time.Now()` returns a different weekday than the foreman's
machine, the computed `monday` variable points to a different day, and the test
assertion fails.

## Fix

Replace `time.Now()` with a fixed reference date that makes the date arithmetic
deterministic:

```go
// DETERMINISTIC — July 13, 2026 is a Monday in UTC
func TestDiscoverTimeBasedPatts(t *testing.T) {
    now := time.Date(2026, 7, 13, 12, 0, 0, 0, time.UTC)  // fixed anchor
    monday := now.AddDate(0, 0, -int(now.Weekday())+1)     // deterministic result
    // ... create incidents on monday ...
    // assertion now always sees "Monday"
}
```

**Rules for choosing the fixed date:**
1. Pick a date where `now.Weekday()` produces the expected value for the test's logic
2. Use UTC to avoid timezone surprises
3. The date should be in the past so `AddDate(0, 0, -N)` doesn't produce future dates
   that could confuse other assertions
4. Add a comment noting why the specific date was chosen (e.g., "July 13, 2026 is a Monday")

## Proven

- **Helix 2026-07-15:** `TestDiscoverTimeBasedPatts` in `pkg/learning/miner_test.go:364`
  used `time.Now()`; passed locally, failed on CI run #236 with "expected Monday, got Tuesday."
  Commit `5dc5c9e` (pattern miner implementation).
