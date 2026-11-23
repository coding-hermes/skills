# Classifying a red gate, and landing a carrier through one

Use when the repo's own suite (or the commit-time guard) reds while you are landing
bookkeeping, or when a board/carrier rebase goes wrong. The goal is to name the arm
that reds and correct the row that owns it, not to bypass or to re-audit.

## 1. Re-run the identical staged diff before theorising

If the same tree with the same staged paths passes on the next run, the arm is
state- or load-dependent. Say so, do not call it a regression, and do not reach for a
hook bypass on the first red. A red that appears on one worktree and not another with
identical scripts is the same signal, and so is a script gate that reds a DIFFERENT target
on each run (§22).

## 2. Isolate the arm by diffing logs, not by grepping FAIL

A mature suite prints hundreds of `FAIL` rows that are intentional negative fixtures,
so `grep FAIL` finds nothing useful. Keep one passing log and one failing log and diff
their PASS/FAIL rows after normalising everything that varies between runs.

```python
# diff two suite logs, printed-rows only
import sys, re
def rows(path):
    out = []
    for l in open(path, encoding="utf-8", errors="replace"):
        s = l.rstrip("\n")
        if s.startswith("  FAIL ") or s.startswith("  PASS "):
            s = re.sub(r'/home/[^ :]*', '<P>', s)
            s = re.sub(r'/var/tmp/[^ :]*', '<T>', s)
            s = re.sub(r'\b[0-9a-f]{7,40}\b', '<SHA>', s)
            s = re.sub(r'\d+', '<N>', s)
            out.append(s)
    return out
a, b = set(rows(sys.argv[1])), set(rows(sys.argv[2]))
for r in sorted(b - a):
    print("only-failing:", r[:160])
```

Exactly one row normally falls out. That row is the arm; everything else was a fixture.

## 3. Find which side is lying before you fix

Grep the EXPECTED string in the source tree. If the only producer of that text prints
the expected wording, the truncation or reformatting happens in a rendering path
(nested/remote row formatter), not in a changed message — which is why the next run can
pass. Do not "fix" a message you cannot attribute; report the path that produces the
mutation.

## 4. Correct the row that owns the fix, in place

A row that names the wrong case sends the next lane at the wrong code. Append a
correction to that owning row (never a duplicate row): the case that actually reds, the
log path and line that proves the named case passed, the isolated arm, and a
respecified remedy with an acceptance test that can fail (N consecutive green runs plus
a seeded negative).

## 5. Count with the full range of the class

`100\.6[4-9]\.` covers only 100.64-100.69, one tenth of the CGNAT /10
(100.64-100.127) — use `100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.`. Measuring with
the narrow slice under-reports a real exposure by most of its size and makes a dirty
tree read clean.

`git grep -oIE '<pat>' HEAD` prefixes the rev, so output is `HEAD:<path>:<match>`: `awk -F: '{print $1}'` yields `HEAD`, not the path. Use field 2 (or drop the rev and grep the
working tree).

## 6. Re-anchor a carrier when the board conflicts

Two lanes writing `tasks.jsonl` and `events.jsonl` make a rebase conflict certain. Never
hand-merge JSONL and never resolve by taking one side wholesale:

1. `git rebase --abort` — restores your commit; nothing is lost.
2. `git worktree add --detach <fresh-dir> origin/main`.
3. In the fresh worktree re-apply only YOUR change: `git checkout <your-old-sha> -- <doc path>`
   brings one file's content forward without touching history, and re-run the board write
   (`boardctl update ... --note ...`) against the new tip so it mints a fresh event.
4. Commit once there (the guard runs the suite once), push `HEAD:main`, verify with
   `git ls-remote` equal to local HEAD.
5. Keep the superseded tree as evidence and say which tree is authoritative.

An amend to dodge the re-run is not worth it: the hook validates the tree you push, and
the whole point is that the pushed tree was measured.

### Carrying an evidence commit across a rejected push

A rejected non-fast-forward usually means another lane landed a board-only delta while you
were writing. Abort the rebase (§6.1), then carry the EVIDENCE commit forward too — the docs
commit is not disposable:

```bash
git worktree add --detach <fresh-dir> origin/main
git -C <fresh-dir> cherry-pick <evidence-sha>    # keeps the commit, its message and identity
git -C <fresh-dir> log --oneline -1              # new SHA after any amend on the rebuild
```

`git checkout <sha> -- <path>` carries only one file's CONTENT and drops the commit; use it
for a single file, cherry-pick when the evidence spans several files you want reviewed as
one change.

- Never write your own carrier's SHA into the artifact or note you are committing. Any
  rebuild (tip moved, amend, conflict) changes that SHA and forces another edit of bytes
  already committed. Cite it positionally — "the docs carrier commit immediately preceding
  this board carrier" — and let the row's `evidence-fingerprint` pin the exact bytes.
- When `origin/main` moved between your read and your push, add a push-time identity
  paragraph to the artifact: old tip → new tip, what the delta contains (board-only vs
  product paths), and that you rebuilt on the new tip rather than forcing. A later reader
  re-deriving your census needs to know which rev it was taken at.
- Re-run the board writer in the fresh worktree (`boardctl create/update …`) instead of
  transplanting JSONL; the writer mints event ids above the new tip's max, which is exactly
  what removes the collision. Prove it after committing:
  `git show origin/main:.coding-hermes/board/events.jsonl | jq -r '.id' | sort -n | uniq -d | wc -l`
  must print `0`.
- Never force-push `main` to win this race. The board is append-only, so a force discards a
  sibling lane's events while looking like a successful push.
- Evidence flags on a replayed board write are a dependency chain, and the writer refuses in
  one direction at a time: `--evidence-artifact` requires `--evidence-fingerprint`,
  `--evidence-fingerprint` requires `--evidence-run-id`. Pass all three
  (`FP=$(sha256sum <artifact path> | awk '{print $1}')` beside the run id) or none. For a row
  with no CI run behind it, drop the artifact flag rather than borrowing an unrelated run id.

## 7. Repair an unmerged index in a shared checkout only after proving it is stale

`git ls-files -u` listing the path at stages 1/2/3 means another lane left a conflict in
the SHARED checkout's index, which blocks every later commit there. Prove there is
nothing to lose before touching it:

- every id in the working-tree file exists in the committed file (no unique rows);
- compare per-row statements and list the ids that differ.

When only YOUR row differs, `git checkout HEAD -- <board path>` restores that one path,
clears the unmerged entry, and reverts nobody's committed work. Disclose the repair in
the report; if any sibling-owned row differed, stop and report it instead.

## 8. A timeout red is an arm that ran out, not a generic red

`gh run view <id> --log-failed` can return EMPTY when the job died on a `panic: test timed
out` rather than a step-level error. Read the job's own log instead:

```bash
gh api repos/<org>/<repo>/actions/runs/<run-id>/jobs \
  --jq '.jobs[]|"\(.name): \(.status)/\(.conclusion)"'
gh api repos/<org>/<repo>/actions/jobs/<job-id>/logs \
  | grep -B5 -A20 'panic: test timed out'
```

The `running tests:` line names the arm and its elapsed time. That is the finding — never
re-run and hope, and never write "CI red" as the cause.

### When the hosted log is EMPTY and it is not a timeout

`--log-failed` returning nothing and `--log` writing a 0-byte file also happens on ordinary
step failures (retention limits, trimming, provider-side gaps). Do not record "CI red, log
unavailable" and do not guess the cause — read the failing step's NAME from the run object,
then grep the workflow for that step to recover the exact command and run it in a clean
worktree at the candidate SHA:

