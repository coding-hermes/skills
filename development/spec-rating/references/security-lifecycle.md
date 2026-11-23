# Security: the lifecycle (how security work GETS STARTED and continues)

Security is not a checklist appended at the end; it is a lifecycle with an
entry point. A spec that cannot show WHEN security analysis happened and
WHAT it produced is not a secure design — it is a hopeful one.

## Stage 1: Threat modeling (how it starts)
Before design freezes, per surface:
- **Enumerate assets**: what is worth stealing/destroying (data classes,
  credentials, availability itself).
- **STRIDE per surface**: every interface/trust boundary (from the
  integration map) gets the six questions: Spoofing, Tampering, Repudiation,
  Information disclosure, Denial of service, Elevation of privilege — each
  either addressed, transferred, or ACCEPTED IN WRITING by the owner.
- **Abuse cases**: the feature viewed as a weapon (the bulk endpoint used
  for scraping; the free tier used for cost bombing; the export used for
  exfiltration). Every abuse case maps to a control or an accepted risk.
- **Trust levels per actor**: who is fully trusted, partially, or hostile —
  per actor class, not per person.

## Stage 2: Design controls (the threat model lands in the spec)
- Each threat -> control (prevent/detect/respond) -> the spec section that
  owns it -> the test that verifies it. A threat with a control but no
  verification is a wish.
- Defense in depth per boundary: assume the outer layer fails; name what
  stops the attack then.
- Least privilege everywhere: per service, per job, per human — the
  permission inventory, and the review cadence that trims it.

## Stage 3: Verify (security is tested, not asserted)
- Abuse-case tests: the abuse cases from stage 1 are TESTS (the scrape
  attempt is attempted in CI/staging; the control provably fires).
- The security regression gate: every vuln fix arrives with the test that
  proves it (same discipline as bug regression tests).
- Pentest/audit cadence: external at milestones, internal continuously;
  findings have owners and SLAs by severity.

## Stage 4: Operate (the lifecycle continues past launch)
- Patch SLAs per severity (ties deps-maintenance.md), the rotation calendar
  (keys, certs, credentials), access reviews, and the incident runbook
  (detect -> contain -> eradicate -> recover -> postmortem) with the
  postmortem feeding new abuse cases (the loop closes).

## Rating checks
- FAIL if no threat model exists or it predates the current architecture
  (threat models are living documents with dates).
- FAIL if any accepted risk lacks a named accepting owner.
- FAIL if a control exists with no verification artifact.
- FAIL if the incident runbook has never been drilled.
