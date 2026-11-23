# SDLC: testing methodology (the project's verification philosophy)

Distinct from cross-testing.md (which covers the test STRATEGY artifacts):
this is the project's testing METHODOLOGY — what verification means here.

## What a complete methodology section documents
- **The testing doctrine**: what kinds of tests exist, in what proportion,
  and what each layer is TRUSTED to catch — stated so a contributor knows
  where a new test belongs.
- **The test-first stance**: TDD enforced, encouraged, or exempted per change
  class (bugfix tests-first is the common floor: the failing test proves the
  bug before the fix).
- **Naming & structure conventions**: test file placement (mirrors source?),
  naming grammar, fixture organization, table-driven patterns per language.
- **What MUST be tested**: the invariant list (every failure-matrix row has a
  test; every public interface has a contract test; every bug fix arrives
  with its regression test).
- **What is NOT tested and why**: the explicit exemptions (generated code,
  glue) — unstated exemptions grow until nothing is tested.
- **Determinism rules**: clocks, randomness, network — always injected;
  flaky tests are quarantined with an owner and a date, never tolerated.
- **The coverage stance**: coverage as a floor metric on changed code (not a
  global vanity number), and the mutation-testing or property-testing
  position (adopted or rejected, with reasons).

## Rating checks
- FAIL if verification of any spec'd behavior is unplanned.
- FAIL if the doctrine says 'tests are important' without saying what breaks
  when they don't exist.
- FAIL if flakiness has no quarantine protocol (flaky tests teach people to
  ignore red).
