# Greenfield Project Onboarding — Fleet Recipe

How to stand up a brand-new project on the coding-hermes fleet end-to-end, from
empty directory to scheduler-registered, task-tracked, worker-ready. Proven on
<project> (2026-08-01, a browser game build driven from a Telegram session).

## 1. Scaffold

- `git init -b main`, then write package/project files directly (write_file
  beats interactive `npm create` prompts). For TS: strict tsconfig, vite.config
  with vitest config, one trivial passing test so the GitReins tests guard has
  something to run.
- `npm install` → `npm run build` + `npm test` must pass BEFORE first commit
  (lint errors from write_file are just missing node_modules — install first).
- AGENTS.md (project rules incl. commit trailer rule), README.md, .gitignore
  (node_modules/, dist/, `.coding-hermes/board/board.db*`).

## 2. DuckDB Board Init (BOARD-V2)

Fresh project has no tasks.md to migrate — create the board directly:

- Copy the schema from an existing project's `.coding-hermes/board/schema.sql`
  (e.g. ~/<project>/.coding-hermes/board/schema.sql). Drop the trailing-comma bug
  if present (`blocked_since TIMESTAMP,` before `)` breaks DuckDB).
- Init via a script run with `~/<project>/.venv/bin/python3` (has
  duckdb 1.5.5; system python3 lacks it). Create board.db, run schema (which
  seeds fixtures NEVER-DONE / E2E-001 / GITREINS-JUDGE), insert the `board`
  header row (project, namespace), then COPY tasks/events/fixtures → parquet.
- Git-tracked: schema.sql + *.parquet. board.db is gitignored (rebuildable).
- Write-path rules (from coding-hermes-board references/board-write-path.md):
  INSERT event FIRST (compute id via `SELECT COALESCE(max(id),0)+1` — DuckDB
  has no setval), THEN header UPDATE, THEN COPY parquet; bind datetime objects
  for TIMESTAMP columns, never ISO strings/ints.

## 3. GitReins

- `.gitreins/config.yaml`: guards (secrets:true, tests:true, test_mode:diff,
  test_command e.g. `npm test` — must not hang, so `vitest run` not watch),
  evaluator limits, `defaults.model: deepseek-v4-flash`.
- `.gitreins/tasks.yaml`: `tasks:` list — note `gitreins install` adds
  tasks.yaml to .gitignore (it's local task state by design; the board parquet
  is the git-tracked source).
- `gitreins install` (from ~/<project>/.venv/bin) installs the pre-commit
  guard hook. First commit must pass it.
- Every commit carries `Co-authored-by: Your Name <you@example.com>`.

## 4. Scheduler Registration + 900s Fast Cooldown

When Bane says "set foreman to Ns cooldown", the authoritative stores are the
scheduler DB (:9090) and fleet.toml — and the board header:

```bash
curl -s -X POST http://localhost:9090/api/v1/projects -H "Content-Type: application/json" -d '{
  "Name": "<project>", "RepoURL": "local:~/<project>",
  "Workdir": "~/<project>", "Weight": 10, "Priority": 8,
  "CooldownS": 900, "DecayRate": 1.0, "Model": "deepseek-v4-flash",
  "Provider": "deepseek-foreman", "NamespaceID": "coding-hermes",
  "Deliver": "telegram:-1003310984808:<thread>", "Enabled": true }'
```

Then:
- `~/.hermes/venvs/board/bin/python3 ~/.hermes/scripts/fleet-cooldown-policy.py --apply`
  regenerates fleet.toml overrides. It only REDUCES cooldown toward target
  (900 when board has ≥1 real pending task, else 7200) — a project created at
  900 stays 900 even with 0 pending ("leave (below target)").
- Update the board header cooldown_s via a DuckDB script (INSERT event → UPDATE
  header → COPY parquet), reason recorded in the event detail.
- Registered + enabled means the fleet foreman picks up pending board tasks at
  the cooldown interval — that's the Bankai guarantee if the interactive
  session dies. To avoid double-driving: mark tasks `in_progress` the moment
  you dispatch a worker; foremen skip in_progress rows.

## 5. Dual Task Stores (Bane's rule)

Claims need tasks in BOTH `.gitreins/tasks.yaml` AND the board:

- GitReins: `mcp__gitreins__task_create` (criteria list) — ALWAYS pass
  `workdir: ~/<project>` or tasks land in the MCP server's own repo.
- Board: one python script inserts all rows (id, title, status, priority,
  complexity, depends_on, primary_model/provider, capability_tags) then exports
  parquet. Commit the parquet.
- Model routing: implementation → kimi-k3/kimi-for-coding, specs →
  gpt-5.6-terra/openai-codex, E2E/browser → gpt-5.6-luna/openai-codex.

## 6. Worker-Spawn Verification

Before any long worker run, smoke-test each provider/model pairing:

```bash
cd /path/to/repo && timeout 120 hermes chat -Q --provider <provider> -m <model> --yolo -q "Reply with exactly: OK"
```

Proven pairs (2026-08-01): `kimi-for-coding`/`k3` (fixed-price Kimi K3),
`openai-codex`/`gpt-5.6-terra` (Terra specs — Hermes-managed auth via
OPENAI_ACCESS_TOKEN; the standalone codex CLI's OAuth can expire independently
with 401 "token could not be refreshed" — don't fight it, use hermes chat).

Long workers: `cd repo && hermes chat -Q ... -q "<task>" > /tmp/worker.log 2>&1`
via terminal(background=true, notify_on_complete=true). `hermes chat -w` is
`--worktree`, not workdir — cwd is inherited. A dead-looking worker (empty log,
no files for minutes) is usually still booting (memory/skills load first) —
check `ps aux | grep <model>` before relaunching.

**If the worker genuinely died mid-task** (partial files on disk, no commit,
process gone — <project> Terra run 1 wrote 6/13 specs then vanished):
checkpoint-commit the partial output immediately (docs commit + co-author
trailer), then relaunch with a RESUME prompt ("files X exist and are good;
finish the rest; don't redo existing files"). Full pattern in
coding-hermes-worker `references/worker-spawn-via-hermes-chat.md`.
