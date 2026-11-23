# Third-party: external APIs (services outside our boundary)

Every external API the system calls is a dependency with a personality. The
spec must document, PER external API:

## The integration contract
- **What it's for** and the one alternative we didn't pick (so the decision
  is revisitable).
- **Auth**: credential kind, storage, rotation, scope; the blast radius of a
  leaked key.
- **Quotas & rate limits**: published limits, the expected headroom, the
  429/402 behavior, backoff policy, and the burst budget per feature.
- **Cost model**: per-call/per-seat pricing at the stated traffic patterns;
  the alert when spend anomalies.
- **Versioning**: their deprecation policy, the version pin, and the
  migration window we commit to honoring.

## The failure contract (the part everyone forgets)
- **Their downtime is our feature outage.** For each API: what degrades,
  what the user sees, the cached-stale answer, the circuit breaker, and the
  manual workaround.
- **Their data**: retention on their side, export path (exit strategy),
  deletion propagation (does our delete reach their store?).
- **Sandbox/test**: how we develop against it without spending real money
  or touching real users.
- **Webhooks/callbacks** (if any): verification, replay idempotency, our
  receiver's availability contract.

## Rating checks
- FAIL if any external API appears in a flow but not in the integration
  inventory with quota + cost + failure rows.
- FAIL if exit/export is impossible or unstated (data hostage risk).
- FAIL if credentials can outlive the integration (no rotation story).
