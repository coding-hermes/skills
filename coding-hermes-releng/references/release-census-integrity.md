# Release census integrity

Three measurement surfaces in a readiness sweep lie in the same way: a cheap counter answers a question it was not asked. Each section below is a rule plus the mechanism that defeats the naive form.

## Count product commits, not carrier commits

`git rev-list --no-merges --count <lasttag>..HEAD` counts the releng lane's OWN bookkeeping. Every pass that files an artifact and a board row adds commits, so a re-fire sees a larger count against zero product change — which reads as "new work landed" and starts an argument with the previous pass's numbers.

- Measure the delta between the previous candidate and the current tip over product paths only:

      git diff --name-only <prev-candidate>..HEAD -- . ':!releng' ':!.coding-hermes' ':!reports' | wc -l

  `0` files is the delta verdict: bookkeeping only, candidate stands.
- Classify commits with the same pathspecs (`git log <range> -- . ':!releng' ':!.coding-hermes'`) so the feat/fix census and the diff agree.
- State the bookkeeping delta in the report ("tip advanced N commits, all bookkeeping") so the next pass does not re-derive it.

## Breaking changes: subject `!` and footer POSITION, never a body grep

`git log <range> --pretty=%b | grep -c 'BREAKING CHANGE'` counts PROSE that mentions the term. Commit messages and release notes routinely describe the census itself ("0 breaking subjects and 0 BREAKING CHANGE footers"), so the grep returns a positive count on a range containing no breaking change at all — and the count is exactly the kind of number a semver decision latches onto.

- Classify from the subject marker and footer position:

      git log <range> --pretty='%s' | grep -cE '^[a-z]+(\([^)]*\))?!:'
      git log <range> --grep='^BREAKING CHANGE' --oneline      # footer-positional match only

- Read the candidate lines before believing either count; a term at line start inside a quoted sentence is still prose.
- When the naive count and the footer check disagree, put BOTH numbers in the report and say which one you used. Silently dropping the noisy count looks like hiding a major bump.
- A major bump is never triggered by a count: propose it and require explicit user confirmation before tagging.

## Non-terminal CI legs: classify against their own baseline

A leg still `in_progress` on the current tip is not a stall until it is compared to what that workflow normally costs. Docker build legs are commonly tens of minutes, so a 15-minute leg reads as hung to anyone who has only seen unit-test durations.

- Get the baseline from one terminal run of the SAME workflow:

      gh run view <green-run-id> --json workflowName,createdAt,updatedAt,conclusion

- Compare elapsed time against it and report elapsed-versus-baseline inline. "Not a stall" then rests on a measurement instead of impatience.
- Every commit spawns the full push-gate workflow set, including bookkeeping carriers, so name run ids per carrier PER WORKFLOW. "CI green" hides which workflows were actually read; a partial read quoted as a whole is the most common false green in a release report.
- Poll the terminal state before a decision that depends on it, and stamp the report with the read time so a later pass can tell a fresh reading from a carried one.

## Re-fire bookkeeping keys

A tick that fires twice must not mint a second pass number and must not re-file rows an earlier fire already wrote.

- Resolve the existing key family BEFORE writing: scan the namespace partition's keys for the lane's tick prefix (`/releng/ticks/<project>/<tick-id>/pass-NN`) and read the prior pass's key.
- Name a repeat fire with a letter cap on the SAME pass (`pass-NN-fireb`, `-firec`); never `pass-NN+1`. The pass number records evaluations of the product, not runs of the scheduler.
- Write only the ledger event. No new artifact, no new board row, no carrier commit, and no rewrite of a still-pending `RELEASE-*` row — a pending row a previous fire filed stays pending, with its original timestamp.
- Verify the write by diffing the appended row's key set against the row immediately above it in the same `current.jsonl`, not against the payload you POSTed.
