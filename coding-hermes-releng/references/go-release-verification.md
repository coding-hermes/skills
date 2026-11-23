# Go release verification patterns

Target audience: releng satellite sweeps on Go repos using `gh release create`,
`go build`, `go version -m`, and Makefile gates.

## Pre-cut: verify the version stamp chain before touching a tag

```bash
# 1. What does the current tag say?
git describe --tags --abbrev=0           # → vX.Y.Z
git cat-file -t vX.Y.Z                   # must say 'commit' (annotated tag deref)
git cat-file -p vX.Y.Z^{} | head -1      # tree sha; cat-file -t on that → tree

# 2. Does the current binary (if any) name the tag?
./bin/<binary> version                    # must print vX.Y.Z, not a date or 'dev'
./bin/<binary> version --json             # two-field probe: both 'version' and 'build' = vX.Y.Z

# 3. Does the repo self-gate version hygiene?
make version-check                        # exits 0 or names the drift
make vuln-check                           # govulncheck; exits 0 or lists vulns
make fmt-check                            # gofmt gate; 0 = clean
```

**Pitfall:** `git tag --verify <tag>` on an annotated tag prints *"cannot verify a non-tag object of type commit"*. That message is harmless — it means the tag object is an annotated tag whose *deref* is a commit, which is exactly what you want. Use `git cat-file -t <tag>` to see the *object* (commit or tag), then `git cat-file -p <tag>^{}` to read the annotated message.

## Artifact identity chain (verify a downloaded release asset)

`scripts/verify-go-release-assets.sh <org/repo> <tag> --expected <full-sha>` already does the download + `SHA256SUMS` + per-asset `go version -m` leg in one run and never executes an asset — run it instead of hand-typing the commands below, which are what stays when the script's assumptions (a `SHA256SUMS` asset, Go-built binaries) do not hold.

```bash
curl -sL -o <asset> <download-url>
sha256sum -c --ignore-missing SHA256SUMS  # exits 0 = checksum matches
go version -m <asset>                     # reads the Go build info embedded in the binary
```

Expected `go version -m` fields:
- `mod ... vX.Y.Z` — matches the tag
- `vcs.revision = <sha>` — matches `git rev-parse vX.Y.Z^{commit}`
- `vcs.modified = false` — must be false for a release asset
- `vcs.time` — commit timestamp

**Re-verify the PUBLISHED bytes instead of rebuilding them.** A post-publication sweep needs no build: download the asset again, check it against `SHA256SUMS`, and read `go version -m` off that download. Four claims fall out of the one download — the digest still matching proves no re-upload replaced the asset since publication; `vcs.revision` names the tagged commit; `vcs.modified=false` proves it was not built from a dirty tree; and the first line's toolchain is the standard library those shipped bytes actually carry, which is the artifact half of any toolchain-floor finding. A local rebuild re-proves the repository, not the artifact: it can be green while the uploaded bytes are stale or were swapped.

**A missing `vcs.*` block is not drift by itself.** A repo whose release driver builds with `-trimpath -ldflags "-s -w -X <pkg>.Version=… -X <pkg>.Commit=…"` and no VCS stamping yields only `path …` and `mod … (devel)` — no `vcs.revision`, no `vcs.modified`. That means "built outside a stamped module", not "built from the wrong tree". Two mechanical causes produce that same `(devel)` shape with no build flag involved, and both are silent:

- **A LINKED git worktree.** `git worktree add` leaves a `.git` FILE, and `go build -buildvcs=true` run there stamps nothing — no `vcs.revision`, no `vcs.modified`, no error — while the identical build in the parent checkout stamps normally. Measure it: `make dist` in a worktree at the tag, then `go version -m <asset> | grep -E 'vcs|mod\s'` prints only `mod … (devel)`. A `ship_check` that asserts only the ldflags version string passes that artifact, so the cut publishes bytes no consumer can tie to the tag. Build the shippable artifact in the canonical checkout or a full `git clone` of the tag, with `DIST_DIR` OUTSIDE the work tree; keep the worktree for upload helpers that merely assert `HEAD`.
- **`DIST_DIR` inside the tree is untracked, and untracked means `vcs.modified=true`.** An ignore rule written `/dist/` does not cover `dist-vX.Y.Z/`, so the documented `make dist DIST_DIR=$(pwd)/dist-vX.Y.Z` stamps its own output directory as a dirty tree. Point `DIST_DIR` at a scratch path for anything provenance-gated.

