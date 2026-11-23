# Cutting through a repo-owned release-prep driver

Target audience: releng lanes cutting a release on a repo that ships its own
version-authority script (`make release-prep VERSION=vX.Y.Z`, `scripts/release-prep.sh`,
`changelog --bump`, a `version:prepare` npm target). The driver, not `git tag` by hand,
is the release path; this file is the sequence it actually forces.

## What these drivers check, and why it shapes the commit count

The one this class converged on refuses, by name, on every one of:

- `DIRTY_TREE` — `git status --porcelain` must be empty
- `NOT_ON_RELEASE_COMMIT` — `HEAD` must equal `origin/main` exactly
- `VERSION_HEADING_EXISTS` / `TAG_ALREADY_EXISTS` — the version is spent once used
- `MISSING_UNRELEASED` / `EMPTY_UNRELEASED` — a heading must exist AND have a body

The `EMPTY_UNRELEASED` refusal is the one that costs a whole extra CI cycle, because the
state it refuses is the NORMAL state of a fast-moving repo: contributors land `feat`/`fix`
commits without touching `CHANGELOG.md`, so at cut time `[Unreleased]` is a heading followed
by nothing. The driver is right to refuse — a release heading with no body is exactly what it
exists to prevent — but it cannot write the notes, and its other two preconditions prevent you
from writing them in the same commit it will promote.

## The sequence that works (two commits, two CI waits)

```bash
# 0. clean carrier at the verified remote tip; never the shared checkout
WT=$(mktemp -d "$SCRATCH/prep.XXXXXX")
git -C "$REPO" worktree add --detach "$WT" "$(git -C "$REPO" rev-parse origin/main)"

# 1. write the [Unreleased] body by hand (the census decides the wording):
#    one line per material commit, scope + what changed + backticked short sha,
#    plus a "Carried forward" subsection for any open artifact gap this cut
#    does NOT fix. Never leave a known blemish unstated.

# 2. commit ONLY that file, push, and WAIT for its exact-SHA runs
git -C "$WT" add CHANGELOG.md && git -C "$WT" commit -F <msg-file>
git -C "$WT" push origin HEAD:main

# 3. driver now sees a clean tree at origin/main
cd "$WT" && make release-prep VERSION=vX.Y.Z     # promotes [Unreleased] -> [X.Y.Z]

# 4. commit the 2-line rollover, push, WAIT again — this SHA is the tag target
git -C "$WT" add CHANGELOG.md && git -C "$WT" commit -F <msg-file-2>
git -C "$WT" push origin HEAD:main

# 5. tag the GATED commit by sha, not the moving tip
git -C "$WT" tag -a vX.Y.Z <gated-sha> -m 'Release vX.Y.Z'
git -C "$WT" push origin vX.Y.Z
```

The rollover diff is exactly two added lines (a fresh `## [Unreleased] — <date>` heading and
the promoted heading). Confirm that with `git diff --numstat` before committing: more than
that means the driver rewrote more than it should, and fewer means it did nothing.

## When the default branch moves between step 2 and step 4

It will. Board and sync lanes push bookkeeping commits every few minutes, so the `HEAD ==
origin/main` precondition fails the moment one lands, and re-running the driver refuses with
`VERSION_HEADING_EXISTS` because it already promoted.

Re-anchor FORWARD; do not reset:

```bash
git -C "$REPO" fetch origin main
TIP=$(git -C "$REPO" rev-parse origin/main)
git -C "$REPO" diff --name-only <prior-sha>.."$TIP"     # must be board/harness paths only
WT2=$(mktemp -d "$SCRATCH/cut.XXXXXX")
git -C "$REPO" worktree add --detach "$WT2" "$TIP"
cp <promoted-changelog> "$WT2/CHANGELOG.md"             # or: git -C "$WT2" checkout <sha> -- CHANGELOG.md
# commit + push from WT2; verify numstat is still 2 insertions, 0 deletions
```

`git reset --hard` is approval-gated on an unattended surface and the block takes the WHOLE
command, so a rescue assembled as one line never runs and reads as a hang. Leave the superseded
worktree in place as evidence and say in the record which tree is authoritative.

The two commits that land after your gated SHA are board-only and excluded from the tag on
purpose: state that boundary in the notes so a reader can tell it from a missed commit.

