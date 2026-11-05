# Spec quorum — round <N>

**Artifact under review:** `<absolute path to specs dir>` · **Frozen at:**
`<commit / date>` · **Do not review from memory: open the files.**

## Stakes

<Copied from 00-frame.md. What breaks if this spec is wrong, and the failure
class it repeats.>

## Files

- `<specs>/00-frame.md`, `00-overview.md`
- `<specs>/_facts.md` — the ledger; every claim below has a fact id
- `<specs>/_rumsfeld.md` — the four quadrants
- `<specs>/flows/*.md`, `modules/*.md`, `contracts/*.md`, `cross-cutting/*.md`
- `<specs>/_coverage.md`

## Job A — did the merged fixes land? (round 2+ only)

For each fix from the previous round, quote the text that now carries it and
return `FIXED` / `PARTIAL` / `NOT-FIXED`. PARTIAL is the normal verdict for a fix
that landed as prose: a newly defined state, alarm, or guard is NOT fixed if the
fact it depends on is never written by any module.

| fix | quote that carries it | verdict |
|---|---|---|
| <one-line fix> | "<verbatim quote>" | FIXED |

## Job B — FACT claims (grade CONFIRMED / CONTRADICTED against the file)

Each claim carries its expected value. A claim you cannot check is UNRESOLVED, and
saying so is a correct answer.

| # | claim | expected | verdict | evidence |
|---|---|---|---|---|
| C1 | <claim with a number> | <value> | | file:line |

## Job C — INFERENCE claims (labelled on purpose: highest-yield target)

These are the coordinator's own causal and completeness reasoning. Attack them.
A single-family CONTRADICTED is a lead; two independent families flagging the
same item has met quorum.

| # | inference | would be falsified by |
|---|---|---|
| I1 | "<X causes Y>" | <split the failing population; count both sides> |
| I2 | "every surface is covered by a flow" | <a route/verb/job in the code with no flow> |
| I3 | "no module has a second writer" | <a store with two write paths> |

## Repeat-offence section

What in THIS set causes the same failure classes again?

- (a) facts with no HOW (a number that only exists in prose or a figure),
- (b) success-marker or string-check state,
- (c) coverage invented rather than derived from a route/verb/job inventory,
- (d) silent-skip paths and "TBD / Phase 2" in a normative section,
- (e) a requirement with a tautological assertion (`test:` that cannot fail),
- (f) a module whose flow does not exist, or a flow step with no module,
- (g) a number retyped into the document that no command reproduces.

## Output format (mandatory, in this order)

1. Verdicts per claim, with file:line evidence.
2. Corrections ranked by severity, each naming the section to rewrite.
3. New verified facts (anything you measured yourself, with the command).
4. Top 5 fixes, ranked.
5. The one measurement the design must pass that the prose cannot prove.
6. Detector line, exactly: `PANEL REVIEW COMPLETE`

## Budget

Verdict sections are mandatory; verification experiments are capped at three. An
unfinished review is a failed review. Read-only: do not install, start services,
or spawn long-running processes — facts needing those are pre-supplied as labelled
pre-run facts above, and you may audit them.