Both defects are invisible to a version-string smoke, so put the acceptance on the artifact: `go version -m` must name the tag commit with `vcs.modified=false` for EVERY produced asset, and the RED arm is the worktree/in-tree build that yields no `vcs.*` block at all. Probe the stamp the driver actually wrote (see the installer recipe below) before filing a provenance blocker, or two of the three `go version -m` checks above fail on every correctly built asset.

If any of those disagree, the published binary was built from a different tree than the tag (date-stamped binary, dirty tree, pre-tag build). Treat as a **doc/artifact drift blocker** — file a RELEASE-* row, do not re-tag. When a Makefile checksum manifest records repository-relative paths such as `dist/<asset>`, validate it from the manifest's path base (usually the repository root); running `sha256sum -c` from inside `dist/` produces missing-file errors from path resolution, not checksum corruption.

## Proving a shipped asset RUNS when `chmod +x` is gated

`gh release download` lands files mode 0644, and chaining `chmod +x … && ./<asset> --version …` presents the EXEC as part of one line, so the gate refuses the whole line and the artifact is downloaded but never exercised — the record then inherits UNVERIFIED for a check that would have passed. The refusal is about the LINE, not about the mode change: run them as two separate calls and both succeed.

```bash
chmod 755 <asset> <asset2>                  # own call, nothing chained to it
timeout 30 ./<name>-linux-amd64 --version   # own call: version / commit / built / toolchain / platform
```

That banner is the strongest single receipt for an asset whose buildinfo carries no `vcs.*` block: it binds the shipped bytes to the tag version, the abbreviated commit, the build timestamp, the toolchain that compiled them, and the target platform. Compare all five against `git rev-parse <tag>^{commit}` and the cut record; run it for this host's asset only, since the other platforms are covered by `go version -m`. Never re-issue the refused chain in another form.

Prefer the repository's own installer when one exists — it sets the mode and asserts identity as part of its contract:

```bash
D=<scratch>/assets; mkdir -p "$D/repo/download/<tag>" "$D/prefix/bin"
gh release download <tag> --repo <org/repo> --dir "$D" --clobber
( cd "$D" && sha256sum -c SHA256SUMS )        # the real published bytes, not a rebuild
cp "$D"/<asset> "$D"/<asset2> "$D"/SHA256SUMS "$D/repo/download/<tag>/"
sh ./install.sh --version <tag> --dir "$D/prefix/bin" --base-url "file://$D/repo"
```

Mirror the installer's own URL shape (`<base>/download/<tag>/<asset>`) exactly; the point of the local mirror is that the bytes under test are the DOWNLOADED ones. An installer that ends by running the installed binary and printing its version (`<bin> vX.Y.Z-<sha>`) closes three legs in one receipt: installability, checksum verification, and a working entry point. Set `--dir` to a scratch prefix so nothing lands on the operator's PATH.

When the driver stamps with `-X` ldflags and skips VCS stamping, the matching read-only provenance probe is the embedded string — `-s -w` strips symbols but not `.rodata`:

```bash
strings -a <asset> | grep -c '<full-40-char-commit>'   # 1 = bound to that commit
strings -a <asset> | grep -c '<tag>'                   # 1 = bound to that tag
```

Run it over every platform binary in the set, not just the one for this host: a subset matrix that stamps only some targets is invisible otherwise.

## Behavioural smoke: exercise the headline feature, and attribute a miss to the FIXTURE

