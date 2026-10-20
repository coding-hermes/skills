# Step 1 — Read the Tracking Ledger (always first)


The ledger is the PM's memory of what was added, across all runs:

- **Central ledger:** `~/.hermes/stand-in/ledger.json` — every item ever added:
  `{id, project, title, added_at, status, last_checked_at, verification_evidence}`.
  Statuses normally progress `added → picked_up → in_progress → complete → verified → stale`; installations may also contain reconciliation aliases such as `referenced`. Treat every status other than `verified` as a follow-up candidate, then resolve it against the current board and evidence rather than rejecting it as an unknown status.
- **Per-project:** the board itself (`.coding-hermes/board/tasks.jsonl` — JSONL canonical) is the
  foreman's copy of the work — the ledger is YOUR copy. **Board store: .coding-hermes/board/tasks.jsonl (JSONL canonical; refs board-storage-canonical.md).**

**Board path anchor — resolve TARGET before you read or write any board (DF-H3PM-04).** Every
`.coding-hermes/...` path in this skill is anchored at the TARGET project's workdir, NEVER at the
directory the tick happens to be running in. A satellite lane (PM, QA, dogfood, sync) runs from a
stand-in workdir (`~/.hermes/stand-in/pm-lane/<project>`, `~/.hermes/stand-in/pm/<project>`,
`~/.hermes/stand-in/dogfood/<project>`, `~/.hermes/sync-workdirs/<project>-sync`) whose own
`.coding-hermes/` is empty by design — a row written there is invisible to every foreman and nothing
will ever close it. Resolve first, every cycle:

