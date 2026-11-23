# Python package release patterns

Target audience: releng satellite sweeps on Python repos using `gh release create`,
`python -m build`, `twine upload`, and pyproject.toml.

## Version triplication

A Python release must agree on version in THREE places before the tag push:

1. `pyproject.toml` → `[project] version = "X.Y.Z"` (or dynamic from file)
2. `src/<pkg>/__init__.py` → `__version__ = "X.Y.Z"`
3. `CHANGELOG.md` → numeric heading `## [X.Y.Z] - YYYY-MM-DD`

If any of these disagree, the CI gate that checks `python -m build` metadata
against the changelog will fail on the tag commit itself.

Two further surfaces are easy to miss and are usually checked by the repo's own
docs-drift script rather than by pytest:

4. the lock's own package stanza (`[[package]] name = "<pkg>"` → `version = …`)
5. current-release stamps in the README release banner, docs/onboarding.md, and any
   spec that says "the package now declares X.Y.Z"

## Version-prep surface on a uv-managed repo

Order matters, and each step has a receipt:

```bash
# 1. declare the version (single line in the [project] table)
# 2. the lock records the project's own version as a package stanza — edit that
#    ONE line and verify the lock instead of re-resolving it
uv lock --check                     # exit 0 + "Resolved N packages" == lock agrees
# 3. reinstall the editable dist BEFORE asserting the CLI version
VIRTUAL_ENV=<repo>/.venv UV_LINK_MODE=copy uv pip install -e . --no-deps
.venv/bin/<entrypoint> --version    # must print the NEW version
# 4. give every stamp its own edit, then let the repo's checkers find the rest
python scripts/check_docs_drift.py  # banner version + live test counts
```

Rules that cost a pass when ignored:

- **The lock's own stanza is a version surface, and a SUITE TEST may be its gate.** Refresh
  it by hand-editing the one stanza OR by `uv lock`; `uv lock --check` proves the invariant
  either way, and a hand edit that leaves `--check` red means the lock was genuinely stale.
  Where the repo asserts single-source-of-truth in a test rather than in a docs-drift script,
  that test compares `pyproject.toml`, `__init__.py`, `CHANGELOG.md` AND the lock stanza, so it
  fails on the bump alone until the lock carries the new version — read that failure as the
  repo telling you the prep commit is incomplete, not as a defect to work around or a
  criterion to soften.
- **`--no-sync` runs the PREVIOUS install.** After a version bump the editable dist still
  carries the old metadata, so `pytest --no-sync` reports the version test red while the tree
  is correct; sync the venv (`uv sync --extra dev`) before the suite, or you spend a cycle
  debugging a code path that has nothing to do with the bump.
- **A uv-built venv may have no pip** (`No module named pip`). Use `uv pip install -e .
  --no-deps` with `VIRTUAL_ENV` pointed at the repo venv; without the reinstall the
  installed dist metadata still carries the PREVIOUS version, so the CLI prints it, the
  version test fails locally, and CI (which installs fresh) passes — the classic
  "local red, remote green" inversion that wastes a gate cycle.
- **Promote the `[Unreleased]` body AND backfill shipped entries that never got one.**
  Run the conventional census over the range and diff it against the entries being
  promoted: features and fixes that landed without a changelog line are the ones users
  file bugs about after the release, and the census is the only cheap list of them.
- **Promote only what you can BIND to a commit in the range.** A bullet that has sat under
  `[Unreleased]` through several releases, citing no sha and describing no landed change in
  `<last-tag>..<candidate>`, is provenance debt: promoting it stamps a claim onto a release
  that did not make it. Carry it as a footnoted "not claimed in this release" line, file a
  `RELEASE-*` row with the check (`git log --oneline <last-tag>..HEAD -- <paths the bullet
  names>`), and leave `[Unreleased]` still holding it until someone binds or deletes it.
  Verify the binding bullet by bullet, not for the section: three honest entries can hide a
  fourth that is years stale.
- **Find the stamps with the checker, not by hand.** A drift script that compares the
  banner version against pyproject and the count claims against a live collection reports
  every stale surface (and the file:line) in one run; hand-grepping for the old number
  misses prose forms like "the package now declares X.Y.Z".

## CHANGELOG promotion pattern

```bash
# Promote the body under [Unreleased] to [X.Y.Z]
# Then reopen an empty Unreleased section
```

**Pitfall:** deleting the `[Unreleased]` section entirely causes changelog drift
checks to fail when the next commit lands with a fresh `[Unreleased]` body.
Always re-open the empty section after promotion.

## CI wiring pattern (pyproject)

