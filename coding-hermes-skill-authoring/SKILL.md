---
name: coding-hermes-skill-authoring
description: >-
  How fleet skills should look — portable decision-frameworks that teach an
  agent HOW to find and choose (projects, models, lanes, targets), never the
  answer itself. Structural conventions, the Portability Law, and the
  decision-framework template every fleet skill should follow.
version: 1.0.0
author: Bane + Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [coding-hermes, meta, skill-authoring, decision-framework, portability]
    related_skills:
      - coding-hermes-map
      - coding-hermes-config
      - coding-hermes-worker-model
      - coding-hermes-never-done
---

# Skill Authoring — Portable Decision Frameworks, Not Answers

> See [coding-hermes-map] for the full skill hierarchy and when to use each skill.

## Why This Skill Exists

A fleet skill has one job: **survive contact with change.** Models rotate,
projects churn, providers rise and fall, hosts get rebuilt. A skill that
names today's answer is stale the day the answer changes — and worse, it
trains agents to obey a table instead of exercising judgment. A skill that
teaches the *procedure for finding the answer* keeps working forever.

## The Portability Law

> A skill may name a PROCEDURE and a LIVE SOURCE OF TRUTH.
> A skill must never name the current ANSWER.

| Belongs in a skill | Never in a skill |
|---|---|
| How to enumerate projects (`fleet.toml`, scheduler API, board dirs) | A specific project name as "the" example answer |
| How to select a model (criteria → live benchmark query → tie-breakers) | A table of today's model IDs and prices |
| How to resolve a provider lane (config fields, env-var indirection) | A hardcoded host, URL, or API key |
| Where to RECORD a decision (DuckBrain key recipe) | The recorded value itself |
| A dated *policy* an operator chose (labeled, with revisit trigger) | An unnamed convention that silently rots |

**The one exception:** an operator's explicit, dated directive ("until
benchmarks or the operator say otherwise") may be quoted IF it is labeled as
policy with an owner and an expiry trigger — because that is an instruction
about *how to decide until re-decided*, not an answer pretending to be
permanent. Keep these in one clearly-marked section, never scattered.

## Anatomy of a Fleet Skill

```
<skill-name>/
  SKILL.md            # the procedure (this file's rules apply)
  references/         # deep dives, checklists, worked examples
  scripts/            # executable helpers (never credentials)
  templates/          # scaffolds the skill stamps out
```

`SKILL.md` structure, in order:

1. **Frontmatter** — `name`, `description` (what + when, ≤2 lines),
   `version` (semver; bump on every behavioral change), `author`,
   `platforms`, `metadata.hermes.tags`, `related_skills`.
2. **Map pointer** — one line referencing `[coding-hermes-map]`.
3. **Purpose** — the question this skill answers, stated as a question.
4. **The decision framework** — see template below.
5. **Recording** — where the outcome is stored (DuckBrain key recipe).
6. **Anti-patterns** — what wrong looks like (named, with the fix).
7. **references/** pointers for depth. SKILL.md stays loadable in one read.

## The Decision-Framework Template

Every "how to choose" section follows five steps:

```markdown
### Choosing <X>

**Question:** <the actual decision, one sentence>

**Criteria (ranked):** <what matters, most important first — measurable>

**Live source of truth:** <the query/recipe that yields today's data>
  e.g. `duckbrain recall --namespace default --key /benchmarks/models/<id>`
  e.g. `GET /api/v1/projects` / `cat fleet.toml` / registry table

**Tie-breakers:** <ordered rules when criteria tie — cost, latency, rotation>

**Record:** <where the choice + rationale land, so the next agent
  re-derives instead of re-decides>
```

Worked micro-example (model selection, done portably):

```markdown
### Choosing the worker model for a task

**Question:** which model runs this task cheapest at acceptable quality?

**Criteria:** (1) task shape — long-context / visual / mechanical / design;
(2) verified benchmark tier for that shape; (3) cost per 1M tokens;
(4) subscription coverage (already-paid beats PAYG).

**Live source:** `duckbrain recall --namespace default
--key /benchmarks/models/<candidate>` for each candidate. Candidates come
from the providers listed in the user's config skill — never from this file.

**Tie-breakers:** covered-by-subscription > cheaper > faster > newer.

**Record:** append the choice + task shape to
`/decisions/model-choice/<date>` so the foreman can audit drift later.
```

The anti-pattern this replaces: a table saying "use model X for Go, model Y
for docs." The moment X is deprecated, the table is a liability.

## Recording Decisions (DuckBrain Contract)

A framework that doesn't record forces every successor to re-derive from
scratch. Every skill's decision step writes:

- **Key recipe:** `/decisions/<domain>/<topic>` — names are stable, values rotate.
- **Value shape:** `{choice, criteria_used, source_snapshot, decided_at, revisit_when}`.
- **Revisit trigger:** the event that invalidates the choice (model update,
  cost change, new project, operator directive). No trigger = the decision
  will rot silently.

## Structural Conventions

- **No real names, no absolute home paths.** Write `~/`, `<project>`,
  `<provider>` — the fleet is public; specifics live in config.
- **Config is the only answer-store.** Keys, models, paths flow through the
  config skill at setup time. A skill referencing specifics is a bug.
- **Procedures are imperative and testable.** "Run X, expect Y" — an agent
  must be able to execute the section and tell pass from fail.
- **Depth lives in references/, obligations live in SKILL.md.** The main
  file must carry the full framework; references add evidence and recipes.
- **Every dated claim gets an expiry.** "As of <date>, <policy>, revisit
  when <trigger>" — or it doesn't belong in the file.

## Reviewer Checklist

Before merging a skill (or a skill edit):

- [ ] Does any sentence name a current answer (model, project, host, key)? → move to config/DuckBrain, keep the procedure.
- [ ] Can a fresh agent follow the framework and reach a decision without asking a human?
- [ ] Is the live source of truth a real command/endpoint that works today — and would still work after the underlying answer changes?
- [ ] Are dated directives labeled with owner + revisit trigger?
- [ ] Does the decision get recorded (key recipe given)?
- [ ] Version bumped, map pointer intact, anti-patterns updated?
