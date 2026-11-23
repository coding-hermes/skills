# JS/TS release verification patterns

Target audience: releng satellite sweeps on Next.js / npm / Docker repos using
`gh release create`, `npm run build`, and GitHub Actions docker-publish workflows.

## Version authority in JS/TS repos

The version stamp lives in `package.json` (`"version"`). For repos that use a
custom release tag namespace (e.g. `v0.6.0-federation.N` instead of the
`package.json` semver), verify the documented release policy before flagging
drift. A repo that deliberately exempts its tag line from `package.json`
version parity is not a hygiene failure — the policy belongs in
`docs/RELEASE-*` or `docs/RELEASE-UPSTREAM-FLOW.md`. File a RELEASE-* finding
only if the policy is absent or contradictory.

**Pitfall:** `npm version` is the default bump tool, but it writes `package.json`,
commits, and tags atomically — never let it run inside an audit tick. Read
`package.json` only; never auto-bump in a verification sweep.

## Docker-based release surface

Many Next.js / full-stack repos ship as Docker images, not npm packages. The
three-layer model still applies, but "build artifacts" means the Docker image
published to a registry, not necessarily downloadable assets on the Release page.

| Layer | Command | Missing = |
|-------|---------|-----------|
| Annotated tag | `git ls-remote --tags origin \| grep 'refs/tags/vX.Y.Z$'` | tag not pushed |
| GitHub Release object | `gh release view vX.Y.Z --repo <org/repo>` | release page + notes absent |
| Docker image published | `gh workflow run <docker-publish.yml> --ref vX.Y.Z` succeeded + registry digest | no published container |

A Release object with 0 downloadable assets is **not a gap** when the
docker-publish workflow ran and succeeded on the tag commit. Record the
workflow run id as the artifact evidence.

## paths-filtered CI: "no run" is not unverified

A workflow gated on `paths:` (e.g. `docs/**`, `scripts/**`, `*.md`) produces
no push-event run when the commit range touches only filtered-out files.
Board-only and specs-only ranges are the common case. `gh run list` showing
nothing on HEAD is **"no run was needed"**, not red and not unverified.

To establish green explicitly when no run exists:
```bash
gh workflow run <wf>.yml --ref main   # dispatch; cite the run id
gh run view <id> --json jobs --jq '.jobs[] | "\(.name):\(.conclusion)"'
```

Record the dispatch run id in the release row so the next tick does not repeat it.

## Masked CI gates: cross-project fleet scripts

A full-suite guard (`npm test`, `go test ./...`) can carry a per-job failure
that is masked at the run level by `continue-on-error: true`. But there is a
second masking class that does not involve `continue-on-error`: a **cross-project
fleet script** (e.g. `bunker-qa.sh`) that is broken in a way the repo's own
test suite validates. The suite exits non-zero on every push regardless of the
repo's code quality, and the failure is NOT a regression in the repo under test.

**Detection pattern:**
1. The failing test file references a script or fixture path outside the repo
   (`~/.hermes/scripts/`, `/usr/local/bin/`, etc.)
2. The same commit range carried clean guards before the fleet script was
   redeployed
3. The script's last-change commit is in a different repo or a different
   project's foreman lane

**Treatment:** File a RELEASE-* P1 finding naming the cross-project script
brokenness. Do NOT block the release on it unless the script failure masks a
real repo regression. Document the guard state explicitly in the release report
so the consumer knows CI-red is a known infra issue, not a code regression.

## npm run build non-determinism

`npm run build` (Next.js webpack) can fail non-deterministically under load
with an uncaught exception (e.g. `TypeError: Cannot read properties of undefined
(reading 'length')`) and succeed on immediate retry. This is an environmental
/ load-dependent failure, not a deterministic code defect.

**Before a cut:**
1. Run `npm run build` at least twice on the tag commit. If the first run fails
   and the second succeeds, record both outcomes.
