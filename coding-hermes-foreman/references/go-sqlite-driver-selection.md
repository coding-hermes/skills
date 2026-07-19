# Go SQLite Driver Selection — `modernc.org/sqlite` vs `mattn/go-sqlite3`

## Decision Tree

```
Need SQLite in Go?
├── Need FTS5 full-text search?
│   ├── YES → modernc.org/sqlite (built-in FTS5, no compile tags)
│   └── NO  → either works, modernc preferred for zero CGO
├── Can't use CGO? (cross-compile, WASM, restricted build env)
│   └── → modernc.org/sqlite (pure Go, no C compiler needed)
├── Existing project already on mattn/go-sqlite3?
│   └── → Stay if no FTS5 needed. Switch if adding FTS5.
└── Need bleeding-edge SQLite features?
    └── → mattn/go-sqlite3 (tracks upstream SQLite releases more closely)
```

## Quick Reference

| Feature | `modernc.org/sqlite` | `mattn/go-sqlite3` |
|---------|---------------------|---------------------|
| Implementation | Pure Go (transpiled C) | CGO wrapper |
| FTS5 | ✅ Built-in | ❌ Requires `-tags sqlite_fts5` |
| C compiler needed | ❌ No | ✅ Yes (gcc/clang) |
| Driver name | `"sqlite"` | `"sqlite3"` |
| DSN params | `?_journal_mode=WAL&_foreign_keys=on` | Same |
| Cross-compile | ✅ Trivial | ❌ Needs C cross-compiler |
| WASM support | ✅ Yes | ❌ No |
| Performance | Slightly slower than CGO | Native C speed |

## DSN (Connection String) Differences

Both use the same pragma query params:
```
:memory:?_journal_mode=WAL&_foreign_keys=on&_busy_timeout=5000
/path/to/db?_journal_mode=WAL&_foreign_keys=on&_busy_timeout=5000
```

**Critical:** The driver name passed to `sql.Open()` differs:
```go
// modernc.org/sqlite
db, err := sql.Open("sqlite", dsn)

// mattn/go-sqlite3  
db, err := sql.Open("sqlite3", dsn)
```

## `go.mod` entries

```
// modernc.org/sqlite
require modernc.org/sqlite v1.35.0

// mattn/go-sqlite3
require github.com/mattn/go-sqlite3 v1.14.24
```

## Common Failure Modes

### FTS5 not available
```
Error: "no such module: fts5"
```
**Cause:** Using `mattn/go-sqlite3` without `-tags sqlite_fts5` compile tag.
**Fix options:**
1. Switch to `modernc.org/sqlite` (recommended — one-line import change)
2. Add `-tags sqlite_fts5` to all `go build`/`go test` commands
3. Create a `fts5.go` file with `//go:build sqlite_fts5`

### `sql: unknown driver "sqlite3"` after switching to modernc
**Cause:** Changed import but forgot to update `sql.Open("sqlite3", ...)` → `sql.Open("sqlite", ...)`.
**Fix:** Search-replace `"sqlite3"` → `"sqlite"` in all `sql.Open()` calls.

### Unknown driver after switching driver
**Cause:** `go mod tidy` didn't pick up the new driver import (blank import `_ "modernc.org/sqlite"`).
**Fix:** Explicitly `go get modernc.org/sqlite@latest` then `go mod tidy`.

## Proven Instance
Rabbit-Hole 2026-07-12 — Phase 2 storage layer. Initial implementation used `mattn/go-sqlite3`; FTS5 virtual table creation failed with "no such module: fts5". Attempted `-tags sqlite_fts5` but the security scanner blocked `go get` for the CGO-dependent driver. Switched to `modernc.org/sqlite` — one-line import change, all 14 storage tests passed including FTS5 full-text search. No CGO, no compile tags, no cross-compile headaches.