```bash
gh run view <id> --json jobs \
  --jq '.jobs[]|select(.conclusion=="failure")|"\(.name): \([.steps[]|select(.conclusion=="failure")|.name]|join(","))"'
grep -n -A4 '<failing step name>' .github/workflows/*.yml      # -> run: make <target>
cd <clean-worktree-at-candidate> && make <target>; echo "rc=$?"
```

A non-zero rc plus the tool's own printed advisories IS the finding, and it is better
evidence than a log excerpt because the next reader can re-derive it. Quote the skipped
downstream steps as the blast radius, record hosted-log unavailability as UNVERIFIED
transport (never as the cause), and keep the vuln/tool versions with their fix versions so
the repair row is dispatchable rather than "make CI green".

**Annotations carry the file and line when the log does not.** A generic failing step
(`Run tests`) beside an empty `--log-failed` still has a check-run annotation naming the exact
failing file, line and errno:

```bash
J=$(gh api repos/<o>/<r>/actions/runs/<run-id>/jobs \
     --jq '.jobs[]|select(.conclusion=="failure")|.id')
gh api repos/<o>/<r>/check-runs/$J/annotations \
  --jq '.[]|select(.annotation_level=="failure")|"\(.path):\(.start_line) \(.message)"'
```

That is how a teardown flake reads `<test-file>:<line> … ENOTEMPTY: directory not empty,
rmdir '/tmp/<dir>'` instead of "CI red", which is the difference between a dispatchable flake
row and an ignored red. Annotations degrade to a bare `.github :: Process completed with exit
code 1.` on runners that emit no path detail — then fall back to the step-name/workflow grep
above and record the cause as UNVERIFIED rather than inferring one from the test names.

### A failure with ZERO executed steps is an account/plan refusal, not a red

The run object printing `failure steps:` with nothing after `steps:` means no step ran at all, so
nothing graded the tree. Confirm the shape and read the reason, which only the check-run annotation
carries:

```bash
gh api repos/<o>/<r>/actions/runs/<id>/jobs \
  --jq '.jobs[]|"\(.name): \(.status)/\(.conclusion) steps=\(.steps|length)"'    # steps=0
JOB=$(gh api repos/<o>/<r>/actions/runs/<id>/jobs --jq '.jobs[0].id')
gh api repos/<o>/<r>/check-runs/$JOB/annotations --jq '.[0].message'
```

An annotation such as "the job was not started because recent account payments have failed or your
spending limit needs to be increased" is a billing/plan refusal at the ACCOUNT level. Classify it
RED_INFRA, never a code red and never ABSENT_BY_PATH_FILTER: the run exists, the path filter admitted
the diff, and the provider declined to start it. An empty `--log-failed` belongs to that signature —
it is not a transport gap to work around.

- Reproduce it ONCE on a later carrier commit before filing. Two zero-step runs on different SHAs
  prove the block is account-stable rather than one queued event, and settle "was it my diff?" in a
  single line.
- Do not re-push hoping, do not re-run the workflow, and do not invalidate an earlier green run on
  the same candidate: an account refusal says nothing about that tree's code.
- It blocks EVERY hosted gate simultaneously, so the release decision is NO-CUT with an
  infrastructure blocker no worker can fix. File ONE owner-gated row whose acceptance is a run at the
  exact prep SHA with executed steps and a real log — never "make CI green" — and keep the rolling
  readiness row pointing at it instead of re-deriving the same block each pass.
- Bind the last GREEN hosted run's id, sha and timestamp beside the first refused one; that pair
  bounds when the block appeared and how much of the range is ungated.
- A tag-push-only release workflow (`on: push: tags: v*`) makes the tag useless as a retry: the run
  it mints starts in the same refused account and dies at zero steps, so "green on the tag commit"
  is unattainable and an owner override of the SOURCE gates still cannot publish. Decide NO-CUT,
  put that mechanism in the blocker row, and escalate the entitlement — the bump is not the
  constraint, so cutting would only burn a version number on an ungated tree.

## 9. Red-by-construction: measure the TREE before blaming the code

When the timed-out arm walks the repository (a tracked-file scan, a repo-wide lint, an
"every file must ..." guard), the suite can be red because the TREE grew, not because the
diff is wrong. Each command below is a receipt; run them in this order:

```bash
git ls-tree -r --name-only <last-green-sha> | wc -l   # tree size at the last green
git ls-tree -r --name-only HEAD | wc -l               # tree size now
git log --format='%h %ad %s' --date=iso --diff-filter=A -- <bloated-path>
git merge-base --is-ancestor <bloat-commit> <red-sha>   && echo ancestor
git merge-base --is-ancestor <bloat-commit> <green-sha> || echo "green predates bloat"
```

That pair of ancestry checks is the causal proof: the bloat landed between the last green
run and the first red one, and is present at both red SHAs.

Then bound it locally with the CI command minus the CI-only multiplier (`-race`,
`-count=2`, coverage). A ~100s local pass under a 30m hosted budget means the arm reds by
construction until the tree or the scan is bounded — a tree/flag problem, not a diff
problem. Attribute per top-level directory to name the single owner:

```bash
git ls-files -z | xargs -0 stat -c'%s %n' \
 | awk '{split($2,a,"/"); s[a[1]]+=$1; n[a[1]]++} END {for (k in s) printf "%10.1f MB %7d files  %s\n", s[k]/1048576, n[k], k}' \
 | sort -rn | head
```

File ONE row for the gate carrying the measurement, never a row that says only "CI is
red": nobody can dispatch "red", but "untrack the committed harness output and the
whole-tree scan returns inside budget" is dispatchable, and its acceptance criterion can
fail.

## 10. Two red workflows are two rows; a closure the gate cannot express is its own defect

Per-job results decide this. A product-code job and a bookkeeping/board-evidence workflow
red on the same commit have different owners and different fixes — do not fold them into
one row.

A gate that validates completions (a commit touching a product file, or a bound run id)
cannot represent a legitimately closed row that touches neither: withdrawn, premise
disproven, duplicate, superseded. Closing one turns that gate red on EVERY later commit,
permanently, so the lane can never produce an exact-SHA green receipt. File it as its own
row, KEEP the gate (never delete or disable a control that exists to stop unevidenced
completions), and name the acceptable remedies: record the debt deliberately after a
triage pass, or give the audit a first-class disposition that still requires a bound run
id.

## 11. A board-status red is a gate defect when the reader and the writer both accept the spelling

A `board-vocab` (or equivalent status-validation) failure does not mean the writer was
wrong. Three surfaces encode the vocabulary and they drift — the writer gate (Go
allowlist), the CI checker's copy of it, and the reader's status classes — and a fourth,
the operator doc, enforces nothing but states intent, which is what decides whether the
disagreement is a bug or a decision. Establish which ones disagree before touching the
board — one probe each, all read-only:

```bash
grep -n 'AllowedStatuses\|allowed.*status' internal/**/board_vocab*.go   # writer gate
sed -n '/_ALLOWED_STATUSES *=/,+3p' ops/check-fleet-invariants.py         # CI copy
# reader: status consts (e.g. `RowBlocked RowStatus = "blocked"`)
# dispatch: does the pending counter include this status?
```

