# Cross-cutting: process artifacts (ADRs, RFCs, design sessions)

Decisions outlive the chat that made them. The spec defines HOW decisions
get made and recorded:

## What a complete process section documents
- **ADR discipline**: per architecture decision — context, options considered,
  the choice, the rejected alternatives (that's the memory), consequences.
  Numbered, immutable, superseded-not-edited.
- **The review gates**: what needs an RFC vs a PR description vs a verbal OK;
  who reviews which class; the quorum for reversible vs irreversible calls.
- **Design sessions**: when a synchronous design meeting is warranted, its
  inputs (the questions the resource files surfaced), its outputs (an ADR or
  a spec section — never just minutes).
- **The decision log linkage**: every spec MUST references its ADRs; every
  ADR references the spec section it changed. Tools like auger formalize
  this (decision ledger, JEV scoring); a file-based ADR/ is the floor.
- **Escalation**: the named path when reviewers disagree, and the
  owner-decision record for calls only the product owner can make.

## Rating checks
- FAIL if a load-bearing decision has no record of rejected alternatives
  (the decision will be re-litigated every 6 months).
- FAIL if 'we decided in a meeting' has no artifact.
- FAIL if irreversible decisions share a gate with reversible ones.