## Verification legs that do not need to execute a downloaded binary

- `sha256sum -c SHA256SUMS` over the downloaded set — the real published bytes.
- `go version -m <asset>` / wheel `METADATA` — reads a non-executable file, so run it BEFORE
  any `chmod +x`. Executing a downloaded asset is itself gated on unattended surfaces and
  costs the command; the release workflow's own `--version` smoke step (visible in the
  `Release` job's step list) is the execution receipt, and `strings -a <asset> | grep -c <sha>`
  is the read-only substitute when the driver stamps with ldflags.
- Tag-triggered CI runs a second full suite AFTER the publish job. Poll it separately by
  branch name (`gh run list --branch vX.Y.Z`) and only call the cut closed when both are green.
- Per-job, never run-level: `gh api repos/<o>/<r>/actions/runs/<id>/jobs --jq '.jobs[]|"\(.name): \(.status)/\(.conclusion // "-")"'`.

## The local suite is not the gate — say so instead of blocking on it

The repo's documented pre-tag step is usually `make test`. On a loaded fleet host that suite
can exceed the whole per-command window, and a cut that stops for it ships nothing. Hosted
exact-SHA CI is the gate; when the local run does not finish, disclose it in the record as
ABSENT local evidence and let the per-job hosted runs carry the tree. Do not paraphrase a
half-finished run as a pass, and do not silently drop the step.

The same arithmetic applies to the COMMIT itself: a guarded pre-commit hook can run the full
test suite on a version-prep tree, so background the commit process (a foreground tool call
dies mid-hook with the tree left half-staged and the log empty), poll it to completion, and
read the hook's log file — not the tool call's rc — for the hook verdict. `git status`
showing staged-but-uncommitted changes 5+ minutes in is a RUNNING hook, not a failed commit.

## File the sequencing gap as its own finding

An empty `[Unreleased]` is a process defect, not a one-off: nothing in the repo populates it
as work lands, and every future cut over an un-noted range pays the same extra commit and
CI cycle. File one row with two acceptable fix shapes and make the acceptance criteria prove
one of them on a later real cut:

- a convention plus a CI check that reds a push carrying `feat`/`fix`/`perf` subjects while
  the `[Unreleased]` body is unchanged; or
- a documented draft mode on the driver that prints entries derived from
  `git log --no-merges <last-tag>..HEAD` filtered to `feat`/`fix`/`perf` and still refuses an
  empty body on promotion.

## Snapshot mode is not read-only until you prove it in a mirror clone

A `RELEASE_DRY_RUN` / `--dry-run` / `--snapshot` flag is almost always implemented as a guard
around the PUBLISH call only. Tag creation, version bumps and file writes run anyway, so a
dry run can mint a real annotated tag, and a second dry run then refuses on the artifact the
first one planted. Never rehearse the cut path in the certified repo, and never report a dry
run as "no side effects" without having watched for them.

Prove it in a throwaway mirror whose `origin` is the mirror itself:

```bash
SCRATCH=<scratch dir>
MIRROR=$SCRATCH/probe.git; WORK=$SCRATCH/probe-work
MDIR=<board/harness dirs to exclude from tree-identity checks>
BEFORE_HEAD=$(git -C <repo> rev-parse HEAD); BEFORE_TAGS=$(git -C <repo> tag --list)

git clone --bare <repo> $MIRROR
git clone $MIRROR $WORK                    # origin = the MIRROR, never the real remote

cd $WORK                                   # simulate the prep the driver expects
<bump EVERY version surface>               # root + each workspace package/version file
<bump any changelog heading the driver promotes>
git commit -am 'probe prep'
git push origin HEAD:<branch>              # makes HEAD == origin/<branch> for the driver's gates

env <DRY_RUN_VAR>=1 ./scripts/<release>.sh ; echo "rc=$?"
git tag --list ; git status --porcelain    # compare against the pre-run pair
env <DRY_RUN_VAR>=1 ./scripts/<release>.sh ; echo "rc2=$?"   # idempotency arm
```

Why the mirror's own origin matters: the driver's preconditions (`HEAD` equals
`origin/<branch>`, clean tree, version heading present) only pass if the simulated prep is
pushed to the branch the clone considers upstream. Cloning the REAL remote and pushing back is
how a rehearsal becomes a publication.

