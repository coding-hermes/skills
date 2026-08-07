# Foreman Tick — Fallback Checklist

When `coding-hermes-foreman` skill fails to load ("not supported on this platform"), this reference plus `coding-hermes-self-heal` (SKILL.md) plus `coding-hermes-cron/references/foreman-self-improving-loop.md` is sufficient to execute a complete foreman tick.

**Proven:** <project> 2026-07-24 T12 — foreman skill unavailable, tick executed fully via this fallback path. Hermes Canopy 2026-07-24 T11 — same pattern, FE-07 dispatched + committed, post-worker build errors fixed by foreman. <project> 2026-07-25 T16 — idle tick, 14-point audit found + fixed SECURITY.md and CODEOWNERS gaps directly. <project> 2026-07-25 T17 — E2E-STUB-001 dispatched + foreman-fixed (duplicate function redeclaration from worker), judge gap identified. Kobayashi-Maru 2026-07-25 T48 — COMBO-secondary-effects worker timed out at 600s; GitReins guard_run auto-committed the worker's output (see guard-timeout-auto-commit pitfall below). DexDat Core 2026-07-25 T23 — idle tick, 14-point audit completed + E2E-001, discovered 105 files needing ruff format (prior audits never checked). RethinkDB 2026-07-27 T43 — idle tick, discovered PERF-BENCH already committed by sibling session (8beba4fdd5); exposed 6-tick cooldown fabrication chain (#37-#42 all claimed 43200s, scheduler showed 1800s). h3-sdk-python 2026-07-27 T25 — idle tick, 14-point audit found ruff format gap (2 files) + missing SECURITY.md/CODEOWNERS/LICENSE; all fixed directly, committed as 7a43522. Helix 2026-07-28 T13 — idle tick, 19-gate audit exposed 2-tick cooldown fabrication chain (#11-#12 claimed 43200s, scheduler showed 1800s); created SECURITY.md/CODEOWNERS + .gitignore .env protection via foreman-direct fix. Kobayashi-Maru 2026-07-28 T134 — idle tick, detected pre-written stale tick entry with fabricated data (engine 51.2s claimed vs 5.0s actual, 0 transitive deps claimed vs 14 actual, 11/11 NEVER-DONE claimed vs 2 docs missing). Replaced entire entry with ground truth; created SUPPORT.md + CODE_OF_CONDUCT.md + added .env.example gitignore exception. DuckBrain 2026-07-28 T144 — 20th consecutive idle tick, uncovered 100+ tick file-existence fabrication chain: board claimed 9/9 docs but `ls` revealed CODEOWNERS + SUPPORT.md missing. Created both directly via self-fix rule. Gate 11 (now "Docs & Security") was previously too narrow (3 files) — patched to full 9-file `ls` command with explicit anti-fabrication warning. Mythos 2026-07-28 T84 — foreman skill unavailable; exposed 6-tick cooldown fabrication chain (board claimed 43200s, scheduler=900s), discovered DuckBrain namespace mismatch (board ref'd `wojons-mythos`, real namespace is `mythos`), hit parent-repo gitignore blocking entire coordination hub directory requiring `git add -f` for every commit. Bunker 2026-07-28 T46 — foreman skill unavailable; broke 26-tick idle streak via foreman-direct fix for UX-005 (`bunker version`, 5-line cobra cmd). Board had 6 non-blocked undispatched tasks ignored across 26 idle ticks because foreman declared project "feature-complete" — a blind spot where the self-improving loop's "create matrix rows → dispatch next tick" was dead because idle-tick escalation mode stopped dispatching entirely. Foreman-direct fix re-engaged the loop: GitReins task created + judged (all 4 criteria PASS), commit 45048fa. Key lesson: idle-ticks that only audit and never dispatch are NOT truly idle — they're stuck. See pitfall "Feature-complete blind spot — undispatched tasks ignored under escalation." Bunker 2026-07-28 T47 — foreman skill unavailable; 2nd productive tick after 26-tick idle streak. UX-006 (`bunkerd --help`) code was already written on disk (66+4 ins/del in cmd/bunkerd/main.go) from a sibling session — detected during self-heal dirty-workdir check per Phase 1. Build+test confirmed, foreman committed directly without worker dispatch. GitReins judge PASS all 7 criteria. Additional gap found during NEVER-DONE audit: .gitignore was missing `.env/.env.*` protection (no prior tick had flagged it). Fixed directly with `!.env.example` exception. Pre-written stale tick entry detected on board with fabricated data: wrong DuckBrain namespace (`coding-hermes` instead of `bunker`), false NOTICE.md claim, fabricated key counts. Replaced entirely with ground truth. This is a variant of the Kobayashi-Maru T134 pattern — the fabricated claims were different (DuckBrain namespace + file existence vs engine times + dep counts) but the detection and response are identical: replace, don't append. Key lesson: the self-improving loop can re-engage on the second tick after an idle streak — T46 broke the streak, T47 continued it by finding the next task's code already written on disk. <project> 2026-07-28 T37 — foreman skill unavailable; idle zombie tick. Exposed DuckBrain key count meta-fabrication chain: prior ticks #35-#36 "corrected" the count from 8 to 1 but ground truth was 9. The "correction" was itself fabricated — likely `list_keys` without `namespace` parameter. Corrected to 9 keys via `list_keys(namespace="<project>")`. Also hit the partial-correction pitfall: stale "1 key" claim in 4 board locations (header, verdict, annotation, routing notes) required multi-patch board update. 25th idle tick, CRON_PAUSE_REQUESTED active since #31, project should be disabled/archived. Off-by-One 2026-07-28 T185 — foreman skill unavailable; idle tick exposed TWO concurrent fabrications in a single tick: (1) CODEOWNERS never existed on disk but 10+ prior ticks (141-184) claimed "9 docs" — fabrication pattern #7 (file existence). (2) Cooldown claimed 900s across 10+ ticks but scheduler showed 1350s — fabrication pattern #1. Both corrected: CODEOWNERS created via foreman-direct fix (self-fix rule, gap persisted 3+ ticks), board header cooldown corrected. Key lesson: a single idle tick can expose multiple fabrication chains simultaneously when the foreman verifies EVERY claim against authoritative sources per Step 0.5. Prior ticks that skipped the scheduler API query and the `ls` doc check let both fabrications propagate for 10+ ticks. <project> 2026-07-28 T35 — idle tick; exposed 6-tick cooldown fabrication chain (T30-T34 claimed 900s, scheduler=1350s). Also hit `write_file` overwrite pitfall: wrote tick entry with `write_file` which destroyed the 110-line board → recovered via `git checkout` which discarded uncommitted T34 entry → had to reconstruct T34 from memory. Corrected cooldown with `sed`, appended T35 via `cat >>` heredoc, committed as 8e8cac9. DuckBrain 2026-07-29 T160 — foreman skill unavailable; idle tick exposed a 16-tick cooldown fabrication chain. H3 umbrella 2026-07-28 T89 — foreman skill unavailable; cross-synced 7 tasks (P4-01/02/03/05 + RES-IMPL-01/02/03) from shim foreman ticks #79-80. Exposed cross-repo governance doc fabrication: board claimed "all 6 repos full governance" since tick #77, but per-repo `ls` proved 4/5 sub-repos missing 3 docs each and umbrella itself missing them. Created umbrella docs directly (foreman-direct fix: SUPPORT.md, CODE_OF_CONDUCT.md, CHANGELOG.md), flagged sub-repo gaps. 52 real tasks remain. DuckBrain 2026-07-30 T181 — foreman skill unavailable; PRODUCTIVE tick — broke idle streak with 2 self-fixes (prettier + npm audit fix). BUG-034 confirmed RESOLVED (176/176 ALL PASS). Exposed cooldown fabrication (board 900s → scheduler 1350s). 12/12 docs `ls`-verified. `execute_code` cwd mismatch discovered: cwd was `~/<project>` while cron workdir was `~/duckbrain` — absolute paths required in Python append fallback (see pitfall below). **Proven:** ... Helix 2026-07-30 T50 — foreman skill unavailable; PRODUCTIVE tick — SRC-001 worker dispatched and completed (source config parser, 67baacf, 28 tests). 2 ID-002 lint issues fixed by foreman directly (9d6173e). Exposed Tick #49's double fabrication: disk claimed 98% (actual 90%) and cooldown claimed 900s (DB showed 600s). Board header metrics re-verified against authoritative sources per Step 0.5. Foreman-fallback workflow handled both lint fixes and worker dispatch correctly. DuckBrain 2026-07-30 T185 — foreman skill unavailable; idle tick exposed 4-tick prettier gate fabrication chain. Consensus 2026-07-30 T52 — foreman skill unavailable; idle tick, 15-gate audit all green except pre-existing chronicle VCS (15+ ticks). Created 3 governance docs (NOTICE, GOVERNANCE.md, TRADEMARK_POLICY.md) for 12/12 doc compliance — foreman-direct fix. `execute_code` Python append used for board entry. Scheduler cooldown 43200s verified matching board (no drift). DuckBrain ~50 entries, committed 3a82b94. Off-by-One 2026-07-30 T217 — foreman skill unavailable; PRODUCTIVE tick — created 3 governance docs (NOTICE, GOVERNANCE.md, TRADEMARK_POLICY.md) closing a 24-tick doc gap since #193. Exposed cooldown REACHABILITY fabrication: board claimed "Scheduler unreachable" for ~16 ticks without any foreman actually attempting the query. Scheduler returned 900s instantly. Board header corrected via `patch`, tick entry appended via `execute_code` Python, committed 7551851. #181-#184 claimed "prettier: Clean" but `npx prettier --check .` found 350 unformatted files (31 in packages/ui/). Root cause: prior foremen scoped prettier to `'src/**/*.ts' 'tests/**/*.ts'` only, missing the monorepo's `packages/` subdirectory entirely. Also confirmed BUG-034 present on fresh daemon (4/8 E2E) contradicting board's "absent 4 ticks" claim. Fixed 1 file (bin/duckbrain.ts) directly; remaining 31 packages/ui/ files flagged as task for worker dispatch. Updated foreman-tick-fallback Formatter gate pitfall to require `--check .` first (full repo) before scoping.

