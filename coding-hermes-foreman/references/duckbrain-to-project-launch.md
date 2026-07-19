# DuckBrain Memory → Full Project Launch Pattern

When a project exists as DuckBrain memory entries but has no repo, no specs, and no foreman, this is the launch sequence. Proven on Rabbit-Hole (2026-07-12): 5 DuckBrain entries → 6 axiom specs → scaffold → GitLab → foreman running.

## When to Use

- User mentions a project that's "a DuckBrain namespace"
- A DuckBrain namespace has architecture entries but no corresponding repo on disk
- The user says "time to get building" or "get the foreman launched"
- A new project needs to be bootstrapped from DuckBrain memory

## Launch Sequence

### Phase 0: Extract from DuckBrain

1. Switch to the project's DuckBrain namespace
2. List all keys (usually under `/project/*`)
3. Recall each key's full memory entry
4. Synthesize the architecture: layers, competitors, gap analysis, killer features

### Phase 1: Write Axiom-Level Specs

Use the `axiom-implementation-specs` skill template. Each spec must be implementation-ready — exact Go interfaces, DDL, error paths, edge cases, Mermaid diagrams.

**Spec structure for a layered system (e.g., collect → classify → express):**
- S01: Overview & Architecture — all interfaces, entities, system diagram, monorepo layout, error propagation table
- S02–S0N: One spec per layer with exact implementation details
- S0N+1: CLI & Deployment — all commands, systemd unit, install script
- Last: Task board with SPEC phase marked complete, then phased implementation

**Spec files go in `specs/` directory.** Not DuckBrain entries. DuckBrain holds the prose-level architecture; specs hold the axiom-level detail.

### Phase 2: Scaffold

**For Go projects:**
1. `mkdir -p <project>/specs <project>/.coding-hermes <project>/cmd/<binary> <project>/internal/<layers> <project>/pkg/types`
2. Create `go.mod` with correct module path
3. Create `Makefile` with build/test/lint targets
4. Create `.gitignore`
5. Create `AGENTS.md` with org reference, architecture summary, foreman details

**For TypeScript projects (pnpm monorepo):**
1. `mkdir -p <project>/specs <project>/.coding-hermes <project>/apps/web <project>/apps/api <project>/packages/<sub1> ...`
2. Create root `package.json` with `"private": true` and `workspaces: ["apps/*", "packages/*"]`
3. Create top-level `tsconfig.json` with strict mode, path aliases
4. Create `.gitignore` (node_modules, dist, .turbo, etc.)
5. Create `AGENTS.md` with stack, monorepo layout, data model from DuckBrain entries
6. Create `.coding-hermes/tasks.md` with concrete task IDs grouped by layer (INFRA, PKG, API, WEB, INT — or project-specific categories)
7. Write `specs/architecture.md` — translate DuckBrain entries into 10-section spec: overview, architecture diagram (Mermaid), component interfaces (TypeScript types, not prose), data model, agentic loop, edge cases, mock data strategy, deployment, open questions

**Key difference from Go:** TypeScript projects need `AGENTS.md` + `specs/` + `.coding-hermes/tasks.md` as the three bootstrap files. No `go.mod`/`Makefile` — those come after `pnpm init`. The spec format uses TypeScript interfaces in code blocks, not Go. The task board uses descriptive categories (INFRA, PKG, API, WEB, INT) rather than Go package paths.

### Phase 3: GitLab Setup

For self-hosted GitLab (`gitlab.readydedis.com`):
1. Check SSH works: `ssh -T git@gitlab.readydedis.com`
2. Create group via API: `POST /api/v4/groups` with `{"name":"...","path":"...","visibility":"private"}`
3. Create project under group: `POST /api/v4/projects` with `{"namespace_id":<group>,"name":"...","initialize_with_readme":false}`
4. Add remote: `git remote add origin git@gitlab.readydedis.com:<group>/<project>.git`
5. Push: `git push -u origin main`

**Token warning:** GITLAB_TOKEN in env may trigger security approval on API calls. SSH is the reliable fallback for git operations. API calls for group/project creation need explicit approval — use the token from `~/.hermes/.env`.

### Phase 4: Foreman Launch

```json
{
  "name": "<project>-coding-hermes-foreman",
  "skills": ["coding-hermes-foreman", "coding-hermes-cron", "hilo-usage", "gitreins"],
  "enabled_toolsets": ["terminal","file","web","search","skills","memory"],
  "model": {"model": "deepseek-v4-pro", "provider": "deepseek-foreman"},
  "workdir": "/home/kara/<project>",
  "schedule": "every 30m",
  "deliver": "telegram:-1003310984808:<thread_id>"
}
```

**Prompt must be self-contained** — tell the foreman what the project is, where the specs are, where the task board is, and the DuckBrain namespace.

### Phase 5: Verify First Tick

1. Run first tick immediately: `cronjob(action='run', job_id='<id>')`
2. Check `git log --oneline -5` — foreman should start scaffold tasks
3. Check `last_status: ok` on the cron job
4. Seed DuckBrain `/project/status` with project state

## Anti-Patterns

- **Skip specs, jump to foreman:** A foreman with no specs spawns workers that invent their own interfaces. The `axiom-implementation-specs` skill says it directly: "If an agent can build two different things from the same spec, the spec is wrong." DuckBrain entries are prose — they are NOT specs. Always write axiom-level spec files before launching the foreman.
- **Launch foreman without scaffold:** The `coding-hermes-foreman` skill's Step 1.5 has an "empty workdir detection" check. If zero source files exist, the foreman creates `## [ ] INFRA — workdir empty, no source code` and skips discovery. Give it at least `go.mod`, `Makefile`, and `.gitignore` so it can self-heal.
- **Use DuckBrain as the spec store:** DuckBrain entries are architecture-level prose. Specs live as files under `specs/` in the repo. The foreman reads files, not DuckBrain, for implementation detail.

## Session Evidence

Rabbit-Hole (2026-07-12): 5 DuckBrain entries under `/project/{concept,collect,classify,express,competitors}` → 6 axiom-level specs (S01-S06, ~65 pages, exact Go interfaces, DDL, eBPF C code, error catalogs, Mermaid diagrams) → scaffold (go.mod, Makefile, .gitignore, AGENTS.md) → GitLab group + project (rabbit-hole/rabbit-hole, ID 17) → foreman cron `256fd74b93d8` (every 30m, deepseek-v4-pro PAYG, toolsets locked). First tick completed 2 commits (scaffold + GitReins config).
