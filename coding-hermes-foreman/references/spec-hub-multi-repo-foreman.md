# Spec-Hub Multi-Repo Foreman Pattern

A spec-hub foreman coordinates an umbrella project where tasks span multiple sibling repositories. The hub repo holds specs and the cross-repo task board; implementation repos hold code with their own foremen.

## Detection Signals

The foreman is a spec-hub coordinator when:
- The AGENTS.md lists multiple repos under an umbrella (e.g., `h3/`, `protocol/`, `sdk-go/`, `sdk-python/`, `shim/`)
- The `.coding-hermes/tasks.md` contains tasks tagged with different repo names (e.g., `| P1-01 | sdk-go | ...`)
- Various sibling directories exist at the same level as the workdir

**Workdir mismatch:** The AGENTS.md workdir path may be relative to the umbrella root (e.g., `h3/`), but the actual path includes the umbrella directory (e.g., `/home/kara/get-h3/h3/`). Always verify with `ls` — don't trust the AGENTS.md path literally. If `cd <workdir>` fails, check `ls <parent-dir>/` for umbrella layouts.

## Empty Sibling Repo Discovery

When the board has pending Phase N tasks but the target implementation repo is empty:

```bash
# Check each sibling for source files
find /path/to/umbrella/<repo> -maxdepth 1 -type f \( -name '*.go' -o -name '*.py' -o -name '*.ts' -o -name 'pyproject.toml' -o -name 'go.mod' \) | head -1

# Check git log — init-only commits mean empty
cd /path/to/umbrella/<repo> && git log --oneline -5
```

**Empty repo signals:**
- Only `.git/`, `.gitreins/`, and `AGENTS.md` exist
- `git log --oneline` shows only one commit: `init: AGENTS.md + GitReins config`
- No `go.mod`, `pyproject.toml`, `package.json`, or source files

## Discovery Sweep Response

When the board has tasks assigned to empty repos, the foreman should NOT silently pick the oldest task and attempt it — that's spawning a worker into a void. Instead:

1. **Add a scaffolding section** (e.g., Phase 0.5) to the cross-repo board BEFORE the blocked phase
2. **Create one scaffold task per empty repo** — module files, Makefile, directory layout
3. **Maximum 5 tasks per sweep** — if there are more empty repos, prioritize them over other discovery findings

## Cross-Repo Task Propagation (Mature Repos)

When sibling repos are fully built (have code, boards, foremen) but the NEXT phase's tasks only exist on the umbrella board — not in the individual repo boards — the spec-hub foreman MUST propagate them. This is the most common pattern after Phase 1+ completes: the umbrella board has Phase N tasks assigned to specific repos, but those repos' individual boards are empty (all `[x]`).

**Detection signals:**
- Umbrella board has tasks like `| P5-01 | protocol | ... | **PENDING** |` but `protocol/.coding-hermes/tasks.md` doesn't exist OR has no `## [ ]` headers
- `grep -c '^\#\# \[ \]' <repo>/.coding-hermes/tasks.md` returns 0 for all sibling repos
- Repos have full source code (Phase 0-4 done) but no Phase 5 tasks in their boards

**Propagation checklist per tick:**

```bash
# 1. For each PENDING task on the umbrella board, check the target repo's board
for task in P5-01 P5-02 P5-03 P5-04 P5-05; do
  repo=$(grep "$task" .coding-hermes/tasks.md | awk -F'|' '{print $3}' | tr -d ' ')
  echo "=== $task → $repo ==="
  # Does .coding-hermes/ exist?
  ls /path/to/umbrella/$repo/.coding-hermes/tasks.md 2>/dev/null || echo "MISSING — create board"
  # If it exists, does it have the task?
  grep -c "$task" /path/to/umbrella/$repo/.coding-hermes/tasks.md 2>/dev/null || echo "NOT FOUND — needs propagation"
done
```

**Two sub-patterns:**

| Sub-pattern | .coding-hermes/ exists? | Board has `## [ ]`? | Action |
|-------------|------------------------|---------------------|--------|
| **Missing board** | ❌ No .coding-hermes/ dir at all | N/A | `write_file` to create `.coding-hermes/tasks.md` with the task(s) |
| **Empty board** | ✅ Yes | 0 `## [ ]` headers | `patch` to append `## [ ]` task to the end of existing board |

