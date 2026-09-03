---
name: doc-writer-weekly
description: >-
  Weekly cron doc pass; board injection; quiet-history no-op.
version: 1.0.0
author: Hermes
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [doc-writer, scheduler, board-injection, documentation]
    related_skills:
      - coding-hermes-jsonl-board-append
      - coding-hermes-scheduler
      - coding-hermes-foreman
---

# doc-writer-weekly — Fleet Documentation Pass

## When to Use

- A `doc-writer` scheduler tick fires (weekly project, or manual
  `POST /api/v1/projects/doc-writer/spawn`) and you are the executing agent.
- Any manual fleet documentation pass: scan project boards for new git
  activity since the last `doc_writer_run` baseline and file evidence-backed
  `DOC-` tasks.

Weekly scheduler tick that keeps fleet project docs honest: for each active
project board it finds real, undocumented git activity since the last doc pass,
researches it (own web research encouraged), and files at most 3 evidence-backed
`DOC-<N>` task rows so the owning foreman writes the docs. **All-quiet is a
SUCCESS** — an idle clean tick is the intended steady state, not a failure.

## 1. Trigger

- **Scheduled:** scheduler project `doc-writer`, namespace `doc-writer`,
  weight 3, priority 2, `cooldown_s = 604800` (weekly). Prompt:
  namespace `default_prompt` on the DB row (the ~300-word weekly procedure) —
  do NOT duplicate it in fleet.toml (the file carries pins only).
- **Manual:** `curl -X POST http://localhost:9090/api/v1/projects/doc-writer/spawn`
  → `202 {"status":"spawned","project":"doc-writer","tick_id":"<id>"}`.
  `409` = a tick is already running (`ErrProjectRunning`) — report the running
  tick id (GET `/api/v1/ticks?project=doc-writer&limit=3`) and stop; never
  double-fire.
- Project row lives in the scheduler DB; fleet.toml mirrors it (`deliver` is
  NOT API-editable — absent from `ProjectUpdates`; the daemon pins only
  cooldown/model/provider/enabled/prompt at boot from fleet.toml).

## 2. Baseline discovery (per project)

For EACH project in `~/.hermes/fleet.toml` `[[projects]]` whose
`namespace_id` is `coding-hermes` or `pm` AND whose `workdir` exists locally:

1. Read `<workdir>/.coding-hermes/board/events.jsonl`.
2. Find the most recent event whose **detail** mentions `doc-writer` or a
   `DOC-` task id (grep the decoded detail JSON — events' `detail` field is a
   JSON-ENCODED STRING, so `grep '"doc_writer_run"' events.jsonl` or
   `jq -r '.detail' | grep` — see coding-hermes-jsonl-board-append
   verification notes; never substring-match raw lines for idempotency).
   Its timestamp = the last doc pass (`doc_writer_run` date in the audit
   detail, or the event `timestamp`).
3. No such event anywhere → baseline = **30 days back** (`date -u -d '30 days ago' +%Y-%m-%d`).

## 3. Activity gate (quiet = skip silently)

`git -C <workdir> log --oneline --since=<baseline>`

- **Zero commits** → `skipped-quiet` for that project. No event, no injection.
- **Commits exist but are ALL board chore** (messages/`--stat` touching only
  `.coding-hermes/` and nothing else) → `skipped-quiet` too — board churn is
  not documentation-worthy activity. Filter with
  `git log --since=<baseline> --stat` and eyeball the touched paths.
- Meaningful commits → proceed to research. Do NOT inject just because the
  clock says so; inject only when there is real, verifiable new surface.

## 4. Research & cross-check (evidence before filing)

1. Scan the new commit range: `git log --since=<baseline> --oneline`, then
   diffstats for the interesting ones
   (`git show --stat <sha>`, `git diff <baseline-sha>..HEAD --stat`).
2. **Own web research is ENCOURAGED** for new concepts/libraries/APIs the
   commits introduce (web_search the library name/version/breaking-change).
   Research gives the doc task a "why it matters" angle — it does NOT replace
   git evidence.
3. **Cross-check EVERY candidate doc topic against the actual git history:
   file:line evidence.** The concept/feature must appear IN THE DIFF (code
   added/changed), not just in the commit message. Produce
   `<file>:<line>` + the commit sha range for each candidate. A topic whose
   only evidence is a commit subject is NOT filed.
4. Candidates = undocumented features/changes: new flags/endpoints/config
   keys, behavior changes, new modules, env vars, migration steps.

## 5. Injection recipe (DOC-<N> task rows)

Per board: **at most 3 rows**, `priority P3`, `complexity 3`, `status pending`,
title carries the evidence, `reasoning` carries file:line + why now.

