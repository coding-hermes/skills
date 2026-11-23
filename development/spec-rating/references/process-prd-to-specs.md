# Process: idea → PRD → specs (the decomposition ladder)

## Stage gates
1. **Core idea** (one paragraph, testable): what it is, who it serves, what
   changes for them. If it takes three paragraphs, it is three ideas.
2. **PRD** — problem, users, jobs-to-be-done, success metrics, constraints,
   non-goals. The PRD names the SYSTEM BOUNDARY: what is inside (must be
   spec'd), what is outside (must be integrated with, see third-party-*.md).
3. **Decompose by surface, not by layer.** Each user-visible capability
   becomes a FLOW (see cross-flows.md); each flow pulls the domains it needs
   (an API flow pulls protocols-http; a sync flow pulls storage + caching).
4. **Write specs per machine** (see cross-machines.md): every runtime process
   gets its platform file + its share of every cross-cutting concern.
5. **Resolve cross-cutting at the system level**: one decision per domain
   (security, observability, cost, compat) that per-machine specs reference —
   never per-machine redefinitions.

## The completeness invariant
Every user-visible capability traces: PRD job → flow → machines →
interfaces → storage/cache/protocols → failure rows. Every artifact in the
chain cites its parent. A capability whose chain has a gap (a flow with no
machine, a machine with no storage) is a spec hole with a name.

## Anti-patterns that fool the rating
- Spec-ing the happy path only (the failure axis catches this).
- Spec-ing the demo, not the product (the flows inventory vs UI/API surface
  check in cross-flows.md catches this).
- Spec-ing components with no contracts between them (the interfaces files
  catch this).
