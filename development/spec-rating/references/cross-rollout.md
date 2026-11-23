# Cross-cutting: feature flags & gradual rollout

## What a complete rollout section documents
- **Flag inventory discipline**: every flag has an owner, a creation date, an
  expiry/retirement plan, and its blast radius (user-level? org? global?).
- **Rollout mechanics**: percentage steps, the audience rule, the metrics
  watched during rollout, and the abort trigger (automatic on the error-rate
  gate, manual otherwise — stated which).
- **The kill switch test**: each flag's OFF is actually safe mid-flight
  (in-progress states handle the flag flip; no half-enabled corruption).
- **Flag debt**: the cleanup cadence — flags older than X with no owner are
  deleted, not admired. Dead flags are config rot and future incidents.
- **Testing both arms**: the flag-on and flag-off paths are both tested
  (a skip-guard that made one arm unfireable yet green is the classic lie).

## Rating checks
- FAIL if any flag's off-state is untested.
- FAIL if a flag exists with no owner and no expiry.
- FAIL if rollout progress can't be observed (percentage-of-what?).