`--version` plus a checksum proves identity; it proves nothing about the behaviour the release is FOR.
After the digest and version legs, run the SHIPPED binary against a throwaway fixture in scratch and
exercise the one behaviour the release notes advertise — a new view/flag/subcommand, on input that
contains both the case it must include and the case it must exclude. Keep the fixture, the exact
command, and the observed result in the artifact-verify log beside the digest; a PASS line with no
observable is unreproducible and a reviewer will re-run it against different data.

**A smoke miss is a fixture hypothesis until you have read the predicate.** A fixture encodes a guess
about how the tool decides; when the output disagrees with the guess, grep the implementation for the
predicate and read it before writing any defect row. The commonest cause is a near-miss field name —
a fixture that set a *date* field while the reader tests a *boolean* flag of similar name produces an
"include" the report calls a bug that does not exist, and the manufactured row costs a downstream lane
a dispatch and the release a red mark. Order: run, disagree, locate the predicate
(`grep -rn 'func .*IsDeferred'`), read it, correct the fixture, re-run — and only then decide. A
disagreement that survives a provably-correct fixture is a product finding, filed with the fixture,
the command, and observed-vs-expected in its acceptance criteria.

Treat the smoke as part of the release record, not an extra: a cut verified only by `--version` reports
"published" for a binary whose new feature may be inert, which is the same class of claim as a commit
message asserting a board closeout.

## Artifact toolchain binding (who compiled the shipped bytes)

`go version -m` reports the toolchain that built the binary, and that toolchain carries its own
standard-library advisories. On a repo whose release driver runs the dist target locally
(`make dist` inside `scripts/release.sh`), the shipped bytes inherit whatever Go the cutter has
installed, so bind the artifact to its compiler explicitly:

```bash
make dist DIST_DIR=<unique-scratch> > <log> 2>&1; rc=$?   # bare rc, never through a pipe
go version -m <scratch>/<name>-linux-amd64/<bin> | head -1  # go1.26.5 … <- the shipped stdlib
govulncheck ./... 2>&1 | grep -E 'Standard library|Module:' # which advisories live where
```

- A floating CI toolchain (`GO_VERSION: "1.26"`, image `golang:1.26`) resolves to the newest patch
  at run time, so a green pipeline says nothing about the bytes the dist target produced on the
  operator's box. CI green and artifact-current are two independent claims.
- Split findings by WHERE the fix lands: a module advisory (`golang.org/x/net@v0.60.0` fixed at
  `v0.62.0`) is a dependency row; a standard-library advisory (fix expressed as a Go patch version)
  is a toolchain-floor row against the build path. Acceptance criteria for the latter must prove
  the refusal — run the gate under a pinned older toolchain (`GOTOOLCHAIN=go1.26.5`) and show a
  non-zero exit plus the named message — and prove the positive under a new enough one
  (`go version -m` on the built binary naming the floor or newer).
- Report the split. "N vulnerabilities" without module-versus-stdlib attribution cannot be
  dispatched to anyone, and rows built from it will be closed against the wrong fix.
- A dist probe is artifact-strategy evidence only while the version stamp and vulnerable toolchain
  are still in place: say so in the sweep so a later reader does not mistake the tarballs for
  publishable assets.

### Enforcing the floor (the fix shape)

Diagnosis files the row; this is what the fix must contain, and it is the same shape in every Go repo
that ships compiled artifacts:

1. **One constant plus a PREREQUISITE target.** `<PROG>_MIN_VERSION ?= X.Y.Z` and a `check-toolchain`
   target that the artifact target depends on (`dist: check-toolchain`). Make runs each recipe line in
   its own shell, so an inlined check covers only itself; a prerequisite runs before the build loop and
   a failure cannot leave half an artifact matrix.
2. **Measure the ACTIVE toolchain, not the host default** — `go env GOVERSION` honours
   `GOTOOLCHAIN=<version>`, which is what lets one machine exercise both arms.