2. Check whether CI carries a production build leg. If CI only runs the test
   suite, a build-breaking state at HEAD will not be caught.
3. File a P2 finding if the pattern recurs; do not block a release on a
   single non-reproducible build failure when the Docker publish path is
   confirmed working.

## Lockfile sync (JS/TS variant)

For repos using `npm`:
```bash
npm ci --package-lock-only              # refreshes package-lock.json
git diff --exit-code package-lock.json  # exits 0 = in sync
```

For repos using `pnpm`:
```bash
pnpm install --frozen-lockfile          # exits 0 = lockfile in sync
```

**Pitfall:** `pnpm 12 + isolated linker` on a fresh store can leave root-level
deps (express, duckdb, etc.) un-linked even though `pnpm install --frozen-lockfile`
exits 0. Verify `node_modules/<dep>` is a symlink, not just present in
`node_modules/.modules.yaml`. If `node bin/<cli>.js help` fails with
`Cannot find module '<dep>'` on a fresh install, pin pnpm in `packageManager`
and add a clean-store link check in CI.

## A publish channel that has never carried a release

A package absent from `npm ls -g <pkg>` proves nothing about the registry — a global install is a
device-local fact. Ask the channel itself:

```bash
cd /tmp && npm view <pkg> version dist-tags | head -3    # E404 = never published, at any version
```

`E404 Not Found - GET https://registry.npmjs.org/<pkg>` means the release workflow's publish step
has never once succeeded, whatever the tags say. That is a first-publication case (owner
authorization required) and simultaneously a workflow finding to explain, not a hygiene nit.

**A version that resolves is not a channel you own.** `npm view <pkg> version` printing a number
only proves someone published under that name. Read the publisher before treating the channel as
available:

```bash
npm view <pkg> name version maintainers time.created repository dist-tags
npm whoami                                                      # ENEEDAUTH = no session on this host either
```

A maintainer address from another domain, a `time.created` far older than the repo, and a
`repository` pointing at a different GitHub org together mean the name belongs to a third party:
publishing would 403, and `npm publish --dry-run` from your tree cannot detect that because it
never leaves the machine. This is a NO-CUT on the CHANNEL, independent of code readiness — report
it with the literal probe output and leave the resolution (scope the package, rename, or publish
through a channel the project does control) to the owner. Same rule when the package name is newer
than the code but the repo carries tags: tags are not publication.

**A tag-pipeline publish with an absent credential burns the version.** When the release workflow
runs CI gate → build → `npm publish` → `gh release create`, a missing registry-token secret lets
the tag push through the gates and then dies at publish: the tag is public and immutable, the
Release step never executes, and the version number is spent on nothing. Preflight the secret
inventory before proposing any tag on an unpublished channel:

```bash
gh api repos/<o>/<r>/actions/secrets --jq '.total_count'       # 0 = no publish credential at all
gh api repos/<o>/<r>/actions/secrets --jq '.secrets[].name'    # names only, never values
```

Zero is a NO-CUT with an owner-gated row, not "tag it and see". Say in the row that publication is
the owner's act and that the worker cannot perform it.

**A pushed tag with no Release and no run on its commit is the fingerprint of exactly that
failure**, and cutting over it silently repeats it. Inventory all three layers per tag:

```bash
# derive peels from the REMOTE, not from local tag objects
git ls-remote --tags <alias> | grep -E 'refs/tags/v[0-9]'      # tag object + the ^{} peel beside it
git merge-base --is-ancestor <peel-40sha> <alias>/<default-branch> && echo BASELINE || echo DIVERGED
gh release list --repo <o>/<r> --limit 10
gh run list --repo <o>/<r> --commit <tag-commit-40sha> --limit 5 --json databaseId,conclusion
```