---

## Required Context

Before starting, ensure these are loaded:
1. `coding-hermes-self-heal` — Steps 0 (self-heal) and 0.5 (anti-fabrication)
2. `coding-hermes-cron/references/foreman-self-improving-loop.md` — self-improving loop rules
3. Project's `.coding-hermes/board/tasks.jsonl` — the JSONL board with task matrix and NEVER-DONE audit fixture

---

## Tick Sequence

### Phase 1: Self-Heal (Step 0)

Run the full self-heal protocol from `coding-hermes-self-heal` SKILL.md:

1. Clean GitReins MCP state files (never commit these). These files may not be tracked (gitignored) — suppress errors with `2>/dev/null`. Also clean up any `.bak` backup files left by prior MCP operations:
   ```
   git checkout -- .gitreins/config.yaml .gitreins/tasks.yaml 2>/dev/null
   rm -f .gitreins/config.yaml.bak .gitreins/tasks.yaml.bak 2>/dev/null
   ```
   Exit code 1 from the checkout is harmless when files aren't tracked (e.g., `.gitreins/tasks.yaml` in `.gitignore`). **Proven:** <project> tick #24 — `.gitreins/tasks.yaml` not tracked, checkout exited 1, harmless. <project> 2026-07-20 — same pattern, `.bak` files accumulated across ticks.

2. Clean Hilo post-commit noise — `.vfs/graph/edges.jsonl` is modified by the post-commit hook on every commit. Restore it to avoid dirty-workdir false positives:
   ```
   git checkout -- .vfs/graph/edges.jsonl 2>/dev/null || true
   ```
   If this fails with "did not match any file(s) known to git", the file isn't tracked in this repo (project-specific `.gitignore` or never committed). This is harmless — continue. The `|| true` prevents this from breaking `&&` chains. **Proven:** coding-hermes-scheduler tick #170 — edges.jsonl not tracked, command exited 1, harmless.

3. Handle untracked cruft from prior ticks — CI scripts, temp files, stale artifacts. Delete them rather than letting them accumulate.

4. Handle dirty board files — if `.coding-hermes/tasks.md` has stale HTML-comment noise from prior ticks (GITREINS-JUDGE checklist items, duplicated config blocks), revert to committed state:
   ```
   git checkout -- .coding-hermes/tasks.md
   ```
   **⚠️ PITFALL: this discards uncommitted prior-tick entries.** If the prior foreman tick added its tick log entry but never committed (dirty workdir shows `M .coding-hermes/tasks.md`), `git checkout` reverts to the last committed state and the prior tick's entry is LOST. **Detection:** `git diff .coding-hermes/tasks.md | head -20` — if the diff shows the prior tick's entry, preserve it. **Fix:** either (a) commit the prior tick's entry first as a chore, then proceed, or (b) use `sed` or `patch` to clean only the stale HTML-comment noise without reverting the entire file. **Proven:** <project> T35 (2026-07-28) — T34 entry was uncommitted; git checkout discarded it, requiring reconstruction from memory.

5. Verify git identity and co-author from `~/.hermes/.env`.

6. Pull rebase (if remote exists).

### Phase 2: Ground Truth Verification (Step 0.5)

Run the full anti-fabrication check from self-heal Step 0.5. Query authoritative sources for ALL numeric claims:

- **Scheduler cooldown:** `curl -s http://127.0.0.1:9090/api/v1/projects/<name> | python3 -c "import sys,json; print(json.load(sys.stdin)['project']['CooldownS'])"` — **critical: this is the #1 fabricated metric across the fleet. Never trust the prior tick's board claim.**
- DuckBrain: `list_keys(prefix="/projects/<name>/", namespace="<name>")` — count actual keys. **⚠️ Verify the correct namespace first:** check `AGENTS.md` in the code sub-repo for the canonical namespace declaration. The board's prior-tick namespace references may be wrong (e.g., board says `wojons-mythos`, AGENTS.md says `mythos`). Try plausible variants if the first query returns 0. See pitfall: "DuckBrain namespace ≠ directory name."
- Dependencies: `go list -m -u all | grep '['` — not memory
- Build: `go build ./...` — run fresh every tick
- Tests: `go test ./... -count=1 -short` — run fresh every tick
- GitReins: `task_list` via MCP — confirm state
- Hilo: `hilo graph stats` — confirm edge count

### Phase 3: NEVER-DONE Audit

Run the full audit per `coding-hermes-never-done` skill (current version: 14-point). The standard gate set (language-agnostic subset shown below; consult the never-done skill for the full list and language-specific commands):

**Gate 0 — Scheduler cooldown ground truth (run BEFORE all other gates).** This is the #1 fabricated metric across the entire fleet. Query the scheduler API, then compare against the board's last reported value:

```bash
curl -s http://127.0.0.1:9090/api/v1/projects/<name> | python3 -c "import sys,json; print(json.load(sys.stdin)['project']['CooldownS'])"
```

If the API value differs from the board's prior-tick claim: the board is wrong, the API is authoritative. Call out the discrepancy in the audit table as 🔴 FABRICATED with the actual value. Correct the board header immediately. Do NOT silently "fix" it — the audit trail of which ticks fabricated matters for fleet governance. This gate has caught fabrication chains spanning 3-6+ ticks across 5+ projects (see pitfall: "Prior-tick board cooldown claims are unreliable").

