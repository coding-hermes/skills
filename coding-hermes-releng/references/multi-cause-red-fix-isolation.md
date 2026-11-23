# Multi-cause red → isolation-proof landings

For a matrix gate that is red on one platform with SEVERAL independent causes. The goal is
causal proof per fix, not a plausible-looking green: a combined branch that turns the board green
does not show which change fixed what, and a fix that merely RESHUFFLES the reds reads exactly
like a fix.

## 1. Split the red into causes before writing any code

```bash
gh run view <run-id> --json jobs \
  | jq -r '.jobs[] | select(.conclusion=="failure") | ".\(.name) \(.conclusion)"'
gh run view <job-id> --log-failed | grep -E 'FAIL|--- FAIL|expected|Not equal' | sort -u
```

Group failing tests by the code path they exercise, not by the file they live in. Two causes look
like one when they fail in the same package. Read the failing test bodies and trace each assertion
to a distinct platform branch — the group is a cause only when you can name the mechanism
(an open mode, a missing empty check, an unset env var read without a fallback) that makes it fail
on that GOOS and pass elsewhere.

## 2. One cause per branch, one worker per branch

- Worktree per cause from the CURRENT default-branch tip: `git worktree add ../<repo>-wt-<cause> -b wt/<cause> origin/main`.
- The worker brief names the failing test names verbatim and the mechanism; its proof obligation is
  "the other cause's tests remain the ONLY reds".
- Add a regression test only if it can FAIL on the platform where it is judged — see the test-rigour
  rule below.

## 3. The isolation run is the evidence

Open each fix as its own PR and read the failing set on the real runner:

```bash
gh pr checks <n>
gh run view <run-id> --json jobs --jq '.jobs[] | "\(.name) \(.status)/\(.conclusion)"'
```

The isolation run is correct when branch A's run is red on exactly branch B's tests and nothing
else. Write that pairing into the PR body as a table (cause → branch → tests cleared → tests still
red), because that table is the only artifact that shows causation after the branches are closed.

If branch A's run turns a test red that was GREEN before it, A is wrong or the causes were
misgrouped — re-attribute before combining. Never combine two branches whose individual runs were
never observed.

## 4. Combine, merge, and keep both fixes attributable

```bash
git worktree add ../<repo>-wt-combined -b wt/<combined> origin/main
cd ../<repo>-wt-combined && git cherry-pick <fix-a> <fix-b>
git push -u origin wt/<combined> && gh pr create --base main --head wt/<combined> ...
gh pr merge <combined> --merge --body "<table + isolation run ids>"
```

Merge with `--merge`, never squash: each fix must stay an individually attributable commit on the
default branch. Then close the isolation PRs with an explicit "superseded by <combined>, merged as
<merge-sha>" comment so the per-cause evidence stays discoverable instead of rotting as an
abandoned draft.

The receipt is the GATE JOB on the MERGE COMMIT (`gh run view <id> --json jobs` naming each matrix
leg), not the PR head, and not a top-level `conclusion: success`. Quote the legs that were red.

## 5. A running job is not a verdict, and an empty log is not a failure

`gh run view <id> --log` (and `--log-failed`) returns EMPTY while a job is still executing — no
lines is "not started" or "mid-step", never "failed". Resolve the state at job and step level:

```bash
gh api repos/<org>/<repo>/actions/runs/<id>/jobs \
  --jq '.jobs[] | "\(.name) \(.status)/\(.conclusion)", (.steps[] | "  \(.name) \(.status)")'
```

Decide the merge on the gate job. A slow non-gate job (a multi-arch container build, a coverage
upload) still running at merge time is reported as IN FLIGHT with its run id — never waited on as
if it were the gate, and never described as green. Blank conclusions in a `gh run list` row mean
queued or running; re-query rather than infer.

## 6. A judge FAIL for test rigour is a real finding

Verdict shapes like `tier1 PASS / tier2 FAIL — the new test passes against the pre-fix code on the
judging host` are correct when the guard branch under test is only entered on the failing GOOS:
`setDefaultPaths` reading `APPDATA` inside a `windows` branch cannot be exercised by a Linux runner,
so the assertion is a no-op there.

Do NOT rewrite the acceptance criterion, loosen the assertion, or re-file the row so a re-judge
passes. Read the test, confirm the mechanism, file a test-rigour row whose acceptance is an
injectable OS/env seam plus a table-driven case per platform, and leave the parent row OPEN with a
note stating the behaviour is fixed and proven while the guard is not. Say in the delivery that the
judge flagged rigour, not behaviour, and that the row was deliberately not closed.

## 7. Scratch probes without destructive commands

An unattended gate refuses `rm -rf`-shaped compound commands — a blocked command is a NON-RUN, so
build the probe out of additive parts instead of retrying a destroyed-copy pattern:

- read file contents at a revision with `git show <sha>:<path>` — no checkout needed;
- create a fresh detached tree per probe: `git worktree add --detach <scratch>/<lane>-<slug> <sha>`;
- never reuse a directory name by deleting it; use a new unique name and report it.

## 8. Do not carry the same blocker pass after pass

If previous passes filed the same red gate and nobody landed a fix, the next pass's job is a bounded
fix inside the wave budget, not another identical finding. State what changed since the last pass
(new attribution, a landed fix, a measured cause) instead of restating the blocker — a lane that
re-reports the same blocker five times has produced nothing but five records.