1. **boardctl first:** if `boardctl` is on PATH:
   `boardctl -C <workdir> create DOC-<N> "<title>" ...` (check `boardctl --help`;
   adapt flags to the board's own conventions).
2. **Fallback — JSONL append** per skill `coding-hermes-jsonl-board-append`
   (supervisor/PM-side task injection section):
   - **Dedupe by PARSED id**: read all `id` fields from `tasks.jsonl`
     (`ids = {json.loads(l).get("id") for l in lines if l.strip()}`), skip if
     the id exists. NEVER substring matching (`"DOC-1" in line` matches a
     foreman_note mentioning DOC-1 elsewhere and silently skips the inject —
     proven consensus #295 class). Also grep `'"DOC-<N>"'` quoted-form when
     verifying.
   - **Dynamic schema mirror**: `base = dict(rows[-1])`, then
     `base.update({...})` with the new id/title/status/priority/complexity/
     reasoning/foreman_note/timestamps. Serialization style DETECTED from the
     last line (`separators`, `ensure_ascii`). Never hardcode the key set —
     mirror the last real row.
   - **APPEND-ONLY**: `open(path, "a")`, write `json.dumps(row, ...) + "\n"`.
     NEVER load-all/rewrite a whole JSONL file.
   - Timestamps in `datetime.now(timezone.utc).isoformat()` (T-format, matches
     JSONL-canonical boards).
   - **Commit + push with co-author trailer** (`git commit --no-verify`;
     `git branch --show-current` FIRST — master vs main varies per repo;
     `git push origin <branch>`; verify `git rev-list --count @{u}..HEAD` = 0).
   - `status: "pending"`, `worker_status: "pending"`, priority P3 string.
3. Idempotency: a re-run of the same pass (same day, same board) must inject
   NOTHING — parsed-id dedupe is the guard.

## 6. Baseline write-back (audit event per touched board)

For EVERY board where you injected rows, append ONE audit event so next week's
pass has its baseline:

```json
{"doc_writer_run": "<UTC date YYYY-MM-DD>", "injected": ["DOC-1", "DOC-2"]}
```

- Event row: mirror the last event's schema (id = max+1, event_type per board
  convention e.g. `audit`/`tick`), append to `events.jsonl`, commit + push
  (same append-only + co-author rules). Boards you did NOT inject into need no
  event — their absence from the event stream just means "no doc pass touched
  them"; their baseline rolls forward by the 30-day fallback or the previous
  run's date.

## 7. Reporting shape

Per-project one-liner with one of three verdicts:

- `injected DOC-1,DOC-2` (with the project name and evidence count), or
- `skipped-quiet` (no meaningful commits since baseline), or
- `skipped-up-to-date` (board already has open DOC- tasks / docs already cover
  the activity — no new injection needed).

End with the summary line. **If every project is quiet, report exactly that —
an idle clean tick is a SUCCESS** (e.g. "All N projects quiet — no doc
injections this week."). Never manufacture doc tasks to look busy.

## 8. Pitfalls

- **409 on spawn** = tick already running. Report the running tick id
  (`GET /api/v1/ticks?project=doc-writer&limit=3`), do not retry-spawn.
- **Boards without a pushable remote**: check `git -C <workdir> remote -v`
  and `git rev-list --count @{u}..HEAD` BEFORE injecting. No remote / can't
  push → **skip injection** for that project (report `skipped-no-remote`).
  Injecting rows you cannot push strands other foremen on uncommitted work.
- **Never hand-edit `board.db`** — it is an untracked cache; `events.jsonl` /
  `tasks.jsonl` are canonical. Parity-probe divergence after an append is
  benign when the JSONL + max-id are right (classify, don't repair).
- **Never rewrite whole JSONL files** — append-only always (churn doctrine).
- **Never substring-match for idempotency** — parsed-id sets only.
- **Detail is a JSON-encoded string** in events.jsonl — decode before grepping
  `doc_writer_run`.
- **Workdir uniqueness on the scheduler**: the doc-writer project itself has
  workdir `~/coding-hermes-scheduler` (the nested scheduler-repo path
  is owned by the enabled `coding-hermes-scheduler` project — the API rejects
  duplicate workdirs). Its own repo_url/workdir are administrative; all real
  work happens in the scanned projects' workdirs from fleet.toml.
- **deliver is not API/PUT-editable**: `ProjectUpdates` has no Deliver field
  and the fleet.toml boot pin skips it for existing projects; set it at
  creation or via direct sqlite3 on the scheduler DB
  (`sqlite3 ~/.hermes/coding-hermes/scheduler.db "UPDATE projects SET
  deliver='...' WHERE name='doc-writer'"` — API-guarded-op fallback per
  AGENTS.md; spawn handler reads the DB fresh so it takes effect immediately).