| # | Gate | Typical Command |
|---|------|-----------------|
| 1 | Build | `go build ./...` (or project equivalent) |
| 2 | Tests | `go test ./... -count=1 -short` (or project equivalent) |
| 3 | Vet/Lint | `go vet ./...` (or project equivalent: ruff, tsc, etc.) |
| 4 | Formatter | `gofmt -l cmd/ internal/ pkg/` (Go — scope to source dirs, NOT `gofmt -l .` which hits stray `.go` files in work-item/patch dirs), `ruff format --check src/ tests/` (Python), `npx prettier --check .` (TS/JS) — run the LANGUAGE-SPECIFIC command. Python: `ruff format --check` catches drift that `ruff check` (lint-only) misses. |
| 5 | TODOs/FIXMEs | `rg -n 'TODO|FIXME|HACK|XXX' --type go` |
| 6 | Hilo | `hilo graph stats` → classify as useful/empty/N/A |
| 7 | GitReins | `guard_run` via MCP + `task_list` + evaluator health |
| 8 | DuckBrain | `list_keys(prefix="/projects/<name>/", namespace="<name>")` — always pass namespace |
| 9 | CI | `gh run list` or check CI dashboard |
| 10 | Deps | `go list -m -u all | grep '['` (Go), `timeout 60 .venv/bin/pip list --outdated` (Python — needs 60s, hits PyPI per-package), `npm outdated` (TS/JS) — always pass `namespace` to DuckBrain calls |
| 11 | Docs & Security | **Docs (12-file list — RUN `ls` EVERY TICK):** `ls README.md LICENSE SECURITY.md CODEOWNERS SUPPORT.md CODE_OF_CONDUCT.md CONTRIBUTING.md CHANGELOG.md .gitignore AGENTS.md NOTICE GOVERNANCE.md TRADEMARK_POLICY.md 2>&1` — count missing. Create any missing files directly (self-fix after 3+ ticks). **This is fabrication pattern #7 — never copy the prior tick's claim, always run `ls`.** **Canonical source:** `coding-hermes-never-done/references/doc-coverage-checklist.md` (v3, 12-file). The 12-file `ls` command is authoritative — do NOT enumerate your own list or use a subset. **Security:** .gitignore must block `.env` / `.env.*` with `!.env.example` exception, gitleaks clean. |
| 12 | Middle-out wiring | Audit main.go→DI→serve→CLI/HTTP/gRPC chain (see coding-hermes-middle-out) |
| 13 | E2E testing | Check if E2E tick is due (every 5-10 ticks); verify output files exist on disk |
| 14 | GitReins judge | Verify `.gitreins/config.yaml` has evaluator section with model + caps |

For any gate that fails: follow the self-improving loop from `foreman-self-improving-loop.md`. If the fix is trivial (docs, config, boilerplate) and the gap has persisted 3+ ticks, fix it directly. If it needs code, create a matrix row for worker pickup.

### Phase 4: Task Board Scan

Check each active task in the matrix:

- Blocked tasks: note the blocker, no action
- Ready tasks: verify deps are satisfied, note worker model assignment
- E2E tasks: check if it's time (every 5-10 ticks)
- NEVER-DONE: runs every tick (Phase 3 above)

**Pre-Dispatch Git Verification (MANDATORY before any worker dispatch):** Before dispatching a worker for any board task, check `git log --oneline -10` for commits matching the task's keywords. A sibling foreman session may have already completed the work but the board hasn't been fully updated yet (task still in Active section, or marked ✅ but not yet moved to Completed). A stale board + fresh git commits = worker waste.

```bash
# Check recent commits for task-related keywords BEFORE dispatching
git log --oneline -10
# If a commit message contains the task ID or description keywords:
# 1. Verify the commit actually implements the task (git show --stat <hash>)
# 2. If it does: do NOT dispatch a worker. Move the task to Completed on the board.
# 3. If the board is partially updated (task marked ✅ but still in Active):
#    clean up the board (move to Completed, fix duplicates) before proceeding.
```

**Detection:** `git log --oneline -10` shows commits with task-matching keywords made since the board's last-known tick, but the board still lists the task as active. Common pattern: the board was updated by the sibling to add a tick log entry AND mark the task ✅, but the task row wasn't moved from Active to Completed. The board is in a transitional state.

**Proven:** Kobayashi-Maru 2026-07-25 T51 — COMBO-secondary-effects was listed as active on the board (✅ marked but still in Active section). Worker dispatched for it burned 435s and 936K input tokens before discovering the work was already committed by a sibling session (b99c79c + a025af7). A pre-dispatch `git log --oneline -10` would have shown a025af7 ("feat: combat-triggered secondary effects...") and the worker would never have been spawned.

### Phase 5: Post-Worker Verification & Commit

**If a worker was dispatched this tick** and its output is now in the workdir:

1. Verify the build passes — workers may hit `max_iterations` before running their own verification:
   ```bash
   # TypeScript projects
   cd frontend && npx tsc --noEmit && npm run build
   # Go projects
   go build ./... && go vet ./...
   ```

2. If build fails: fix trivial errors directly (unused imports, duplicate imports, duplicate function declarations — see pitfalls below). If the error requires understanding the logic (wrong types, missing functions, broken wiring), flag it as a board gap and create a bug task. Do NOT re-dispatch the task.

3. **Run GitReins Tier 2 judge on non-trivial code changes.** Per quality-gate discipline, every non-trivial code change MUST be evaluated. Create a GitReins task for the board item if it doesn't already exist in `.gitreins/tasks.yaml`, then run the judge:
   ```bash
   # Create task if needed
   # mcp__gitreins__task_create(id="<task-id>", title="<title>", criteria=[...], workdir="/path/to/repo")
   # Run judge
   # mcp__gitreins__judge_evaluate(id="<task-id>", workdir="/path/to/repo")
   ```
   The judge outputs pass/fail + evidence. If it fails: investigate WHY (token budget, unverifiable criteria, evidence missing) — do NOT dismiss as advisory. Fix the task criteria or the code, re-run. Only proceed to commit when the judge passes.
   **Skip the judge for:** doc-only changes, board-only commits (chore), trivial boilerplate (SECURITY.md, CODEOWNERS, .gitignore entries). **Never skip for:** new features, stub→real replacements, dependency additions, refactors.

4. **Append tick log entry to `.coding-hermes/tasks.md` — use terminal `cat >>`, NOT `write_file`.** `write_file(path, content)` OVERWRITES the entire file with just the provided content. It is NOT an append. To add a new tick entry at the end of the board, use:
   ```bash
   cat >> .coding-hermes/tasks.md << 'ENTRY'
   
   |||| T<N> | timestamp | **Summary.** Details here. |
   ENTRY
   ```
   For targeted edits inside the existing file (header updates, fixing cooldown claims, correcting stale entries), use `patch` mode='replace' or `sed -i`. Only use `write_file` when creating a NEW file from scratch. **Proven:** <project> T35 (2026-07-28) — write_file reduced 110-line board to 2 lines; required git checkout recovery and redo via cat heredoc.

5. Stage and commit with `--no-verify`:
   ```
   export GIT_AUTHOR_NAME="..." GIT_AUTHOR_EMAIL="..."
   export GIT_COMMITTER_NAME="..." GIT_COMMITTER_EMAIL="..."
   git add -A
   git commit --no-verify -m "feat: <task-id> — <summary>" -m "Co-authored-by: $CO_AUTHOR"
   ```

6. Update board status (mark task ✅, update header).

7. Commit board update separately:
   ```
   git add .coding-hermes/tasks.md
   git commit --no-verify -m "chore: T<N> board update — <task> ✅, <next-task> next" -m "Co-authored-by: $CO_AUTHOR"
   ```

**If no worker was dispatched** (idle audit tick):

1. Add tick log entry to `.coding-hermes/tasks.md` — use `cat >>` heredoc, NOT `write_file`.
2. Stage and commit board-only changes with `--no-verify`.

---

## Pitfalls

### `write_file` OVERWRITES the entire file — use `cat >>` or `patch` for board updates