3. **Compare numerically per component, accepting `>=` the floor.** String compare ranks `1.26.9` above
   `1.26.10`. Avoid GNU-only `sort -V`: where sort rejects it the substitution is empty, the gate fails
   closed, and the operator reads a floor violation on a toolchain that is actually fine. Use awk /
   integer arithmetic, or detect the missing capability and say so in the message.
4. **Mirror the same constant in the release driver's preflight**, before it writes any version surface;
   a dry run should WARN rather than die so the plan still prints on any host.
5. **Pin the CI image to an explicit patch** (`GO_VERSION: "1.26.10"`, never `"1.26"`) in the same
   change, and confirm the image tag exists (registry lookup) before pushing — the first pipeline then
   proves it pulls.
6. **Document the floor beside the other release requirements** with the reason (the advisory), the
   enforcement point, and the `go version -m` proof command.
7. **Acceptance criteria prove BOTH arms:** RED under the older pinned toolchain (non-zero exit naming
   the floor, zero artifacts written) and GREEN under the floor (exit 0, `sha256sum -c` clean,
   `go version -m` naming the floor or newer). Phrase the floor as `>= X.Y.Z`; an exact-string criterion
   reds a correct tree on the next toolchain bump.
8. A floor/CI/docs change stages no `.go` files, so a diff-scoped guard prints
   `DEGRADED PASS (… No Go files staged)`. Quote it for what it proves and run the suite yourself — it
   is not a full battery.

## The version stamp can be silently inert (const vs var, and goreleaser signing)

A build that succeeds proves nothing about whether the version it reports is the version being released.
Two failure modes are common enough to probe on every sweep:

**`-X` only rewrites string VARIABLES, and a symbol that does not EXIST fails just as silently.** If the
CLI declares its default inside a `const (` block (`version = "0.1.0"`), the linker discards
`-X main.version=<tag>` without a warning, so every artifact reports the hard-coded value forever. Do not
assume `main.commit`/`main.date` exist to carry the rest: grep each symbol
(`grep -nE '^\s*(var|const)\b|version|commit|date' cmd/<bin>/main.go`) before trusting the ldflags,
because two of the three are routinely dead and the artifact then has no provenance at all. The tell is a
banner reading `(build dev)` from a build that passed `-X …=<sha>`: that stamp usually comes from
`debug.ReadBuildInfo().vcs.revision`, which is empty inside packaged builds that strip VCS stamping, so it
also breaks every staleness tool that compares a deployed binary to a release tag. Fix shape: package-level
`var version, commit, date string`, prefer the flag, fall back to build info, then `dev` — plus a test that
builds with `-X main.version=<x>` and asserts the banner, since no source-tree test can see a link-time
stamp disappear. Prove it both ways:

