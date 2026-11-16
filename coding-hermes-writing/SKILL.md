---
name: coding-hermes-writing
description: >-
  Use when writing or editing ANY file in the coding-hermes/skills repo — SKILL.md
  frontmatter, body structure, section style, references/, the normative manifest,
  or dispatch classes. This is the single writing authority: rules, formats, style.
  GitReins guard on this repo enforces the mechanical subset; the rest is review.
version: 0.2.0
author: Bane + Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [coding-hermes, skills, writing, style, manifest, enforcement]
    related_skills:
      - coding-hermes-skill-authoring
      - coding-hermes-map
      - coding-hermes-foreman
---

# Writing rules for the coding-hermes skills repo

Every SKILL.md in this repo is written under THIS skill. GitReins guard runs
`scripts/style_check.py` (FAIL tier) and `scripts/manifest_check.py` on every task;
review enforces the rest. If a rule blocks a legitimate case, change the rule here
first — never bypass the check.

---

## 1. Frontmatter (FAIL tier — mechanical)

Every SKILL.md MUST carry, in this order:

```yaml
---
name: coding-hermes-<name>          # exactly the directory name
description: >-                     # folded block, ONE paragraph, trigger-style
  Use when <concrete trigger>. <what the skill does>. <what it owns or forbids>.
version: X.Y.Z                      # semver; bump on every material edit
author: Bane + Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [coding-hermes, <topic>...]
    related_skills:                 # the skills it composes with, max ~6
      - coding-hermes-...
---
```

- `description` is the **dispatch surface**: agents load skills by matching the trigger
  to their situation. Write "Use when <situation>", never "This skill is about…".
- `related_skills` lists composition, not friendship.
- No `license:` drift — repo-wide MIT at the top level; per-file `license: MIT` is optional.

## 2. Body structure (review tier — with a FAIL floor)

Required order, sections that do not apply are omitted (never left empty):

1. **H1 title** — `# <what it is>` (not the skill name)
2. **Role paragraph** — what this agent/skill owns, in one paragraph, second person
   ("You are…") for agent skills, third person for reference skills.
3. **The graph/table** — every agent skill carries the mermaid skill-map block or a
   when-to-use table. A skill without a discovery surface cannot be dispatched.
4. **Doctrine sections** — the rules, numbered when they are clauses (clause numbers are
   citable in reviews; "clause 8" must resolve).
5. **Pitfalls** — fleet history that already cost time, each with its measured instance.
6. **Changelog / provenance** — dates and owner decisions live at the bottom, never in the body.

## 3. Style rules (review tier)

- **Imperative rules, declarative facts.** Rules say "never X because Y". Facts say
  "X measured N on date". No advice-to-self, no logs of what happened today.
- **English, ASCII, plain.** No Chinese in visible output (kanji identity markers in
  mode-skill titles are the one exception). No emoji in doctrine.
- **Measurements carry their source.** Every number cites where it came from — a command,
  a board, a log. A number with no source is deleted, not softened.
- **Owner law is quoted verbatim** with attribution and date ("Bane, 2026-11-15"), and
  marked as standing order when it is one. Never paraphrase an owner directive.
- **Owner-owned skills are named**: scheduler, task-router-product-ops, boardctl,
  *-foreman-ops, quorum-lineup — no curator patches; changes go through the owner.
- **Size budget**: a SKILL.md is a dispatch surface, not a manual. Target < 700 lines;
  past that, split into `references/<topic>.md` and link it. References are
  documentation, not skill body — they carry the depth.
- **No fleet-specific paths in portable skills.** `/home/kara/...`, hostnames, chat ids
  belong in config or the project's own docs — a skill another operator installs must work.
- **Superseded text is rewritten, never appended.** When a rule changes, replace it and
  record the change at the bottom. A skill with two live versions of one rule is broken.
- **Every clause a foreman can violate has a test or a measurable signature.** "Clause N
  is violated when <observable>" — if you cannot name the observable, it is a preference,
  not a clause.

## 4. Dispatch classes (mechanical — manifest)

Every skill carries exactly one dispatch class in `skills-manifest.json`:

| Class | Meaning | Example |
|---|---|---|
| `always` | Loaded every tick of its role | coding-hermes-foreman, coding-hermes-map |
| `trigger` | Loaded when its description matches the situation | stuck-lane-triage, perf |
| `route-only` | Never auto-loads; referenced by other skills | references-only packages |
| `owner` | Bane-owned; no curator patches; changes via owner | scheduler, boardctl |

`scripts/manifest_check.py` FAILs when a SKILL.md directory is missing from the manifest
or a manifest entry has no SKILL.md. Regenerate with `scripts/manifest_check.py --write`.

## 5. Enforcement tiers — what tier 1 catches and what needs a tier-2 judge

Tier 1 (mechanical, blocks every commit) covers only what a pattern can decide:
frontmatter validity, name/dir match, manifest drift, baseline regressions, H1
presence, TODO/FIXME, size budget, CJK. **Tier 2 (LLM judge) fires on material
SKILL.md body edits — any commit touching a skill body, not just references/ or
the manifest — because those need judgment the checker cannot make:**

- description is *actually* trigger-style (matches how agents search)
- doctrine clarity: clauses citable, no two live versions of one rule
- owner law quoted verbatim, accurately, with attribution
- new rules carry a measurable signature; the composition set is sane
- superseded text properly rewritten, not appended

Reference-only churn (scripts/, references/, manifest regens) skips tier 2 —
judging a whitespace diff trains noise.

## 6. Barrier implementation (what actually runs)

- `scripts/style_check.py` — frontmatter FAIL tier + body WARN tier. GitReins guard and CI run it.
- `scripts/manifest_check.py` — manifest drift FAIL. `--write` regenerates.
- Both run on every commit via the GitHub Actions workflow; GitReins tasks on this repo
  run them as part of the tier-1 battery.
- **Testing the checker**: run it against a deliberately-broken scratch copy before
  trusting a green pass — a checker that has never seen a failure is not a checker.

## 7. Pitfalls

- **`description:` folded style (`>-`)** — a single-line description breaks agent matching.
- **Duplicate clause numbers** — the foreman skill carries two `7.`s from a merge; new
  clauses append with the next free number, never renumber historical ones.
- **Kanban/PRD text pasted into skills** — a skill states the rule; the report that
  motivated it stays in the report.
- **Editing `~/.hermes/skills` directly** — that is the deploy target; the hourly enforcer
  reverts it. The only write path is this repo → `origin/main` → enforcer → grep-verify.