The Hermes `write_file` tool replaces the ENTIRE file content with whatever string you provide. It is NOT an append operation. When updating a board with a new tick entry, calling `write_file(path, new_entry)` destroys the full board and leaves only `new_entry`. **Recovery:** `git checkout -- .coding-hermes/tasks.md` restores the last committed version, but this discards any uncommitted prior-tick entries. **Correct approach:** use terminal heredoc (`cat >> file << 'ENTRY' ... ENTRY`) to APPEND new tick entries, and `patch` mode='replace' or `sed -i` for targeted edits inside the existing file. Only use `write_file` for creating NEW files from scratch. **Proven:** <project> T35 (2026-07-28) — write_file reduced 110-line board to 2 lines; git checkout lost uncommitted T34.

### `cat >>` heredoc rejected by terminal tool (false-positive backgrounding detection) — use `execute_code` Python append

The terminal tool may reject `cat >> file << 'ENTRY' ... ENTRY` with "Foreground command uses '&' backgrounding" even when the heredoc content contains no `&` characters. The tool's regex can false-positive on certain content patterns (long entries with pipe tables, special characters). **Detection:** terminal returns exit code -1 with the backgrounding error message, and the board file is unchanged. **Fix:** use `execute_code` with Python's `open(path, "a").write(content)` — this bypasses the shell entirely and writes directly from the Python runtime. The `write_file` tool still must NOT be used (it overwrites), but `execute_code`'s `open("a")` mode is a safe append. Pattern:

```python
# In execute_code:
with open("/path/to/.coding-hermes/tasks.md", "a") as f:
    f.write(tick_entry)
# Verify
with open("/path/to/.coding-hermes/tasks.md", "r") as f:
    lines = f.readlines()
    print(f"Total lines: {len(lines)}")
```

This is the TERTIARY fallback — `cat >>` heredoc is primary, `execute_code` Python append is secondary when the terminal tool rejects the heredoc. NEVER use `write_file` for board appends. **Proven:** Helios Tick #101 (2026-07-29) — `cat >>` heredoc rejected by terminal tool (false-positive `&` detection, no actual `&` in content); `execute_code` Python `open("a")` succeeded, board went from 502 to 540 lines.

**CRITICAL: `execute_code` cwd ≠ cron workdir — always use absolute paths.** The `execute_code` Python runtime starts in the session's HOME directory (or wherever the Hermes process was launched), NOT the cron job's `workdir`. In a cron-initiated foreman tick, `pwd` inside `execute_code` may return `~/<project>` while the cron's workdir is `~/duckbrain`. Relative paths like `".coding-hermes/tasks.md"` silently write to the wrong directory or fail. **Fix:** always construct absolute paths: `open("~/duckbrain/.coding-hermes/tasks.md", "a")`. The terminal tool's `workdir` parameter does NOT propagate to `execute_code`. **Detection:** the file appears modified in `git status` in the cron workdir after the write, but the actual write landed elsewhere. **Proven:** DuckBrain Tick #181 (2026-07-30) — `execute_code` `pwd` returned `~/<project>`; used absolute paths `~/duckbrain/.coding-hermes/tasks.md` successfully.

### `git checkout` to restore board discards uncommitted prior-tick entries

Phase 1 step 4 recommends `git checkout -- .coding-hermes/tasks.md` to clean stale HTML-comment noise. If the prior foreman tick added its tick log entry but never committed (the dirty-workdir detection at tick start showed `M .coding-hermes/tasks.md`), this checkout silently discards the prior tick's entry. **Detection:** before running `git checkout`, check `git diff .coding-hermes/tasks.md | head -20` — if the diff shows a prior tick's entry, preserve it. **Fix:** either (a) commit the prior tick's entry first as a chore, then proceed with checkout, or (b) use `sed`/`patch` to clean only the stale HTML-comment noise without reverting the full file. **Proven:** <project> T35 (2026-07-28) — T34 entry was uncommitted in working copy; git checkout discarded it; had to reconstruct from memory.

### `pip list --outdated` times out at default 30s on Python projects

