# Dependencies: maintenance, upgrades, and staying current

Selection is a day; maintenance is the marriage. The spec must state:

## The upgrade policy (per dependency tier)
- **Security-critical** (crypto, auth, parsers, anything touching untrusted
  input): patch within a stated SLA (e.g. critical CVE < 48h), auto-update
  PRs, and the test depth that makes that safe.
- **Framework**: major-version upgrade windows planned; never more than one
  major behind; the migration cost estimated and scheduled, not discovered.
- **Leaf/utility**: floating ranges OK, lockfile enforced, renovate/bot owned
  by name.

## The standing obligations
- Lockfiles committed; builds reproducible from them.
- Deprecation tracking: a source (release notes, bots) that feeds a backlog,
  with dates — not vibes.
- An upgrade drill: the process was actually done once for a real breaking
  change, or the estimate is fiction.
- Fork policy: when we fork/vendor (see deps-vendoring.md), who carries
  patches, and the re-parenting cadence.

## Rating checks
- FAIL if any dependency's current version is 'whatever installed last'.
- FAIL if the CVE response SLA is unstated for internet-facing surfaces.
- FAIL if no one is named who can assess and land an upgrade.
