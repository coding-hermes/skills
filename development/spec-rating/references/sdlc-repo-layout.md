# SDLC: repository layout (folder/file hierarchy as a contract)

## The principle (per <project>)
Not brute-force: 'I need to write this module' — but 'where does this module
FIT in the hierarchy so it correctly makes sense'. Layout is a design act;
the spec specifies it BEFORE modules exist.

## What a complete layout section documents
- **The tree**: the full directory structure, annotated per directory with
  what belongs there and what does NOT.
- **Placement rules**: a new module's home is decided by stated rules
  (by-layer? by-feature? by-deployment-unit?), with examples of the rule
  applied to real cases — the next contributor (human or workhorse) must be
  able to DERIVE the location, not guess it.
- **Import/dependency rules**: which directories may import which (enforced
  by lint or package boundaries — e.g. domain never imports handlers; the
  rule AND its enforcement are both stated).
- **The public/private boundary**: what is importable from outside the repo
  (the packages that are API) vs internal forever.
- **Growth accommodation**: where the 10th service, the 50th model, the
  second UI goes — the layout survives growth without re-architecture.
- **The census check**: every file in the tree maps to a spec'd purpose;
  every spec'd artifact has a home (orphan files and orphan specs both fail).

## Rating checks
- FAIL if module placement is by convenience ('it seemed fine at the time').
- FAIL if import rules exist but nothing enforces them.
- FAIL if the layout cannot answer 'where does this new thing go' without
  asking the author.
