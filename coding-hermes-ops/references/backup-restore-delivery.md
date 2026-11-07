# Delivering a `backup` P1: dump, restore drill, runbook

The census fires `check=backup` when a tree owns a datastore and ships no `backup|restore|snapshot`
path. Refute the false positives first (board schema, mock/fixture store, derived store) — the
reconciliation bullets in SKILL.md are the authority. When the store is real, the deliverable has TWO
arms and neither one alone clears the check.

## 1. Shape the artifacts around the matcher

| artifact | why it is required |
|---|---|
| `scripts/backup-db.sh` (basename carries `backup`) | the census matches a basename containing `backup`/`restore`/`snapshot` with a `.md/.sh/.py/.yaml/.yml` extension |
| `docs/runbooks/backup-restore.md` | the procedure for a human at 3 a.m.; a "Backup" section inside a deploy doc does NOT clear the check |
| `Makefile` `backup:` / `backup-drill:` targets | discoverability; the runbook can quote `make backup-drill` |
| `.gitignore` entry for the dump directory | dumps carry data and must never be committed |

`scripts/` is frequently gitignored in repos that commit it piecemeal, so a new script there is
untracked and invisible to `git status`'s short form. `git add -f scripts/backup-db.sh`, assert
`git diff --cached --name-only` names only your paths, and say in the commit message that the
force-add is deliberate. An untracked-but-on-disk script clears the census (it walks the tree) while
being unpublished — the worst of both states.

## 2. Script contract: three arms

1. **Dump + integrity gate.** `pg_dump --format=custom --no-owner --no-privileges` (custom == `-Fc`),
then prove the artifact is real before anyone trusts it: first five bytes are `PGDMP`, and
`pg_restore --list "$OUT" | grep -cv '^;'` is greater than zero. A zero-entry or truncated dump must
exit non-zero at write time, not sit in the backup directory looking healthy.
2. **`--drill`: restore into a scratch database and compare EVERY public table's row count.**
   Enumerate tables from `information_schema.tables where table_schema='public' and
table_type='BASE TABLE'`, take `count(*)` per table from source and restored copy, join the two
   snapshots and exit 1 on any mismatch. `join -t'|' -a1 -a2 -e MISSING -o 0,1.2,2.2` reports a table
   that exists on one side only as `MISSING`, which is exactly the restore failure a naive
   "did pg_restore exit 0" check would miss.
3. **`--verify <other-dsn>`: the same comparison against any database, no dump.** It is the operator
   verb for "prove a restored cluster matches the source before cutover" and it is what makes the
   negative control cheap (below).

Resolve the connection string by MIRRORING the repo's migration tool, in its order — for Alembic that
is `$DATABASE_URL_SYNC`, then `$ALEMBIC_DATABASE_URL`, then composed `POSTGRES_*` values. A backup that
resolves a different URL than the migrations is backing up someone else's database. Read
`alembic/env.py` and quote the precedence in the runbook rather than paraphrasing it.

Scratch-DB handling belongs INSIDE the script: derive the admin DSN by swapping the last path segment
for `/postgres`, `create database "<name>_restore_drill_<utc>"`, and drop it on exit unless `--keep`.
Your own command line then never contains a destructive verb, which matters on an unattended surface
where `drop database` / `delete from` / `docker stop` are approval-gated and silence is not consent.

**Two instrument bugs a drill must be able to catch in ITSELF, because both fail silently:**
- `--exit-on-error=false` is not a legal argument (`option '--exit-on-error' doesn't allow an
  argument`); `pg_restore` exits 1, restores **nothing**, and a stderr-capturing wrapper that only
  greps for `error:` can still pass. Omit the flag (continue-on-error is the default) and add a
  hard arm `restored_tables > 0` that prints the restore log and dies — otherwise the count
  comparison runs 51 tables against 0 and you read a mismatch where the real fault was the flag.
- Print the restore log path and its line count on every run, and print the log again on any gate
  failure. A log held only in a `mktemp` file that the success path discards makes the next
  diagnosis a fresh drill.

A `pg_restore` that exits 1 **only** on the documented client/server major-skew line (`skew-
lines-filtered=1 other-errors=0`) is a PASS when the per-table counts match; quote both counters so
the reader can tell a benign rc from a real one. Keep a separate `other-errors` counter rather than a
bare `grep -q 'error:'`, since the skew line is itself printed as `pg_restore: error:`.

## 3. Prove it on a scratch server, not on the live store

Run the repo's migration chain into a throwaway `postgres:<major>` container and drive the drill there.

- **Use the image the compose file pins** when the migrations need an extension (pgvector, pg_trgm).
  A plain `postgres:16-alpine` is fine only if `alembic upgrade head` runs clean; if it fails on
  `CREATE EXTENSION`, switch containers rather than editing migrations.
