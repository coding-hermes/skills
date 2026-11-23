# Cross-cutting: deployment & operations

## A spec fails deployment rating if any of these is missing
- Artifact per machine: what is built (container? binary? image?), from what, tagged how.
- Environments and their parity story (dev/staging/prod drift is a stated risk, not a surprise).
- The deploy mechanics: rollout strategy (rolling/blue-green/canary), health-gating,
  and the automatic rollback trigger.
- Config & secrets delivery per environment; what changes require a deploy vs a config flip.
- Day-2 ops: resize, migrate region/host, backup verification, and the DR runbook (RTO/RPO
  numbers, and the date of the last restore TEST).

## Rating checks
- FAIL if rollback is possible but unpracticed or untriggered by any signal.
- FAIL if any environment exists that cannot be rebuilt from code + config alone.
- FAIL if the DR runbook has never had a restore test and no date is recorded.
