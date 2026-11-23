# Release-surface inventory and evidence-path policy

Two preflights that decide whether a cut is ONE cycle or three, and whether the durable
record survives the tick.

## 1. Inventory every surface that carries the current tag

The repo's own version gate is evidence about the surfaces it PARSES, never about the
surfaces that exist. A gate that reads the release doc (a pin line plus download URLs)
leaves duplicate pins in prose, in Makefile defaults and in CODE untouched — and the
code pin is the one that reddens the suite after a prep commit the documented procedure
called complete.

Run this before composing the prep commit, with the tag currently in the tree (not the
one you are about to cut):

```bash
git grep -n 'v<CURRENT_TAG>' -- ':!vendor' ':!dist' ':!*.lock' ':!*.sum'
```

Classify every hit into one of three shapes and act per shape:

| shape | example | action in the prep |
|---|---|---|
| gated doc surface | the pin line, the `/releases/download/<tag>/` install URLs | move it; the gate proves it |
| ungated doc prose | "the published vX asset rejects this flag", an install-identity sentence, the cut procedure's own example tag | move the ones the release-being-cut makes false; file the rest as doc-staleness rows, do not sweep the whole file into the prep |
| code/test literal | a test asserting `strings.Contains(readme, "Current release: **vX.Y.Z**")`, a fixture, a golden file | move it in the SAME prep commit — this is the one no gate watches |

