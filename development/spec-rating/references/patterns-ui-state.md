# Patterns: client state (the UI side of the data model)

The server spec is half the story; every client (web SPA, mobile, CLI cache)
holds STATE that must be spec'd or it grows by accident.

## What a complete client-state section documents
- **The state inventory**: per client — server state held locally (caches
  of API data), UI state (form state, selections), session state (auth,
  preferences), and the durable/local-first data. Each classified: who owns
  the truth, how stale the local copy may be.
- **The cache-invalidation rule on the client**: refetch-on-focus,
  TTL, websocket push, or manual refresh — stated per data class (the
  stale-read answer: what does the user see while fresh data loads?).
- **Optimistic updates**: which mutations are optimistic, the rollback
  when the server rejects, and the reconciliation when two devices diverge.
- **The offline/local-first stance**: what works offline (the local store
  schema, the sync rule — deploy-hybrid-edge.md and deploy-embedded-
  bundled.md apply here directly).
- **State-machine discipline for UI flows**: screens with multiple modes
  (loading/empty/error/content) — every view's states enumerated, no
  impossible-state combinations (the type system or the store design
  enforces it).
- **State persistence**: what survives restart (URL, local storage,
  keychain) and what doesn't — per piece, with the PII answer
  (cross-privacy.md applies to client stores too).

## Rating checks
- FAIL if any screen has an unreachable-or-unhandled state combination.
- FAIL if optimistic updates exist without a rollback answer.
- FAIL if client stores hold PII with no encryption/retention statement.
- FAIL if the invalidation rule is 'the developer refreshes manually'.
