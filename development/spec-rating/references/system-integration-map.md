# System: the integration map (how the orchestra comes together)

The engine and module specs say each piece works. THIS file specifies the
assembly: every connection between pieces, who owns each requirement, and
what makes the assembled whole a STABLE system rather than a pile of
working parts.

## 1. The integration inventory (every seam, listed)
Per integration point — API call, queue topic, shared file, database, CLI
script invocation, config handoff, cron trigger:
- **Producer -> consumer**, the artifact exchanged (schema/contract id).
- **The contract**: where it lives (the file that owns it), its version,
  its compat promise.
- **The failure answer**: what the consumer does when the producer fails
  or lies (garbage in).
- **The script/connection registry**: every script that glues (deploy
  scripts, migration runners, cron entries, health probes) — what it
  touches, what credentials it needs, what owns keeping it current.

## 2. The ownership matrix (what file owns what)
- A single table: every requirement/integration -> its OWNING spec file
  -> its verifier (the test/check that proves it live).
- Rules: one owner per requirement (others link); ownership transfers are
  recorded; an integration with no owner is an orphan and fails rating.

## 3. The stability requirements (what makes the whole stable)
- **Interface stability between pieces**: which seams are frozen (internal
  APIs others build against) vs free-to-change (with the wave/broadcast
  rule for breaking them).
- **Dependency direction**: the acyclicity rule (who may depend on whom);
  cycles are named and justified or broken.
- **Whole-system invariants**: what is true of the ASSEMBLED system even
  when every part is individually correct (no lost updates across seams,
  eventual consistency bounds, no unbounded queues between pieces) —
  these live HERE, not in any single module spec.
- **The integration test strategy**: per seam — the contract test that
  proves producer/consumer agree; the assembly test that boots the whole
  and probes the canonical flows; the chaos set that breaks one piece
  and measures the whole.
- **The stability budget**: what the system tolerates from each piece
  (restarts, latency, garbage) before the WHOLE degrades — the answer
  must be per-seam, stated, and tested.

## 4. The assembly verification (how you KNOW it's stable)
- The whole boots from the spec tree alone (fresh environment, no tribal
  steps) — the bootstrap test, run on a schedule.
- The canonical end-to-end flows execute against the assembled system in
  CI, not just unit-passing parts.
- The failure drills from cross-failures.md are executed at the SYSTEM
  level (kill one piece, watch the whole recover) — piece-level tests
  passing proves nothing about the assembly.

## Rating checks
- FAIL if any seam between two spec'd pieces has no contract file.
- FAIL if any integration has no owner in the matrix.
- FAIL if the whole system cannot be assembled from the spec tree alone.
- FAIL if system-level failure drills don't exist (piece tests green,
  assembly unproven — the classic 'works on every part' lie).
