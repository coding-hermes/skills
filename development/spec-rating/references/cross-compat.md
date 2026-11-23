# Cross-cutting: compatibility & versioning

## A spec fails compat rating if any of these is missing
- The interface inventory with per-interface compat promise: API, DB schema, message
  schemas, config format, on-disk/on-wire formats.
- The change policy per interface: additive-only windows, deprecation lifecycle
  (announce -> warn -> remove) with real timeboxes.
- Client skew: what happens when an old client meets a new backend, and a new client
  meets an old backend — per breaking change, the behavior is named.
- Data migrations that are reversible (or the explicit one-way-door with a named backup).
- The compat test matrix: which version pairs are tested before every release.

## Rating checks
- FAIL if any stored format has no version field (the first migration is then a rewrite).
- FAIL if a breaking change has no client-skew behavior named.
- FAIL if 'we will just migrate everything' has no runbook and no window.