Cover every version surface the driver validates. In a monorepo that is the root manifest plus
each workspace manifest; bump only one and the driver's own consistency check refuses before
touching the code path you wanted to exercise — which reads like "the tool is safe" when it is
only "the tool never ran".

Read the outcome as three separate legs and cite all three:

- **publisher leg** — the POST/`create-release` call suppressed? Prove the network leg
  separately (payload file, stubbed `curl`, or the script's own dry-run line), because a
  suppressed POST beside a minted tag is exactly the shape to file.
- **mutation leg** — `git tag --list` and `git status --porcelain` before vs after. Any new tag
  or dirty path in a "read-only" mode is the defect.
- **idempotency leg** — the second run. Refusing on an artifact the first run created proves
  the mutation, and proves a preview is one-shot.

Afterwards re-read the certified repo (`rev-parse HEAD`, `tag --list`, `porcelain`) and say in
the record that it is byte-identical to the pre-probe pair — the probe's value collapses if a
reader cannot tell it never touched the release surface.

File the defect with a fail-first arm (the minted tag from a dry run), a fixed arm (two
consecutive dry runs both rc=0 with an unchanged tag list and clean tree), and an acceptance
criterion that the guard wraps EVERY mutation rather than only the publish call. A preview
that plants a tag is not cosmetic: run against the wrong SHA and the tag lands on the wrong
commit, which is a published-release repair rather than a clean cut.

## The first cut on a repo whose stamp already equals the target version

A driver that compares the version-authority file against the requested version and exits with
`<file> already says X.Y.Z — nothing to prepare` looks like a sensible no-op guard and is a
blocker on the FIRST release: nothing else in the repo ever bumps that stamp, so the bump commit
IS the cut, and the guard makes the only reachable input refuse. Both arms are needed in the
record:

```bash
# fail-first arm: on the unfixed driver, the tree whose stamp already equals the target
sh scripts/version-prep.sh 0.1.0 ; echo "rc=$?"       # rc!=0, no commit created

git clone --no-hardlinks --branch <branch> . "$SCRATCH/probe/repo"   # throwaway, origin = clone
cd "$SCRATCH/probe/repo"
git config user.email <lane>@localhost && git config user.name <lane>   # clone inherits no identity
STAMP=$(git rev-parse HEAD:<version-file>)
sh scripts/version-prep.sh 0.1.0 ; echo "rc=$?"        # fixed arm expects rc=0

# fixed arm assertions, in this order
git rev-parse HEAD:<version-file>          # must EQUAL $STAMP byte-for-byte
git log --oneline -1                       # exactly one new commit
git show --stat --oneline HEAD             # changelog-only, nothing else swept in
head -5 CHANGELOG.md                       # promoted heading with today's date + fresh empty Unreleased
sh scripts/version-prep.sh 0.1.0 ; echo "rc2=$?"       # must still REFUSE (rc!=0), HEAD unmoved
```

The last line is the one that gets dropped: a fix that permits the equal-version cut must not
permit a second promotion over the now-empty `[Unreleased]`, or it deletes the driver's real
protection. Assert the stamp BLOB is unchanged rather than trusting the diff text — a rewritten
file with the same content is harmless, a changed blob is a version bump nobody authorized.

Never accept unit tests as the proof of this class: the offline suite is typically green against
both the broken and the fixed driver, because the defect lives in the guard's branch condition and
the tests stub it. The real invocation is the only discriminating evidence. Keep a lint baseline
across the change too (`shellcheck -S warning scripts/*.sh` before and after) and report the two
counts, so a fix is not credited with a green that is merely a raised warning threshold.

## A gate that resolves its own CI target must be labelled, not celebrated

When the pre-cut check cannot pass because a bookkeeping-only tip has no hosted run of its own, the
honest fix is a resolver (`--print-ci-sha`) that names the last SHA the workflow actually requires.
That makes the gate satisfiable without inventing a receipt, but the run it returns belongs to the
CANDIDATE, not to the tip: record it as "gate binds to `<candidate>`" in the artifact and never as
CI-green-at-the-tip. Two further traps: the resolver's answer changes once the fix itself lands (see
the self-match rule above), and a path-filtered workflow will answer "no runs" for many legitimate
SHAs — an empty run list for a docs/board tip is the filter working, not a broken gate.