**Tag names are not tag identity.** `git for-each-ref refs/tags` in a working checkout answers about
the LOCAL tags, which a fetch may never have aligned with the remote: the same name can peel to a
reachable commit locally and to an unreachable commit remotely. When the remote peel fails the
ancestry test, the published tag ships code that was never merged into the default branch — a
consumer checking that tag out gets a divergent history, and a census based on the local peel is
measuring a lineage the release never referenced. Prefer the remote peel as the release fact, print
both in a table when they disagree, and pick the census baseline as the newest tag whose REMOTE peel
is an ancestor of the default branch — naming the tag you skipped and why.

An annotated tag that exists on the remote with no Release object and no run on its commit is an
ORPHAN, not the last release artifact: name it as one in the report, and never "fix" it by
force-moving the tag — the tag is public history.

**Green CI is not version-hygiene evidence.** The version stamp is duplicated across surfaces no
gate reconciles: `package.json`, the lockfile's ROOT version (`.version` and
`.packages[""].version`, which are separate fields — check both), a README badge, the CLI's own
help/version banner literal in source, and any hard-coded version a CI step asserts. A
lockfile-sync check that compares dependency RANGES only, plus a CI step asserting a literal,
both stay green through a multi-way split; the observable symptom is `--version` printing one
version while `help` prints another. Census the surfaces directly:

```bash
jq -r '.version' package.json
jq -r '.version, .packages[""].version' package-lock.json
node bin/<cli>.js --version ; node bin/<cli>.js help | head -3
git grep -nE '[0-9]+\.[0-9]+\.[0-9]+' -- ':!*.lock' ':!node_modules' ':!CHANGELOG.md' ':!<board-dir>'
```

Report the surface count with each value and its `file:line`. A single-value claim ("version is
X") is false on such a repo and leaves the cut row unactionable.

To prove the publish PATH without publishing, `npm publish --dry-run --access public` from the
tagged tree prints the tarball contents and any `bin` path-normalization warning — cite it as
shape evidence, and keep the real publication owner-gated.

**Prove the tarball INSTALLS. `--dry-run` does not.** The package that consumers receive is the
packed artifact, not the checkout, and `files[]` decides what survives: an install hook
(`postinstall`, `prepare`) that invokes a path excluded from `files[]` builds and tests green in the
repo, ships an artifact that every consumer install fails on, and no in-tree test can see it because
the script is present on disk. Two steps settle it:

```bash
npm pack --pack-destination <scratch>/pkg > /dev/null 2>&1
npm pack --dry-run 2>&1 | grep -c '^npm notice scripts/'          # 0 while package.json declares postinstall
cd <scratch>/consumer && printf '{"name":"probe","private":true}\n' > package.json \
  && npm install <scratch>/pkg/<name>-<ver>.tgz --no-audit --no-fund > install.log 2>&1; rc=$?
echo "rc=$rc"; grep -E 'npm error (code|command)|No such file' install.log
```

Capture `rc` by redirection, never through a pipe — `npm install ... | tail` reports tail's status
and turns a failed install into a false 0. `rc=127` with `command sh -c bash scripts/<hook>.sh` and
`No such file or directory` is the whole finding: the artifact is uninstallable, the fix belongs in
the packaging manifest (ship the script, relocate it under a shipped directory, or drop the hook),
and the release is blocked until a clean consumer install exits 0 and `node_modules/.bin/<cli>
--help` exits 0. Cite the tarball's sha256 with the rc so the probe is reproducible against the exact
bytes you judged. When an open row already names this acceptance test, attach your reproduced
receipt to it instead of filing a duplicate row.

Audit the dependency tree the same run: `npm audit --omit=dev --json` separates the advisories a
consumer inherits from dev-only noise — count production criticals and highs, since a dev-only
tree can look alarming while shipping nothing.

## Open-pending P2s: not hard release blockers

A P2 that is a CLI contract decision (exit code semantics, usage-line accuracy)
or a contained stale install (foreman skill uses a fresh binary) does not block
a release cut. Record them as open findings in the report but do not block the
release on their account. The next release tick should confirm they are resolved
before the following cut.
