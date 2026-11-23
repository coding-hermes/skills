# SDLC: the intent-to-project ladder (small/medium intent -> complete system)

The north star: a human states a small-to-medium intent; workhorse models
produce a complete, built system. The ladder this skill set serves:

1. **Intent intake** — the human's paragraph, captured verbatim (the
   operator's words are evidence; restate-then-confirm, never silently
   paraphrase).
2. **Clarify against the resource files** — start from
   `process-file-routing.md`: the project shape gives the minimum set, intent
   signals add files, and each skipped family gets a written reason. The
   first workhorse pass then surfaces the questions the intent does NOT
   answer. The operator
   answers decisions; OPEN items get owners.
3. **PRD** (process-prd-to-specs.md) — the intent becomes problem/users/
   metrics/constraints.
4. **The spec set** — manifesto, layout, module specs, flows, data,
   failures: one section per applicable resource file, each written through
   the workhorse loop (answer → write → self-rate → next).
5. **Rating pass** — a SECOND agent rates the spec set against the same
   files (the rater never rated its own homework). Verdicts per domain;
   FAILs route back to step 4.
6. **Build** — the spec set decomposes into module-sized work orders
   (sdlc-module-template.md is the work order shape); workhorse models
   build one module each; the CI/CD and review sections govern landing.
7. **Verify live** — the spec's own verification section (testing
   methodology, SLOs) is executed against the built system; the spec that
   predicted the checks watches them pass.

## The invariant that makes this honest
At every rung, the artifacts cite their sources and the OPEN list is
visible. A ladder run that produces a complete-looking spec with an empty
OPEN list has hidden its unknowns — the rung isn't done.