## Coverage is measured against the release RANGE, not the list a row enumerates

A reconciliation row routinely enumerates the SHAs to add ("the twelve material commits landed after
the prep commit"). A worker that adds exactly those twelve closes the row — and every other material
commit in the same release range stays unannounced, with the section's own "not in this release"
prose now asserting the remainder is bookkeeping. The row's list is a snapshot of one range; the
obligation is the whole `<last-tag>..<candidate>`.

Derive the material set from the census and test each commit twice, because a change can be
described without citing its SHA:

```bash
for s in $(git log --no-merges --format='%h %s' <tag>..<candidate> | grep -E '^[0-9a-f]+ (feat|fix|perf)' | cut -d' ' -f1); do
  printf '%s sha_hits=%s\n' "$s" "$(grep -c "$s" CHANGELOG.md)"
done
grep -c '<issue-or-row-id>' CHANGELOG.md    # the description path, for every uncited SHA
```

- SHA-only grep OVERSTATES the gap (an entry that describes "the admission-time skip for empty
tasks-mode lanes" covers the commit without naming it); description-only census UNDERSTATES it. Run
both and read them together.
- Weight each uncited commit by its product paths — `git show --name-only --format= <sha>` — before
calling it material. A `perf:` or `feat:` commit that touches only `docs/` or the board is not
shipped behaviour; one touching `internal/`, `cmd/`, or `ops/` is, and that path list is what makes
an omission auditable to someone who was not in the pass.
- Report covered/total ("12 of 17 material commits cited") with the uncited SHAs listed by type,
subject and product path. A bare "changelog incomplete" cannot be dispatched and gets re-derived by
the next pass.
- Treat the section's own scope sentence ("everything outside the N prep-range commits is board,
harness, QA, releng or documentation bookkeeping") as a CLAIM to verify, not as the definition of
done. When an uncited product commit makes it false, correcting that sentence is part of the finding,
not cosmetic prose.

## The driver's generated release notes are not the release notes

A repo-owned cut script usually opens the forge release with generated notes, so a successful cut
leaves a non-draft release whose body is a raw commit list. That body is a receipt, not a changelog —
nobody installs from a commit dump. Replace the body and title after the cut, then verify the object:

```bash
gh release edit vX.Y.Z --repo <org>/<repo> --notes-file <notes.md> \
  --title '<tag> — <one-line theme>'
gh release view vX.Y.Z --repo <org>/<repo> \
  --json tagName,isDraft,isPrerelease,publishedAt,targetCommitish,url
```

- Build the notes from the shipped CHANGELOG section: install line, the upgrade-path delta whenever the
  project or its import name changed, Added/Changed, and a Known-issues section drawn from the check
  surface you actually measured. State the sharpest user-facing fix as mechanism in prose (what used to
  happen, what happens now, what pins it) rather than as a commit subject.
- Keep the notes file and COMMIT it (`docs/releases/<tag>-notes.md`): later re-fires re-hash the
  published body against that file, so a scratch-only notes file leaves the release unauditable.
- Editing the body moves neither the tag nor `publishedAt` — that timestamp stays the cut time. Say in
  the record that the body was replaced post-cut so a later reader does not read two cuts.
- Re-read the release object afterwards (`draft=false` is the minimum receipt) and confirm the tag on the
  remote still resolves to the intended commit: `git ls-remote --tags origin 'vX*'` shows BOTH the
  annotated tag object and the peeled `^{}` commit, which is what pins the tag to the certified SHA.

## A pre-dated section for the target version is a claim, not preparation

When the changelog ALREADY carries `## [X.Y.Z] — <date>` before you cut, the driver does not refuse —
the heading exists and has a body — so every note-completeness refusal is silent and the cut ships
whatever that section says. Re-derive the section against the release RANGE (`<last-tag>..HEAD`), never
against the date in its heading: feature commits that landed after the section was written are
unannounced while the heading asserts the version is complete.

- Backfill the missing entries and re-date the heading to the SHIP date in the prep commit, before the
  cut. Two undocumented features shipped because the section was written a month earlier is a
  documentation defect no gate catches.
- Say in that commit message that the change corrects a stale section, so it cannot be read later as
  late feature development.
- The commit that records the cut authorization is the natural carrier for the backfill: one commit,
  both acts named in its message, and the row it advances states which section was re-derived.
