# Multi-Repo Spec-Hub Foreman — Phase 0 Scaffold Pattern

When the foreman's project is a **spec hub** that coordinates multiple implementation repos (not a single code-producing repo), Phase 0 scaffolding follows a different template. The foreman is not the implementer — it's the coordinator.

## When to Use

- The project is a collection of repos (e.g., `get-h3` with `h3`, `protocol`, `shim`, `sdk-go`, `sdk-python`, `sdk-typescript`)
- The foreman's workdir is the spec hub (the central repo with `specs/`, `.coding-hermes/tasks.md`, `AGENTS.md`)
- Implementation repos have their own foremen
- Phase 0 is about making the hub pushable, not writing production code

## Phase 0 Deliverables (Spec Hub)

| Deliverable | Purpose | Example |
|---|---|---|
| `go.mod` | Integration test module (cross-repo tests live in the hub) | `module github.com/get-h3/h3` |
| `Makefile` | Common ops: `lint`, `test`, `guard`, `clean`, `setup` | Targets for Python venv, pytest, ruff |
| `pyproject.toml` | Python tooling if any integration tests are Python | pytest + ruff dev deps, setuptools build |
| `.gitignore` | Exclude venv, cache, build artifacts | `.venv/`, `__pycache__/`, `.pytest_cache/` |
| `.gitreins/config.yaml` | Secrets guard at minimum; enable build/lint/tests when code exists | `guards.secrets: {enabled: true, severity: block}` |
| `AGENTS.md` | Repo collection map, architecture, key decisions, development guide | Full org map with all 6 repos |
| DuckBrain `/spec/<project>/*` seeds | Distilled spec content for worker context | One entry per spec file, comprehensive embedding_text |
| DuckBrain `/project/<name>/status` | Project state snapshot | Phase, tasks completed, gate status |

## Verification Pattern (Differs from Code Foremen)

Since Phase 0 has no production code, verification is **file existence + content quality**, not build/test:

1. **File existence**: `ls go.mod Makefile pyproject.toml .gitignore .gitreins/config.yaml AGENTS.md`
2. **GitReins guard**: `timeout 120 gitreins guard` — will show `go_build PASS`, `go_lint PASS`, `go_tests PASS (no test files)` — this is CORRECT for a spec hub with no Go test files
3. **AGENTS.md quality**: Must have org map with all repos, architecture section, key decisions, development section
4. **DuckBrain seeds**: `duckbrain_list_keys(prefix="/spec/<project>/")` — one entry per spec file
5. **Board update**: All Phase 0 tasks marked `[x]`

## Board Pre-Existing Detection

Phase 0 tasks (GitReins config, AGENTS.md) may be marked "pending" on the board but already exist on disk. Before spawning a worker for ANY Phase 0 task, check:

```bash
ls .gitreins/config.yaml AGENTS.md specs/ 2>/dev/null
```

If they exist and are substantive (not stubs), verify quality and mark `[x]` — do NOT spawn a worker or re-create them. The board is documentation, not truth.

## Gate Check

The Phase 0 gate is: `gitreins guard` PASS, repo is pushable. On a spec hub with a `go.mod` but no Go source files, the guard will show all Go checks as PASS (the module compiles trivially). This is expected and does NOT indicate tests are passing — it means there are no test files to fail.

## After Phase 0

The next tick should:
1. Clone/create implementation repos (the foreman's `cd` targets for worker spawns)
2. Configure foreman crons for each implementation repo
3. Phase 1 tasks can then run in parallel across repos

The spec hub foreman continues to coordinate — it updates the cross-repo board, writes DuckBrain findings, and runs integration tests. It never writes production code for implementation repos.

## Proven

H3 (2026-07-12): Phase 0 scaffold complete in one tick. go.mod, Makefile, pyproject.toml, .gitignore created. Pre-existing GitReins config and AGENTS.md verified (no re-creation). 6 DuckBrain seeds + status entry written. Guard PASS. Board fully `[x]`. Implementation repos not yet created — Phase 1 blocked on repo initialization.
