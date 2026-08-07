# Board Storage — Canonical Doctrine (Bane directive 2026-08-07)

## The rule

**The git-tracked board store is JSONL** (`tasks.jsonl` + `events.jsonl` under
`.coding-hermes/board/`). Git-uploadable, diffable, and DuckDB reads it natively
(`read_json_auto`). `board.db` and `*.parquet` are REBUILDABLE CACHES — never
tracked, never committed.

> **Cache stance (Bane 08-07): the cache is just a query store for task work —
> NOT a performance or correctness system. Don't burn cycles on cache parity.**
> If `board.db`/parquet lags, drifts, or breaks: rebuild it from the JSONL
> (`COPY tasks TO ...` / `COPY events TO ...`) and move on. No repair ceremony,
> no narrative, no multi-store reconciliation. The ONLY store that must be
> correct is the JSONL.

- `.db` files cannot be uploaded to git repos — that's the whole point.
- Parquet is binary too — same rule (untracked cache only).
- Migrated boards keep a `board.db` locally for the live store + parity probes;
  the JSONL files are what git tracks and what reviewers diff.

## Audit command (what "in line" means)

```bash
git ls-files .coding-hermes/board/
# MUST NOT list: board.db, *.parquet
# MUST list: tasks.jsonl, events.jsonl (plus schema.sql, fixtures.jsonl)
```

## Correction recipe (board task JSONL-NORM-001)

1. `git rm --cached` any tracked `board.db` / `*.parquet` (keep working copies).
2. Add to `.gitignore`: `.coding-hermes/board/board.db`, `.coding-hermes/board/*.parquet`.
3. Ensure `tasks.jsonl` + `events.jsonl` exist, are tracked, and are current:
   export from the cache if migrating (`COPY tasks TO '<bd>/tasks.jsonl'` is NOT
   the way — use `dump_board_state.py` / `sync_board_jsonl_mirror.py`; or export
   JSON from duckdb with `read_json_auto`-compatible rows).
4. Parity probe JSONL vs `board.db` → MATCH.
5. Commit with co-author trailer: "board: JSONL canonical store — untrack
   board.db/parquet (Bane directive 08-07)".

## Pitfalls

- **`board.jsonl` header must be STRICT single-line JSONL.** Header-writing
  scripts used `json.dump(indent=2)` (append_board_event.py, sync_board_jsonl_mirror.py,
  append_board_task_completed.py) producing 16-line pretty JSON for one row —
  not diffable, not JSONL. All patched to `separators=(",", ":")` (2026-08-07,
  helios tick 186). If a board's board.jsonl has >1 line, normalize it:
  `python3 -c "import json; p='.coding-hermes/board/board.jsonl'; d=json.load(open(p)); open(p,'w').write(json.dumps(d, ensure_ascii=False, separators=(',',':'))+'\n')"`.
- **`COPY ... TO os.path.join(...)` inside a plain SQL string is a silent
  trap** — DuckDB may accept it as an expression and write nowhere sensible.
  Always pass the REAL path: `con.execute(f"COPY tasks TO '{path}' (FORMAT PARQUET)")`.
- **events tables differ per board** — some have `task_id`/`actor` columns with
  NOT NULL constraints (inserting without `actor` → ConstraintError); some use
  `tick_number` as TIMESTAMP, others INT. DESCRIBE the table before inserting.
- **`complexity` is TINYINT in some schemas, VARCHAR in others** — coerce by
  DESCRIBE type before insert.
- DuckDB autocommits: a failed later statement leaves earlier INSERTs committed
  — a "FAIL" run may still have landed rows. Always idempotency-check by id and
  repair, don't re-insert.
- JSONL append style: byte-preserve untouched lines (see git-tracked-jsonl-editing).
- **Every task row MUST carry `primary_model` + `primary_provider`** (fleet default:
  `deepseek-v4-flash` @ `deepseek`). The board audit (fleet-board-audit.py) flags
  non-complete rows with no model — 7 rows across 4 repos were missing one
  (2026-08-07, created by tools that omitted the field). Any task-creation path
  must set them (create_board_tasks.py payloads include them; duckdb INSERTs
  must too). Backfill recipe: `UPDATE tasks SET primary_model='deepseek-v4-flash',
  primary_provider='deepseek' WHERE status NOT IN ('complete','done','verified')
  AND (primary_model IS NULL OR primary_model='')` + COPY parquet + surgical
  JSONL row edit.