```bash
go build -ldflags "-X main.version=9.9.9 -X main.commit=<sha>" -o /tmp/v ./cmd/<bin>
/tmp/v version        # must print v9.9.9; prints the default => const, or a wrongly-scoped symbol
grep -n -B3 'version = "' cmd/<bin>/main.go   # is that line inside `const (` or `var (`?
```

Then prove it through the repo's own toolchain in snapshot mode (`goreleaser release --snapshot --clean
--skip=publish`, or the dist target) and run the binary out of the produced archive — that is the receipt
that binds the defect to the release path rather than to your hand-typed command. Bump blast radius also
lands in the suite: grep the test tree for the outgoing version string (`grep -rn '0\.1\.0' --include='*_test.go' .`)
before promising a bump, because every asserted banner/status line must move with it.

**goreleaser's `signs:` block defaults to `cmd: gpg`.** A cosign-shaped stanza written without `cmd: cosign`
(`args: [sign-blob, --key=env://COSIGN_PRIVATE_KEY, --signature=${signature}, ${artifact}]`) is executed as
`gpg sign-blob --key=…`, which fails with `gpg: '<arg>' is not considered an option` / `no command supplied`
and aborts the release AFTER the builds and archives, i.e. nothing is ever uploaded. Read the failure line
for `cmd=gpg` and fix the stanza (v2 shape: `cmd: cosign`, `signature: ${signature}`, `certificate:`) — a
missing secret store is a second, independent gap, so a repo showing both (0 Actions secrets AND the bad
stanza) does not become releasable by provisioning secrets alone. Pin the workflow's own install of the
packager in the same change (`go install …@latest` floats, so the config a snapshot run just validated is
unproven for the next tag). On a repo that has never cut a release, that snapshot run IS the sweep's
artifact receipt: record what it produced — binaries, archive formats per platform, checksum manifest,
archive contents — and the exact step it died at, so the finding reads "the build half works, publishing
fails here" instead of "the pipeline looks broken".

**`before:` hooks can dirty the tree mid-build.** `before.hooks: [go mod tidy, go generate ./...]` runs
between checkout and compile, so a hook that rewrites a tracked file makes the produced binary stamp
`vcs.modified=true` even though the source tree was clean when the command started. Check
`git status --porcelain` after a snapshot run: when only `dist/` is untracked the build is clean, when a
hook touched a tracked path, the artifact fails a `vcs.modified=false` gate and the fix (pin the hook, or
build from a path that does not run it) belongs in the acceptance criteria, not in a waived gate.

## Stale install detection

When the operator has a binary on `$PATH` (e.g. `~/.local/bin/<tool>`):

```bash
go version -m ~/.local/bin/<tool>
file ~/.local/bin/<tool>
stat -c '%Y' ~/.local/bin/<tool> | xargs -I{} date -d @{}
```

Red flags:
- `vcs.modified = true` — dirty build
- `version --json` returns `"dev"` — from-HEAD build cannot name its own revision
- `mtime` predates the newest merge that the binary should carry
- `go version -m` reports an older toolchain (e.g. `go1.26.5` vs expected `go1.26.6`)

Containment check: does the owning foreman's skill mandate using `./bin/<tool>` instead of the PATH copy? If yes, the stale binary is an operator risk, not a board-write risk — file a P2 blocker row and do not manually refresh the binary in the same tick (two writers building simultaneously into the same live workdir is how dirty-mtime confusion recurs).

### Enumerate EVERY installed copy, then let the repo's own gate fingerprint them

One PATH copy is never the whole picture. `which -a <tool>` plus a direct probe of `~/.local/bin`, `$(go env GOPATH)/bin`, and any package-manager prefix finds the copies that actually shadow each other, and they fail in DIFFERENT shapes: an old release reports a stale semver (`vX.(Y-1).Z`) with a clean `vcs.modified=false` and an ancestor revision, while a `go install`-from-HEAD copy reports `version dev` with `mod <module> v0.0.0-<ts>-<sha>` and a revision that is NOT an ancestor of the tag. Both belong in one row — the remedy is the same reinstall — but the reasoning must name each copy's distinct fingerprint, or a reader assumes the release is fine and only one binary is old.

Do not hand-diff these. When the repo ships an install-drift target (`make install-check RELEASE_TAG=<tag>`, `scripts/install-check.sh`), run it from a clean detached worktree at the fetched tip and let it compare version, embedded module version, `vcs.modified`, and revision ancestry in one arm:

```bash
W=$(mktemp -d)/wt; git -C <repo> worktree add --detach "$W" origin/main
make -C "$W" install-check RELEASE_TAG=<tag> > <log> 2>&1; echo rc=$?   # bare rc, never piped
```

A non-zero exit with `FAIL version: … prints '<old>' but the release is <tag>` / `FAIL module version: …` / `DRIFT detected` is a complete finding: quote those lines verbatim in the row's reasoning. Do not re-run the check after reinstalling and call the row closed — closing is the foreman's call, and a tick that both measures and mutates cannot be re-verified.

Acceptance criteria for the follow-up row prove the FIX, not the gate:

- reinstall from the published assets only (checksum equal to the release `SHA256SUMS` entry), and state that a rebuild from HEAD does not satisfy it even though it may report a plausible version;
- per copy: `version` prints `v<tag>`, `go version -m` shows `mod <module> v<tag>`, `vcs.revision = <tag commit>`, `vcs.modified=false`, and `sha256sum` equals the published digest;
- before/after probe output pasted for each path, so a reader sees which copy moved;
- an explicit prohibition on editing `PATH`, shell profiles, symlink targets, or other host config to satisfy the gate — the gate measures the copies, and reordering lookup order makes it green while the stale binary stays installed.

This stays a DEPLOY row (P2), never a release blocker: the published artifact verified independently, so the cut stands and the tick reports NO CUT alongside the drift row.

## Tag object vs Release object: both must exist

```bash
git ls-remote --tags origin | grep 'refs/tags/vX.Y.Z$'   # tag must be there
gh release list --repo <org/repo> --json tagName,isLatest  # Release object must exist
gh release view vX.Y.Z --repo <org/repo>                   # must show assets
```

A tag without a Release object is a **gap in the release surface**. The tag is fine; the Release page, notes, and assets are missing. Do not re-tag — the consumer path (tag-pinned docs, go get) can work while the release page is blank. File a RELEASE-* blocker naming the gap.

**Pitfall:** `gh release view --json tagName,isLatest` fails on `gh` versions that do not support `isLatest`. Use `tagName` and `assets` (universally available) instead of `isLatest`.

**Do not hand-create the Release when a tag push publishes it.** Before choosing a publish path, grep the workflows for a tag trigger that ends in a release step (`grep -rn 'tags:' .github/workflows/`, then read that job for `gh release create` / a release action). On such a repo, pushing the annotated tag IS the cut: the workflow builds the platform matrix and creates the Release with its assets. Running `gh release create` yourself then either collides with the existing Release or races the workflow and leaves a half-written asset set. Sequence: push the tag → poll the run whose `headBranch` equals the tag → `gh release view <tag> --json tagName,isDraft,isPrerelease,publishedAt,assets` → compare the asset names against the workflow's matrix and COUNT them, because one failed matrix leg leaves a Release that otherwise looks complete. Only when no tag-triggered publisher exists do you create the Release yourself after the gates, and either way the report says which path was taken.

A release published by the repo's own workflow also dates the cut: record `publishedAt` in the row and in the report instead of the tag-push timestamp, since the workflow can finish minutes later and a reader comparing the two will otherwise read them as drift.

## Publisher provenance: a zero-step publish job means the assets were built LOCALLY

Read the release workflow run at the tag commit before crediting the forge with the build:

```bash
gh run view <run-id> --json conclusion,jobs \
  --jq '{conclusion, jobs: [.jobs[]|{name, conclusion, steps: (.steps|length), startedAt}]}'
```

`conclusion: failure` with a publish job whose `steps` is `0`, started and updated within seconds of each other, is a queue/billing-level refusal — nothing compiled, nothing uploaded. When the Release object's assets then appear about a minute AFTER that dead job, the payloads came from an operator's local `goreleaser`/`make dist` run: the release carries no forge-side build receipt, and a config with no `signs:` block publishes no signature asset, so nothing afterwards binds those bytes to the tag commit.

That is a `RELEASE-*` row, never a re-tag: backfill the empty changelog section for that version, curate the release body, and state the local-build provenance explicitly in it. Do not edit the published body to imply hosted provenance, and never move the tag.

Read the body for what the notes filter admitted, too. A release body that is a machine commit dump dominated by bookkeeping subjects (`board:`, `settle:`, `ops:`, `chore:`) means the changelog `filters.exclude` list omits the repository's actual bookkeeping types; the row's acceptance must widen that list AND prove the widening with a dry run over the release range showing zero such lines, so the next cut cannot regress it.

A digest match against the release's own checksum asset proves the bytes were not swapped after publication. It cannot prove who built them — state which of the two claims each receipt supports instead of reporting "checksums verified" as if it settled provenance.

## Makefile release gate patterns common in this fleet

```makefile
# BT-030 guard: refuse date-stamped release when repo HAS tags
release: test
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1 && [ -n "$$(git tag)" ]; then \
		if ! printf '%s' '$(VERSION)' | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$$'; then \
			echo "refusing to release: VERSION is not a vX.Y.Z tag" >&2; exit 1; \
		fi; \
	fi
```

Three enforcement surfaces for each gate (Makefile + CI + `go test ./...`):
- `make fmt-check` → `go test -run TestGofmt ./internal/fmtcheck`
- `make version-check` → `go test -run TestVersioncheck ./internal/versioncheck`
- `make vuln-check` → `go test -run TestVulncheck ./internal/vulncheck`

The tri-gate (fmt + version + vuln) must all pass before a cut. The CI workflow and `go test ./...` run the same check-only Go packages, so a local pass before a tag push is a strong CI predictor.

## `govulncheck` is a live-database probe, not a tree receipt

Read the exit code bare and unpiped — `timeout 420 govulncheck ./... > <log> 2>&1; echo rc=$?` — because a pipe reports the last stage's status. A non-zero exit (3 while findings exist in current releases) IS the finding, not a tool failure; 0 is the only clean receipt.

The advisory database is remote and live, so this gate is exempt from the zero-material-path carry rule: a byte-identical tree can report a NEW advisory published after the previous pass, and an exit-0 carried from an earlier pass is not evidence about today's candidate. Re-run it every pass and quote three values per finding — the advisory id, the affected symbol with its version (`net/http@go1.26.10`), and the `Fixed in:` version — because a row built from less cannot be closed against the right fix.

A `Fixed in: <symbol>@<stdlib patch version>` line means the fix is a TOOLCHAIN FLOOR, not a dependency bump: the `toolchain` line in `go.mod`, the CI image pin, and the `check-toolchain` prerequisite must all move together. Until that lands, the release lane records NO-CUT with the triple above; a reachable advisory in the shipped HTTP stack of an HTTP service is a hard blocker and only an explicit owner override licenses tagging through it.

### A stdlib red must name the right Go, or it is the SCANNER talking

`govulncheck` classifies the standard library of whatever Go the scan resolves, and that is not
always the candidate's. `go run golang.org/x/vuln/cmd/govulncheck@latest ./...` builds the scanner
from its own module graph, so its reported stdlib can lag the module's declared `toolchain`/CI image
and list advisories against a patch the candidate never ships — while the same tree scanned by the
pinned scanner and by `-mode=binary` on the built artifact is clean. Before recording a toolchain
floor, cross-check three values: the Go version the scan names, `go env GOVERSION` / `go.mod`'s
`toolchain` line, and the CI image pin. When the scanner's Go is older than the candidate's, the
red is the scanner's, not the candidate's — re-scan with a pinned scanner version and with
`-mode=binary <built-artifact>`, quote all three modes, and state which one you trust. Record the
scanner version with every cited verdict; `govulncheck` has no `-goversion` flag (it errors
`flag provided but not defined`), so the pin is the only way to fix the resolved stdlib.

## Readiness decision: "no release warranted" vs "blocked"

| Situation | Action |
|-----------|--------|
| CI green, artifacts verified, but zero user-facing commits since last tag | Report "no release warranted" — do not file a RELEASE-cut row |
| CI green, artifacts stale (doc/artifact drift class) | File RELEASE-cut row; cut from clean clone of the tag commit |
| CI red on the tag commit | NO-GO, full stop — do not release without explicit user override |
| Stale install, no install target in Makefile | File P2 blocker row; do not manually refresh the binary mid-tick |
| Tag exists, Release object missing | File RELEASE-* blocker; do not re-tag |
| CHANGELOG claims a release that has no tag/Release | File blocker; treat changelog heading as CLAIM not RECEIPT |

## Open-pending P2s that are NOT release-blocking

A P2 that is a CLI contract decision (exit code semantics, usage-line accuracy) or a
contained stale install (foreman skill uses a fresh binary) does not block a release
cut. Record them as open blockers in the report but do not block the release on
their account. The next release tick should confirm they are resolved before the
following cut.
