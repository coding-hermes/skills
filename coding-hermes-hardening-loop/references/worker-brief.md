# Worker brief skeleton

A brief is a falsifier, not a to-do. Fill every section; a brief that cannot fail
will produce a patch that cannot be checked.

```markdown
# WORKER BRIEF — <ROW-ID> (<severity>): <one sentence naming the defect, not the fix>

Worker in a coding-hermes wave. Repo: this worktree, branch `wt/<ROW-ID>` (from current
`origin/main`). Commit on this branch. DO NOT push, merge, or edit the board.

## The measured defect

<What is true today, with file:line and the exact observation. Quote the returned
error/JSON, not a paraphrase. If it was found by review, say which review and on what
build. Never write "may be" — if it is unmeasured, the first task is to measure it.>

## What to do

1. <Requirement, phrased as observable behaviour.>
2. <The named code / verdict / field the operator will see.>
3. <The disclosure: which spec/doc paragraph must state the new truth, dated.>
4. <What must NOT change — the path that already works.>

## Boundaries

- Do not touch <sibling subsystem>, the guard config, or the board.
- Do not weaken <existing contract> to make the new behaviour easy.
- Do not invent a second spelling for an existing outcome/code.

## Tests

- `go build ./...`, `go vet ./...`   (<adapt to the project's real gates>)
- Targeted: `<packages>`
- **Every new test must be shown to FAIL against pre-change code** — state how you
  checked (stash, checkout of the old file, a copied test file on the base commit).

## Deliverable

One commit on `wt/<ROW-ID>`:

    <type>(<scope>): <what changed and why, in the repo's commit convention>. Addresses <ROW-ID>.

Final message: <the exact evidence the coordinator will try to reproduce — named
codes, JSON shapes, counts, the pre-change failure of each test — and everything you
deliberately left out>.
```

## Rules of thumb

- **One seam per brief.** Bundling is for rows that touch the same function and the
  same fail-closed question; otherwise the merge, not the work, becomes the risk.
- **Name the residual.** "Not measured: <x>" in the brief tells the worker that
  stating a gap is expected, not a failure — which is what stops the invention.
- **Give the escape hatch a name.** When a requirement can be met two honest ways,
  say "choose and state which" — otherwise the worker guesses what you wanted and
  hides the choice in a commit body.
- **Never let the brief promise a feature that is an owner decision.** Point at the
  blocking row id instead.
- Put demo/repro commands in the brief only when they are safe to re-run: no `pkill -f`
  whose pattern matches the worker's own argv, no fixed ports without a free-port check.
