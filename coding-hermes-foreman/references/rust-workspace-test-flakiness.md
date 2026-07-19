# Rust Workspace Test Flakiness — Diagnostic Pattern

When `cargo test --workspace` reports a test failure but the same test passes when the crate is tested in isolation, the cause is typically **parallel execution contention** rather than an actual code defect.

## Root Causes in Rust Workspaces

| Cause | Common In | Signal |
|-------|-----------|--------|
| DuckDB/WAL file locking | `hilo-graph`, any crate using DuckDB | "Table already exists" or WAL replay errors |
| Temp directory collisions | Test suites that use `tempfile::TempDir` with same prefix | "Permission denied" or stale PID files |
| Shared port binding | Tests that bind to hardcoded `localhost:<port>` | "Address already in use" |
| Environment variable pollution | Tests that set/read `std::env::var` without isolation | "assert left != right" failures across unrelated tests |
| SQLite/FTS5 WAL contention | `hilo-metadata` inventory tests | EOF parsing errors on JSONL |

## Diagnostic Procedure

```bash
# Step 1 — run the specific failing crate's full suite
cargo test -p <crate> 2>&1 | tail -10

# Step 2 — if that passes, the workspace-level failure was parallel contention.
# If that also fails, run the specific test:
cargo test -p <crate> --lib <test_name> 2>&1

# Step 3 — if even the isolated test fails, it's a real regression.
# If isolated passes but crate-level fails, it's inter-test contention within the crate.
# Run with single thread to confirm:
cargo test -p <crate> -- --test-threads=1 2>&1 | tail -5
```

## Decision Tree

| Pattern | Verdict | Action |
|---------|---------|--------|
| Workspace FAIL → crate PASS | Parallel contention | Do NOT create task. Log as known flake. |
| Crate FAIL → isolated PASS | Intra-crate contention | Create `## [ ] TEST — test isolation issue in <crate>` |
| Isolated FAIL | Real regression | Create `## [ ] BUG — <test_name> fails` |

## Proven

**Hilo foreman 2026-07-16:** `test_append_blob_index_writes_jsonl` in `hilo_backends::s3::tests` failed under `cargo test --workspace` (parallel s3::tests) but passed under `cargo test -p hilo_backends --lib s3::tests`. 500 tests total, 0 real failures. Root cause: JSONL file contention during parallel S3 test execution.
