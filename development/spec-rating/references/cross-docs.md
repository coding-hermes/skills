# Cross-cutting: documentation deliverables

The system SHIPS documentation; the spec states which docs exist, for whom.

## What a complete docs section documents
- **Per audience**: user guide, operator/runbook, API reference, developer/
  contribution guide — each with owner, update trigger (docs update IN the
  same change as behavior), and the staleness check.
- **The API reference contract**: generated from code (OpenAPI et al) and
  therefore never lying, or hand-written with a drift check — never
  hand-written alone.
- **Runbooks as code**: each failure-matrix row links its runbook; runbooks
  have last-tested dates.
- **The doc tests**: links resolve, examples run (documented-example
  reproducibility), and the CI job that keeps docs from rotting.
- **In-product docs**: error messages, onboarding copy, tooltips — owned and
  reviewed like code, localized per the i18n scope.

## Rating checks
- FAIL if any doc's update mechanism is 'someone remembers'.
- FAIL if API examples can't run (the fastest doc rot).
- FAIL if the runbook exists for a failure the system can have, but not for
  the one it will have (the top incident class is always documented first).
