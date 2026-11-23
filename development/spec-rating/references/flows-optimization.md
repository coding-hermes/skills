# Flows: optimization (a documented act on the spec, not a hope)

Optimization is performed ON the flow spec, with before/after evidence —
never by silently rewriting steps. The spec records the optimization pass.

## The optimization checklist (run per hot flow)
1. **Count the calls**: chattiness = calls per journey execution. The spec
   states the number and justifies it, or merges steps (round-trip
   reduction: fetch everything one step needs in one call).
2. **Find the serial-when-parallel**: steps with no data dependency that
   run sequentially; declare them concurrent (and their join rule).
3. **Move slow off the critical path**: steps the user doesn't wait for
   (email, analytics, cache-warming) become async — with the completion
   contract (paradigms-sync-async.md).
4. **Cache at the right hop**: per step, is the data re-fetched that a
   cache already holds? (caching-*.md rules apply at flow level too.)
5. **Batch the batchable**: N individual calls inside a loop -> one batch
   call, with the batch boundary + partial-failure rules
   (paradigms-interaction-patterns.md).
6. **Pre-compute the expensive**: derivations computed per-request that
   could be computed at write time or cached — stated with the staleness
   accepted.
7. **Shed the optional**: what the flow drops first under load (the
   degradation ladder), so optimization under pressure is designed, not
   improvised.

## The rules that keep optimization honest
- **Measure, then optimize**: the optimization pass records the baseline
  (calls, latency budget per step) and the target — optimizing without a
  baseline is vibes.
- **Correctness is the constraint**: every optimization re-states the
  invariants it preserves (idempotency, ordering, atomicity). An
  optimization that breaks a terminal-state invariant is rejected, period.
- **The failure paths survive**: optimizing the happy path never deletes
  error flows — the error-depth parity check still passes after.
- **Re-rate after**: an optimized flow re-runs the completeness checks
  (surface matrix, terminal states, re-entry) — optimization is a spec
  change and re-enters rating.

## Rating checks
- FAIL if a hot flow (high-traffic per traffic patterns) has no recorded
  optimization pass with a baseline.
- FAIL if any optimization lacks its preserved-invariant statement.
- FAIL if the post-optimization flow has fewer error flows than the
  original.
