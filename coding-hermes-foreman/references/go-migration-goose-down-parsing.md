# Go Migration — Goose Directive Parsing in Custom Runners

**When:** A Go project has a custom migration runner that loads `.sql` files via
`//go:embed migrations/*` and applies them with a custom `splitStatements()`
function, but the `.sql` files use goose-format directives (`-- +goose Up`,
`-- +goose Down`).

**The bug:** The custom runner treats `-- +goose Down` as a comment line and
skips it, then executes ALL remaining SQL statements — including the Down
(rollback) section — as part of the Up migration. The Down section typically
contains Postgres-specific syntax (`DROP COLUMN IF EXISTS`, `DROP INDEX IF
EXISTS`) that SQLite rejects.

**Detection:**
```bash
# Server startup fails with SQLite syntax error on a migration
./bin/app serve --db-url sqlite:dev.db
# → migrate: failed to apply migration 020_xxx.sql (version 20, statement 6):
#   sqlite: exec: SQL logic error: near "EXISTS": syntax error (1)
```

**Fix — strip Down section in filter/parse step:**
```go
// In filterForSQLite() or equivalent, after building the result string:
// Strip goose-format Down migration sections.
if idx := strings.Index(result, "\n-- +goose Down"); idx >= 0 {
    result = result[:idx]
} else if idx := strings.Index(result, "-- +goose Down"); idx >= 0 {
    result = result[:idx]
}
```

**Partial-migration recovery:** When the bug already ran and partially
applied a migration (Up statements succeeded, Down statement failed after
applying some Down side effects):

1. Check `schema_versions` — the migration may not be recorded
2. Verify each Up statement's side effects: `PRAGMA table_info()`, check
   indexes via `SELECT name FROM sqlite_master WHERE type='index'`
3. Insert the missing tracking record: `INSERT INTO schema_versions (...)`
4. Re-create any indexes that were dropped by the partial Down execution
5. Re-run the migration runner — it will skip already-tracked migrations

**Go code for rapid SQLite inspection (when sqlite3 CLI is unavailable):**
```go
//go:build ignore
package main

import (
    "database/sql"
    "fmt"
    _ "modernc.org/sqlite"
)

func main() {
    db, _ := sql.Open("sqlite", "file:dev.db?_journal_mode=WAL")
    defer db.Close()

    // Check schema_versions
    rows, _ := db.Query("SELECT version, name FROM schema_versions ORDER BY version")
    // ...
    
    // Check columns
    rows, _ = db.Query("PRAGMA table_info(<table_name>)")
    // ...
}
```

**Proven:** Consensus 2026-07-14 — migration 020 (`020_model_registry_sync_source.sql`)
had goose format; custom runner in `internal/migrate/migrate.go` executed Down
section statements 5-8 (DROP INDEX IF EXISTS + 3× ALTER TABLE DROP COLUMN IF
EXISTS). Statement 6 failed on SQLite's lack of `IF EXISTS` for `DROP COLUMN`.
Up statements 1-4 had already applied (columns added, index created). The Down
DROP INDEX (statement 5) succeeded and dropped the index. Recovery: insert
schema_versions row, re-create index, restart server.