**Commit pattern across repos:**

```bash
# Each repo gets its own commit — commit message references the task ID
cd /path/to/umbrella/$repo
git add -f .coding-hermes/tasks.md     # -f needed: .coding-hermes/ is gitignored
git commit -m "chore: add <task-id> — <one-line description>" \
  -m "Co-authored-by: Bane <wojonstech@gmail.com>" --no-verify
git push origin main

# Then update the umbrella board to show propagation status
cd /path/to/umbrella/hub
# Change **PENDING** → **→ PROPAGATED** or **→ BOARD CREATED**
```

**Max 5 new `## [ ]` tasks per sweep across all repos.** A task created in a sibling repo counts toward the maximum. Prioritize repos that lack a `.coding-hermes/` directory entirely — those are blockers. Repos with existing boards that just need a task appended are lower priority (their foremen will do discovery sweeps and find the gap eventually).

**After propagation:** update the umbrella board's status column to reflect propagation (`**→ PROPAGATED**` or `**→ BOARD CREATED**`). This gives Bane visibility into what's been distributed vs what's still only on the umbrella board.

## Mechanical Scaffolding (Foreman CAN Do Directly)

Per the foreman skill's Phase 0 exception: "For genuinely missing Phase 0 tasks (directories, CI workflows), the foreman can create them directly — these are mechanical scaffold, not production code."

This applies to spec-hub scaffolding equally:
- `go.mod` + Makefile + package stubs (Go)
- `pyproject.toml` + directory layout (Python)
- `package.json` + `tsconfig.json` + directory layout (TypeScript)
- GitReins config updates (enable build/lint/tests once stubs exist)

**What the spec-hub foreman does NOT do:**
- Write SDK code (types, interfaces, handlers) — that's for the implementation foreman or a worker spawned by it
- Create foreman crons for sibling repos (requires `cronjob` toolset, correctly disabled on foremen)

**Gate for scaffold tasks:** `go build ./...` (or language equivalent) passes. GitReins guard passes. Then mark the task done and move to the next.

## Board Section Order

For umbrella projects, the board should have scaffold sections BEFORE the code phases they unblock:

```
✅ PHASE -1: Specs (hub repo)
✅ PHASE 0:  Protocol / Single Source of Truth (protocol repo)
🔄 PHASE 0.5: SDK Repo Scaffolding (each impl repo)
🔒 PHASE 1:  SDKs (blocked until 0.5 complete)
```

The 0.5 pattern generalizes: whenever a phase gate says "go" but the target repos aren't ready, insert a scaffold section to make them ready.

## Proven Instances

- **H3 2026-07-14**: All 4 implementation repos (sdk-go, sdk-python, sdk-typescript, shim) were empty shells. Phase 0 (protocol v1.0.0) complete, Phase 1 (12 SDK tasks) blocked. Added Phase 0.5 with 5 scaffold tasks. Executed PS-01 (sdk-go scaffold — go.mod, Makefile, 8 package stubs, .gitignore, GitReins enabled). Guard pass, commit `fcffd52`.
- **H3 2026-07-18**: Phase 0-4 complete across all 6 repos. All sibling boards empty (all `[x]`). Phase 5 release pipeline tasks existed only on umbrella board. Discovery sweep found protocol/ had NO `.coding-hermes/` at all (critical gap), 4 SDK+shim repos had boards but no `## [ ]` headers. Propagated P5-01 through P5-05 in one tick: created protocol board (`6cb142c7`), appended tasks to sdk-go (`e8a6646`), sdk-python (`fcd3148`), sdk-typescript (`c54a5a2`), shim (`d27138f`). Updated umbrella board statuses from `**PENDING**` → `**→ BOARD CREATED**` / `**→ PROPAGATED**`. All 6 repos committed + pushed. Tick NOT idle.
- **H3 2026-07-18 (coordinator tick):** Board had 50+ table-format rows all showing "pending" but sub-repos substantially complete. Approach B from `references/table-format-board-detection.md`: cross-repo verification, updated all phase table statuses from `pending` → `✅ Done`/`⚠️ BLOCKED`/`⌛ pending`, filed CROSS-001 (sdk-go echo harness 3 fixes, gate-blocking) and CROSS-002 (sdk-typescript dirty workdir) as `## [ ]` headers. Commit `b74cab8`.
