# Cross-cutting: data traffic patterns

## What a complete traffic section documents
- Per data class: producer, consumer(s), direction, payload size, frequency (steady AND
  peak), and growth curve.
- The topology diagram: where data crosses a network boundary, with the latency and
  bandwidth budget per link.
- Burst shape: what the 10x moment looks like (launch, batch job, incident) and what
  absorbs it (queue, cache, shed).
- Data gravity: which flows are chatty (N calls per user action) vs coarse; the call
  count per canonical user journey, stated.
- Privacy border: where personal data crosses a boundary, and the encryption/residency
  rule at each crossing.

## Rating checks
- FAIL if any flow lacks both a steady-state and a peak estimate.
- FAIL if the canonical journey's call count is unknown (chattiness is the top
  latency and cost killer and it hides until load tests).
- FAIL if PII crosses a boundary with no stated encryption/residency rule.