```bash
TARGET="${CODING_HERMES_PROJECT%-pm}"     # strip the lane suffix (-pm / -qa / -dogfood)
TARGET_WORKDIR=$(sqlite3 ~/.hermes/coding-hermes/scheduler.db \
  "SELECT workdir FROM projects WHERE name='$TARGET';")
BOARD="$TARGET_WORKDIR/.coding-hermes/board/tasks.jsonl"   # + events.jsonl for row history
readlink -f "$BOARD"                                       # prove which file you are about to touch
# Sanity check: verify board path matches reconciler's BOARD RESOLUTION section

# Check if project is enabled before doing any work
ENABLED=$(sqlite3 ~/.hermes/coding-hermes/scheduler.db \
  "SELECT enabled FROM projects WHERE name='$TARGET';");
if [ "$ENABLED" -eq 0 ]; then
  # Follow disabled target procedure: run reconciler, audit board read-only, 
  # verify open ledger premises with real commands, log cycle, escalate disable
  echo "Project $TARGET is disabled (enabled=0). Following disabled target procedure."
  # Continue with reconciler and read-only audit as described in "A DISABLED target"
else
  # Project is enabled, continue with normal PM cycle
fi


If the bare-TARGET lookup returns no row, do NOT escalate yet — the family's primary lane may be named `<target>-foreman` (h3-family convention), not the bare name: `SELECT name, workdir, enabled FROM projects WHERE name LIKE '<target>%'` and use the FOREMAN lane's workdir as TARGET_WORKDIR. A select matching only the satellite rows (`-pm`/`-qa`/`-sync`) resolves to stand-in dirs — never treat those as the board path. Escalate only when the LIKE sweep itself finds no foreman row. **Pitfall — the tick prompt's coarser variant (stop and escalate on a bare lookup miss) omits the `-foreman` fallback and burns a cycle on families with no bare-name scheduler row.** This chain is the authority, not the prompt. An earlier turn's ESCALATE on that miss is a read-only verdict, not a write: re-resolve via the LIKE sweep, run the cycle, report the corrected resolution. Apply the SAME fallback to every scheduler-DB query in the cycle, not just the workdir lookup: the ticks table keys by the FOREMAN lane name (`project_name='lore-foreman'`), so a bare-name liveness/zombie query returns 0 rows and fabricates a starvation verdict. If the lookup returns no row at all, or the board file is absent, STOP and report ESCALATE — never create a
`tasks.md` or `tasks.jsonl` anywhere under a stand-in workdir. Where the stand-in dir already carries
the satellite link (`.coding-hermes/board -> <TARGET_WORKDIR>/.coding-hermes/board`), a cwd-relative
write DOES reach the real board — confirm with `readlink -f .coding-hermes/board` before trusting it,
because an empty real `.coding-hermes/` and a live symlink look identical to a bare `ls`. The DB row
is still the authority even when a symlink looks right: a satellite's `.coding-hermes/board` symlink
can point somewhere OTHER than `projects.workdir` (measured: the `-qa` and `-pm` lanes of one
project linked different stand-in dirs), so always resolve TARGET from the DB and verify the
resolved path is a real file before reading it. When the board is a FAMILY board (audit lanes
sharing one tasks.jsonl), read foreman liveness FAMILY-wide (`project_name LIKE '<family>%'
grouped by project_name on ticks`) before reading a stale target-only last tick as starvation —
sibling foremen consume the same rows. Full rule, the
the symlink pattern and the measured fleet state: `docs/board/standin-workdir-board-resolution.md` in
`get-h3/h3`.

Load the ledger. For each item in the ledger where `project == TARGET` and `status != verified`:
- Check its row on the project board (does it still exist? status changed?)
- That's your **prior-run follow-up list** for this cycle.

**Important: The ledger file is a single JSON document with an `items` array, not JSONL.** 
While the file occasionally contains formatting issues that prevent standard JSON parsing (e.g., escaped newlines), 
it should be parsed as a single JSON object. Extract the `items` array from the parsed object.
Avoid parsers that expect JSONL format, as they will undercount items. When in doubt, verify 
by checking `grep -c "\"project\": \"<TARGET>\"" ledger.json` against the parsed item count. Match
the FIELD VALUE exactly: a census grepping the bare TARGET word anywhere in the JSON also counts
unrelated items whose prose merely contains the word (a lane named for one concept collides with
the English word for the everyday noun) and inflates the count.

To extract items for TARGET project with status != verified:
Use the robust ledger parser script:
```bash
python3 ~/.hermes/skills/coding-hermes-project-manager/references/ledger_parser.py ~/.hermes/stand-in/ledger.json TARGET
```
This handles malformed JSON, escaped newlines, and various ledger formats reliably.
The parser is SHAPE-TOLERANT (bare dicts, bare lists, and items-wrapper lines all yield) — if you
 ever patch it, keep every shape covered and test against a ledger line of each shape: a parser
that only handles one shape crashes mid-scan (`AttributeError: 'str' object has no attribute
'get'` / `'list'`) on the others, which looks like a broken ledger but is a broken tool.
**Pitfall**: the ledger parser can return empty output on some ledger formats — verify with the grep form above, and read the CLEAN-ZERO rule in Pitfalls before declaring the tool broken.
- **When checking ledger item dates for staleness, note that the `added_at` field may or may not end with 'Z'. Use datetime parsing that accepts both, or use the ledger parser script which handles this.
 If the script returns empty output but grep shows matches, use the grep method or write a simple custom parser script.

**When the canonical reconciler ITSELF crashes on `json.load`, repair the ledger in place — tolerance is not a fix.** The corruption class is file-level: literal `\n` two-character sequences inside the main document, invalid backslash escapes, raw control characters inside strings, and trailing JSONL documents appended after the main doc — every downstream lane fails until it is repaired, and the defects STACK so a single string-aware sanitize pass is required (iterated regex passes just move the decode error to the next defect class). Backup to a timestamped copy first, repair encoding ONLY (never stamp item statuses — closure stays the reconciler's `--apply` job), write atomically, and verify by re-running the reconciler dry. Full recipe: `references/ledger-corruption-repair.md`.

### Step 1a — Reconcile the ledger against the boards BEFORE listing anything

Run the reconciler first (dry-run by default — read the numbers, then `--apply`). Full procedure, age buckets, parsing rules, and orphan resolution: `references/reconciler-procedure.md`.

```bash
python3 ~/.hermes/stand-in/ledger_board_reconcile.py            # dry run, print the buckets
python3 ~/.hermes/stand-in/ledger_board_reconcile.py --apply    # stamp the closable drift (SKIP when the dry run shows drift_closable=0 — a no-op run still rewrites the ledger file for nothing; --apply only stamps items whose board row is TERMINAL, never verified items, never board rows, never no_id_match entries; when the flag is a no-op the tool still echoes `applied=False` in its SUMMARY — read the SUMMARY, not the flag name, to know what actually happened)
```

Report the reconciled open count (and each residual bucket) — never the raw `added`/`picked_up` count, because that number is what made the digest overstate outstanding work. For a single-target tick the reconciler is FLEET-WIDE (no --project filter): attribute the residual buckets to other projects, and count the TARGET's real open rows from the board itself — terminal = complete/wontfix/superseded; recurring fixtures (E2E-001/NEVER-DONE style slots) are not real open work, report them separately. Grepping the reconciler output for the TARGET's name yields nothing (no per-target section) — an empty grep is not evidence of no open work; the board census is the only per-target count.

**The reconciler resolves the BARE project name only** (its `--help` exposes just `--apply/--ledger/--scheduler-db/--backup-suffix` — no alias or project-map), so for a family whose primary lane is `<name>-foreman` it prints `NO BOARD` for the bare name and dumps every one of that project's ledger items into `board_missing`. Those items can therefore never reach the `drift_closable` bucket and are never stamped by `--apply`, however many of their board rows are already terminal. Read that `missing` bucket as a RESOLUTION ARTIFACT, never as absent work, and do not hand-stamp the ledger outside the canonical tool (single-implementation rule): instead reconcile that one target manually against the RESOLVED foreman board — load `ledger.json`, take items where `project == '<name>'` and `status != verified`, join each id to its keep-last board row, and report the two buckets separately: board-open work (row still pending/in_progress/blocked) and drift-closable (board row already terminal, ledger still `added`/`picked_up`). Name the drift-closable ids in the report so the resolver owner or the next cycle can stamp them, and state the tool limitation itself as the cross-project escalation when the bare name has no scheduler row at all. Never present the reconciler's bare-name `board_missing` count as the target's backlog or as proof that the resolved board is absent; label it as a resolver artifact, then give the resolved foreman board's own open census separately.

Parse the reconciler's MACHINE summary, not the human tail — markers, bucket keys, GROUPED detail arrays, and the CAPPED-SAMPLE rule (a detail array can omit your target entirely while its board carries dozens of open rows): `references/ledger-and-board-pitfalls.md` (§ machine summary, § capped samples).