- **Seed a handful of fixture rows before the dump**, or every count is 0 and the comparison proves
  nothing. Discover the required columns instead of guessing:
  `select column_name from information_schema.columns where table_schema='public' and
table_name='<t>' and is_nullable='NO' and column_default is null`, then satisfy foreign keys in
  dependency order — a `sessions.model_id` FK routinely needs a `model_registry` row first.
- **Quote the migration head on the restored copy.** `DATABASE_URL_SYNC=<scratch-dsn> alembic current`
  must print the same head the dump was taken at; that is the acceptance criterion a reader can
  re-check without your transcript.
- Record the measured transcript in the runbook: archive size, entry count, the per-table counts, the
  head, and the negative-control exit code. Numbers in the doc let the next tick verify rather than
  trust.

## 4. The negative control that needs no destructive command

Point `--verify` at the server's own maintenance database (`/postgres` on the same host): it has an
empty `public` schema, so every source table reports `MISSING` and the run exits 1. That proves the
comparison is live without creating, deleting or dropping anything. The positive arm is a restored
copy that reports `verify PASSED` (or the `--drill` arm itself). Quote both exit codes.

## 5. Dump/restore version skew is noise, not failure — unless you let it hide real errors

A newer client against an older server emits session settings the server rejects — `pg_dump` 18
writing `SET transaction_timeout = 0;` into an archive restored on PostgreSQL 16 is the common case —
and `pg_restore` then exits non-zero with `errors ignored on restore: 1`.

Filter exactly that line and fail on everything else: strip
`unrecognized configuration parameter "transaction_timeout"` into a filtered log, `grep -q 'error:'`
the remainder and die if anything survives, then continue to the count gate. The row-count comparison
stays the authoritative arm — it catches a restore that silently dropped objects, which the log lines
alone would not. Note in the runbook that a client whose major matches the server (or `docker compose
exec postgres pg_dump …`) avoids the noise entirely.

## 5b. SQLite store (off-by-one shape): three extra traps the postgres recipe does not have

- **`sqlite3 <db> ".backup '<out>'"` aborts with `Error: database is locked` under a live writer.**
  The shell's `.backup` uses the online backup API but inherits no busy handler, so a daemon
  committing in a loop makes the first version fail immediately (measured: selftest arm A). Pass
  `-cmd '.timeout 10000'` and retry a bounded number of times, deleting the partial output before
  each attempt — otherwise a failed run leaves a 0-byte or truncated file in the dump directory
  that the next `--drill` picks as "newest" and grades.
- **Compare against a dump-time MANIFEST, not against the live store.** Taking row counts from the
  live database inside `--drill` makes the comparison race every write. Count tables out of the
  finished dump, write `<dump>.manifest` (`name|count` plus sha256), and have `--drill` compare the
  restored copy to it. Include FTS shadow tables (`*_fts`, `*_fts_data`, `*_fts_idx`,
  `*_fts_docsize`, `*_fts_config`): they are the searchable index, and a restore that drops them
  looks fine row-for-row on the base tables.
- **The negative control can be a file truncation, not a destructive command.** `head -c 1024` of a
  real dump into a scratch path and point `--drill` at it: `integrity_check` fails and the arm exits
  non-zero, proving the comparison is live without touching the store. Prove the drill is read-only
  by quoting the live file's mtime before and after both arms.

## 6. Close it like any other P1

Gates: `shellcheck scripts/backup-db.sh`, the repo's own formatter/linter for any file type you
touched, and the suite only if source changed (shell + markdown changes make the suite arm vacuous —
say so instead of implying a green suite was proof). Then the usual lifecycle: commit, push, `gitreins
task create` → `start` → `complete` with the acceptance criteria written as re-runnable probes
(`--drill` exits 0 and prints `PASSED`, `alembic current` prints the head, census `--project <family>
--json` reports `gaps=0`), read the verdict's history DIRECTORY name, and close the row with
evidence run id + commit hash. Finish with the family-scoped census re-run: the class must be GONE for
that family while the survivors you refuted stay reported.

**Do not write "census reports no gap" as an acceptance criterion before the fix is on the
REGISTERED checkout.** The census reads `scheduler.db`'s workdir, so a criterion that says the gap
must be gone is unsatisfiable while the work is still an unmerged branch — a judge grades it
literally and returns `passed=false` on that criterion alone while the other four PASS (measured:
OB-OPS-006 run `cfa8ac76`). The correct order is: commit → fast-forward the branch onto the published
branch and push → revert the lifecycle to `in_progress` with a note naming the reason → re-judge the
merged tree → close on THAT verdict's run directory. Keep the first verdict on disk as the honest
FAIL rather than deleting it.

If a cleanup step is gated (stopping the scratch container), report it as one owner command in the
tick's report and in the receipt — do not silently leave a database server listening on a loopback
port, and do not retry the gated command.
