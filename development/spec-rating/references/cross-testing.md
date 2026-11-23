# Cross-cutting: testing

## A spec fails test rating if any of these is missing
- The test strategy per layer: unit/integration/E2E proportions, and WHAT each layer
  is trusted to catch (unit for logic, integration for wiring, E2E for journeys — stated).
- Test data: fixtures strategy, PII policy for test data, and how tests stay deterministic
  (clocks, randomness, network injected).
- The pre-merge gate vs the canary/prod checks: what blocks a merge, what alarms after.
- Performance/load tests: the scenario set matching the stated traffic patterns, run when.
- Chaos/failure drills: which failure paths from the spec are actually exercised, where.

## Rating checks
- FAIL if the spec promises failure recovery no test ever exercises.
- FAIL if E2E suites mock the wiring the E2E exists to prove.
- FAIL if the load scenario set doesn't match the stated traffic patterns (peak shape,
  burst multiplier, sustained baseline).