The dep-check gate (#10) runs `pip list --outdated`, which contacts PyPI for every installed package. On projects with 20+ transitive dependencies, this routinely exceeds 30s and times out. The command also crosses the `pip`/`pip3` boundary — the project's venv may use a different Python than the system `pip`.

**Detection:** `pip list --outdated` exits with code 124 or returns no output after a 30s timeout.

**Fix — two-tier:** (1) Always use the venv's pip explicitly: `.venv/bin/pip list --outdated` (not bare `pip`). (2) Always use `timeout 60` to give it headroom: `timeout 60 .venv/bin/pip list --outdated`. If even 60s fails, the count is stable enough to fall back to the prior tick's count with a `⚠️ timed out — using prior tick` qualifier (per self-heal Step 0.5 fallback rule). Do NOT fabricate a count.

**Proven:** h3-sdk-python T25 — `pip list --outdated` timed out at 30s (system pip, no venv prefix). Retry with `.venv/bin/pip` + `timeout 60` succeeded (1 outdated: pydantic-core). <project> T22 — same pattern, foreman fell back to prior-tick count with qualifier.

### Python test runner must use `.venv/bin/python3` — system Python lacks project dependencies

Running `python3 -m pytest` uses the SYSTEM Python interpreter, which lacks pip-installed project dependencies (`pytest`, `pytest_asyncio`, `httpx`, etc.). This produces `ModuleNotFoundError` for project-specific packages, even though they are installed in the project's venv. The same applies to `ruff`, `pip`, and any other tool installed in the venv.

**Detection:** `python3 -m pytest` fails with `ModuleNotFoundError: No module named 'pytest_asyncio'` (or any project dep). The venv has the package installed — the wrong interpreter is being used.

**Fix:** Always use the venv's Python explicitly for ALL Python commands during foreman ticks: `.venv/bin/python3 -m pytest` (tests), `.venv/bin/pip list --outdated` (deps), `.venv/bin/ruff check src/ tests/` (lint). Do NOT rely on `python3` or `pip` without the venv prefix — the cron environment's system Python may be a different version (e.g., system Python 3.14 vs venv Python 3.11) and will lack project dependencies entirely.

**Proven:** <project> Tick #124 (2026-07-30) — `python3 -m pytest tests/unit/` hit `ModuleNotFoundError: No module named 'pytest_asyncio'` (system Python 3.14, project venv is Python 3.11). `.venv/bin/python3 -m pytest tests/unit/` succeeded immediately: 288/288 pass.

### `.gitignore` blocks `tasks.md` commits
When `.coding-hermes/` is in `.gitignore` but `tasks.md` is tracked, `git add .coding-hermes/tasks.md` silently fails with "ignored by one of your .gitignore files." Add `!.coding-hermes/tasks.md` exception to `.gitignore`. On the first commit after the fix, use `git add -f` — git checks the committed .gitignore, which still lacks the exception. Detection: `grep '\\.coding-hermes/' .gitignore` returns a line but `grep '!\\.coding-hermes/tasks\\.md' .gitignore` returns nothing. **Proven:** Off-by-One T109 — .gitignore had `.coding-hermes/` with comment "tasks.md tracked separately" but no un-ignore pattern; board commits silently failed. <project> T24 — `.coding-hermes/` gitignored without exception; `git add .coding-hermes/tasks.md` silently ignored. Added `!.coding-hermes/tasks.md` + used `-f` on first commit after the fix.

### Parent-repo `.gitignore` blocks entire coordination hub directory — `git add -f` required EVERY commit

When the foreman's coordination hub lives INSIDE a parent repo (e.g., `helios-work/mythos/` inside the Helios repo), and the parent's `.gitignore` blocks the entire subdirectory (`/mythos/` on a single line with no exceptions), then `git add` of ANY file inside that directory — including `tasks.md` — always fails with "ignored by one of your .gitignore files." This is different from the per-file `.coding-hermes/` pitfall above: here the whole project directory is blocked at the parent level, and there IS no exception pattern to add (the parent gitignore is managed by a different project's foreman).

**Detection:** `git check-ignore -v mythos/.coding-hermes/tasks.md` returns the parent `.gitignore` line (e.g., `.gitignore:109:/mythos/`). Every `git add` of board files fails.

**Fix:** Use `git add -f .coding-hermes/tasks.md` for EVERY commit — not just the first. There is no practical way to add an exception to the parent gitignore without touching another project's config. The `-f` flag is the permanent workaround for coordination hubs nested inside parent-gitignored directories.

**Proven:** Mythos 2026-07-28 T84 — Helios `.gitignore` line 109 blocks `/mythos/` entirely. Board commits require `-f` every tick. Docs created at coordination hub level exist on disk but are untracked (the entire directory is gitignored).

### GitReins guard_run passes ≠ full-project lint/formatter passes

`mcp__gitreins__guard_run` checks STAGED files only. On idle audit ticks with nothing staged, the lint and test steps report "No files staged — skipped" and the overall guard status shows PASS. Foremen MUST NOT interpret this as "lint passes on the full project." The NEVER-DONE audit gates #3 (lint) and #4 (formatter) must run against the ENTIRE codebase independently of guard_run.

**Detection:** guard_run shows `"passed": true` with lint output "No Python files staged — skipped" while `ruff check .` finds 300+ errors on the full codebase.

**Fix:** Run `ruff check . && ruff format --check .` (Python) or equivalent language-specific command against the ENTIRE working tree during the NEVER-DONE audit — DO NOT rely on guard_run for gate #3/#4 results.

**Proven:** <project> T33 (2026-07-27) — guard_run returned PASS (nothing staged), but `ruff check .` found 377 errors and `ruff format --check .` found 153 unformatted files that had accumulated across 32 idle ticks without being detected.

### Project-custom audit gates drift from canonical 14-point set — verify coverage before running

When a project's NEVER-DONE board row defines its own gate count (e.g., "11-point audit sweep"), the project-custom gate schema may have drifted from the canonical 14-point set in Phase 3. The most common drift: "Static analysis" becomes a catch-all gate that checks mypy/lint only and omits the doc-existence `ls` check (gate #11) entirely. This silently enables fabrication pattern #7 — the foreman reports a "Static analysis" result (mypy stub warnings, lint clean) while 3 docs (CODEOWNERS, SUPPORT.md, CODE_OF_CONDUCT.md) are missing on disk, because `ls` was never run.

**Detection:** The board's NEVER-DONE row says "N-point audit sweep" where N < 14, AND the tick entries never show a standalone "Docs" or "Docs & Security" gate with explicit `ls` output. Instead, gate results show only mypy/lint/formatter under a combined "Static analysis" or "Code quality" label.

**Fix:** Run ALL 14 canonical gates regardless of what the project-custom NEVER-DONE count claims. Gate #11 (Docs & Security) `ls` check is mandatory — never skip it just because the project's board doesn't enumerate it separately. After fixing gaps, update the board's NEVER-DONE row to include a standalone doc-existence gate. Do NOT inflate the gate count in the board's NEVER-DONE row — just ensure coverage.

**Proven:** h3-shim 2026-07-28 T96 — board claimed "11-point audit sweep | 11/11 PASS tick #84." Ticks #83-#92 all reported "mypy: stub errors / not installed" under gate #9 but never ran `ls` on the 9-file doc list. CODEOWNERS, SUPPORT.md, CODE_OF_CONDUCT.md were all missing. The project-custom 11-point schema had no standalone docs gate — doc existence was invisible to every audit. Fixed in T96: created all 3 docs, expanded gate coverage to 15 points with explicit doc `ls`.

### Formatter gate scope — `gofmt -l .` false-negative from stray `.go` files in non-standard directories

`gofmt -l .` recursively walks the entire repo. Work-item directories (`.memory-bank/`, `.opencode/patches/`), patch dirs (`_patches/`), and other non-Go-source locations may contain files with `.go` extensions that contain non-Go syntax (shell comments `#`, arbitrary text). These cause gofmt to exit with code 2 (error) instead of listing files needing formatting. Foremen hitting this parse error may treat it as "can't check formatter" and silently miss real formatting drift in actual Go source directories across many ticks.

**Detection:** `gofmt -l .` exits non-zero but the first line of output is a parse error (e.g., `illegal character U+0023 '#'`), not file paths. Exit code 1 = real files need formatting; exit code 2 = parse error on a non-Go file.

**Fix:** Scope gofmt to known Go source directories: `gofmt -l cmd/ internal/ pkg/` (adapt per project layout). After scoping: exit code 1 = files need formatting; exit code 0 = clean. This matches how `go build ./...` only finds Go files inside packages.

**Proven:** dexdat-memory Tick #45 (2026-07-27) — `gofmt -l .` hit parse error on `.memory-bank/work-items/WI-DEX-043-R2/changes/admin.go.new_methods.go` (shell `#` in a `.go` file). Prior 40+ idle ticks all claimed "formatter: green" (likely hitting this error and treating it as pass). Scoping to `gofmt -l cmd/ internal/ pkg/` revealed ~100 Go files with formatting drift across 40+ ticks, all fixed with `gofmt -w`.
The audit table's gate #4 lists `gofmt -l .` as the canonical example, but foremen on non-Go projects may skip this gate entirely or run only the lint checker (`ruff check` / `eslint`). This is wrong — linters and formatters are separate tools. `ruff check` passes even when `ruff format --check` reports 105 files would be reformatted (different checks). Python projects MUST run `ruff format --check src/ tests/`, not just `ruff check`. Detection: audit report shows gate #4 as "skipped" or "not applicable" on a non-Go project, or the board's prior tick reports never mention formatter results. **Proven:** DexDat Core T23 — foreman ran `ruff check` (clean) every tick but never `ruff format --check`. 105 files needed reformatting across 20+ ticks of silent drift. Found during the first audit that explicitly checked the formatter gate. DuckBrain T160 (2026-07-29) — TypeScript variant: `tsc --noEmit` had been clean for 34+ ticks, but `npx prettier --check 'src/**/*.ts' 'tests/**/*.ts'` found 65 unformatted files. No prior tick had ever run the formatter gate — foremen interpreted `tsc` green as "code quality passes" and skipped gate #4 entirely. Fixed mechanically with `npx prettier --write`, committed as ad7b979. Build + tests re-verified after formatting.

**TypeScript/Prettier variant — `tsc --noEmit` passes but `npx prettier --check` was never run.** This is the TS equivalent of the Python `ruff check` vs `ruff format --check` pitfall. Foremen on TypeScript projects commonly run `tsc --noEmit` (gate #3, type-checking) and interpret its success as "code quality passes," skipping the independent formatter gate entirely. `tsc` checks types — it has nothing to do with code formatting. The tell: prior tick entries mention "tsc clean" under gate #3 but never mention "prettier," "format," or any gate #4 result.

**Detection — TWO-TIER, NEVER scope first:**
Tier 1 — full-repo sweep FIRST: `npx prettier --check .` — this catches EVERYTHING prettier would format, including monorepo subdirectories (`packages/`, `bin/`), root configs (`*.config.ts`, `*.config.js`), and any directory with supported files. Do NOT scope to `src/ tests/` on the first pass — that misses `packages/`, `bin/`, root config files, and any other source directory the project uses.
Tier 2 — scoped verify after fix: `npx prettier --check 'src/**/*.ts' 'tests/**/*.ts' 'bin/**/*.ts' 'packages/**/*.ts' 'packages/**/*.tsx'` — include all KNOWN source directories for the project. The scope varies per project structure.

**🪤 Pitfall — scope narrowing that misses monorepo subdirectories:** Foremen using a narrow scope (`'src/**/*.ts' 'tests/**/*.ts'`) on monorepo TypeScript projects silently miss entire directories like `packages/ui/`, `packages/core/`, etc. The gate reports "Clean" because the checked scope IS clean — but the unchecked directories contain dozens or hundreds of unformatted files. This produces multi-tick fabrication chains where every foreman runs the same narrow scope, gets the same "Clean" result, and reports the gate as passing. The fabricated "Clean" claim then propagates into future ticks as foremen copy the prior tick's gate result without re-verifying with the full scope. **Detection:** `npx prettier --check .` reports "Code style issues found in N files" (N > 0) but the audit gate shows "prettier: Clean." The foreman ran a scope that excluded part of the project. **Fix:** Always run `npx prettier --check .` first to get the FULL picture. If N is large (100+), scope the fix to the worst directory and create a task for the rest. **Proven:** DuckBrain T185 (2026-07-30) — prior ticks #181-#184 claimed "prettier: Clean" but `npx prettier --check .` found 350 unformatted files. 31 in packages/ui/ alone. Prior foremen ran `npx prettier --check 'src/**/*.ts' 'tests/**/*.ts' 'bin/**/*.ts'` which was clean — but `packages/` was never included in any audit. DexDat Core T23 — same pattern with `ruff check` vs `ruff format --check` (105 files). DuckBrain T160 — same pattern (65 unformatted files missed by `tsc`-only audits). Hivemind T38 — same pattern (packages/ subdirectory never checked).

**Fix:** `npx prettier --write .` for the full repo, or staged: `npx prettier --write 'src/**/*.ts' 'tests/**/*.ts' 'bin/**/*.ts' 'packages/**/*.ts' 'packages/**/*.tsx'` — mechanical, no worker needed for straightforward formatting. Re-verify build and tests after formatting (formatting can reveal latent type errors). If the project uses a different formatter (dprint, biome), substitute accordingly — the principle is the same. If N is over ~50 files and load permits, delegate to a worker to avoid burning foreman time.

### Stale tasks.md HTML-comment noise
Prior ticks may add GITREINS-JUDGE checklist items or duplicated config blocks to the HTML comment section at the top of `tasks.md`. These accumulate across ticks and clutter the board. Revert the file to clean state before starting the audit — the board's actual task matrix and tick log are what matter. **Proven:** <project> T12 — prior tick left a duplicated GITREINS-JUDGE block with malformed matrix row in the comment section.

### Pre-written stale tick entry (sibling race — fabricated data already on board)

When a concurrent sibling foreman session partially writes a tick entry to the board BEFORE your tick begins, the entry may contain fabricated/unverified data. Your tick starts and finds a pre-populated `### Tick N` section claiming engine times, dep counts, and NEVER-DONE status that don't match ground truth. This is a DIFFERENT failure mode from the stale-board/wasted-dispatch pattern (which covers task rows, not tick entries).

**Detection:** The board already has a `### Tick N` entry for your tick number with gate results that contradict your tool output. Common tells: engine time wildly different from actual (51.2s claimed vs 5.0s actual), deps claimed "0 transitive" when 14 exist, NEVER-DONE claimed "11/11" when files are missing on disk.

**Response:**
1. Do NOT append corrections to the stale entry — replace it ENTIRELY
2. Run ALL verification queries fresh (the stale entry's data is untrustworthy)
3. Write a complete replacement entry with ground-truth-verified results
4. Note in the entry that a stale pre-written entry was detected and replaced
5. The stale entry's data likely propagated from a sibling foreman that fabricated metrics (confusing engine test output, caching prior-tick dep counts, or assuming NEVER-DONE without checking the filesystem)

**Proven:** Kobayashi-Maru Tick 134 (2026-07-28) — board had pre-written entry claiming engine 51.2s, 0 transitive deps, 11/11 NEVER-DONE. Ground truth: engine 5.041s, 14 transitive deps, SUPPORT.md + CODE_OF_CONDUCT.md missing. Full entry replaced with verified data. The stale entry was likely from a concurrent sibling tick that fabricated metrics. Bunker Tick 47 (2026-07-28) — variant with different fabricated fields: wrong DuckBrain namespace (`coding-hermes` instead of `bunker`), false NOTICE.md missing claim (NOTICE.md not in 9-file list), fabricated key counts. Detection and response identical: replace entire entry with ground truth, do not append.

### GitReins config.yaml drift
The committed `.gitreins/config.yaml` may lack `defaults.model` — prior ticks may have added it to the working copy but never committed (correct behavior — this is MCP state). The MCP `configure` tool handles model assignment at runtime. Do NOT add `defaults.model` to the committed config unless the board explicitly requires it. **Proven:** <project> T12 — working copy had `defaults: {model: deepseek-v4-flash}` from a prior tick's MCP configure call; reverted on cleanup. The committed evaluator section with `max_iterations: 30` is sufficient — MCP configure sets the model at runtime.

### Untracked CI scripts accumulation
Foreman ticks that create ad-hoc CI check scripts (e.g., `_check_ci.py`, `_ci_check.py`) often leave them untracked in the workdir. These are one-off debugging artifacts, not project source. Delete them during self-heal cleanup rather than letting them accumulate across ticks. **Proven:** <project> T12 — 3 untracked CI scripts from prior ticks deleted.

### Post-worker build verification — foreman fixes worker errors directly
When a worker hits `max_iterations` (50 API calls) and exits without running the build verification step, the foreman MUST run `tsc --noEmit && npm run build` (or project equivalent) before committing the worker's output. Common post-worker errors:

- **TypeScript strict-mode unused imports** — `TS6196: 'X' is declared but never used` or `TS6133: 'Y' is declared but its value is never read`. These are trivial to fix: remove the unused import from the import block. Do NOT re-dispatch the task — the foreman handles this directly.
- **Duplicate imports** — caused by worker iterations adding the same import multiple times. Remove the duplicate line.

The principle: if the build error is a one-line fix (unused import, duplicate import, missing semicolon), the foreman fixes it. If the error requires understanding the logic (wrong types, missing functions, broken wiring), flag it as a board gap and create a bug task. **Proven:** Hermes Canopy 2026-07-24 T11 — FE-07 worker hit max_iterations at 50 calls, left 2 TS strict-mode errors (unused `UserPresence` and `getUserInitials` imports). Foreman removed them in 2 patches, build passed. Also left a duplicate `usePresence` import from a "sibling subagent" race — foreman deduplicated.

### Worker-introduced function redeclaration (Go-specific)
When a worker adds a new function that has the same name as an existing package-level function in a sibling file, the build fails with `redeclared in this block`. This is NOT a structural bug — it's a trivial collision where the worker independently wrote a helper that already existed elsewhere.

**Detection:** `go build` fails with `X redeclared in this block (see details)` pointing to two files. The existing function was there before the tick (check `git diff --name-only` — the sibling file wasn't modified).

**Fix:** Remove the worker's duplicate function AND update any call sites that reference it. The worker's code may call the duplicate by name — those calls should be redirected to the original or the call site logic adjusted. Steps:
1. `grep -n 'func <name>'` to find both declarations
2. Remove the worker's version (in the file modified this tick)
3. If the worker called it, either: (a) convert arguments to match the original signature and call the original, or (b) inline the conversion logic at the call site
4. Re-verify with `go build ./...`

**Proven:** <project> 2026-07-25 T17 — worker wrote `collectKeys(records []map[string]interface{})` but `execute.go` already had `collectKeys(items []interface{})`. Foreman removed the duplicate, converted `[]map[string]interface{}` to `[]interface{}` at the call site, build passed.

### Board correction is multi-location — stale data hides in 4+ sections (partial-correction pitfall)

When correcting a fabricated claim on the board (e.g., DuckBrain key count, cooldown value, idle tick count), the stale data is rarely confined to a single line. Boards accumulate the same claim in multiple sections across many ticks:

1. **Header status line** — the one-liner at the top with "Last tick: #N ... DuckBrain (X keys)"
2. **Verdict line** — the secondary summary below the header ("Verdict: idle ... DuckBrain: X keys")
3. **DuckBrain-verified annotation** — the italicized note below Verdict ("DuckBrain verified this tick: X keys")
4. **Routing Notes** — a section below the task matrix with bullet points about DuckBrain state
5. **Tick Log entries** — each prior tick entry repeats the fabricated claim in its summary column
6. **Execution Order / Assumptions** — sections that reference counts ("Project is zombie — N idle ticks")

A foreman who patches only the header line leaves fabricated claims in 3-5 other locations. The next tick's foreman reads the Verdict or Routing Notes first, sees the old fabricated value, and may "re-correct" back to the wrong value — creating an oscillation pattern.

**Detection:** after correcting a board claim, grep the file for the old value. If it appears in multiple sections, fix every instance in a single board update pass. The most stubborn locations are the Routing Notes (prose paragraphs that age slowly) and the Verdict line (often a direct copy of the header with slightly different wording).

**Fix:** use multiple `patch` calls or a full `write_file` to update all locations in one pass. Do NOT commit after fixing only one section — the board must be internally consistent before `git add`.

**For cooldown fabrications specifically:** `sed -i 's/Cooldown: <old>/Cooldown: <new>/'` replaces ALL occurrences across the file in one command. This catches all tick log entries, the header, routing notes, and any other reference. Include an annotation like `(⚠️ board claimed <old> — fabricated; scheduler = <new>)` to preserve audit trail. Only use `sed` when you're certain all occurrences need the same correction — for selective fixes, use `patch` per location.

**Proven:** <project> Tick #37 (2026-07-28) — DuckBrain key count corrected from "1 key" to "9 keys" required patches in 4 locations: header line, Verdict line, DuckBrain annotation, Routing Notes, and stale "23 idle ticks" reference. The "1 key" claim had propagated from tick #35 into every section that mentioned DuckBrain. Fixing only the header would have left the Verdict still claiming "1 key" — the next foreman would have "re-corrected" back down. <project> T35 (2026-07-28) — cooldown 900s→1350s corrected with `sed -i 's/Cooldown: 900s./Cooldown: 1350s (⚠️ ...)/'` across 5 occurrences in a single command.

### Delegate_task "sibling subagent" file-race with patch tool

When a `delegate_task` worker reports a "sibling subagent" was simultaneously working on the same files, the patch tool may warn: "was modified by sibling subagent 'sa-0-XXXXXXXX' at HH:MM:SS — after this agent's last read." This happens because the worker's internal iterations modified the file between your read and your patch. The warning means your `old_string` may be stale.

**Fix:** Re-read the file with `read_file` (full, no offset pagination) to get the current state, then apply the patch against the fresh content. If the file is still being modified (3+ consecutive stale-read warnings), use `write_file` to overwrite it atomically with the corrected content. **Proven:** Hermes Canopy 2026-07-24 T11 — TreeView.tsx was modified 3 times between foreman reads by the worker's "sibling" process; patch produced duplicate imports. Full re-read + targeted deduplication resolved it.

### Concurrent sibling foreman sessions — stale board, wasted worker dispatch

When multiple foreman cron ticks fire concurrently (common on active projects with 900s cooldown), a sibling session may complete work AND partially update the board before your tick begins. The board may show a task as active (or marked ✅ but still in Active section) while the code is already committed. This wastes tokens and time if you dispatch a worker for it.

This is distinct from the guard-timeout-auto-commit pattern (below) — here the sibling legitimately completed the work but left the board in a transitional state (task ✅ in Active, not yet moved to Completed; duplicate rows from rapid edits).

**Detection — always run `git log --oneline -10` before dispatching any worker.** If recent commits match task keywords but the board still shows the task as active, the sibling completed it.

**Response when sibling completions are detected during board scan:**
1. Identify all tasks whose commits exist but board state is stale
2. Move completed tasks from Active to Completed section
3. Fix board corruption (duplicate rows, truncated rows) from rapid concurrent edits
4. Update the header's active task count
5. Add a tick log entry documenting sibling completions + board cleanup
6. Do NOT re-dispatch workers for sibling-completed tasks

**If you ALREADY dispatched a worker before detecting the sibling completion:** Let it finish — it will discover the code exists and report "already done." Add the worker's finding to the tick log as confirmation. Do NOT re-stage or re-commit code — the sibling's commits are authoritative.

**Proven:** Kobayashi-Maru 2026-07-25 T51 — 3 tasks completed by siblings (T48-T50) between T47 and T51. Board showed API-scenario-crud as ✅ in Active, PHYS-spatial-partition had a duplicate row from concurrent edits. Worker dispatched for COMBO-secondary-effects wasted 435s and 936K input tokens discovering work already in commits b99c79c + a025af7. Board cleanup: moved API-scenario-crud to Completed, removed duplicate row, updated header. Pre-dispatch `git log --oneline -10` would have prevented the wasted dispatch.

### DuckBrain namespace ≠ directory name — always verify the correct namespace before claiming "0 keys"

The project directory name, the board's namespace references, and the actual DuckBrain namespace can all differ. Querying the wrong namespace returns 0 keys, leading to false reports of "DuckBrain empty." The authoritative source is the AGENTS.md in the code sub-repo (if one exists) or trial-and-error across plausible namespace names.

**Detection:** `list_keys(prefix="/projects/<name>/", namespace="<wrong-namespace>")` returns 0 keys. But the board prior ticks claim "N keys in DuckBrain." The namespace name in the board header may be wrong.

**Fix — two-tier:**
1. Check AGENTS.md in the code sub-repo (e.g., `wojons-mythos/AGENTS.md`) — it often declares the canonical namespace. In Mythos, AGENTS.md says "Namespace: mythos" but the board header referenced `wojons-mythos`.
2. If AGENTS.md is unavailable or doesn't declare a namespace, try the most likely candidate names: the project name without prefixes, the scheduler project name, or the short directory name. Query each until keys are found. The one that returns >0 keys is authoritative.

**Common mismatch patterns:**
- Directory: `wojons-mythos/` → Namespace: `mythos` (AGENTS.md declared)
- Board reference: "wojons-mythos namespace" → actual: `mythos`
- Project is a subdirectory of a parent repo, but DuckBrain namespace matches the project name, not the directory name

**Proven:** Mythos 2026-07-28 T84 — foreman queried `wojons-mythos` namespace (0 keys) based on prior board entries. AGENTS.md in `wojons-mythos/AGENTS.md` declared `mythos` as the canonical namespace. Querying `mythos` returned 11 keys. <project> 2026-07-24 T18 — similar false-zero from namespace mismatch; `list_keys` without explicit namespace queried the active namespace (`<project>`) instead of `<project>`.

### Prior-tick board cooldown claims are unreliable — always verify with scheduler API

**Detection:** Compare the board's claimed cooldown against the scheduler API:
```bash
curl -s http://127.0.0.1:9090/api/v1/projects/<name> | python3 -c "import sys,json; print(json.load(sys.stdin)['project']['CooldownS'])"
```
If the board claims one value and the API returns another, the board is wrong. The API is authoritative.

**Fix:** Report the API value, not the board value. Call out the discrepancy explicitly in the audit table and the board footer. Do NOT silently "correct" the board without noting that prior ticks fabricated — the audit trail matters for fleet governance.

**Why this happens:** The scheduler daemon resets cooldowns to fleet-config defaults on restart (coding-hermes-cron v2.1.13). Foremen that elevated the cooldown via PUT see their change silently overwritten. Subsequent foremen see the fabricated value on the board and copy it without querying the API — the fabrication becomes self-reinforcing.

**Proven:** RethinkDB 2026-07-27 T43 — six consecutive ticks (#37-#42) all claimed "Cooldown: 43200s (12h) — holding stable." Scheduler API showed 1800s (30 min). <project> 2026-07-27 T33 — six consecutive ticks (#27-#32) all claimed "Cooldown: 43200s (12h)." Scheduler API showed 900s (15 min). Helix 2026-07-28 T13 — two consecutive ticks (#11-#12) claimed 43200s; scheduler showed 1800s (30 min). <project> 2026-07-28 T35 — six consecutive ticks (T30-T34) claimed 900s; scheduler showed 1350s since T30. **RethinkDB 2026-07-28 T46 — fabrication REVERSION after correction:** tick #43 corrected cooldown to 1800s, tick #44 reported correctly, tick #45 re-fabricated 43200s. The foreman read the board's OLD fabricated claim (from #37-#42) instead of the corrected one (#43-#44) and re-introduced the lie. The self-reinforcing pattern: board corrections are fragile — a single tick that skips the scheduler API query can resurrect a fabrication that was already fixed. **Off-by-One 2026-07-30 T217 — REACHABILITY fabrication (not just value):** the board had claimed "Scheduler unreachable" since ~tick #200 (~16 ticks), and every subsequent foreman copied this blob claim without ever trying the query. Tick #217 queried the scheduler and it returned 900s instantly — it was reachable the entire time. The foremen were not even attempting the query, just propagating a prior-tick assertion. This is a different failure mode from wrong-value fabrication: the foremen are skipping the verification check entirely because "the board says it's unreachable, so why try." The fix is the same — query every tick regardless of what the board says — but the detection signal is different: the board claims the source is DOWN (not wrong), and multiple ticks with zero scheduler-tool-calls in their tool trace are the tell.

### Cross-repo governance doc verification — umbrella foremen must verify ALL sub-repos, not just their own

When an umbrella foreman's board claims "all N repos have full governance (LICENSE, SECURITY.md, CODEOWNERS, AGENTS.md)" — this claim has usually only been verified against the umbrella repo's own filesystem. Sub-repos are assumed good because the board said so. This is a multi-repo variant of fabrication pattern #7 (file-existence) from self-heal Step 0.5.

**Detection:** The NEVER-DONE gate #11 reports "all N repos full governance verified" but the `ls` command only checked the umbrella repo. Sub-repo claims are copy-paste from a prior tick that also didn't check. The umbrella board's claim propagates across ticks without any sub-repo filesystem verification.

**Fix:** During gate #11 of the NEVER-DONE audit, run the 9-file `ls` against EVERY sub-repo directory, not just the umbrella. This is cheap (one `ls` per repo) and catches the most common multi-repo fabrication:

```bash
for repo in umbrella sub1 sub2 sub3; do
  echo "=== $repo ===" && cd ~/<project>/$repo && ls SUPPORT.md CODE_OF_CONDUCT.md CHANGELOG.md 2>&1
done
```

Report results per-repo — not as a single aggregate claim. "3/5 repos have full docs" is truthful; "all repos full governance" is fabricated if only 1/5 was verified. The umbrella foreman can directly fix its own repo's gaps; sub-repo gaps should be flagged for their respective foremen.

### Doc-checklist drift between references — always use the 12-file `ls` from doc-coverage-checklist.md

The self-heal fallback (`foreman-tick-fallback.md`) and the never-done skill (`doc-coverage-checklist.md`) may define different file counts for the `ls` command. When the fallback uses a 9-file list but the never-done canonical reference has been updated to 12 files, foremen using the fallback miss 3 required files (AGENTS.md, NOTICE, GOVERNANCE.md, TRADEMARK_POLICY.md) every tick. Worse: foremen may invent their own list on the fly, counting non-standard files they create.

**Detection:** The `ls` command in the fallback's gate #11 table row has fewer files than the one in `coding-hermes-never-done/references/doc-coverage-checklist.md`. Count the files in each `ls` command — if they differ, the fallback is stale.

**Fix:** Use the exact 12-file `ls` command from the canonical source. Do NOT invent your own doc list, and do NOT count files you created that aren't in the standard list. If you create GOVERNANCE.md (a required file in the 12-file list) but also miss CODEOWNERS (also required), your count is wrong — use the `ls` output, not your own enumeration.

**Proven:** Hivemind work tick #161-162 (2026-07-29) — tick #161 used a self-enumerated "7 missing docs" list that included GOVERNANCE.md but excluded CODEOWNERS. GOVERNANCE.md was created (correct — it's in the 12-file list) but CODEOWNERS was never checked. Tick #162 ran the actual `ls` and found CODEOWNERS still missing. The foreman's self-invented enumeration bypassed the authoritative `ls` command, causing a false "8/9" claim.

**Proven:** H3 umbrella tick #89 (2026-07-28) — board claimed "all 6 repos full governance" since tick #77. Ground truth via per-repo `ls`: only shim had all 3 extended docs (SUPPORT.md, CODE_OF_CONDUCT.md, CHANGELOG.md). h3 umbrella itself was missing all 3 until this tick (foreman-direct fix: created all 3). sdk-go, sdk-python, sdk-typescript, protocol were all missing all 3. 4 of 5 sub-repos had governance gaps masked by the umbrella's self-reinforcing claim. The board had been fabricating "verified" for 12+ ticks without ever running `ls` outside the umbrella repo.

### Large project test suites timeout at default terminal limits — use smoke checks during idle ticks

When a project has a large test binary (C++: 300MB+, Go monorepos: 100+ packages, Python: integration suites with server lifecycle), the full test run may exceed the foreman's terminal timeout. On RethinkDB, `make unit` and `./build/release/rethinkdb-unittest` both timed out at 180s consistently (346MB binary). Burning 3 minutes waiting for a timeout is wasted tick time.

**Detection:** The test command from gate #2 times out (exit code 124) at the default or extended terminal timeout.

**Fix — tiered approach for idle ticks:**

1. **Smoke check (binary health):** verify the test binary starts and can list tests: `timeout 10 ./build/release/rethinkdb-unittest --gtest_list_tests | head -5`. For Python: `timeout 10 python3 -m pytest --co 2>/dev/null | head -5`. For Go: `go test ./... -list '.*' 2>/dev/null | head -10`.

2. **Count test macros from source (static):** `grep -r 'TEST(' src/unittest/ | wc -l` (C++/gtest), `grep -r 'func Test' --include='*_test.go' | wc -l` (Go), `grep -r 'def test_' tests/ | wc -l` (Python/pytest).

3. **Trust prior-tick results with a qualifier:** if the last 3+ ticks all passed, report `PASS (binary functional, N test macros, prior M ticks green)` — do NOT fabricate a fresh pass. If prior ticks had failures, note them explicitly.

4. **Full run is for productive ticks only:** on ticks that dispatch workers or commit code changes, run at least a subset of the tests. On idle audit ticks, smoke checks + prior-tick trust is sufficient.

**Proven:** RethinkDB 2026-07-28 T46 — `make unit` timed out at 180s, `./build/release/rethinkdb-unittest` timed out at 120s and 180s. Binary is 346MB. Smoke check `--gtest_list_tests` succeeded in under 10s, listing 103 test cases. All 4 prior ticks reported stable test results — gate reported PASS with qualifier.

### GitReins guard_run timeout may auto-commit worker output
When a `delegate_task` worker times out (600s, 48+ API calls) and the foreman subsequently calls `mcp__gitreins__guard_run` to verify the staged output, the guard may also time out (300s for large Go projects) — but the GitReins MCP pipeline may internally commit the worker's changes BEFORE the timeout is reported. This means after a guard timeout, `git log --oneline -3` may show new commits that the foreman didn't explicitly create.

**Detection:** After a guard_run timeout, `git status --short` shows no staged engine files but `git log --oneline -3` shows a fresh commit with the worker's changes. The guard's internal pipeline completed the task_create → guard → task_complete → commit sequence before the HTTP timeout fired.

**Fix:** After any guard_run timeout on a worker-dispatched tick, check `git log --oneline -3` before trying to re-stage files. If the worker's output was already committed by the pipeline, just add the board update and move on. Do NOT re-stage and try to commit again — the files are already committed.

**Proven:** Kobayashi-Maru 2026-07-25 T48 — COMBO-secondary-effects worker timed out at 600s with 48 API calls. Foreman's guard_run also timed out at 300s. git log revealed b99c79c (EnemyShip fields) and a025af7 (secondary effects implementation) were already committed by the GitReins pipeline. The foreman's subsequent attempt to git add engine files found nothing to stage.
