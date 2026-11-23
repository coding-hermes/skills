# Cross-cutting: release engineering

## What a complete release section documents
- **Versioning**: the scheme (semver + what counts as breaking), applied to
  binaries, APIs, schemas, and formats alike.
- **The changelog**: generated or curated, user-facing language, and the
  breaking-changes section that is never empty-failed.
- **Artifacts**: what is built per release (binaries per OS/arch, images, docs),
  signed/provenance-attested how, and where they live (the retention and the
  'reinstall 3 versions ago' path).
- **Channels**: dev/staging/prod (or stable/beta), the promotion path, and what
  gates a promotion (the CI verdict, the soak time).
- **The release runbook**: who cuts, from where, the checklist, and the
  yank/recall procedure for a bad release.
- ** cadence**: release-on-train vs release-on-demand, and the emergency-patch
  path that skips the train without skipping the gates.

## Rating checks
- FAIL if a release artifact can't be reproduced from its tag.
- FAIL if rollback to the previous version is untested for the current release shape.
- FAIL if the changelog claims features the tree doesn't contain (a lying changelog
  is worse than none).
