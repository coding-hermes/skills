# Posture-sweep integrity — measuring and publishing a public-surface audit

Depth for the releng posture sweep. Load when a tick re-measures a posture row that already exists,
when the audit doc becomes a tracked artifact of the same repository it grades, or when a head/lineage
count is about to be quoted.

## Count the ref surface from git, not from the API's first page

`gh api repos/<o>/<r>/branches` is paginated at 30 per page. A default read returns the first page
and looks like a complete census: a repo with 72 published heads printed 20 rows, and that number
then travels into a report as "20 branches".

```sh
git ls-remote --heads <published-url> | wc -l          # the count
gh api repos/<o>/<r>/branches --jq '.[].name'         # names, page 1 only
```

A fresh `git clone` makes the same mistake from the other side: it fetches only the default branch,
so `git rev-parse gh/master` fails with `unknown revision` on a head that IS published and the
lineage question reads as "absent". Fetch every head before measuring or declaring anything absent:

```sh
git remote add gh <published-url>
git fetch gh '+refs/heads/*:refs/remotes/gh/*' --tags
git rev-list --left-right --count gh/<other>...gh/<default>
```

A returned pair like `772 753` is the finding: disjoint lineages, not a lag. Pair it with an
anonymous-reachability probe (`curl -s -o /dev/null -w '%{http_code}' <raw-url-of-an-internal-path>`)
and quote the code — a 200 from an unauthenticated client is the difference between "an old branch
exists" and "internal material is published".

## A posture number is a timestamped measurement with a delta

Re-measure every leg at the tip being audited and print the previous figure beside it. The delta is
the finding: `331 files / 1267 occurrences` becoming `550 / 2554` in two days says the publishing
workflow is the driver, which is stronger than any single count. Probe with the SAME scope flags as
the row that owns the gap (`-o` occurrences vs `-n` lines, and which paths are excluded) or the two
numbers are not comparable and the delta is noise.

When the growth driver is mechanical — every judge bundle committing patch/verdict files that embed
absolute worktree paths — the remedy belongs in the owning row's acceptance criteria as an ordered
ladder (stop publishing the path, add a gate with a proved-red arm, name the target count), not in a
fresh duplicate row. One row per posture CLASS; a second row for the same class splits its closure.

## A scan that cannot finish inside its budget is UNVERIFIED, never clean

Bound every leak/posture scan by wall time and record the bound beside the result. A full-tree secret
scan on a repo carrying large generated, data or verdict directories routinely runs past a couple of
minutes; the probe is then killed and leaves NO result — "no findings before the kill" is not a clean
bill, and "the scan is slow" is not a posture finding either. Record the leg as UNVERIFIED naming the
scanner, the budget and the fact it was not re-run, and put "a scanner that completes on this tree"
into the row's acceptance criteria so the gap is closable rather than re-attempted into the same
timeout by every later pass. Never narrow the scanned tree to make it pass without saying you did.

## Split `git grep` output on the right field, and count a class twice

`git grep` against a REVISION prefixes every hit with that revision, so the path is field 2, not
field 1. `git grep -oIE '<pattern>' HEAD -- . | cut -d: -f1 | sort -u | wc -l` answers `1` — the
literal `HEAD` — beside a perfectly plausible occurrence count, and the file census then contradicts
an earlier pass for no reason at all. Split on `-f2` whenever a tree-ish is on the command line;
`-f1` is correct only for a working-tree grep. Re-derive a count before publishing it: a census that
disagrees with the previous sweep by an order of magnitude is usually the probe, not the tree.

Quote BOTH counts for any leak class on a repo that tracks judge bundles — with the bundles, and
with `':!.gitreins'` — and attribute the bundle copies to the bundle-publish fix, not to the row that
owns the literal. Tracked `commit.patch`/`worktree.patch` files re-publish whatever the diff carried,
so one address in three docs becomes a dozen hits in history: the file census multiplies while the
owned literals have not changed, and a reader given only the larger number concludes the row doubled
in severity. Extend the owning row's scope with a `--note` naming both figures instead of opening a
duplicate row, and say in the addendum which fix drains which count.

**A published total that equals one of your own subtotals is a scoped count labelled as a total.**
Before publishing a class census, print the split (`.gitreins`, board, docs, everything else) and the
per-file counts, then check the headline against them: if the number you were about to write matches a
subtotal exactly, the reader searches the wrong surface and the next pass measures a class twice the
size of the one described. Record the producing command beside the figure — a count whose command is
unknown cannot be audited, only re-derived.

**Reprinting the literal is never required to report a leak class.** Publish counts and file paths, not
the address, host path or token shape itself. An audit that reprints them joins the class it measures,
so where a repo tracks its own audit docs the lane's own artifacts become the fastest-growing
contributor to the very census being published. Measure your own share, disclose it in the addendum, and
scrub it in the same carrier — that is the one part of the class a releng lane can remove without
editing another lane's artifact.

## Publishing the carrier, and what a gate claim binds

- **A gate claim binds only the sha it was RUN on.** Grade the carrier tree, not the parent you measured
  before editing: a docs/board carrier pushed from a clone carries no commit-time hook, so nothing else
  will catch it, and "PASS measured before the addendum" is a green for a tree nobody is served.
