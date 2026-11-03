---
name: coding-hermes-hardening-loop
description: "Use when hardening an existing system end-to-end in a self-sustaining loop — one row per worker, coordinator-verified proof, deploy as the test, quorum between waves."
version: 1.1.0
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

## Goals, subgoals, and the feeder — one request, many ticks

A single user request must produce **many completed ticks**, not one polished partial. The
mechanism is three layers that all have to be real, or the work stops when attention does:

1. **The goal** — one statement of the end state plus its gates, in the user's terms:
   *what a stranger will be able to do when this is done, and how we will know.* Write it
   down where it survives a context loss (the goal surface, and mirrored as the loop's
   contract row). Include the non-goals and the owner decisions it does not cover, so the
   loop cannot drift into them.
2. **The subgoals** — sequenced, outcome-based, each one **independently dispatchable and
   independently verifiable**. A subgoal is sized to one worker turn and one coordinator
   verification: "the panel states its posture, proven on a live build", not "improve the
   UI". Map every actionable subgoal to the owning board row(s); a subgoal without a row is
   lost from the loop, and a row without a subgoal is invisible to the goal.
3. **The feeder** — the mechanism that turns *finished work* into *next work* without the
   user asking again. In practice:

   - **Completion is the trigger.** Each background worker exits with a notification; that
     batch is your cue to verify → merge → close → dispatch the next row. Never end a turn
     at "dispatched" unless a process is in flight whose completion will wake you.
   - **The board is the durable queue.** Rows, not your memory, hold what is left. Any turn
     can be resumed by reading the top open rows and the loop contract row.
   - **A heartbeat for quiet stretches.** When nothing is in flight and nothing is blocked,
     a cron tick (or the foreman's own schedule) keeps the loop turning; when something *is*
     in flight, the completion notification is the heartbeat and an extra tick is noise.
   - **One dispatch per lane, check before you add.** Read what is already running before
     starting another worker, so a resumed session cannot double-dispatch the same row.
   - **The terminal subgoal is always an evaluation pass** — re-read the goal, inspect the
     evidence, and append new bounded subgoals *only* where a verified premise justifies
     them, then re-append the evaluation. The loop feeds itself from evidence, never from
     the wish to stay busy.
   - **A terminal evaluation the loop cannot WRITE is prose, not a loop.** Stating "append new
     subgoals" in this skill does not persist anything: name the surface the evaluation writes
     to, and make each appended item carry an artifact. Concretely, the evaluation pass must
     (a) APPEND to the standing goal's own subgoal list on its persistence surface — never
     restate the intent in a report — and (b) create or name a board row with acceptance
     criteria and a falsifier for every subgoal it adds. Then read the state back: a subgoal
     that exists only in a transcript or a chat summary was never added. An evaluation whose
     subgoals have no rows is unjudgeable and the loop spins on it; a row with no subgoal is
     invisible to the goal.

**Check the feeder before believing the loop is turning.** "Self-sustaining" is a claim about a
mechanism, and the mechanism is inspectable in one step. Read the goal's own state row (status,
turns used, last verdict, last turn timestamp, subgoal count) and grep the feeder's prompt for
the re-append clause. A goal sitting at one turn with a single restated subgoal, days stale,
is the signature of a feeder that stopped — not of work in progress. The three ways a feeder
dies silently, each of which looks identical from the outside: it is disabled; its prompt never
carried the re-append clause (so it finishes iterations and never adds the next one); or it
points at a different board than the goal's work, so it is busy and irrelevant. Report which
one it was, and do not re-enable a feeder whose prompt lacks the clause — repoint or rewrite it
first, or you buy more turns of the same stall.

**Partial work is a named state, not an acceptable stop.** Before ending a turn, answer one
question: *is there an executable subgoal and nothing in flight?* If yes, that is not a
stopping point — dispatch it. If you are blocked, name the blocking row and the decision it
needs, then move to the next executable subgoal rather than idling behind it. The loop stops
only when (a) the acceptance flows pass on the deployed artifact and the open-row census is
zero, (b) it is waiting on an owner decision that is explicitly recorded, or (c) the user
stops it. Everything else is "in progress" and must have a live feeder behind it.

**Report per batch, not per tick.** One consolidated message when a completion batch lands:
what is now true and measured, what is in flight, what is blocked and on whom. Never let the
feeder's own noise become the report.

## One iteration, in order

