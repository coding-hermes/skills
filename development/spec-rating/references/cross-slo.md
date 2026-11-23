# Cross-cutting: SLOs & error budgets (the reliability contract)

Deeper than observability (which measures): this is what we PROMISE.

## What a complete SLO section documents
- **Per user-facing capability**: the SLO (availability % and/or latency bucket),
  measured how (the SLI formula, the window), and the error budget it implies.
- **The budget policy**: what happens at 100% burn (freeze features? page out?),
  at 50% (review), and who owns the call — the policy is the difference between an
  SLO and a decoration.
- **Dependency subtraction**: our SLO minus each critical dependency's SLO — the
  arithmetic that shows whether the promise is even possible.
- **The degradation ladder**: which features shed first when budget burns (ties to
  the graceful-degradation list).

## Rating checks
- FAIL if an SLO exists with no SLI formula (who measures, on what data).
- FAIL if dependency SLOs are ignored in our promise (99.9% on top of a 99.5%
  third party needs an answer).
- FAIL if no consequence exists for budget exhaustion.