Check which ENUM owns the disputed spelling before reading reader tolerance as intent. A
constant like `StatusFailed TickStatus = "failed"` is a TICK status, not a row `RowStatus`,
so it proves nothing about the board vocabulary — a board row carrying it came from a
serializer or hand edit that bypassed the writer gate, which is why these rows usually
appear inside a `[ci skip]` board commit and why the first ordinary push afterwards is the
first red. Name the enum in the finding ("`failed` is a tick-disposition value, not a board
status") and file the repair against the rows and the serializer, not against the reader.

Probe the canonical writer directly instead of reasoning about it — `boardctl create --id
PROBE-1 --title probe --status <spelling>` on a scratch board, plus `boardctl validate`
and `boardctl sweep-status --decide` on the real one. If the writer accepts and `validate`
prints `RESULT: OK`, the CI allowlist is the outlier and the row was a legitimate write:
file a gate row, do not rewrite rows.

Commit ordering alone is NOT intent evidence, and treating it as such is how a lane
prescribes the reversal of a deliberate policy while calling it a bug fix. A reader class
that predates the writer gate says only that the reader tolerates rows the gate rejects —
the defensive-reader case, which is compatible with a deliberately closed writer
vocabulary. Bind every claim about intent to a commit:

```bash
git log -S'<phrase from the doc line>' --format='%h %ad %s' --date=short -- <doc path>
git merge-base --is-ancestor <doc-commit> <reader-commit> && echo doc-after-reader
git merge-base --is-ancestor <doc-commit> <gate-commit>   && echo doc-after-gate
```

Read the WHOLE paragraph the doc line lives in, not the sentence a prior row quoted. A
doc line that says "re-spell to <allowed set>" is routinely followed, in the same
sentence or the next, by the stronger statement that the disputed spelling is *outside the
vocabulary on purpose*. A row that quotes only the first half reads as "the docs side with
the gate" while omitting the words that settle the question — and when that docs commit
postdates both code surfaces, the exclusion is a recorded decision, so the widening is a
POLICY REVERSAL.

A policy reversal can still be the right repair, but it must be framed as one and
justified from a surface that outranks the doc line: the operator's own harness doctrine
(what the parking convention for owner-gated rows is), the canonical writer's acceptance,
and the reader's dispatch arithmetic. Say in the row's reasoning that a documented
decision is being reversed, which doc line changes in the same commit, and why the
doctrine wins — a reviewer who checks the docs will otherwise reject the change, and a
foreman will implement it as an oversight fix and revert nothing but the sentence.

Check the direction of the cheap fix. Re-spelling a parked row to the dispatchable status
clears the red but makes it dispatchable — for owner-gated rows that queues owner
decisions as foreman work, which is worse than the red. The correct repair is a lockstep
vocabulary widening (writer gate + CI copy + the pin test that asserts they match), a
seeded-board fixture proving the newly legal status passes while genuinely off-vocabulary
spellings still fail, and the doc line that currently tells operators to re-spell.

Acceptance criteria must forbid the tempting shortcuts: no re-spelling the parked rows, no
deleting or skipping the invariant step, no `continue-on-error` / `|| true`.

The writer's vocabulary is CLOSED and narrower than the statuses rows already carry, so a
disposition like "superseded" or "duplicate" is refused outright (`boardctl: status
"duplicate" not in write vocabulary {pending,in_progress,review,blocked,complete,failed}`).
Do not widen the vocabulary to express one disposition. Park the row as a terminal-looking
`blocked` with a `--blocked-reason` naming the canonical survivor ("SUPERSEDED by <id>,
which carries the current measurement — do not dispatch"), and put the same pointer in the
note. That keeps one live candidate for the foreman instead of two. And check
whether CI has ever SEEN the parked rows: a row added by a `[ci skip]` commit appears in no
run, so the failing log undercounts the violations and the next ordinary push is the first
red.

## 12. A local red is not automatically a product red: ambient env and hosted-only divergences

Before attributing any local suite failure to the candidate tree, split the failures into
three classes and say which each one is. A worker shell carries ambient flags that the
repo's fail-closed tests key on — check the environment first, because those tests cannot
pass there by construction and their names look exactly like real regressions:

```bash
env | grep -i '<REPO-PREFIX>'      # e.g. an APPROVED/OVERRIDE flag exported by the harness
env -u '<FLAG>' go test -short ./<pkg> -run '<Test>' -count=1   # clean-env re-run
```

Classify as: (1) PRODUCT — reproduces in a clean-env re-run of the failing test at the
same SHA; (2) ENVIRONMENT — passes with the ambient flag unset, and the flag is visible in
`env`; (3) UNATTRIBUTED — fails hosted but passes locally at the same SHA. Only class 1
goes into a repair contract. Class 2 is noise the next pass will otherwise re-chase, so
name the flag value in the record. Class 3 is neither a flake to ignore nor a regression to
fix: state that the local run at the same SHA passed, keep it out of the repair row, and
prefer a rerun or a sibling's later fix as the decider — a hosted-only failure that a
sibling later repairs was a real race in the new test, and claiming "flake" without that
receipt is how a live defect gets closed as noise.

For class 1, bind the finding to the introducing commit with a two-SHA red-proof in
separate clean worktrees rather than a single failing run:

```bash
git worktree add --detach <pre-dir>  <sha-before-change>
git worktree add --detach <post-dir> <sha-after-change>
(cd <pre-dir>  && go test -short ./<pkg> -run '<Test>' -count=1)   # expect ok
(cd <post-dir> && go test -short ./<pkg> -run '<Test>' -count=1)   # expect FAIL naming file:line
```

That pair is what lets the row say "introduced by <commit>, at <file>:<line>" instead of
"the suite is red", and it survives the fix landing mid-pass — re-run the same single test
at the newest tip to show the conversion back to `ok`.

### Temp-root identity: a symlinked or ancestor-polluted TMPDIR/GOTMPDIR reds whole packages

Two mechanisms, both class ENVIRONMENT, both invisible to hosted CI because CI's temp root is
neither symlinked nor inside a shared `/tmp`:

- **The temp root IS a symlink.** A build/test temp variable pointing at a symlink
  (e.g. `GOTMPDIR=/var/tmp/<name>` → elsewhere) reds every test that classifies symlinks or
  asserts on the temp root's identity — symlink-evidence and path-comparison tests trip on
  the root itself, and the failure names the test's own helper, not your diff. Unset the
  variable (`env -u GOTMPDIR make test`) rather than repointing it; repointing keeps the
  class alive.
- **A stray directory ABOVE the temp root.** Helpers that locate the repo by walking UP for a
  marker directory (`catalog/`, `go.mod`, `.git`) resolve outside the worktree when the test's
  scratch dir sits under a shared temp root that already has such an ancestor. Fix by giving
  the run a dedicated root with no shared ancestors: `TMPDIR=/var/tmp/<dedicated> make test`.

Print the identity before theorising, and prove the flip per package instead of asserting it:

```bash
printf 'TMPDIR=%s GOTMPDIR=%s TMP=%s\n' "${TMPDIR-<unset>}" "${GOTMPDIR-<unset>}" "$TMP"
readlink -f "${TMPDIR:-/tmp}"                       # resolved != literal => class 2 or 1
ls -la "$(dirname "$(readlink -f "${TMPDIR:-/tmp}")")" | head   # stray markers above the root
go test -count=1 ./<pkg> -run '<Test>'                       # with the ambient variable set
env -u GOTMPDIR TMPDIR=/var/tmp/<dedicated> go test -count=1 ./<pkg> -run '<Test>'
```

Rules that follow:

- The decision-grade receipt is a CLEAN-ENV FULL run at the candidate SHA
  (`env -u GOTMPDIR make test` → `<n> packages ok / 0 FAIL`). Quote that, and say plainly that
  the earlier reds were host state, or the next pass re-chases them.
- Provenance the stray host state before filing (`stat` its mtime and owner). A marker dir with
  an old mtime owned by the operator predates the candidate by months: it is host state, not a
  product change.
- File the ISOLATION defect as its own P2 row against the test that depends on ancestors of
  the temp root — acceptance is the test passing under a hostile temp root, not "make tests
  green". Do not fold it into the release blocker and do not edit the shared host path from a
  verify-only lane.
- Two distinct hosts-state mechanisms seen in one log are two rows; one row titled "suite is
  flaky locally" is undispatchable (§10).

## 16. A verdict that reds on a toolchain-resource init error measured the HOST

A `verdict.json` reading `passed: false` on a clean tree is not automatically a source
defect. Read the failing test's own message: when every failure in the arm is a resource
INIT error rather than an assertion (`failed to initialize build cache`, `cannot load
module cache`, `permission denied` creating a cache dir), nothing in the candidate's code
was measured.

Prove the attribution before writing the row — the receipts are cheap:

```bash
CACHE=$(go env GOCACHE); printf 'GOCACHE=%s -> %s\n' "$CACHE" "$(readlink -f "$CACHE")"
test -e "$CACHE" || echo "DANGLING: cache path does not resolve"
mount | grep -i "$(dirname "$(readlink -m "$CACHE")")" || echo "parent not a mount"
python -m pytest <failing-node> -q -p no:cacheprovider          # reproduce at the same SHA
gh run list --repo <org>/<repo> --limit 10 \
  --json headSha,status,conclusion --jq '.[]|select(.headSha=="<full-40-sha>")'  # hosted verdict
```

A cache path resolving into an UNMOUNTED mountpoint (a symlink to `/mnt/<vol>/...` whose
volume is absent) makes every build in that shell die at init while hosted CI on the same
SHA is green. That combination IS the finding: the verdicts are unusable release
evidence, and the tree is not defective. Frame it as class ENVIRONMENT (§12), never as a
product red, and act in this order:

1. File an infra row naming the exact dangling path, with acceptance criteria that forbid
the temptations (marking the affected tests `xfail`/`skip`, widening a timeout, deleting
the tests) and that require a fresh verdict after the fix, plus an explicit statement on
whether the earlier REDs were environmental.
2. Do NOT repair a shared host path, mount, or exported variable from a verify-only lane.
   Another lane's cache is not yours to change mid-sweep; the repair row is the action.
3. Do NOT record the release decision as blocked on that red. Name which evidence legs are
   unusable and decide from the legs that did measure the tree (exact-SHA hosted CI,
   publication state, artifact digests).

**Absence and failure are different findings, and the difference decides the next pass's
work.** Enumerate the verdict tree for every commit in the range before writing "no
verdict found" — the directory name is the commit-ish, and the schema varies, so read it
defensively:

```bash
for d in .gitreins/history/*/*/verdict.json; do
  printf '%s ' "$(basename "$(dirname "$d")")"
  jq -r '"passed=\(.passed) class=\(.pass_class // "-") task=\(.task_id // "-") dirty=\(.working_tree_dirty_path_count // "-") at=\(.evaluated_at // "-")"' "$d"
done
```

A tree of RED verdicts recorded as "missing" reads as *untested*, which queues a judge
re-run; the truth is *tested and red for an environmental reason*, which queues an infra
fix. Recording the wrong one burns a full pass and teaches the next reader that a
verdict-producing repo has none.

## 13. A gate whose answer depends on the tag the cut is about to create

Some repos gate the docs/version surface on `git describe --tags --abbrev=0`: the README
must not name a tag older than the newest one, and a block marked "requires a build from
HEAD" is a violation once those commands ship in the newest tag. Such a gate is
**unsatisfiable on the version-prep commit** — the tag it compares against does not exist
yet — and satisfiable only once the tag is immutable. Three consequences, in order:

1. Do not conclude the prep is wrong when its own unit tests red. Read the shipped-docs
test's premise line; when it names the OLD tag and lists the commands you just promoted as
"not a command in the newest release tag", that is the tag-absence, not a bad edit.
2. Do not split the cut into "land prep → wait green → tag". That order can never produce
a green prep commit. The repo's own checklist usually already says ONE commit, ONE tag,
ONE push — follow it (`git push <remote> HEAD:<default> refs/tags/v<X.Y.Z>`), and note
that a full-depth checkout on the branch run fetches the tag in the same push, so the
branch run is green too rather than racing.
3. Pre-measure the tagged state BEFORE the tag exists. `git clone --shared` gives the
clone its own refs over shared objects, so a tag created there is invisible to the real
repository:

```bash
git clone --shared --quiet <repo> <scratch>/sim-$$
cd <scratch>/sim-$$ && git checkout -q <candidate-sha> && git tag v<X.Y.Z>
go run ./cmd/<repo-docs-gate> -dir .        # or the repo's own release gate
```

Copy the edited files in before running; the clone's working tree is the candidate, its
tags are the post-cut world. That run is the receipt for "the tagged tree passes", and it
is the only way to see the FULL violation list (expect the doc edits to be real: stale
markers, every mention of the previous tag) while the tag is still revocable. Never create
a tag in the real repository to test the gate.

## 14. A red inside a third-party action's SETUP step is infrastructure, and a re-run cannot start until the run ends

Distinguish this from a tree verdict by the STEP, not the job conclusion:

```bash
gh api repos/<org>/<repo>/actions/jobs/<job-id> \
  --jq '.steps[]|"\(.number) \(.name): \(.conclusion // "-")"'
```

A job whose failing step is an action INSTALL (`bufbuild/buf-setup-action`, or any
`uses:` setup step) reporting `Unexpected HTTP response: 504`, with the real gate step
listed `completed/skipped`, never measured the tree. Two readings convert that into
evidence instead of an excuse: the same error reds a SIBLING commit's different job inside
the same window (a provider/outage signal, not a diff signal), and the same leg passes on a
later commit — which proves the leg works and forbids retiring it.

Re-running is usually blocked, and the error text misleads:

- `gh run rerun <id> --failed` → `cannot be rerun; its workflow file may be broken` while
  any leg is still `in_progress`. The run is not rerunnable until every job terminalises.
- `gh api -X POST .../actions/jobs/<job-id>/rerun` → HTTP 403 `The workflow run containing
  this job is already running`.

So one queued self-hosted leg (`startedAt: null` on an online-but-busy runner) blocks the
re-run of an unrelated failed leg for as long as it hangs. Record both as PENDING/
UNVERIFIED with their run ids, state which leg actually measured the tree, and leave the
re-run to the next pass. Also trust the run OBJECT over `gh run list`: the listing can say
`completed/failure` while `gh api .../actions/runs/<id>` still says `in_progress` for the
same run.

## 15. A guard reporting lint findings while its own log shows a dependency failure is measuring the ENVIRONMENT

Symptom: the commit-time guard reds at deny level with clippy/lint findings on a diff that
contains no source at all, and re-running changes nothing. Read the guard's log instead of
the console transcript, and check the toolchain paths it depends on:

```bash
git config core.hooksPath
ls -t .gitreins/logs/guard-*.log | head -1        # READ it
printf '%s\n' "$CARGO_HOME"; ls -ld "$CARGO_HOME" "$CARGO_HOME/git" "$CARGO_HOME/git/db"
df -h "$(dirname "$CARGO_HOME")"
```

A log line like `failed to create directory $CARGO_HOME/git/db/<crate>: Permission denied
(os error 13)`, or any crate-fetch failure, means no lint pass ever ran: the dependency
could not be materialised and the guard mapped that onto its findings channel. That is
class ENVIRONMENT above, and it blocks EVERY commit in that shell, not just yours.

Two repairs, in this order: scope a real home for the command (`CARGO_HOME=$HOME/.cargo
git commit …`), then file rows — one for the lane env (exported path / missing mount), one
for the guard design, because a dependency, toolchain, or network failure must be reported
as abort/inconclusive rather than as findings, or an unavailable cache is indistinguishable
from real lint debt forever.

When the diff genuinely touches no source (board JSONL, changelog prose) and must land in
this tick, bypass WITH disclosure — never silently:

```bash
git -c core.hooksPath=/dev/null commit -F <msg>   # <msg> carries a GUARD DISCLOSURE paragraph
```

The paragraph states (a) the environmental cause with the exact error, (b) that the diff
contains no source file, (c) the equivalent measurement that did run — the hosted job and
run id exercising that same linter. Then prove scope: `git show HEAD~1:<path>` beside the
working file, normalise both (`jq -cS … | sort` for JSONL), diff, and confirm only the
intended rows moved. A bypass without those three elements is an unmeasured commit.

## 17. A coverage-floor breach is untested NEW code, not a broken suite

Read the failing step's own numbers before classifying. `covercheck: total 78.5% of
statements (floor 80.0%)` plus a per-package line plus ZERO test failures means the suite
is healthy and new statements arrived untested — the repair is tests for the named code,
not a fix to the code. The bookkeeping that looks like a second defect is not one: the CI
job lists `Test` as `skipped` beside a failed `Coverage` step because the repo's cover
target runs its own `go test`. Quote that as design, never as a missing gate.

Reproduce with the repo's own target, unpiped so the exit code is the gate's, and write
the profile OUTSIDE the tree (a tracked dist/ or output dir makes the tree dirty and can
shift later provenance stamps) — but confirm first that the target REACHED the assertion.
A repo-owned gate target that exits non-zero with an empty or two-line log
(`make: *** [Makefile:N: cover-check] Error 1`) never ran the checker: it died in its own
plumbing (missing prerequisite, profile path, cleaned output dir). Read the wrapper's truth
from the log length, lift the underlying invocation out of the target recipe, and run it
directly with the same floors before recording a red:

```bash
make cover-check > /tmp/cov.log 2>&1; echo "rc=$? lines=$(wc -l < /tmp/cov.log)"   # <=2 lines => plumbing
OUT=$(mktemp -d /tmp/releng-cov.XXXXXX)
go run ./cmd/covercheck --profile=$OUT/cov.out --min-total=80 --min-package=60 --exempt=<pkg>; echo "rc=$?"
```

A direct rc=0 beside a target rc=2 is a defect in the TARGET (its own row), not a gate
failure — reporting it as one sends the fixer at coverage debt that does not exist.

```bash
make cover-check; echo "rc=$?"
OUT=$(mktemp -d /tmp/releng-cov.XXXXXX)
go test ./... -count=1 -short -coverprofile=$OUT/cov.out >/dev/null
go tool cover -func=$OUT/cov.out | grep -E '<newfile>\.go' | awk '{printf "%-70s %s\n",$1,$3}'
```

A file reading 0.0% across every function names the owner: `git log --diff-filter=A
--format='%h %s' -- <file>` binds it to the feat commit that introduced it, and the
per-pass total (79.9% → 77.9% after the feature → 78.5% now) shows the floor was breached
BY that commit rather than by slow drift. Put the repair on the row that already owns the
gate: floor unchanged, cover the named uncovered functions, assertions that fail at the
introducing commit, and an explicit note that covering only an EARLIER feature's paths
cannot clear a floor breached by a later one.

Do the per-file/per-package rollup with `go tool cover -func | awk`/`grep`, never an
inline interpreter heredoc: the unattended command gate refuses `python3 - <<EOF`
outright (approval timeout, nothing ran) and the refusal costs the whole batched call,
including any safe read sharing that line. When the rollup is declined, keep the
per-function evidence you already hold and mark only the rollup leg UNVERIFIED.

### A carried gate number is a claim; re-measure at the exact candidate SHA

A standing readiness row quoting `<pct>% of statements (floor <floor>%)` is a snapshot of
some earlier pass and can be wrong at the current candidate — a different profile scope, a
breach fixed since, or a bumped floor all produce the mismatch. Re-measure the gate at the
exact candidate SHA before re-filing it red. When a fresh run exits 0 above the floor, the
ROW's premise is what changed: correct it in place, name the superseded figure beside the
new one, and leave the floor alone. Retuning a threshold to preserve the old narrative
hides the debt, and re-filing last pass's red because the row still says red burns a pass
on paid debt while the gate that actually reds goes unattributed.

Carry the MARGIN into the blocker, not just the floor. A pass 0.2 pp above the minimum
re-reds the moment the fix adds one uncovered statement, so the acceptance criteria must
say "floors unchanged, add no uncovered statements" — otherwise the fixer's own test
helper becomes the next blocker.

### The red can migrate between gates on a byte-identical tree

Two consecutive passes can red DIFFERENT gates with zero product diff
(`git diff --name-only <prior-candidate>..HEAD -- <product paths> | wc -l` = 0): earlier red
coverage, later red `govulncheck`. Nothing regressed and nothing was fixed. Some gate
inputs are not functions of the tree — the vulnerability index is fetched at run time, a
coverage floor depends on profile scope, a lint gate on the installed compiler — so tree
identity carries the CODE-derived gates (build, format, unit tests) and does not carry
those.

- Do not certify a moved candidate by tree identity for a data-indexed gate; re-run it at
  the exact SHA.
- Name the gate that reds NOW with the run id that shows it, and record the earlier breach
  as PAID with the measurement that pays it.
- Expect the red to persist at the SAME step on a board/evidence-only carrier. That
  persistence is positive evidence the breach is source- or toolchain-bound rather than a
  flake of one SHA — quote both run ids instead of pushing a third time.
- A standard-library advisory whose fix is expressed as a Go patch version is cleared by
  bumping the module's `go` directive (CI reading `go-version-file: go.mod` follows), one
  line, no `go.sum`/vendor churn. Keep the blocker that narrow: "fix CI" is not
  dispatchable.

### The decision-grade number: statements to the floor, and the one file that clears it

A percentage is a symptom; the shortfall in STATEMENTS is the assignment, and it is often
small. Coverprofile columns are `$1=file:start,end`, `$2=numStmts`, `$3=count` — do not split
on `:` or `$2` becomes a line number, every block reads as 0 statements, and a
"biggest uncovered blocks" listing comes back empty while one file holds hundreds of them:

```bash
awk '{t+=$2; if($3>0) c+=$2} END {need=int(t*0.8+0.9999);
  printf "total=%d covered=%d pct=%.3f need=%d short=%d\n", t,c,100*c/t,need,(need>c?need-c:0)}' cov.out

awk '{f=$1; sub(/:[0-9].*$/,"",f); t[f]+=$2; if($3>0) c[f]+=$2}
     END {for(k in t) if(t[k]) printf "%6.1f%% %5d/%5d %s\n",100*c[k]/t[k],c[k],t[k],k}' cov.out \
  | sort -n | head -15
```

`need = ceil(floor * total)` and `short = need - covered` is how many statements the fix
must cover. Then check whether ONE untouched file already exceeds `short`: covering `n`
statements takes the total to `100*(covered+n)/total`, so a single 0% file larger than the
shortfall clears the floor with margin. Put all three numbers in the row (shortfall, the
file's statement count, the resulting total and margin) — a fixer reading only "reach the
floor" cannot tell whether that is one file or twenty.

## 18. A secrets gate red on a tracked PLACEHOLDER file is a contract defect, not a leaked credential

A secrets step that exits non-zero while its log says `gitleaks: clean` / `no leaks found`
means the failing arm is a POLICY scanner, not the entropy scanner. Read the finding line: a
path-class rule (`SENSITIVE PATH`, credential-store path class) fires on the FILE NAME, so
`.env.example` — dummy values and all — cannot be staged regardless of content.

Classify before filing. The tree is not leaking and the code is not red, so do not record the
release as blocked on a code defect and do not ask for the scanner to be relaxed globally.
The three acceptable remedies, all in ONE row: untrack the file and ship a sample with no
secret-shaped values, keep it tracked and pass the documented per-path override with a
recorded reason, or move the values to a secret manager. Acceptance must be able to fail (a
green secrets step on a commit that touches the file) and must forbid the shortcuts (`||
true`, deleting the arm, an unscoped allowlist).

Expect the red to persist on EVERY later verdict until the file is handled, so a sweep that
finds it cites the existing row and the same verdict path instead of re-deriving it as a new
finding each pass.

Name the failing step from the run OBJECT: the rendered view of a failing run prints only
`✓ Set up job` / `✓ Complete job`, so a `grep -iE 'job|step|failure'` over it reports the
wrong picture.

```bash
gh run view <run-id> --repo <org>/<repo> --json jobs \
  --jq '.jobs[]|"JOB=\(.name) concl=\(.conclusion) failed_steps=\([.steps[]|select(.conclusion=="failure")|.name]|join(","))"'
```

## 19. A hosted red whose failing file and toolchain lines match the last green tag is RUNNER drift

Signature: an exact-SHA hosted job reds, the error text is an environment complaint rather
than an assertion (`compile: version goX does not match go tool version goY`, a compiler
naming a different patch than the module cache), and the test function exists unchanged in
the tree that last passed. Prove that before filing anything:

```bash
gh run list --repo <org>/<repo> --limit 25 --json databaseId,headSha,name,conclusion \
  --jq '.[]|select(.headSha=="<candidate-40sha>")|"\(.databaseId) \(.name) \(.conclusion)"'  # red now
git log --oneline <last-green-tag>..HEAD -- <failing-test-file> | wc -l             # 0 commits
git show <last-green-tag>:<failing-test-file> | grep -c 'func <TestName>'           # 1
diff <(git show <last-green-tag>:go.mod | grep -E '^(go|toolchain) ') \
     <(grep -E '^(go|toolchain) ' go.mod) && echo identical
```

A green run on that tag tree, zero commits to the failing file, and identical `go`/`toolchain`
directives leave the RUNNER as the only variable. Then name the moving part in CI instead of
the product: a `setup-go` step with `go-version-file: go.mod` resolves the newest patch of
the minor (say `1.26.11`) while the module pins `toolchain go1.26.10`, so any test that shells
out to `go build` runs the nested build under the pinned toolchain and dies on the mismatch.
Grep the test tree for the nested invocation to confirm the linkage, and count the error
string (`grep -c 'does not match go tool version'`) — dozens of identical lines are ONE root
cause, and the count is the cheap multiplier.

File it as the CI-pin row, never a code row: a literal `go-version` in every job (or a
`toolchain` bump that matches the float) plus one acceptance criterion that fails when the pin
is removed. Do not accept "make CI green", a skipped test, or `|| true`. The gate WAS red at
the candidate, so the release stays NO-CUT — but it is an environment blocker with a one-line
repair, not a regression, and the next pass must re-measure on the fixed pin rather than
re-deriving the same red.

## 20. Two consecutive reds do not establish a broken main — sample the run history in both directions

A readiness sweep that reads only the tip's run will call a flaky arm a broken main, and the
next pass inherits the wrong finding. Before writing "CI red on main", print the conclusion
of every recent push-to-main run with its SHA, in order:

```bash
gh run list --repo <org>/<repo> --limit 8 \
  --json databaseId,headSha,conclusion,status,event,createdAt \
  --jq '.[]|"\(.createdAt) \(.headSha[0:8]) \(.event) \(.status)/\(.conclusion) \(.databaseId)"'
```

A pattern like FAIL, FAIL, SUCCESS, SUCCESS with the same failing file, the same teardown
step, and 100% of tests passing is an INTERMITTENT teardown defect, and the row must say so:
"intermittently red, 2 red then 2 green" beats "main is red" because it tells the fixer the
assertions are fine and the defect is in child-process exit / rpc drain, and it tells the
next sweep not to re-file the same red.

### Carriers of ONE product tree are a repeated-measures sample

The strongest flake evidence a releng pass can produce cheaply is conclusion variance across
commits that share byte-identical product code, because bookkeeping carriers add a draw on the
same tree for free. Build the sample and the identity proof together — the conclusion column is
meaningless without the delta column:

```bash
gh run list --repo <org>/<repo> --workflow <gate>.yml --limit 12 \
  --json databaseId,conclusion,headSha,createdAt \
  --jq '.[]|"\(.createdAt) \(.conclusion // "pending") \(.databaseId) \(.headSha[0:8])"'

for S in <sha> <sha> <sha>; do                       # each carrier of the tree
  printf '%s product_paths=%s\n' "$S" \
    "$(git diff --name-only <candidate> $S -- . ':!releng' ':!.coding-hermes' ':!reports' | wc -l)"
done
```

A zero in every `product_paths=` column plus FAIL and SUCCESS in the same conclusion column is
intermittent, full stop: nothing in the product changed between the readings. Report it as
"N of M carriers red", naming each red's run id and test — never as "the suite is red", which
reads as a broken main and sends the next pass chasing a regression that does not exist.

Classify the failing ASSERTION, not the test name. A wall-clock bound
(`require.Less(t, duration, 2*time.Second)`; a microsecond ratio between a 200-row read and a
10 000-row read) is a gate-margin defect whose fix removes or injects the margin, and it reds on
runner speed rather than on the code. A behavioural assertion is a product finding. Quote the
comparison and its observed values (`144.25µs is not less than or equal to 142µs`) — the numbers
are what tell the fixer the assertion is noise-sensitive.

Disposition, in this order:

- Look for the OWNING row before filing anything. A pending row that already names the class (or
a close test) owns the fix; append one audit event with the new instance, its run id, its
assertion line and the sample counts, and leave the row's status alone.
- A CLOSED row that covered the same test with a different mechanism is not coverage. Say so in
the event — the earlier fix addressed a different failure, so citing the closure as "already
handled" hides a live gate defect.
- A repeat on a row that is already filed is corroboration: put it in that fire's ledger record
with the updated count and say "measured, not refiled". Do not mint a row and do not mint a
carrier for it; a flake-class row whose evidence grows per carrier turns every push into new
work.
- State the release consequence in one line: whatever SHA is tagged must carry a green run on
that gate, so an intermittent red makes a tag-time green a coin flip rather than a
certification — and it does NOT move a product decision made on a green candidate.

### The rerun of the failed jobs is the CLASSIFIER, not a retry

A red whose failing assertion is a transport class (`httpx.ReadTimeout`, `ETIMEDOUT`, a 504 from a setup action) is classified by re-running the SAME sha, never by pushing another commit:

```bash
gh run rerun <run-id> --repo <org>/<repo> --failed
gh run view <run-id> --json status,conclusion,updatedAt     # poll; do not block a foreground call on watch
```

Green on the failed-job rerun means class FLAKE: it stays out of every repair row FOR THE PRODUCT, and both readings go in the record — the red job's own error line with its wall time and pass/fail counts, and the rerun's green conclusion with its timestamp and the same sha — so the next pass cannot re-chase it.

A flake classification is not a disposition for the GATE, though. When the same sha produced failure AND success, the gate cannot certify anything, so it gets its own row (P2 is right) naming the asserting file:line, both attempt outcomes with their attempt numbers, and the ambient condition the assertion depends on — filesystem/kernel feature support, timer margins, transport reachability. Acceptance is the arm inverted: it must FAIL under the hostile condition and pass across N consecutive runs. Leaving it unfiled because "the tree is fine" is how "CI green on the tag commit" stays a coin flip while the board reads clean; saying so in the cut row is required too, because exact-SHA green at tag time is then luck rather than certification. The gate's answer at that sha is then the rerun's green, cited by the same run id.

Two limits. A rerun certifies only the sha it ran on; it never lends itself to a sibling or mirror sha, which has no run at all. And a rerun that STAYS red converts the flake claim back into a product finding, so record the rerun whichever way it lands — a rerun performed and not written down is either a wasted tick or a suppression.

Do not let intermittency soften the gate, though — sharpen it. When the release workflow
requires a green run on the tagged SHA, a green reading at tag time is luck rather than
certification, and a red tagged run aborts the cut mid-flight. State that explicitly in the
cut row and escalate the defect's priority rather than downgrading the blocker.

Correcting a prior pass's classification is a first-class write: append an addendum to the
evidence artifact with the run table, refresh the owning row in place (`boardctl update …
--note`) naming the earlier characterization as superseded, add one audit event, and keep
both readings so the correction is auditable. Never edit or delete the earlier pass's text.

## 21. A job that never STARTED is executor-absent — and a row minted from its stage name says the wrong thing

"The job ran and failed" and "the job was queued and never began" look identical in a job
list that prints only name + failed status, and only the second one measured nothing. Read
the execution fields before attributing a stage:

```bash
# GitLab: /projects/<id>/pipelines/<pid>/jobs  (gh: actions/runs/<id>/jobs)
curl -s -H "PRIVATE-TOKEN: $TOK" "$API/projects/<id>/pipelines/<pid>/jobs?per_page=100" \
  | jq -r '.[]|"\(.name) status=\(.status) started=\(.started_at // "NULL") reason=\(.failure_reason // "-") queued_s=\(.queued_duration // 0) runner=\(.runner.id // "none")"'
```

`started_at: null` with `failure_reason: stuck_or_timeout_failure` and a `queued_duration`
in the hundreds of thousands of seconds is a job that never executed: no step graded the
tree. Classify it executor-absent infrastructure (RED_INFRA), never a code red, and never
"failed at <stage>" — the stage name in the payload is the stage that WOULD have run.

- **A board row generator keyed on job name + failed conclusion will mint `fix <stage>` rows
  for jobs that never started.** A worker dispatched at one hunts a defect that does not
  exist while the real cause (no online runner, a dead runner pool) goes unfiled. Before
  dispatching any CI-fix row, re-read the job's `started_at`/`failure_reason`/`runner` and
  correct the row in place (one row, appended correction — never a duplicate): "the
  `<stage>` job was never started; queue timeout at <n> s; no runner was assigned".
- **A runner listed `active` is not a runner that is polling.** Check `contacted_at`; null
  on an active runner means stale, so the queue can grow forever with the pool looking
  healthy in the roster.
- **Bound the outage instead of calling it a one-off red.** Count consecutive pipelines
  whose jobs all carry `started_at: null`, then cite the last pipeline that actually
  executed a job (id, sha, finished-at) — "no executed CI for <n> days" is the decision-grade
  number, and it is what turns "CI red" into "CI absent" with a date.
- A supersession chain inside one tick (several pipelines minted in minutes, none with an
  executed job) is positive proof the gate is not merely red once; record the chain rather
  than the newest id alone.

## 22. The gate that deletes its log, and the gate that reds a different target each run

A repo-owned local gate script (the `scripts/local-ci.sh` class: turbo/vitest/make fan-out
wrapped in a driver) usually removes its own log on exit. Never edit that script from a
verify-only lane to keep the log, and never report "red, log unavailable" — shim `rm` on
PATH so the log is copied out before the script's own cleanup runs:

```bash
S=<scratch>/releng
mkdir -p "$S/rmshim" "$S/gate-logs"
printf '%s\n' '#!/bin/sh' \
  'for a in "$@"; do case "$a" in *.log) cp -f "$a" "'"$S"'/gate-logs/" 2>/dev/null;; esac; done' \
  'exec /bin/rm "$@"' > "$S/rmshim/rm"
chmod +x "$S/rmshim/rm"
PATH="$S/rmshim:$PATH" timeout <budget> <gate command> <worktree> 2>&1 | tail -20
grep -nE 'FAIL|✕|AssertionError|ENOENT|ETIMEDOUT' "$S"/gate-logs/*.log | head
```

Read the captured log before theorising: it names the file, line and assertion the gate
died on, which no exit code carries. A zero-byte or missing capture means the script unlinked
by another mechanism (an `exec`-replaced shell, a `trap`-cleaned temp dir) — then pass the
script's own log-path argument or env var instead of widening the shim.

### Red on a different target each run is LOAD sensitivity, not intermittency of the product

The discriminating evidence is a matrix, and each cell is cheap:

```bash
for i in 1 2 3; do PATH="$S/rmshim:$PATH" <gate command> >/dev/null 2>&1; echo "run$i rc=$?"; done
(cd <worktree>/packages/<pkgA> && pnpm exec vitest run)          # isolation: green
(cd <worktree>/packages/<pkgB> && pnpm exec vitest run)          # isolation: green
pnpm exec turbo run test --force                                 # whole fan-out alone: green
uptime; nproc                                                    # load <N> on <M> cores
```

Failures on target A, then target B, while `turbo run test` and each target alone are green,
means the parallel fan-out starves wall-clock timers: nothing in the product regressed and
nothing was fixed. Then read the preserved log for the actual margin — a test asserting a
`success === false` for a 100 ms timeout against a 200 ms resolve is a 2x margin that any
oversubscribed runner crosses.

- Report the load average and core count BESIDE the failing assertion. "Red 3/3" without the
  host state reads as a broken product and will be re-chased; "red 3/3, different package
  each time, load 37 on 16 cores" is a dispatchable gate-margin defect.
- One row, not one per package. Acceptance must be assertable: fake timers (or margins an
  order of magnitude above the resolve), N consecutive gate runs green, and a gate that
  preserves its log (a documented log path, not an `rm` at exit) so the next pass reads the
  failure instead of re-deriving it.
- The gate still cannot certify the release. Say so plainly: the tree is probably fine, the
  GATE is not a pass, so the decision stays NO-CUT and the artifact records why the evidence
  leg is unusable rather than quoting the isolation greens as a green gate.
- Do not chase the red as a worker task. A lane that files "make tests green" queues a
  rewrite of healthy tests; the margin, the fan-out concurrency, and the log path are the
  three levers, and the row names all three.

## 23. A docs-only carrier reds because the DOC is the checker's INPUT

A guard red on a commit whose every path is documentation is not a flaky suite, not a
broken gate, and not a licence to bypass. Mature repos run CLAIM checkers over the docs
tree — a script that scans documents for assertions it can verify: every secret-scan claim
must name its scan options, every command a README shows must exist, every status table
must match the registry. Your prose is the failing input.

Attribute it per SECTION before reading a single assertion, because the suite prints
hundreds of fixture rows and the text nearest the `FAIL` row is usually not the input:

```bash
G=$(ls -t .gitreins/logs/guard-*.log | head -1)        # the guard's OWN log
for f in "$G" "$GREEN_LOG"; do
  awk '/^[0-9]+\. /{sec=$0} /^  (PASS|FAIL) /{n[sec]++} END{for(s in n) print s"|"n[s]}' "$f" | sort
 done > /dev/null   # write each to its own file, then:
join -t'|' -j1 /tmp/sec_green.txt /tmp/sec_guard.txt | awk -F'|' '$2!=$3'
```

One line comes back: the section whose row counts moved. In a docs carrier that section is
almost always a claim/scope checker, and the arm did not touch code at all. Then run that
section's script by hand and let its own finding line name the offending sentence of YOUR
file, instead of grepping the docs for a phrase you assumed it matched.

Repair the CLAIM, not the checker. State the measured truth — the job's real scan scope,
the command's real flags — and re-run the checker directly to exit 0 before committing.
Deleting the claim silences the gate and destroys the evidence; relaxing the checker is a
policy change that belongs in a board row, not inside a carrier whose value is its audit
trail. A gate that rejected your first draft twice was right twice: record the rejection
and the correction in the artifact so the next reader sees the gate doing its job.

### The commit outlives a foreground tool timeout

A guard that runs the repo's full suite takes minutes, longer than a foreground command
budget. Dispatch `git commit -F <msg>` in the tool's background mode and wait on the
session handle; a bounded foreground poll (`for i in $(seq 1 N); do sleep 10; done`) dies
at the tool's own ceiling and reads as "the commit hung" while the hook is still working.
A detached `setsid nohup` wrapper can return no output at all — use the tool's own
background mode instead. Prove the landing afterwards with `git log -1` moving off the
pre-commit SHA plus `git show --stat HEAD`; a backgrounded commit's exit status is not
visible to you, and the guard may have exited non-zero without moving HEAD.

## 24. A carrier with ZERO runs: prove the skip is intentional, then carry the CI referent by product identity

Board/evidence-only commits are routinely pushed with a skip marker, and such a carrier
returns **zero check-runs AND zero workflow-runs**. That is the workflow's path filter
working, not an outage and not green — measure both surfaces before saying anything about CI:

```bash
gh api repos/<org>/<repo>/commits/<40-sha>/check-runs --jq '.total_count'
gh api "repos/<org>/<repo>/actions/runs?head_sha=<40-sha>&per_page=20" --jq '.total_count'
git log -1 --format='%s' <40-sha>        # skip marker: [ci skip] / [skip ci]
```

Both zeroes plus a skip marker in the subject means no gate ever saw that tree. Record the
carrier as `no CI evidence (by design — board-only, skip marker)`, never as green, and never
let "no runs" become "CI unavailable" without checking the marker.

The honest referent is the newest SHA that DID carry runs, and tree identity is what makes it
honest — scope the diff to the paths the gates actually compile or lint, so board/report/docs
churn cannot mask a product difference:

```bash
git diff --quiet <ci-sha> <tip> -- cmd internal Makefile go.mod go.sum vendor .github \
  && echo product-identical
```

Byte identity over the product paths upgrades the referent from "an older green" to "the same
code, graded": cite the run ids (with attempt number) of that SHA beside the identity proof.
Without the proof, a SHA that merely shares an ancestor with the carrier proves nothing — the
delta could be a real product change that never ran. And keep the two claims separate in the
record: the CARRIER is untested, the CODE is graded at `<ci-sha>`.

## 25. The same defect filed N times is structural — audit the remediation path, not the artifact

A deploy/drift/version finding that has been filed and closed several times against the SAME
artifact is not a run of careless operators. The recurrence is the signal: the path the operator
is told to take re-creates the condition, so each fix is undone by its own repair. Count the
history first — it is the argument the row needs:

```bash
jq -r 'select(.id|startswith("<FAMILY>")) | [.id,.status,(.completed_at // "-"),(.title // .summary // "")] | @tsv' \
  .coding-hermes/board/tasks.jsonl | sort -k3
```

Several `complete` rows on one artifact, the last one closing shortly before the symptom
reappears, is a loop. Then read the GATE's own advice: grep the checker for the string it
prints on failure and follow that command's fallback branch.

```bash
grep -rn 'fix:' <checker-or-Makefile>          # the hint text the operator obeys
sed -n '<hint-target recipe>' <Makefile>       # does its no-artifact branch rebuild from HEAD?
```

When the printed remedy builds from the checkout (because the staged artifacts are absent), the
artifact it installs reports a `dev`/pseudo-version, which is exactly the drift the checker
just flagged — the gate instructs the operator to recreate the defect. That contradiction IS the
finding; file it against the install path, not against the operator and not against the
checker's threshold.

Two supporting measurements make the row dispatchable:

- **Localise the drift to a copy**, not to "the deploy": list every candidate on `PATH`
  (`command -v`, `go/bin`, `/usr/local/bin`) and print `go version -m` per copy — `vcs.revision`
  plus its ancestry relative to the last tag tells you which copy is dirty and which is clean, so
  the fixer is not asked to repair binaries that never drifted.
- **Quote the comment that forbids the behaviour**, when the repo carries one beside the
  offending branch. A tracked comment saying "a checkout build reports dev, which is the drift
  this target exists to prevent" turns the finding from opinion into a design violation.

Acceptance criteria must close the loop rather than re-running the remedy: a committed test for
the no-artifact branch, and explicit prohibition of the two tempting shortcuts — cutting a
release to supply the missing artifacts, and re-running the install without staged assets.
Park it at the severity of a remediation defect (it blocks clean evidence, not the code), not at
the severity of the release blocker it keeps re-opening.

## 26. A repo-wide guard red on a path the GATED job never lints is pre-existing debt, not this cut's red

The commit-time guard and the CI job that gates the release routinely lint DIFFERENT scopes:
the guard runs its static analysis over the whole tracked tree, while the workflow runs
`mypy src/ scripts/`, `golangci-lint ./cmd/... ./internal/...`, or `ruff check src`. On a tree
where both are true, guard-red AND CI-green can hold for months — so a cut lane that reads the
guard red as "I cannot commit this release" blocks work it is authorized to ship, and one that
bypasses silently deletes the guard's meaning on that tree.

Classify with three cheap reads before deciding anything:

```bash
G=$(ls -t .gitreins/logs/guard-*.log | head -1); grep -nE 'error|FAIL' "$G" | head
git diff --name-only <last-tag>..<candidate> | grep -c '<path named in the finding>'   # 0 => pre-existing
grep -nE 'mypy|golangci|ruff|eslint|lint' .github/workflows/*.yml                      # the GATED scope
```

Zero commits touching that path in the range plus no CI step whose scope includes it makes the
finding pre-existing and outside the release's reach. Then:

- **Not product red.** Do not block the cut on it, and do not re-census semver for it.
- **Not yours to fix.** A releng satellite verifies, it does not develop; a tree-wide lint debt
  is a worker row with its own blast radius. "Closing a red the lane is permitted to fix" covers
  reds the RELEASE gate actually rests on, and this one is not among them.
- **Still not silently bypassed.** Commit with the bypass, and the message body carries the
  finding at `file:line`, the words "pre-existing, outside the CI <job> scope (<scope>)", and
  the hosted run/job that is the authoritative gate. File one row for the ambient red with both
  acceptable exits — fix the finding, or narrow the guard's scope to the gated one in the
  harness config. An unfileled ambient red is re-derived by every later pass and teaches lanes
  that gate output can be ignored, which is the expensive half.

When the same guard's tests leg SKIPS because a detached worktree ships no venv, that is an
ABSENT leg — quote it as absent, never as a pass — and let the hosted exact-SHA run carry the
tree. The two disclosures belong in one paragraph: red finding out of scope, tests leg absent,
hosted run authoritative.