1. **Pick ONE row.** Highest severity first, but prefer a bundle *only* when the
   rows share one seam (same function, same fail-closed question). Bundling
   unrelated rows buys merge conflicts, not speed. **Size check first:** if the
   top row's criteria span two seams — e.g. a live-artifact proof *and* a scheduler
   record/executor change owned by other open rows — it cannot be closed in one
   iteration. Annotate it with a `foreman_note` naming the owning rows and the
   reduced criteria, then take the highest row that can be *closed completely*
   today. One closed row beats two half-rows, and the note stops the next session
   re-implementing a sibling's seam.
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
- **The alert nobody reads.** A detector whose output is a log line or an append-only
  JSONL that no process consumes is the "exited 0 having done nothing" lie one layer
  up: the operator still learns about the outage by looking. Before closing a
  watchdog row, name the consumer; if none exists, file the delivery gap as its own
  row and say so in the closed row's residual list. Check whether the fleet already
  has an alert file with no reader (a sibling alert JSONL with zero grep hits in
  scripts and repos is evidence, not coincidence) before copying that pattern.

## Sequencing notes that keep the loop alive

- **Merge discipline beats speed.** Only the coordinator merges and pushes; a worker's
  branch is input, never truth. When a worker fails to commit (stale base, red gate
  from a sibling's bug), take its clean patch to a fresh worktree off current
  `origin/main` and land it yourself after re-running the gates.
- **A dead seat is not a finding.** A judge that exits non-zero with a stub, or
  thinks for an hour and returns nothing, produced no evidence; replace it with a
  *different* family rather than counting it. Report the substitution.
- **Keep a deployable artifact current.** Redeploy after each wave that changes
  behaviour a human will test, re-seed its demo data, and restart any demo helper
  process you rely on — then verify with a real round trip, because "the container
  is up" is not "the flow works".
- **File the gap you did not close.** Every honest residual ("Postgres variant not
  run", "busy-409 not reproducible", "handshake door measured by tests only") goes
  into the closed row's summary *and*, when it is real work, into its own row.
- **A rendered continuation is not the state row.** The loop advances by judging a
  *render* of the goal, and that render can truncate a long criteria/subgoal list without
  signalling it — so an agent enforcing only what the continuation showed quietly stops
  enforcing whatever fell off the end. Re-read the persisted state row and diff it against
  the continuation before concluding a criterion was dropped or a subgoal finished; keep the
  board rows as the durable contract and treat the goal as cadence, not truth.

## The fleet's own audit — what "broken feeder" actually looks like at scale

Across all 36 goal rows in `~/.hermes/state.db`: the skill's directions were right and the fleet
was still failing all of them, in three specific ways:

1. **Four rows sat `active` with nothing feeding them** — last turns 107h, 159h, 376h and 686h old.
   `active` is not a claim that the loop is running; only `last_turn_at` is.
2. **A goal pinned at `turns 1/20`, verdict `wait`** ("the agent has only dispatched subagent waves
   and is waiting on them") for **16 days**. `wait` is the quietest death: it looks like patience.
   If `last_verdict == wait` and `waiting_on_delegations == 0`, nothing is coming and the loop is
   dead while reading as healthy.
3. **Subgoal decay, exactly as predicted.** The 28-subgoal goal ended with four consecutive
   subgoals whose entire text is `coding-hermes-bankai` — a restated name, no artifact, unjudgeable.
   Its last verdict (`continue`) adjudicated a turn that "reports a test run but provides no
   concrete evidence" — the judge was right and the loop still advanced, because criteria the
   judge cannot falsify default to pass-through.

**The audit is one query, not an essay** — the goal row itself is the evidence:

```sql
select key, value from state_meta where key like 'goal:%';
-- then per row: status, turns_used, last_turn_at, last_verdict,
--               waiting_on_delegations, len(subgoals), and whether each subgoal names an artifact
```

Run it before believing you armed a loop, and again before reporting one as "running". Report the
count of `active` rows against the count of rows with a `last_turn_at` newer than the feeder's
cadence — the gap between those two numbers is the number of loops that died and were never buried.

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
- `references/goal-loop-mechanics.md` — the concrete persistence surface for goals and
  subgoals (`state_meta` → `goal:<session_id>`), the arming API with its read-back, and the
  one-pass diagnosis of a feeder that stopped — **plus what the engine actually does when
  probed (barrier expiry is lazy and nothing wakes a parked goal; `add_subgoal` accepts
  duplicates; no repeat-verdict detector exists) and a throwaway-session probe script that
  exercises all three without calling a model.**