Also read the build driver's default version resolution (`VERSION ?= $(shell git describe
--tags --abbrev=0 ...)`): after the tag exists it resolves to the tag you just cut, so a
later offline build silently reproduces the previous release identity unless VERSION is
passed explicitly.

Why the code literal matters beyond one red run: it makes the documented procedure
untrue. A worker following the release doc step for step produces a prep commit that
passes the doc's own gate and then fails CI, so the next pass trusts a procedure that
does not work. Fix the literal for this cut AND file the de-duplication as its own row:
the assertion must derive the tag from the repo's version-check package instead of
hardcoding it, with a red arm proving it still fails when the pin drifts.

Budgeting: a red prep commit costs a second CI cycle before the tag, so the grep is part
of step one. When the suite is red only because of the literal, the fix-forward commit is
the tag target and the red commit is never tagged — say so in the record, because a
reader seeing two prep commits otherwise assumes the first was sloppy.

Reading the failure: a coverage target that redirects the suite (`go test ./... -short
>/dev/null && ...`) reports nothing but `make: *** [Makefile:NN: cover-check] Error 1`.
Do not re-run the target to learn more — read the failing test NAME out of the hosted job
log (`gh api repos/<org>/<repo>/actions/jobs/<job-id>/logs`) and rerun that one package
locally.

**Run the gate against the PUBLISHED tag as a control before attributing the red.** A
hygiene gate that exits non-zero for the proposed tag and 0 for the tag already in the
tree proves the SURFACES are stale and the gate is sound — a different finding from "the
gate is broken", and a different row. Capture both exit statuses by redirection and quote
the pair:

```bash
make version-check VERSION_TAG=v<proposed> > out.new 2>&1; echo "proposed rc=$?"
make version-check VERSION_TAG=v<published> > out.old 2>&1; echo "published rc=$?"
```

proposed non-zero + published zero = stale surfaces, owned by the version-prep row. Both
non-zero = the gate itself is red and blocks any cut until it is repaired, whatever the
surfaces say. Cheap, and it stops the next pass from filing a gate defect against a gate
that is doing exactly its job.

## 1a. An installer's default version is an ARTIFACT SELECTOR, not a label

A version constant inside an install/bootstrap script is not cosmetic: it chooses which
published artifact gets fetched. Trace the variable to the URL and filename it builds
before judging the surface — the tag string alone tells you nothing about impact.

```bash
grep -n -E 'VERSION|_TAG' install.sh            # the default and every read of it
# then follow each use to the download URL / asset filename it constructs
```

Rules:

- Compare the default against the NEWEST published tag, not against the changelog. A
default that lags while the tree is current is the defect even when every manifest is
right.
- Order the selector bump against PUBLISH, decided by what the installer does when the named
  artifact is missing. If it falls back (a mirror, a lazily resolved download), bump it in the
  version-prep commit and let the release land behind it. If it hard-fails — `curl ... || exit 1`
  on the release download, or a mandatory `SHA256SUMS` — a prep-time bump turns every
  release-mode install into a hard 404 for a version that does not exist yet, from the prep
  commit until publish and permanently if the cut is abandoned. Bump it in a POST-PUBLISH
  commit instead, once the assets and their checksums are uploaded.
- Either way the row needs a drift gate (installer default != newest PUBLISHED tag fails), not
  just a bump: the lag regenerates on every cut, and a gate keyed to the manifest version
  instead of the newest published tag either reds through the legitimate pre-publish window or
  can only be satisfied by publishing and bumping in one motion.
- Say in the row which ordering applies and why. The next pass reads a lagging default as pure
  drift and "fixes" it back into the prep commit, recreating the 404 window.
- The bug is worse than a wrong label when the lagging artifact is the one a containment,
  security, or packaging fix exists to replace: release mode then reliably installs the
  defective wheel while the release notes describe the fixed one. State the artifact-level
  consequence in the row.
- Acceptance needs a COLD-PATH proof with the override env var UNSET — the default is what
  is broken, so a run that sets the variable proves nothing. Assert the downloaded asset
  name/version matches the published tag and the installed binary self-reports it.
- Version surfaces live in three places that drift independently: the script default, the
  script's own usage/help text, and the docs' copy-paste example (often with a comment
  naming the old default). Grep all three; filing only the script default leaves a doc
  that still teaches the stale path.

## 2. Evidence-path policy: an ignored artifact dir can be deliberate

`git check-ignore -v <artifact>` is the probe, but the ignore FILE decides the verdict.
When the rule carries a policy comment — audit artifacts preserved on disk but never
tracked, durable evidence living under a history/ tree instead — that is the repository's
decision, not an accident to route around.

- Do not force-add against a stated policy, and do not report the record as unverified
  because the file cannot be committed.
- Carry durability in the board row: artifact absolute path plus its `sha256sum` in
  `detail.evidence[]`, with the hash derived from the final file (not typed).
- Say in the note which ignore rule makes it untracked, so a later pass does not "fix"
  the missing blob or re-litigate the path.
- Compute the hash AFTER the artifact is final, and re-hash after any edit; an earlier
  evidence entry keeping a stale hash is normal, not corruption.

A repo that force-added older artifacts in the same directory before the rule landed is
not precedent to keep doing it: local precedent never outranks the policy it broke.

## 3. Re-derive every identifier in the pass that writes it

A durable artifact is read months later as fact, so an id, duration or timestamp carried
from an earlier pass (or from your own summary of one) is unfalsifiable at that distance.
Derive each value with the command that produces it DURING the current pass, and keep the
command beside the number in the receipt table.

- **Release-object ids are not in `gh release list`'s JSON subset.** `--json databaseId` is
  refused (unknown field). Query the API and match on the tag:

  ```bash
  gh api repos/<org>/<repo>/releases --paginate \
    --jq '.[] | [.id,.tag_name,.published_at,.draft,.prerelease] | @tsv'
  ```

  Cite the `tag -> id -> published_at` triple. An id alone cannot be checked by the next
  reader, and a remembered id is frequently a different release's.
- **Prove tag immutability rather than assuming it.** `git ls-remote --tags origin 'refs/tags/v*'`
  returns both `refs/tags/X` and `refs/tags/X^{}`; `git cat-file -t <sha>` distinguishes an
  annotated tag object from a commit. Record the PEELED commit for the current release so a
  later pass can show the name was not re-pointed. A mismatched tree under a new version
  number is fixed forward — never force-move a tag, and never tag a tree whose version
  surfaces still name the previous release.
- **Timestamps carry an offset.** `stat -c '%y'` prints the host's local offset
  (`... 05:13:36.000000000 -0500`). Quote it with that offset or convert (`TZ=UTC stat -c
  '%y'`, `date -u -r <file>`); relabelling a local reading as `Z` shifts the record hours and
  silently invalidates any "built after the fix" inference drawn from it.
- **Durations are recomputable, not rememberable.** Read them from the run object
  (`gh run view <id> --json createdAt,updatedAt,conclusion`) instead of estimating; a guessed
  duration sitting beside a real run id is the error a reviewer fixes in one query.
- **A deployed binary's identity is hash plus its own `--version`** — never a path or mtime
  alone. A binary reporting the LAST release's version with an mtime before the current tag
  means "host current for the release already published", which is a PASS for that release
  and says nothing about the tree being cut. State which of the two you measured, and cite
  the repo-built artifact's hash separately from the installed copy's.

## 4. Bind every receipt to exactly one subject

A pass produces several near-identical receipts — candidate CI, evidence/carrier CI, the
tree fingerprint, the release-object id — and they are one copy-paste apart. Bind each to
the single SHA it grades, in its own field, and let the FIELD NAME carry the subject
(`candidate_ci_run`, `carrier_ci_run`, `release_object_id`):

- Never merge two receipts into one attribute. A value like
  `candidate_ci_run="43725527644 on ab679438"` records the BOARD commit's run under the
  candidate's name; every later reader, including you on the next pass, inherits a
  candidate receipt that belongs to a different tree.
- Before writing, read each pair aloud: run id → the `headSha` it graded, version → the
  commit whose manifest says it. `gh run view <id> --json headSha` is the check, not memory.
- A readback proves PERSISTENCE, never CORRECTNESS. `recall` returning your record intact
  says the write landed; it says nothing about whether a field names the right commit. After
  the readback, re-check the values a reader would act on (candidate, tree, run ids,
  decision) against the receipts in the same pass; a durably stored wrong value outlives the
  tick and becomes the next pass's starting assumption.
- Repair a wrong value in an ALREADY-WRITTEN ledger or memory record the same way a pushed
  carrier is repaired: one new record whose key and fields name the corrected field and the
  reason (`.../pass<N>-ci-truth`, each id paired with its commit), then read it back. Do not
  silently leave it because the decision did not change, and do not rewrite the original
  record in place — history plus a labelled correction is the auditable shape.
