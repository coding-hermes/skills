# Step 3 — THE PRE-ADD GATE (think before you write)


**This is the step Bane asked for explicitly: before ANY task is added, think
about whether the scheduler will actually fix it.** A task that won't be
picked up is worse than no task — it's theater. Gate every candidate:

| Gate | Check | Fail → |
|------|-------|--------|
| G1 **Format** | The task row matches the board's exact format (v2.1 `|||` rows or matrix `\| ID \| Task \| ...`; JSONL boards validate with `boardctl validate -C <dir-containing-.coding-hermes>` — there is NO `--file` flag; `~/.hermes/scripts/validate-board-format.py` is the LEGACY md-matrix validator and FAILS every JSONL board with `MISSING: matrix header` (measured 2026-09-22 on coding-hermes-scheduler); quote the `[error]`/RESULT delta pre- vs post-edit, never a green/red) | Fix format or skip |
| G2 **Enabled** | Project `Enabled=true` in `GET /api/v1/projects` — never add tasks to a disabled project | Skip + note in report |
| G3 **Model** | Task row has a valid model/fallback the foreman can dispatch (copy the board's convention) | Fill from board convention |
| G4 **Scheduler sees it** | Board file is at the path the foreman reads (`.coding-hermes/tasks.md` or `.coding-hermes/board/tasks.jsonl`), committed or writable — **ANCHORED (DF-H3PM-04): that path is `<TARGET_WORKDIR>/.coding-hermes/board/tasks.jsonl` (with `events.jsonl` beside it) for the TARGET resolved by the Step 1 board-path recipe — workdir read from `~/.hermes/coding-hermes/scheduler.db` — and NEVER a path under a stand-in workdir (`~/.hermes/stand-in/**`, `~/.hermes/sync-workdirs/**`). A board written under a stand-in dir is invisible to the foreman and no reader will ever close its rows; if TARGET does not resolve, STOP and ESCALATE instead of writing somewhere writable** | Write + commit |
| G5 **Foreman woken** | After writing, if the live cooldown ≥ 43200 (12h idle tier) → `PUT {"CooldownS":3600,"DecayRate":1.0}` (fast lane = 1h; Bane 08-15 tiers: fast 3600 / default 21600 / idle 43200) — **EXCEPT when the project's fleet.toml pin (~/.hermes/fleet.toml `cooldown_s`) equals the current live cooldown**: the wake must NOT override the operator pin. NEVER PUT below the operator pin. Skip the wake entirely in that case. The live cooldown is read from `GET /api/v1/projects/<name>` (single-project GET; returns `cooldown_s`, `cooldown_pin_s`, `cooldown_pin_by`, `enabled`, and `latest_tick` — richer than the 200-row truncated list). Response shape: the fields are NESTED under a `project` key with `latest_tick` as a sibling (`{"project": {"cooldown_s": ...}, "latest_tick": {...}}`) — reading them off the top level yields None and can look like a missing project — the scheduler DB's `projects` table has NO PascalCase `CooldownS` column (that SELECT errors), but the snake_case columns `cooldown_s, cooldown_pin_s, cooldown_pin_by` DO exist and answer the pin question in one query without an API roundtrip (`SELECT cooldown_s, cooldown_pin_s, cooldown_pin_by FROM projects WHERE name='$TARGET'` → e.g. live 900, pin 86400, `fleet-toml-import`); fleet.toml is where the operator pin lives, not the live value. A `cooldown_pin_by` of `fleet-toml-import` on the live row means the pin is operator-enforced: never PUT below it, and a pin of 21600 or higher means NO wake at all. | Do it (never for disabled, never below an operator pin matching the live cooldown) |

**Note**: The wake decision is independent of whether tasks were written. Even with 0 rows gated-in, if CooldownS ≥ 43200 and the fleet.toml pin does NOT equal the current CooldownS, still wake foremen to consider picking up existing open tasks.

**Resolving the live cooldown when the API list truncates.** `GET /api/v1/projects` returns only the FIRST 200 projects; a missing target means truncation, not deletion. The DB is authoritative for enabled+workdir, `fleet.toml` for cooldown intent; if the target is absent from the list, decide G5 from `fleet.toml` alone (a 21600+ pin means NO wake) and do not re-query in a loop.

**There is NO `POST /api/v1/projects/<name>/wake` route — verify a guessed endpoint's existence once, then fall through to the pin/cooldown decision (G5) and the board itself.** A 404 `{"error":"not found"}` on a plausible-looking wake path means the endpoint does not exist, not that the foreman is unreachable: the scheduler wakes foremen via cooldown state and board-driven dispatch, so G5's cooldown PUT is the only write-shaped mechanism, and a fresh pending row on the board is the wake signal. Probing further invented routes burns the tick.
| G6 **No zombie block** | Project has no `status='running'` tick with `session_id IS NULL` (zombie rows block picks), and no `status='running'` tick whose `heartbeat_at` stopped advancing — judge liveness against `heartbeat_at`'s own offset (or now-UTC), NEVER against the tick ID's embedded timestamp: tick ids embed UTC while `spawned_at`/`heartbeat_at` carry explicit local offsets, so a wall-clock diff against the id misreads a live advancing tick as hours-stalled — check `~/.hermes/coding-hermes/scheduler.db`; the `ticks` table keys the project as `project_name` (there is no `project` column). Tick queries written from remembered column names fail (there is no `started_at` — the time columns are `spawned_at`/`created_at`/`completed_at`): run `PRAGMA table_info(ticks)` once before authoring a new tick query. When the failure happens, sqlite3 misreports it as `Parse error in 2nd command line argument` — naming the shell argument, not the column — so it reads like a quoting problem; don't re-check your quoting, go straight to PRAGMA. Example query: `sqlite3 ~/.hermes/coding-hermes/scheduler.db "SELECT COUNT(*) FROM ticks WHERE project_name='<TARGET>' AND status='running' AND session_id IS NULL;` should return 0. | Clear row, `POST /api/v1/evaluate` |
| G7 **Dedup** | No existing open task with the same problem — fingerprint by CONTENT, never by id (see "G7 in practice" below) | Merge or skip |
| G8 **Structural audit (raw lines)** | The board has no id written on more than one line, and `boardctl validate` is not FAIL. G7 is a PRE-ADD gate: it only compares a candidate row against open rows, so it can never see the board's other duplicate class — the same id on many lines. Audit the RAW file, never a keep-last view (see "G8 in practice" below) | Collapse to one line per id (keep LAST), fix vocabulary, re-validate |

Only tasks that pass ALL gates get written. For each gated-in task, record in
the ledger: the gate results (esp. G5/G6 actions taken) so the cycle report
can show "added X tasks, woke Y foremen, cleared Z zombies".

### G7 in practice — dedupe by CONTENT, never by id

On QA and dogfood boards the row id is a **rotating cycle slot, not a finding
identity** (boards have measured dozens of same-id rows holding many distinct
titles, and one recurring finding filed under 15 different ids). So an id match
proves nothing, and an id mismatch hides real duplicates. Fingerprint the
finding, not the name: normalise title+detail (lowercase; strip punctuation,
dates, numbers, commit shas, volatile counts) and key on that. Coerce before
joining: `detail` (and any free-text field) can be a DICT on legacy rows, and `id` can be an INT
(event-shaped rows inside tasks.jsonl carry numeric ids), so `json.dumps` non-string non-id values
before concatenating and GUARD any string op on ids (`r.get("id") if isinstance(r.get("id"), str)
else "NOID"`) — a str-join fingerprint pass or id-prefix census crashes mid-scan (`'int' object has
no attribute 'split'`) otherwise. Same crash class in any ad-hoc board scan: rows omit
 optional keys, so `r.get('completed_at').startswith(...)` throws AttributeError on
 the first row without the key — write `(r.get('completed_at') or '')` for every
 optional field you chain a method onto.

- Same fingerprint, several open rows → keep the OLDEST as canonical, mark the
  rest `status='complete'` with `superseded_by=<canonical id>` and one line of
  why. `superseded_by` may name a THIRD row (not a same-finding sibling) when the board itself records the roll-up — e.g. a releng re-sweep row that explicitly says two older pending rows are superseded by it — but only cite evidence from the board's own commit text, never the PM's inference. Make the annotation TWO-SIDED: also add (or extend) a `supersedes`
  array on the CANONICAL row listing the folded ids — but SET it from a
deduplicated list in one pass (`r['supersedes'] = sorted(set(...))`), never
  blind-`append`: the canonical row is often re-folds' target across cycles
  (another lane folds a second duplicate onto it later), and an unguarded
  append writes the same id twice into the list. Verify the final row reads
  back with exactly one entry per folded id before committing. Never delete a row; never rewrite a closed one. **Do NOT use
  `status='duplicate'`** — it is outside `boardctl`'s vocabulary
  (`{blocked,complete,failed,in_progress,pending,review}`, 'completed' accepted as
  a read alias), so a row folded that way is INVALID: `boardctl validate` reports
  it as an error and every validate-gated audit skips it. Measured 2026-09-19 on
  crier: the six rows this doctrine had folded to `status='duplicate'` were exactly
  the ones validate flagged, and they had sat there invisibly for days.
- A new finding in the SAME failure CLASS as an existing open row (e.g. another instance of deploy-drift, same fingerprint family) is an EVIDENCE REFRESH on that row — append the new instance to its detail — not a new id; mint a row only for a distinct problem needing distinct work. A child hunter's claimed novelty never overrides this content-fingerprint check.
- Same id, different content → the id was reused. Give each distinct finding its
  own stable id (`<PREFIX>-<PROJECT>-<next free>`) and record the rename in
  `foreman_note`. `next free` means free across ALL rows, not just open ones —
  a sequential id already carried by a COMPLETE row is taken. Check the mint
  candidate against every id on the board (any status) before writing it.
- Repair while you are in there: ids that are only digits, priorities outside
  P0-P4, out-of-vocabulary statuses, and double-encoded rows (a priority value like
  `P1","source":"qa-dagger` is a corrupt line — re-encode the whole row as valid
  JSON, keeping the original text in `foreman_note`). Corrupt fields on TERMINAL
  (complete/failed) rows are repair-in-place, not rewrite: preserve every close
  field byte-identically (commit_hash, worker_summary, files_changed, guard
  result), replace ONLY the corrupt value, append the repair (with the original
  value) to `foreman_note`, and quote the validate RESULT delta pre→post as the
  verification line. Foremen themselves can emit
  out-of-vocab statuses (`closed` is NOT an alias — only completed/done/in-progress/open/reopen/todo
  are accepted), so an `boardctl validate` vocab error can be the foreman's own close write, not a
  PM fold; repair to `complete` and keep the foreman's `foreman_note`/`commit_hash`/close metadata
  intact. Free-form `guard_result`/`ci_result` strings on OLD rows are warnings, not errors —
  leave them rather than touching rows you were not otherwise editing.
**Write atomically: handle both tasks.jsonl and events.jsonl together — write to temp files, validate the board, then swap in both files atomically.
On failure, restore originals.**
- The PM lane in the scheduler is the only writer of a board during its tick;
  hunters read. Two writers on one board is the corruption this gate exists to
  prevent.

### G8 in practice — audit the RAW lines, never a keep-last view

G7 fingerprints CONTENT among open rows and is deliberately id-blind (ids rotate
as cycle slots), so it structurally cannot see the other duplicate class: **the same
id written on several lines.** Every reader resolves the board by keep-LAST, so a
duplicate-id board looks perfect through a loader lens — the extra lines are invisible,
and `boardctl` refuses ambiguous ids on write, silently blocking row closures. Run both
checks on the raw file every cycle (full collapse procedure, terminal-dup-set rules,
validate-FAIL decomposition: `references/g8-raw-audit-collapse.md`):

```bash
# 1. id multiplicity + malformed-line count + status census + open-row listing,
#    computed on RAW lines (a keep-last parse reports 0 duplicate ids by construction).
#    Shipped script; exit 2 = malformed lines, exit 3 = duplicate ids —
#    never report a clean audit over either. The verdict line
#    (lines=/unique_ids=/duplicate_ids=) prints FIRST, above the open-row
#    listing — page its HEAD, not its tail, before judging the audit clean:
python3 ~/.hermes/skills/coding-hermes-project-manager/scripts/g8-board-audit.py "<board>/tasks.jsonl"

# 2. vocabulary / format / legacy-shape errors
boardctl validate            # a FAIL here is an ERROR, not a warning
```

Classify validate WARNINGS before acting — only `[error]` counts gate a verdict. Known-benign: `headerless board (no board.jsonl)` is the normal shape of a per-project workdir board whose first line is a task row (no status header exists, so the header counter is skipped, not failing); a legacy non-canon key on one old row is that row's shape, not corruption; a large count of `events.jsonl ... legacy shape tolerated` warnings (missing or legacy-typed event ids) is event-HISTORY shape, not a task-line error — report the count, change nothing.

If the shipped script is unavailable, write an equivalent helper to a /tmp file and run it as a plain command — do NOT run the audit as a `python3 - <<'PY'` verbatim heredoc: the G8 raw-line audit reads board rows, which carry ops vocabulary, so an inline heredoc body gets hardline-blocked exactly like the standalone scripts above.

Signals that mean the audit is real: `bad_lines=0`, `duplicate_ids={}` (no id
appears twice), and `validate` reporting no errors. Do not require `unique_ids ==
lines` on a mixed `tasks.jsonl`: id-less event-shaped rows are tolerated and make
`unique_ids < lines`; require equality only when every parsed line is id-bearing.
Legacy duplicate *event* ids and id-less event lines are tolerated warnings — ignore
them, never task-line errors. When a census shows one status value repeated hundreds
of times, group the rows by ID before reading it as a duplicate-id class — a status
count is one per row, so `complete` ×132 on a 184-row board is ordinary board
history, not 132 duplicate lines.

**Collapse procedure** (append-log board): keep the LAST line per id — that is the
line every reader treats as live — and drop the earlier ones, byte-preserving every
kept line. Handle both tasks.jsonl and events.jsonl together: write to temp files,
validate the board, then swap in both files atomically. On failure, restore originals.
Never re-serialize the whole file: a line-touching rewrite that changes untouched
lines makes `git diff --numstat` disagree with the row count you edited,
which is the signature auditors use. Then re-parse and assert `unique_ids == lines`
before committing. Make that assert SHAPE-TOLERANT: boards mix task rows with (a) blank
separator lines and (b) stray EVENT rows inside tasks.jsonl (`event_type`-keyed, possibly
numeric-only id) — skip blanks and count event rows as id-bearing, or a healthy board
fails the assert and reads as corruption.

**Keep-OLDEST vs keep-LAST, and WHY a G7 fold is an IN-PLACE EDIT on a per-row JSONL board.** G7's fold says *keep the oldest canonical*; the board's readers resolve keep-LAST, and `boardctl validate` errors on ANY id appearing on more than one line. So on a JSONL board where each id exists exactly once, appending a new superseding line under the SAME id is WRONG — it manufactures a duplicate-id validate FAIL that silently blocks every later closure of that row (measured: append-fold of 5 rows → 5 `[error] duplicate task id` lines; in-place rewrite → OK). Fold those boards by rewriting the losing row IN PLACE: set `status='complete'`, add `superseded_by=<canonical id>`, append the fold reason + evidence to `reasoning`, keep the original title/detail. An append-style superseding line is only correct on boards that legitimately carry the same id on multiple lines (rotating-cycle-slot boards) — and even there, keep the LAST occurrence, since that is the line every reader resolves; anything that deletes or rewrites earlier lines must keep LAST or the reader resolves the row you meant to retire. Snapshot the board to /tmp before the fold; if the first attempt produces validate errors, restore the snapshot and redo — never patch on top of a half-folded board. Verify every fold with BOTH `boardctl validate` (error-count delta) and the G8 raw-line audit (`unique_ids == lines`). Never invent `status='superseded'`: it is outside boardctl's vocabulary and makes validation fail. If the canonical row's acceptance criteria fully cover the losing row, rewrite the losing row in place as `complete` with `superseded_by` and evidence naming the canonical row; if the work is not actually resolved, keep the losing row in its real open status and do not collapse it. Annotate the winning row when fresh evidence changes the scope, naming the evidence source and generation time so the next reader can identify the canonical work without re-deriving the count.

- **Remote parity: check the LANE branch first, not main.** A big `origin/main..HEAD`
count on a clean-tree repo is usually NOT stranded work — foremen commit on lane
branches with `origin/main` as the eventual merge point. Read the current branch
(`git branch --show-current`), compare it against ITS OWN remote
(`git rev-list --count origin/<branch>..HEAD` plus the reverse) before treating
anything as unpushed, and run `git remote -v` to see which remotes exist (a repo may
have `origin` as a public mirror plus a push mirror under another name — do not
assume which one the fleet pushes to). No `origin` remote ≠ parity check failed:
resolve the actual push remote from `git remote -v` and diff against it
(`git rev-list --count <remote>/<branch>..HEAD`), fetching first so a fresh working
tree reads a real upstream ref instead of a stale/missing one.

- **Repair a board-format defect before gap hunting or row gating.** A board that
contains valid task objects but is physically pretty-printed or concatenated is
not scheduler-visible: `jq -s`/a tolerant decoder may recover objects while
`boardctl` and line-wise readers see zero tasks. Snapshot first, recover objects
with a whitespace-skipping decoder, rewrite one object per line atomically, then
run G8 and `boardctl validate` before treating the backlog as real or filing a
replacement row. This applies to auxiliary metadata too: if the task/event
census is clean but validation reports `board.jsonl ... EOF`, inspect that
metadata file rather than rewriting tasks or events; compact the existing single
JSON object with `jq -c`, validate it line-wise, and rerun validation. Do not
turn a structural format repair into a product finding or backlog count. Commit
and push the repair, then verify branch parity; otherwise all later counts,
dedupe decisions, and wake decisions are based on an invisible queue.

- **Read the board as a coherent snapshot when another writer may be active.** Capture the board's bytes (or a content hash plus size and mtime) before parsing; perform the raw census, open-row listing, dedupe check, and validation against that same snapshot. Recheck the live file's hash/size afterward. If it changed, discard every count and verdict derived from the earlier read and rerun the census after the writer lands or becomes quiet. A transient parse/validation failure during a rewrite is provisional evidence, not a board defect to report or repair. Never mix a pre-write row count with a post-write total, and do not write the DuckBrain cycle record until the final board audit is stable; if the board changes afterward, append a correction record at the same key. **When a live writer keeps the board moving, label counts as pinned snapshots, not PM before/after effects: report `snapshot_before`, `snapshot_after`, and `changed_by_writer=true`, and do not attribute the delta to your lane. If the writer is still running at close-out, retain the latest stable snapshot and hand off the required re-audit; do not manufacture a clean post-state from a moving file.**

- **Classify duplicate-ID sets by row shape before collapsing them.** A duplicate in `tasks.jsonl` may be a real task rewrite, a terminal shadow, or an event-shaped record misplaced in the task file (for example, `event`/`summary`/`commit` with no status). Treat a record with no task status and event-shaped fields as history, not a task: move that exact raw line byte-for-byte to `events.jsonl` (append only if the identical event is not already there), then validate both files. Never drop an event-shaped line merely because keep-last would hide it. A distinct task reusing an existing id must receive a unique id plus a provenance note; do not delete it as a duplicate. Only collapse a genuine task duplicate after proving which line is live and which line is stale, then re-run G8 and `boardctl validate` on the written snapshot.

- **Separate board-format repair from product findings.** If the format repair
restores existing rows, do not file a duplicate format finding or count the
recovered rows as newly gated work. Re-run the current open census after repair
and gate only distinct, independently reproduced product gaps; this keeps a
structural recovery from inflating the PM queue.

**A pending + complete pair for the SAME id means the row is CLOSED — the pending line is a stale shadow.** Resolve keep-last BEFORE the premise walk: reading the pending shadow as open work invents backlog, and the complete line's `commit_hash` is the probe target for verification. The G8 raw audit (duplicate-id census) is the cheapest way to surface this class — run it before deciding what is open.

**Duplicate-id collapse is safe ONLY on terminal dup sets — judge the duplicate class, not the id count.** Collapse a
duplicate set only when the kept (last) line is terminal and carries the close verdict; when the duplicated ids are
genuinely OPEN, do not collapse (that deletes the foreman's pickable work) unless both lines are the same finding —
a sibling lane's enriched rewrite (diff the lines: a rewrite carries the original's fields plus a lane note; two
distinct tasks carry different remediation text). Full G8 decision tables (incl. the id-reUSE class — see references/g8-id-reuse-fold.md): `references/g8-raw-audit-collapse.md`.

