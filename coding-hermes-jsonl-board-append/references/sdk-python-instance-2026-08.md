# sdk-python (get-h3/sdk-python) board instance — facts as of 2026-08-07 tick #84

Instance of the JSONL-canonical board WITHOUT a board.jsonl header file (Variant B in SKILL.md).

## Topology
- Migrated at tick #83 (JSONL-NORM-001, Bane 08-07 directive). Tracked set:
  `events.jsonl` + `tasks.jsonl` + `fixtures.jsonl` + `schema.sql`.
  `board.db` + `*.parquet` = gitignored untracked caches.
- NO `board.jsonl` header file exists — the header lives in board.db's `board` table
  (table name `board`, NOT `board_header`). `WHERE namespace='sdk-python'` — `project=`
  holds the display name 'H3 Python SDK' and silently matches 0 rows.
- Stock `append_board_event.py` is NOT safe here (FileNotFoundError on missing
  board.jsonl after already appending JSONL + DB insert). Use the template.

## Append recipe proven tick #84 (event id 59)
1. Detail JSON at /tmp/h3sdkpy84_detail.json (JSON object).
2. One-shot script: JSONL append (id = MAX+1) → DB insert → header UPDATE
   (last_tick/updated_at/ticks_total=84/ticks_idle=1/last_commit=pre-tick HEAD 7c373e6).
3. Parity MATCH 59/59 pre- and post-append (board_jsonl_parity_probe.py).
4. Commit events.jsonl only (7ce1756, co-author trailer), push, then phase-2 DB-only
   header UPDATE last_commit=7ce1756 (no git commit — board.db untracked).

## Per-tick conventions
- Event timestamps: post-migration events are UTC (e.g. 05:36:22 = 00:36:22 local -05);
  scheduler tick NAME timestamp is host-local. Stay consistent with the last event.
- Idle ladder: idle #1-2 = FULL gate (pytest + ruff + format + make generate + guard +
  deps + CI + issues + hilo + parity); #3+ = cheap tier; #5+ = git-status only.
  ticks_idle header: +1 per idle tick; productive ticks don't visibly reset.
- E2E-001 cadence: 5-tick windows, due at the CLOSING tick (window #83-88 open after
  #83's 43/43, closing tick #88 non-deferrable). Battery runs :8777 via shim venv
  h3-test; CI's own battery job (GAP-001) serves :9191.
- Scheduler: fleet.toml pins cooldown_s=900 (changed 2026-08-07 00:38; API agrees —
  the ops-ref "expect 7200" is STALE). Verify fleet.toml mtime vs API UpdatedAt; never PUT.
- Ports: :9191 = helios-bin (sibling project — never kill), :8000 known zombie,
  :8777 only during E2E due-cycle.
- Strays in repo root: board.db (0B), dagger.db, namespaces/ — pre-existing, leave.
