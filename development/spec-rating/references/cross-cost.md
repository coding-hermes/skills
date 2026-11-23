# Cross-cutting: cost model (unit economics)

## What a complete cost section documents
- Per component: the monthly cost at stated traffic (infra + third-party + model calls),
  and the COST DRIVER per component (what makes it grow — requests, seats, data, tokens).
- Unit economics: cost per user-action / per-customer / per-job at target scale, and
  the gross-margin answer if this is a product.
- The growth curve: 2x users = what bill? The line where architecture must change.
- Budget controls: per-team/per-feature budgets, the alert thresholds, the hard-stop
  or soft-stop decision for runaways.
- The waste list: idle environments, oversized instances, unlogged egress — with the
  review cadence that finds them.

## Rating checks
- FAIL if any third-party integration has no cost row (billing surprises are spec failures).
- FAIL if no unit metric exists (cost is only discussable per-something).
- FAIL if a runaway mechanism (agentic loops, fan-out jobs) has no ceiling and no alert.
