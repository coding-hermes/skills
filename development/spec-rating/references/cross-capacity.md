# Cross-cutting: capacity planning

Distinct from performance (speed at load): this is SIZE and GROWTH.

## What a complete capacity section documents
- **Per resource**: the sizing formula from the traffic patterns (users, req/s,
  data volume, model tokens) to instances/storage/quotas — so scaling is arithmetic,
  not vibes.
- **Headroom policy**: N-1 survival (lose the biggest node, still serve), the
  burst reserve, and when headroom triggers the scale-out.
- **The scaling axes per machine**: vertical ceiling (the biggest box we can buy),
  horizontal axis (shard key), and the wall where the architecture must change —
  named in advance.
- **Quota planning**: third-party quotas vs our peak (the 429 forecast), and the
  negotiated-limit path.
- **The review cadence**: capacity reviewed at every growth milestone, not at incident.

## Rating checks
- FAIL if any resource's ceiling is unknown ('we'll scale when we must').
- FAIL if the shard key / partition axis is unnamed for any store expected to grow.
- FAIL if peak quota exceeds third-party limits with no plan.
