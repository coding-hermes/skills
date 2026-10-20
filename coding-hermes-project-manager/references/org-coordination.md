# Org Coordination: Dependencies, Initiatives, Feedback (PM layer depth)

The fleet is not N independent projects — projects depend on each other
(shared libraries, API contracts, config conventions, skill repos). A PM
coordinates ACROSS projects, the way a human PM runs initiatives across an
org. This layer turns gap-pushing into org improvement.

## Dependency graph awareness (read, each cycle)

Check where projects consume each other:

- **Shared repos / libraries**: which projects import or vendor another
  fleet project (e.g. projects consuming `gitreins-poc`, `duckbrain`,
  `coding-hermes-scheduler` skills, `hermes-canopy` as a dependency)?
  `grep -rl "coding-hermes\|gitreins\|duckbrain" <workdir>/go.mod|package.json|pyproject.toml`
  per project is a cheap probe.
- **API/service consumers**: which projects call another project's HTTP API
  or MCP server (e.g. foremen calling the scheduler :9090, sync crons
  posting to DuckBrain :3000)?
- **Skill/knowledge consumers**: which projects load which coding-hermes
  skills — a skill change ripples to every consumer.

**Synchronization finding pattern:** when project A (consumer) shows a gap
that is really caused by project B (provider) — a broken contract, a missing
field, an undocumented API — the PM does NOT file it as A's task. File it as
**B's task with a cross-reference** (`depends_on: <A-PROJECT>-GAP-###`) and
note the consumer impact in the description: "breaks <A>". Providers get the
fix, consumers get the verification. This is how dependent projects stay
synchronized instead of each patching around the other.

## Initiative tracking

Bane runs initiatives across the org (e.g. "get all projects over the
finish line", "board storage git-safety", "DuckBrain sync hardening").
The PM tracks them in `~/.hermes/stand-in/initiatives.json`:

```json
{"initiatives": [{
  "id": "INIT-DONE-REAL",
  "name": "Real done, not green tests",
  "started": "2026-08-04",
  "criteria": "Every enabled project has: integration guide, API docs, <60s short tests, verified fixes",
  "projects": ["hermes-canopy", "ring-runner", "..."],
  "status": "in_progress",
  "last_updated": "2026-08-04T..."
}]}
```

Each cycle: for each active initiative, update `projects` with the ones
gated/verified this cycle, note progress in the cycle's DuckBrain log, and
flag initiatives where NO project made progress in 72h (that's a stalled
initiative — escalate in the report). When an initiative's criteria are met
for all its projects, mark it `complete` and celebrate it in the report —
that's the "really over the finish line" signal.

## Feedback loop (close the loop with foremen)

Gap-pushing is one-way until feedback comes back. Each cycle:

- **Read foremen's tick reports** from the last 24h (DuckBrain
  `/fleet/projects/<name>/ticks/*` or the board's tick history) — did any
  foreman already fix something you flagged? Verify + update the ledger.
- **Feed forward**: when a gap keeps recurring across 3+ projects (e.g.
  "no API docs" everywhere), that's a SYSTEMIC pattern — create a
  **systemic finding** in the cycle log (`/stand-in/YYYY-MM-DD/cycle`
  attributes: `systemic_patterns`) AND add it to the matching initiative.
  Systemic patterns are how the fleet improves instead of firefighting
  one project at a time.
- **Feed back to the org**: Bane checks in and delegates; your cycle logs
  (DuckBrain + HTML report) are the feedback he reads. Make them honest:
  what got verified (with evidence), what stalled, what's systemic.
