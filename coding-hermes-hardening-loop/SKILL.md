---
name: coding-hermes-hardening-loop
description: "Use when hardening an existing system end-to-end in a self-sustaining loop — one row per worker, coordinator-verified proof, deploy as the test, quorum between waves."
version: 1.0.0
author: totalwindupflightsystems
license: MIT
metadata:
  hermes:
    tags: [hardening, verification, loop, coordinator, live-proof, quorum, deployment, 錬成]
    related_skills:
      - coding-hermes-foreman
      - coding-hermes-worker
      - coding-hermes-quorum
      - coding-hermes-plus-ultra
---

# 錬成 HARDENING LOOP — The Forge

## 錬成の精神 — The Philosophy of the Forging

錬 (ren) is smelting: ore into metal. 成 (sei) is completion: the thing that
holds its shape. 錬成 is not "make it bigger" — it is *heat, strike, inspect, heat
again*, until the metal stops moving under its own weight.

The loop exists because a finished feature and a true claim are different objects.
A worker says "done"; a commit says "changed"; only your own measurement says
"works". This skill is the order of those three, repeated until a *stranger's*
skepticism runs out.

## When to use, and when not

Use when the question is **"is this actually true yet?"** — an existing system that
must be made trustworthy under adversarial review and then deployed: a UI a
non-author will touch, a security boundary, a durability claim, a protocol's
honest vocabulary.

Do not use for greenfield feature buildout (that is the foreman's tick), and do not
use it to re-litigate a plan: the loop consumes *defects*, never opinions.

## The contract row is the loop's spine

Write the loop itself onto the board as a row (goal + gates + the subgoal rule).
Every iteration then points at a row, so the loop survives a context loss: a new
session reads the top rows and continues. Without this row, "keep improving" is
prose and dies with the session.

State the whole contract in that one row: top open row → one worker → isolated
worktree → coordinator verifies by exercise → merge only on reproduced evidence →
deploy and re-run the real flows → adversarial review of the landed diff → file
every new gap as a new row → repeat.

## One iteration, in order

1. **Pick ONE row.** Highest severity first, but prefer a bundle *only* when the
   rows share one seam (same function, same fail-closed question). Bundling
   unrelated rows buys merge conflicts, not speed.
2. **Write the brief to a file** (never inline in a command string — quoting dies).
   The brief carries: the measured defect with file:line, the requirement, the
   boundaries (what NOT to touch), the exact tests to run, and "show each new test
   failing against pre-change code". A brief without a falsifier produces a
   plausible patch.
3. **Dispatch into its own worktree**, fresh from `origin/main`. Two workers at a
   time is the sane ceiling on a shared box; watch loadavg, not vibes.
4. **Strip worker board hunks** — workers must not write the board; when they do,
   `git checkout origin/main -- <board paths>` then `--amend` before rebasing.
5. **Rebase onto current `origin/main` and count deletions.**
   `git diff --name-status origin/main..HEAD | grep -c '^D'` — a branch cut before
   a sibling merge will happily *delete the sibling's new files*. Zero deletions is
   the expected number; every deletion is a stale-base revert you must restore.
6. **Build, vet, run the targeted suites yourself.** "Tests pass" from a worker is
   a claim; the exit code is the fact.
7. **Exercise the artifact — with a control.** For each claim, run the real thing
   (binary, container, browser, two instances) and, separately, run the same test
   against pre-change code to prove the test *can* fail. A test that cannot fail is
   decoration. Prefer the control that would have caught the original defect.
8. **Merge `--ff-only`, push every remote, close the row in the same breath** — with
   the measured numbers, the named codes, and the honest residual gap, never a
   summary of intent. Close-and-push together so a sibling cannot land on a tree you
   already moved.
9. **Deploy as a test.** A merged tree is not a running system: rebuild, redeploy,
   and re-run the user-visible flow. Deployment is where build-vs-source drift,
   migration portability, and edge-proxy assumptions surface — the three classes no
   per-branch verification catches.
10. **Re-review between waves, not after every commit.** Convene 2–3 adversarial
    seats from *different* model families, each asked one question that cannot be
    answered "looks good": *did the fix fix it, or move the lie one layer down?*
    Every finding becomes a row in the same session that read it; a finding that
    lives only in a transcript is gone.

## Where the lies hide — check these before declaring a wave done

- **The status line.** A UI that prints "ok" while discarding the backend, auth and
  build identity it already fetched. Make the panel state the posture the server
  reports, and render a non-durable backend in words.
- **The success word.** `delivered` for `leased`/`acked`/`expired`, a canned body
  counted as an answer, a message consumption reported as work completion. The
  vocabulary must name what happened; a cut budget is its own outcome, not a success
  and not a refusal.
- **The label that asserts more than the code did.** A verdict called *verified*
  that only established *reachable*; a publisher identity taken from a header and
  recorded as if it were a signature; a handshake that is bypassable by omitting the
  header that triggers it. Either prove possession or rename the verdict — never
  leave the strong word on the weak proof.
- **The control that cannot work.** A button that posts a payload the server is
  required to refuse; a field the page never sends.
- **The local-leg-only check.** Authorization enforced on the request you received
  but not on the one you forwarded. Every hop re-runs the same check, and every
  refusal is recorded where the operator reads it.
- **The fail-open fallback.** A type assertion that, when it fails, calls the
  unguarded path instead of refusing. Composition bugs are security bugs once the
  guarded path is the only thing doing the checking.
- **The silent default.** A knob whose safe value changes behaviour the operator
  cannot see. Name it at startup, in the status payload, and — when it degrades what
  the page can do — on the page itself.

## Sequencing notes that keep the loop alive

- **Merge discipline beats speed.** Only the coordinator merges and pushes; a worker's
  branch is input, never truth. When a worker fails to commit (stale base, red gate
  from a sibling's bug), take its clean patch to a fresh worktree off current
  `origin/main` and land it yourself after re-running the gates.
- **A dead seat is not a finding.** A judge that exits non-zero with a stub, or
  thinks for an hour and returns nothing, produced no evidence; replace it with a
  *different* family rather than counting it. Report the substitution.
- **Keep a deployable artifact current.** Redeloy after each wave that changes
  behaviour a human will test, re-seed its demo data, and restart any demo helper
  process you rely on — then verify with a real round trip, because "the container
  is up" is not "the flow works".
- **File the gap you did not close.** Every honest residual ("Postgres variant not
  run", "busy-409 not reproducible", "handshake door measured by tests only") goes
  into the closed row's summary *and*, when it is real work, into its own row.

## Anti-patterns

- Closing a row on a worker's report, a tick, or a spec paragraph.
- Rerunning a flaky test until green and calling it fixed (file the flake instead).
- Letting the same session both write and bless a change without an outside reader.
- A "verification" that only greps for a string the change itself added.
- Ten clean merges over a red `main`: run the merged tree's own gates before you
  believe your own wave.

## References

- `references/worker-brief.md` — the brief skeleton that produces falsifiable work.
- `references/live-proof.md` — how to write a proof script that can fail, and what a
  good control looks like.
- `references/board-closeout.md` — the close-out summary shape (measured, numbered,
  residual gap named).