- **Read the remote before staging.** `git log --oneline origin/<branch> -5` and the diff stat: if a
  sibling lane already landed this exact fix, drop your diff, keep theirs, and record the independent
  confirmation instead of a duplicate edit — two lanes reaching one defect minutes apart is stronger
  evidence than either alone, and the duplicate conflicts on the exact line you both changed.
- **A pushed carrier cannot be amended.** `--amend` mints a divergent sha, the push is rejected
  non-fast-forward, and force-pushing a default branch is not an option. Recover without rewriting
  history: save the final file (`git show HEAD:<path> > <scratch>/final`), `git rebase origin/main`
  (the conflict is exactly that file), write the saved final over it, `GIT_EDITOR=true git rebase
  --continue`, prove the new tip carries the gated tree (`git diff --stat <gated-sha> HEAD` silent),
  then push the follow-up commit.

A carrier that touches only board and docs does not need a GitReins judge run. Firing
`gitreins task complete` for it appends another tracked verdict bundle — the exact mechanism the same
sweep is filing as exposure — and this class of repo runs its full suite inside the commit hook,
which can outlive the tick. Run the repo's own gate at the served tip, quote its rc, and state in the
report that the judge was skipped and why.

## When the audit doc is tracked by the repo it grades

A repo that ships an audit-scope checker over its own `docs/audits/` turns the evidence artifact into
a build input: a doc line naming a scanner without naming its scope reds `tests/selftest.sh` on a tip
whose code commit was green.

- Run that checker STANDALONE immediately after writing the doc, and again after any later edit. It
  exits in under a second; the suite that embeds it does not.
- The rule is per LINE. A cell written in the first pass and a second case appended later are two
  separate claims, so adding a scan row after the checker went green re-reds the carrier alone.
- Satisfy it by STATING the scope ("working tree only; no `--log-opts`, so history is not covered"),
  never by deleting the scanner's name — deleting the word passes the checker and destroys the claim.
- Re-run the full suite at the carrier tree before committing: the doc AND the board rows both feed
  suite sections, and a green measured before the last edit proves nothing about the carrier.

## Publish consistently with what the lane just filed

A lane that files "publishing judge bundles leaks host layout" must not then publish its OWN verdict
bundle as a `chore(gitreins)` commit — that is the same mechanism, and a report naming the growth
driver while contributing to it is not evidence. Keep the verdict in the scratch clone, cite its run
directory in the row or the audit event, and say in the report that publishing it was declined and
why. The same discipline covers the audit doc itself: write placeholders (`~`, `/home/<user>/`) and
re-grep the finished file for the leak class it describes before staging it.

## Scope a public-ref deletion by sweeping every published head first

"Branch X carries internal material" is not yet a recommendation: the blast radius of deleting a ref is
the number of OTHER published heads that carry the same paths, and that number has to be measured, not
assumed. Sweep all heads for the path itself:

```sh
git ls-remote --heads <published-url> | awk '{print $2}' | while read -r r; do
  git cat-file -e "$r:<internal-path>" 2>/dev/null && echo "CARRIES $r"
done
git cat-file -e "<ref>:<internal-dir>" && echo CARRIES_INTERNAL_DIR
```

A result of `1 of 79` is what turns an owner-only destructive action into a single command
(`git push origin --delete <ref>`) with the other 78 heads untouched — quote the carrier count and the
total, and never propose deleting heads that do not carry the material. Count with `ls-remote --heads`
or `for-each-ref refs/heads`; a glob refspec undercounts because `*` does not cross `/`, so nested
`wt/<task>` heads vanish (79 real heads read as 27). Prove fetch completeness with an explicit-refspec
re-fetch that produces EMPTY output, not by comparing two counts computed the same way.

Pair the carrier scan with two independent lineage facts before calling the ref stale or divergent: an
anonymous reachability probe of the raw URL (`curl -s -o /dev/null -w '%{http_code}'`, 200 = published
today) and `git merge-base --is-ancestor` between the two lineages. Unrelated histories plus a single
carrier is a legacy lineage, not a lagging branch, and that classification is what justifies deleting
rather than merging.

## Preserve a ref outside the repo before asking for its deletion

A public repo must not receive the preserved blob as a tracked file — preserving by committing a bundle
joins the exposure class it is meant to close. Bundle it OUTSIDE the repository instead, then verify and
hash it:

```sh
git bundle create /<outside>/<repo>-<ref>-lineage.bundle <ref>
git bundle verify /<outside>/<repo>-<ref>-lineage.bundle
sha256sum /<outside>/<repo>-<ref>-lineage.bundle      # quote it in the report
```

This converts "blocked, owner must decide" into "one command, reversible": the owner deletes a ref whose
full history survives at a named path with a named hash, which is the only form in which a destructive
owner-gated ask is reasonable to make unattended. Name the one command, and say what it does not touch.

## A row's own quoted number is not a receipt

An acceptance criterion that states a count is a claim to re-measure, not a fact to repeat. Re-run the
scanner over the exact scope the row names, quote its own output figure beside the row's, and report the
discrepancy as a finding to correct in the row — the direction of a claim routinely holds while its
number is wrong, and repeating the row's figure propagates an unreproducible number into the release
record. Do not re-derive a redacted report's body to avoid the discrepancy: when a summary read of the
report JSON is refused, the scanner's own stdout is the receipt and the report body stays unread — state
that leg as unread rather than routing around the refusal.
