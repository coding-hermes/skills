# Dependencies: vendoring and forking

## When the spec must choose vendor/fork, and what it must then document
- **Why**: the upstream won't take the patch / we need it faster than
  upstream moves / survival under upstream abandonment. State which of these
  is true, because it changes the carrying cost.
- **The patch set**: tracked as a numbered series against an upstream ref,
  not a mysterious blob.
- **Re-parenting cadence**: the scheduled upstream sync, and the sign that
  triggers it (security fix, new feature).
- **The exit**: what would make us drop the fork (upstream merges it, the
  need disappears) — decided while we still remember why we forked.

## Sub-setting: copying code (not a fork)
- Vendored snippets carry a provenance header (source, version, license,
  date) and an owner — otherwise they rot invisibly.

## Rating checks
- FAIL if a fork exists (or is proposed) with no re-parenting plan.
- FAIL if vendored code has no provenance and no owner.
- FAIL if forking is chosen where an interface boundary + adapter would be cheaper.
