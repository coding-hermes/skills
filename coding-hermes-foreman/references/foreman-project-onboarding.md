# Foreman Project Onboarding Checklist

End-to-end workflow for onboarding a new project into the coding-hermes fleet.
Use when Bane has staged a new project (ACs, repo, namespace) and wants the
foreman going.

## What Bane Provides

Bane typically stages these before asking for the foreman:
- **DuckBrain namespace** — already created, set as default for the session
- **Git repo** — cloned locally, remote wired, initial commit pushed
- **Acceptance criteria** — `.hermes/acceptance-criteria.md` with numbered SPECs
- **GitReins config** — `.gitreins/config.yaml` (may need tuning for project language)

## What You Create

### 1. AGENTS.md

Document the project: name, purpose, tech stack, architecture overview, quality
gates, development commands, commit rules. Pattern from existing projects
(heading, hermes-dagger, helix). The AGENTS.md is what the foreman loads to
understand the project context on every tick.

### 2. .coding-hermes/tasks.md

Translate `.hermes/acceptance-criteria.md` into actionable work items. Each SPEC
becomes a section with checkbox subtasks. Start with a "Project Setup" section
for language-specific scaffolding (pyproject.toml, go.mod, package.json, etc.).

Format:
```markdown
### SPEC-001: Title
- [ ] Subtask one
- [ ] Subtask two
```

### 3. README.md (if stub)

Expand the minimal README with project overview, architecture summary, dev
commands, and links to ACs/tasks/AGENTS.

### 4. Hilo Initialization

Initialize Hilo's code graph on the project so the foreman can query dependencies
and blast radius before changes. Even if there are no source files yet (markdown
only), run `hilo init` — it creates `.vfs/manifest.yaml` and installs git hooks
(post-commit for auto-warming, post-merge for cross-machine sync).

```bash
cd /path/to/project && hilo init
```

Then classify files (no-op on empty projects, but establishes baseline):

```bash
hilo classify
```

### 5. .gitignore

Create `.gitignore` with Hilo cache exclusions and language-specific patterns:

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/
dist/
build/

# Hilo — local cache files (rebuildable)
.vfs/graph/graph.db
.vfs/graph/graph.db.wal
.vfs/graph/.last_warm

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.*
!.env.example
```

The `.vfs/manifest.yaml` and `.vfs/.dirty` marker remain tracked — only the
rebuildable DuckDB cache is excluded.

### 6. GitReins Tasks

Register initial tasks via `mcp__gitreins__task_create` for the project-setup
phase so the foreman has structured criteria to evaluate against.

### 7. Foreman Cron

Create via `cronjob(action='create', ...)`. **Must match canonical shape exactly:**

| Field | Value |
|-------|-------|
| skills | `["coding-hermes-foreman", "coding-hermes-cron", "hilo-usage", "gitreins"]` |
| model | `deepseek-v4-pro` |
| provider | `deepseek-foreman` (PAYG — never prepaid) |
| schedule | `every 30m` (interval format, not cron `*/30`) |
| enabled_toolsets | `["terminal","file","web","search","skills","memory"]` — NO delegation, NO cronjob |
| workdir | `/home/kara/<project>` |
| deliver | `telegram:-1003310984808:<thread_id>` — explicit, never `origin` |
| name | `<project>-coding-foreman` |

**All fields must be set at creation time.** The `cronjob` tool accepts
`model`, `provider`, `enabled_toolsets`, `workdir`, and `deliver` as
parameters. Setting them during creation avoids the post-creation JSON
patching documented in `references/cron-json-patch-pattern.md`.

**After creation, verify canonical shape:** check `hermes cron list` output
confirms all fields — skills, model, provider, toolsets (no delegation),
interval schedule, explicit delivery thread, workdir.

### 8. DuckBrain Namespace Sync Cron

Every project with an active foreman needs a DuckBrain sync cron for memory
compaction and cross-reference freshness. Active foreman = `every 2h` interval.

```json
{
  "name": "<project> DuckBrain namespace sync",
  "schedule": "0 */2 * * *",
  "no_agent": true,
  "script": "duckbrain-sync.sh",
  "deliver": "local",
  "model": null,
  "provider": null
}
```

### 9. Commit and Push

Commit all scaffolding files (AGENTS.md, README.md, .coding-hermes/tasks.md,
.gitreins/tasks.yaml) with a `chore:` prefix.

## Pitfalls

- **GitReins guard fails on markdown-only repos.** When the project has no
  source code yet (just .md files), the test guard fails with "no tests
  collected." Use `git commit --no-verify` for the initial scaffolding commit.
  The foreman will run proper guards once code exists.

- **Don't use `origin` delivery.** Auto-detection strips thread IDs in group
  chats. Always use explicit `telegram:-1003310984808:<thread_id>`. Match the
  thread Bane is discussing the project in.

- **DuckBrain namespace may already exist.** Bane often pre-creates the
  namespace. Check with `mcp__duckbrain__list_namespaces` before creating.

- **The foreman won't know about the project until its first tick.** Don't
  manually trigger (`cronjob(action='run')`) unless Bane asks. The 30m
  interval is fast enough.

- **GitHub org invitation may be pending.** When Bane creates a new GitHub org
  for a project (e.g., `Hermes-DAGger`) separately from the repo, the
  `totalwindupflightsystems` account may have a pending membership. Accept it
  before transferring repos:
  ```bash
  # Check org exists
  gh api /orgs/<org-name>
  # Check membership status
  gh api /user/memberships/orgs --jq '.[] | select(.organization.login=="<org-name>")'
  # If "state": "pending" → accept:
  gh api -X PATCH /user/memberships/orgs/<org-name> -F state=active
  ```
  Pending org memberships don't appear in `gh org list`. Always check the API.
  This is different from repo invitations (`/user/repository_invitations`).

## Verification Checklist

After onboarding, confirm:
- [ ] `hermes cron list` shows foreman with canonical shape
- [ ] `hermes cron list` shows DuckBrain sync with `no_agent: true`
- [ ] `git log --oneline -1` shows scaffolding commit
- [ ] `git push` succeeded (check remote)
- [ ] Hilo initialized (`.vfs/manifest.yaml` exists, git hooks installed)
- [ ] `.gitignore` created with Hilo cache exclusions
- [ ] DuckBrain namespace exists and is populated with project context
- [ ] `.coding-hermes/tasks.md` has project-setup + all SPECs as work items
- [ ] `.gitreins/tasks.yaml` has at least one registered task
