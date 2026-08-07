---
name: coding-hermes-jsonl-board-append
description: >-
  Append events to JSONL foreman boards without board.jsonl.
version: 1.0.0
author: Hermes curator
platforms: []
metadata:
  hermes:
    tags: [coding-hermes, board, jsonl, duckdb, foreman, tick]
    related_skills:
      - coding-hermes-foreman
      - duckdb-board-write-pipelines
      - duckdb-board-store-repair
  support_files:
    - templates/append_event_no_header.py
    - references/sdk-python-instance-2026-08.md
---

# Coding Hermes — JSONL Board Event Append

Append a foreman tick's audit event to a JSONL-canonical board (Bane 08-07 directive:
JSONL is the git-tracked store; board.db + *.parquet are untracked rebuildable caches).

## When to use
- A tick finished and you need to write its audit event to a board whose tracked set is
  `events.jsonl`/`tasks.jsonl`/`fixtures.jsonl`/`schema.sql`.
- The stock `append_board_event.py` is unsafe on this board (see pitfalls).

## Step 0 — Topology check (never skip)
```bash
git ls-files .coding-hermes/board/        # tracked set
ls .coding-hermes/board/                  # does board.jsonl exist?
```
Two JSONL topologies:
- **A: `board.jsonl` header file EXISTS** → stock `append_board_event.py` works:
  `source ~/.hermes/venvs/board/bin/activate && python3 ~/.hermes/skills/coding-hermes-foreman/scripts/append_board_event.py <repo> <tick> <detail.json> --set ticks_total=N --set ticks_idle=M --set last_commit=<pre-tick HEAD>`
  (ONE KEY=VALUE per `--set` — a single `--set` with space-separated pairs dies with
  `unrecognized arguments`).
- **B: NO `board.jsonl`** (header lives in board.db `board` table only) → stock script
  CRASHES mid-run; use the one-shot custom pattern (`templates/append_event_no_header.py`).

## Variant B recipe
1. Write the event `detail` object to `/tmp/<tickprefix>_detail.json` via write_file
   (must be a valid JSON object — bare text is refused by write_file's JSON lint).
2. Copy the template to `/tmp/<tickprefix>_append.py` and edit the CONFIG block:
   BOARD, DETAIL, TICK, PRE_HEAD (`git rev-parse HEAD` BEFORE the append),
   NAMESPACE (read from the board table), TICKS_TOTAL, TICKS_IDLE.
3. Run with the board venv:
   `source ~/.hermes/venvs/board/bin/activate && python3 /tmp/<tickprefix>_append.py`
   — appends events.jsonl (id = MAX(id)+1 from JSONL, the source of truth), INSERTs
   board.db events, UPDATEs the board header (last_tick/updated_at/ticks_total/
   ticks_idle/last_commit) WHERE namespace='<ns>'.
4. Parity probe: `python3 ~/.hermes/skills/coding-hermes-foreman/scripts/board_jsonl_parity_probe.py <board_dir>`
   — must print MATCH (exit 0).
5. Commit ONLY tracked files (`git add .coding-hermes/board/events.jsonl`), co-author
   trailer mandatory, `--no-verify`, push.
6. Phase-2 (DB-only, NO commit): `UPDATE board SET last_commit='<new sha>' WHERE namespace='<ns>'`
   — header ends the tick matching HEAD; board.db is untracked, so git stays clean.

## Pitfalls
- **Crash order:** stock `append_board_event.py` appends events.jsonl + INSERTs board.db
  FIRST, then opens `{board}/board.jsonl` — on headerless boards it dies with
  FileNotFoundError AFTER those writes. Non-zero exit, header stale, event already landed.
- **Never re-run after a crash:** next id = MAX(id)+1 from JSONL would REUSE the id of
  the event that already landed → duplicate row. Recovery: parity probe first; if the
  event is in BOTH stores, only fix the header via UPDATE — do not re-append.
- **Header table is `board`**, not `board_header` (CatalogError otherwise).
- **WHERE namespace=**, never `project=` — project holds the DISPLAY name (e.g.
  'H3 Python SDK') and silently matches 0 rows.
- **ticks_idle convention:** pass prior+1 on idle ticks; productive ticks don't visibly
  reset it on some boards — don't fight it (per-board foreman-ops decides).
- **Timestamps:** post-migration events may be UTC (`datetime.now(timezone.utc)`),
  while the scheduler tick NAME timestamp is host-local — pick the board's current
  convention (check the last event) and stay consistent.

## Verification (always)
- Parity probe before AND after append (board_jsonl_parity_probe.py, exit 0 = match).
- `git log -1 --format='%B' | grep '^Co-authored-by:'` after commit.
- `git log origin/<branch>..HEAD | wc -l` = 0 after push (branch: resolve via
  `git symbolic-ref refs/remotes/origin/HEAD` — main vs master varies per repo).

## Cache rebuild from JSONL (board.db + parquet caches)

After the append — or any time board.db/parquet drift from events.jsonl/tasks.jsonl —
rebuild the caches from JSONL (the authoritative tracked store), never from parquet.
Proven h3-sdk-typescript tick #79 (2026-08-07). Use `scripts/rebuild_board_caches.py <repo-dir>`
or hand-roll with these rules:

- **JSON-typed columns kill plain-string INSERTs.** Migrated boards' `tasks` table has
  JSON-typed columns (worker_summary, guard_result, ci_result, review_notes, blocked_reason,
  blocked_since, dispatched_at — check `information_schema.columns` WHERE
  table_name='tasks' AND data_type='JSON'). Inserting a plain string dies
  `ConversionException: Malformed JSON at byte 0 of input`. Wrap every JSON-column value
  in `json.dumps()`; also int-coerce `complexity` (JSONL may carry `"low"` strings).
- **DELETE-before-INSERT wipes the table on mid-loop failure.** First rebuild attempt ran
  `DELETE FROM tasks` then failed on the FIRST INSERT (Malformed JSON) → table left EMPTY,
  parity probe then counts 0 tasks. Recovery: re-run the full rebuild with JSON handling —
  the events table is untouched by a tasks failure, so the two halves are independently
  re-runnable. Safer ordering: load JSONL rows into memory + detect JSON columns FIRST,
  then DELETE, then INSERT (or wrap in BEGIN/COMMIT).
- **Verify a roundtrip, not just counts:** after rebuild, SELECT a JSON column
  (e.g. worker_summary) to confirm it round-tripped, then COPY both tables to parquet.
  The parity probe is count-only — content drift slips through (same class as the
  <project> #76 count-MATCH false confidence).

## Support files
- `templates/append_event_no_header.py` — parameterized one-shot append for variant B.
- `scripts/rebuild_board_caches.py` — rebuild board.db events/tasks + parquet from the
  JSONL canonical store (JSON-column-aware, DELETE-safe ordering).
- `references/sdk-python-instance-2026-08.md` — get-h3/sdk-python instance facts
  (topology, header location, scheduler pin, E2E-001 window cadence).
