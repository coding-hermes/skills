---
name: coding-hermes-stuck-lane-triage
description: >-
  Diagnose a fleet lane that keeps firing without finishing work. Separates the
  three independent facts — why it fires so often (admission mode), why ticks
  come back empty (outcome mix), and what is actually blocking it (the barrier).
  Includes the coverage-proof gate that makes residue deletion safe, and the
  reporting shape an owner can act on.
version: 1.0.0
author: Bane + Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [coding-hermes, scheduler, lane, triage, recovery, residue]
---

# Stuck lane triage

## When to Use

Load this when any of these is true:

- A lane's ticks arrive far closer together than its configured `cooldown_s`.
- Most of its recent ticks end `dry_run` / `no_changes` with 0 commits.
- The same board has sat unchanged for hours while ticks keep firing.
- An owner asks "why is this lane running fast / looping / not completing work".
- You are about to pause, re-enable, or repair a lane and need to know which of
  admission / outcome / barrier is the actual problem.

Do NOT load this for a single failed tick (that is failure attribution) or for a
lane that never fires at all (that is a cooldown-pin or scheduler problem).

A lane that fires every few minutes and produces nothing looks like a runaway
scheduler. It almost never is. Diagnose in this order and do not skip to the
fix: the frequency, the emptiness and the barrier are three different facts, and
reporting one as if it were another is how a lane loops for days.

## Step 1 — explain the FREQUENCY (admission mode, not a bug)

```bash
DB=~/.hermes/coding-hermes/scheduler.db
sqlite3 -line "$DB" "SELECT name,enabled,admission_mode,cooldown_s,cooldown_pin_s,
  no_progress_threshold,no_progress_ticks,consecutive_failures
  FROM projects WHERE name='<lane>';"
```

`admission_mode=tasks` admits the lane **whenever the board holds pending work**,
falling back to the cooldown pin only once the board is DRAINED. With a non-empty
board the wall-clock cooldown never engages, so fast re-firing is the design
working, not a fault. Confirm with the deferral mix:

```bash
sqlite3 "$DB" "SELECT reason,COUNT(*) FROM deferrals WHERE project_name='<lane>'
  GROUP BY reason ORDER BY 2 DESC LIMIT 8;"
```

`tasks_no_work` present means the drained path is live; `cap`, `load_gate` and
`budget` mean the lane is queued behind resources, which is healthy contention.

**Why the stop-loss does not save you:** `no_progress_ticks` resets on any
commit. A lane that lands one commit every few ticks never reaches
`no_progress_threshold`, so it churns forever with a zero counter.

## Step 2 — separate the EMPTINESS from the barrier

```bash
sqlite3 -header -column "$DB" "SELECT outcome,COUNT(*) n,SUM(COALESCE(commits,0)) commits
  FROM ticks WHERE project_name LIKE '<prefix>%' AND spawned_at > '<since>'
  GROUP BY outcome ORDER BY n DESC;"
sqlite3 -header -column "$DB" "SELECT COALESCE(NULLIF(error,''),'<none>') err,COUNT(*)
  FROM ticks WHERE project_name='<lane>' AND spawned_at > '<since>'
  GROUP BY err ORDER BY 2 DESC LIMIT 6;"
```

A lane with many `dry_run`/`no_changes` ticks **and** some `committed` ticks is
not dead: something blocks it that only sometimes clears. Do not report "it is
broken". Name the error string, and name what the committed ticks did.

## Step 3 — find the BARRIER (usually the working tree)

```bash
cd <lane workdir>
git status --porcelain --untracked-files=all | wc -l
```

Thousands of paths means every write-gated step refuses.

**Classify before you act — tracked vs untracked is the whole ballgame:**

```bash
git ls-files '<suspect path>' | wc -l     # >0 => TRACKED (bloats clones + CI)
git status --porcelain '<suspect path>'    # ?? => untracked (dirties the gate)
```

An untracked barrier is cleared by quarantine or by ignoring it. A **tracked**
residue is a different repair: it is committed and clean, so it is not a
dirty-tree barrier at all — it is BLOAT. It inflates every clone and it can be
the reason code CI is red. Never assume which one you have; measure it.

Scope the proof to the directory prefix. `git ls-files | grep -c <name>` counts
unrelated files that merely carry the name in their path and reports a
tracked-looking number for a directory with zero tracked files.

## Step 4 — PROVE coverage before deleting any evidence

Residue named `rescued-*`, `*.bak`, `history-copy` is almost always duplicated
verdict evidence. Deleting it blind destroys the only copy of something.

1. Enumerate the unique `(date, run-id)` pairs in the residue.
2. Enumerate the canonical store (for example `.gitreins/history/<date>/<run-id>/`).
3. The difference — pairs in the residue but NOT in canonical — are the
   **orphans**, the only payload that can be lost.
4. Copy the orphans into the canonical store, then **re-run the comparison and
   require `orphans == 0`** before removing anything.

A residue of N task-bundles that each contain the same run-ids is N−1 redundant
copies by construction. Measure it (count how many bundles carry each run-id)
rather than trusting the word "rescued".

## Step 5 — remove, ignore, verify

```bash
git rm -r --cached --quiet <residue> && rm -rf <residue>
printf '\n<residue-glob>/\n' >> .gitignore
git add .gitignore <canonical-store>
git -c core.hooksPath=/dev/null commit -F -     # data-only; disclose the bypass
```

Verify with numbers, not vibes:

```bash
du -sh <residue parent>                          # before vs after
git ls-files '<residue parent>' | wc -l          # tracked count before vs after
git status --porcelain | head                    # must be empty
git ls-remote origin refs/heads/<branch>; git rev-parse HEAD   # must be equal
```

## Step 6 — prevent the recurrence

- Add the residue glob to `.gitignore` **in the same commit** that removes it,
  or the next rescue sweep recommits it.
- Leave the lane paused until the tree is clean, then unpause and confirm one
  tick ends `committed` rather than `dry_run`.
- If a non-empty board is what keeps admission open, that is expected. Say so
  instead of "fixing" it.

## Reporting to the owner

Give four things, and no more:

1. The lane is stopped, and by whom.
2. Ticks versus commits over the window.
3. The named barrier, and whether it is tracked or untracked.
4. What remains on the board, split into **dispatchable** / **blocked with a
   reason** / **dependent**.

A count of pending rows is not a status; the split is. For the blocked class,
quote the blocker (a disk threshold, an unreachable target, a dependency chain)
rather than the row title.

## Pitfalls

- **Tick ids are UTC while `spawned_at` is local.** An id that looks a day ahead
  of its timestamp is a timezone, not a second scheduler. Before claiming
  concurrency, verify each `completed_at` precedes the next `spawned_at`.
- **`ticks.tokens_in` bundles cache reads.** Never quote it as fresh input.
- **`admission_mode=tasks` plus a non-empty board means fast re-fire by design.**
  Do not file it as a scheduler regression.
- **A dry run is not a failed tick.** `error='no_changes'` means the lane ran and
  had nothing it was permitted to do.
- **Do not re-enable an operator-disabled lane to "test" a fix.** Verify the
  tree directly and report.
- **A duplicated bulk copy is a lane action, not an owner ruling.** Once
  duplication is proven and orphans are zero, execute the dedupe. Escalating a
  proven-redundant residue upward is how a lane burns days re-measuring the same
  barrier.
