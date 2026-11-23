# Controlled-pair attribution: same tree, two runs, different results

A release lane constantly faces this: the candidate advanced, the tree looks unchanged, and CI is
red in a different place than last time. The reflex — "same tree, so my earlier verdict carries" —
is wrong for a CI run and right for a build. This page separates the two.

## Establish the pair

Two commits form a controlled pair when their MATERIAL path diff is zero:

```bash
git diff --name-only <older-candidate>..<newer-candidate> \
  | grep -vE '^(\.coding-hermes/|\.gitreins/|docs/|CHANGELOG\.md|README\.md)' | wc -l   # 0 = pair
```

The exclusion set is the BUILD-carry set, not the decision set: docs and the changelog do not enter
the compiled tree, but they are exactly what a release decision reads. Zero material paths means the
build/test/package legs carry; it never means the CI sample carries.

## What a pair lets you assert

Compare the FAILING SET, not the run badge — a run's conclusion is an AND, and one flaky arm hides
everything else.

| Observation across the pair | Conclusion | Action |
|---|---|---|
| The same test fails in both runs | Deterministic on this source | This is the release blocker; file or patch exactly this test |
| A test fails once and passes once | Environment-shaped | Do not let it block a cut; hand it to the test's owner as its own row |
| A whole job reds once and greens once | Runner/infra sample | Re-run before attributing anything to the product |
| Different GATES red on identical source | Gate inputs are not functions of the tree | Cite both run ids; never claim the tree regressed |

Language discipline follows from the table. "Deterministic red on <test>" requires both runs showing
it. "Flake" requires both runs showing different outcomes on identical source — one red is not a
flake, and one green is not a fix. Anything else is "unmeasured, one observation", stated as such;
the same lane will read that sentence back next pass as fact if it is stronger than the evidence.

## Read the run's own verdict before reading its failures

Assert the run's conclusion first: `gh run view <id> --json status,conclusion,headSha`. A
`--log-failed` dump is only meaningful for a COMPLETED run that actually failed. While the run is
still in progress, or after a fail-fast cancellation, the dump comes back empty or one line long —
and an empty failed-log is inconclusive, never green. An empty dump that sits beside a red
conclusion means the log window, not the tree, is what you measured; re-query the run instead of
reporting either verdict.

A matrix arm cancelled by fail-fast contributes NO failing set. Only the arm that actually ran has
one, so write "arm <x> red with <n> failures, arms <y>/<z> cancelled" and treat the missing arms as
unmeasured rather than implying the whole matrix was judged.

The discipline extends to a bookkeeping carrier: a carrier whose run reproduces the IDENTICAL failed
count and failed-test names proves the carrier transported evidence, not source — the red conclusion
still belongs to the candidate, and the carrier must never be cited as the green run. Identical-set
comparison is the receipt; "it only touches docs and the board" is the assumption.

## Environment-shaped tests

A test is environment-shaped when its fixture is derived from host truth rather than from a fixed
input: the root filesystem's backing block device, mount layout, `/proc` counters, device-mapper or
overlay/CoW roots, core count, kernel version, free space, interface MACs.

The failure mode to name precisely: an assertion that walks `/sys/block` looking for a whole-disk
device that HOLDS the root partition fails on any image whose root is a mapper/CoW device, because
no physical disk holds that partition — the chain terminates at `dm-N`. Same source, same test,
different host image, opposite verdicts.

The remedy is never "loosen until it passes". Either resolve through sysfs truthfully (walk
`/sys/class/block/<dev>/slaves/` recursively and continue through virtual devices) or SKIP loudly
with a named reason in the test output. A silently-passing assertion is the defect this class exists
to produce, and a silent SKIP is a different lie — the reason string is the deliverable.

## Reporting the pair

Put both run ids, both commit shas, the observed failing tests per run, and the material-diff count
in the same block; a reader must be able to re-derive the split without rerunning anything:

```
run         commit    unit-tests   host-topology arms   toolchain arm
<run-a>     <sha-a>   failure      3 failed             failed
<run-b>     <sha-b>   failure      3 passed             failed
```

That table is what converts "CI is red" into "one deterministic blocker, one infra-owned row". Do
not compress it to a sentence in the verdict; the table is the evidence.

## Consequence for the decision

A red run whose only deterministic arm is a blocker row already filed changes nothing about the tag
decision, so the verdict stays NO CUT — but say WHY it is NO CUT (the deterministic arm), not merely
that a run is red. Conversely, if the pair shows the deterministic set is now empty and only
environment-shaped arms remain, the decision is "green except for infra arms" and the honest move is
to escalate or re-run with the owner's knowledge — never to quietly call it green.