```yaml
- name: Build wheel
  run: python -m build

- name: Check metadata
  run: python -m twine check dist/*

- name: Publish to PyPI
  if: github.ref_type == 'tag'
  env:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

## Dogfood SHIPPABLE blocker (same doctrine as JS/TS repos)

A dogfood commit whose subject reads `dogfood: <repo> SHIPPABLE — N P1 + M P1`
acknowledges P1s remain open on untouched surfaces. Treat every named P1 as a
RELEASE-* blocker until the owning board rows are closed. The SHIPPABLE label is
a readiness flag, not a waiver.

## Publish leg: read the workflow, do not race it

A tag-triggered publish workflow is the sole publisher. Read it before the cut and
note what it already asserts, because those steps ARE part of the release gate:

tag-to-pyproject parity, an already-published short-circuit, wheel metadata and
console-script version, a fresh-venv install of the built wheel, the upload, and the
Release object. A green tag run therefore certifies more than "files uploaded" — cite
its per-job state instead of re-deriving those checks by hand. Never create the Release
or upload assets manually alongside it: whichever lands first makes the other fail on
existing asset names, permanently.

**Classify the trigger before proposing a tag.** `on: push: tags: ['v*']` makes the tag ref the publish switch: one tag push runs the parity asserts, builds, uploads to the index, and creates the Release. In a readiness sweep that makes the tag itself an irreversible act, so say it precisely — "no tag exists, therefore nothing was published" is true, while "we could tag now to prepare" is false. Record the trigger in the tooling inventory so no later lane treats tagging as bookkeeping, and list what the workflow asserts (tag vs `pyproject` version, already-published short-circuit) as gates that will fail the tag run, not conveniences.

`generate_release_notes: true` produces a placeholder body from PR titles. That is
normal for this pattern; the durable notes live in the committed CHANGELOG, so point
the record there rather than treating an empty Release page as a failed release.

## Build the shipped artifact from an EXPORTED tag tree

The published bytes must derive from the tagged commit and nothing else. A prep worktree can carry unstaged edits, a stray `build/`, and no venv; an export has none of that:

```bash
git archive <tag-or-prep-sha> | tar -x -C $S/export-<tag>
cd /tmp && <repo-venv>/bin/python -m build $S/export-<tag> --outdir $S/dist-<tag>
```

Run it from a NEUTRAL cwd (`/tmp`) with the repo's own interpreter: a `build/` directory in the cwd shadows the `build` module, and a detached worktree usually has no venv, so a bare `python -m build` there fails on imports rather than on the tree. Keep `--outdir` outside the export so a rebuild cannot ingest the previous artifact. Export again at the TAG SHA after tagging — the prep tree and the tag are different commits the moment anything lands in between, and `python -m build <srcdir>` takes the directory, never the checkout you happen to be standing in.

## Published-artifact receipt (independent of CI)

After the tag run is green, prove the INDEX serves the version and its entry point works.
One command pair, no registry API:

```bash
uv venv /tmp/verify-X.Y.Z --python 3.11
VIRTUAL_ENV=/tmp/verify-X.Y.Z UV_LINK_MODE=copy uv pip install -q '<pkg>==X.Y.Z'
/tmp/verify-X.Y.Z/bin/<entrypoint> --version    # expect "<pkg> X.Y.Z"
```

This is strictly better than polling the registry JSON: it exercises resolution,
metadata, and the console script in one leg, and it needs no `curl` pipeline (which an
unattended surface can gate-block, leaving the leg unverified for no good reason).

## Install verification — from the ARTIFACT, not the source tree

`pip install .` on a clean virtualenv proves the source tree resolves; it proves nothing
about what the release ships. A wheel that imports cleanly can still deliver a library
instead of a tool, and can omit runtime helpers that the code loads by path. Verify the
CONSTRUCTED artifact:

```bash
uv build --out-dir /tmp/dist
gh release download <tag>            # or install /tmp/dist/*.whl directly
python3 -m venv .v && .v/bin/pip install ./<pkg>-X.Y.Z-py3-none-any.whl
```

Then assert all four, because each fails independently:

1. **The console command exists.** `ls .v/bin` and `importlib.metadata.distribution(<pkg>).entry_points`.
   No `[project.scripts]` in pyproject means the wheel ships NO executable — the documented
   `pkg --version` invocation is unavailable to every pip user no matter what the README says.
2. **Path-loaded runtime helpers are inside the artifact.** List the archive and grep for them:
   `python -c "import zipfile;print(zipfile.ZipFile(p).namelist())"` and `tar tzf <sdist>`.
   Enforcement layers, loaders, shell/launcher scripts and `standalone/` trees are commonly
   excluded by default include rules while their Python modules ship — the artifact then
   references files that are not there.
3. **Advertised capabilities are ACTIVE at import.** Import the package from the installed
   wheel and read stderr for "<tier> not applied" / "falling back" warnings. A release note
   that headlines a feature the artifact silently disables is a false claim even when every
   gate and test is green, because the tests ran against the source tree.
4. **Version and provenance from the installed metadata**, not `pyproject.toml`:
   `importlib.metadata.version(<pkg>)`.

5. **The import root is the one the docs use.** A repo whose code lives in `src/` but
   whose `pyproject.toml` declares no `[tool.setuptools] package-dir`/`packages` builds a
   wheel that flattens the CONTAINER away: `src/*` lands directly in `site-packages`, so a
   bare `__init__.py`, `core/`, `main.py` sit at top level, `find_spec("src")` is None, and
   every documented `python -m src.<mod>` invocation fails from the installed artifact
   while still working in the checkout. Diagnose from the wheel, never from grep:
   `unzip -l <whl> | head -20`, then `cat <dist-info>/top_level.txt` — generic names like
   `core`, `main`, `db` there ARE the flattening signature — and check that
   `<dist-info>/entry_points.txt` exists at all. The fix is packaging config plus a docs
   update in one commit; it is not a reason to re-tag the artifact you already shipped.

When the surface REFUSES the install leg — venv creation or package installation gated on this
host — that leg is UNVERIFIED: not passed, and not a reason to skip the cut. Do not retry it in
another shape and do not route around the gate. Name it in the notes and the row as one
unverified leg, and cite what the archive itself proves in its place (`unzip -l <whl>`,
`<dist-info>/top_level.txt`, `src/<pkg>/__init__.py` present in the listing). That is LAYOUT
evidence: it proves the packaging fix shipped and says nothing about import success or entry
points. State both halves, because a reader shown only the archive listing assumes the runtime
leg ran.

File the gap when the artifact is hollow. Installing successfully is not shipping.

## Deployed-binary staleness is its own finding

## Two-arm probe: prove the fix before the notes claim it

A fix commit message states intent; the notes need measured behavior. When the release's
headline is a fix, build BOTH artifacts — the last published version and the candidate —
and run the same probe against each, under an environment HOSTILE to the fix's assumption
(shadowed interpreter, missing helper, unset variable):

```bash
uv build --out-dir $S/dist-old            # run from a worktree at the previous tag
uv build --out-dir $S/dist-new            # run from the tag worktree
for v in old new; do
  uv venv $S/v-$v >/dev/null && VIRTUAL_ENV=$S/v-$v uv pip install -q $S/dist-$v/*.whl
done
mkdir -p $S/fakebin && printf '#!/bin/sh\nexit 127\n' > $S/fakebin/python3 && chmod +x $S/fakebin/python3
PATH=$S/fakebin:$PATH $S/v-old/bin/<entrypoint> <args>; echo "old rc=$?"
PATH=$S/fakebin:$PATH $S/v-new/bin/<entrypoint> <args>; echo "new rc=$?"
PATH=<normal> $S/v-new/bin/<entrypoint> <args>; echo "control rc=$?"   # proves the probe is sound
```

Record both exit codes and whether the advertised verdict/JSON line appeared. A partial
fix shows up here as "new arm improved but still failed", which no green CI or commit
message reveals.

If the probe contradicts the claim, publish anyway when the new artifact strictly improves
on the old one, and disclose it in the notes: a `## Known residual (measured, not fixed
here)` section with the remaining hardcoded `file:line`, both arms' exit codes, and the
follow-up row. Cite lines that exist in the tagged tree — a judge reading the notes will
re-derive the residual claim and fail notes that overstate it.

Never name an acceptance surface you have not executed. `pkg.__version__` is not universal;
if the package defines no such attribute, the correct check is
`importlib.metadata.version("<pkg>")` plus running the console script.

## Hand publish when the workflow cannot publish

When the repo's publisher dies on a permissions defect (the Actions token lacking
`contents: write`) rather than on the tree, and the repo documents a manual fallback, that
fallback is the sanctioned path — confirm the local credential can actually push
(`gh api repos/<org>/<repo> --jq .permissions.push`), publish once, and disclose the failed
workflow runs by id instead of calling the release pipeline green.

```bash
uv build --out-dir $S/dist-<tag>                       # from the immutable tag worktree
sha256sum $S/dist-<tag>/* > $S/dist-<tag>/SHA256SUMS
gh release create <tag> --verify-tag --title "<name>" --notes-file <notes.md> \
  $S/dist-<tag>/* $S/dist-<tag>/SHA256SUMS
```

Verify read-only into a FRESH timestamped directory (`gh release download <tag> --dir
$S/verify-$(date +%s)`; `sha256sum -c SHA256SUMS`) — never open the line with `rm -rf`, the
unattended gate refuses the whole command and the leg is never verified.

Record the publication as a tracked artifact beside the notes (`docs/releases/<tag>-published.json`):
release id, tag, url, `draft`/`prerelease`, created/published timestamps, publisher login,
the publish path used and why, tagged commit SHA, tag-SHA CI run id, the BLOCKED workflow
run ids, `body_sha256` + `body_bytes` of the notes file, and every asset's size and sha256.
That file is what makes the next pass able to prove the release without re-deriving it.

## Deployed-binary staleness is its own finding

A pipx/`~/.local/bin` install lagging the index is checkable without running the binary:
`ls -d ~/.local/share/pipx/venvs/<pkg>/lib/python*/site-packages/<pkg>-*.dist-info` and read
`Version:` from its `METADATA`. Record it as STALE with both numbers (installed vs index),
keep it as its own row so it is dispatchable, and say explicitly that it does not block a
cut — otherwise the release row carries a deploy defect it can never close.
