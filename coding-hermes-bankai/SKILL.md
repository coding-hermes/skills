---
name: coding-hermes-bankai
description: "BANKAI: full-auto mode — finish ALL tasks, drive the fleet."
version: 1.3.0
author: Bane + Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [bankai, mode, full-auto, scheduler, ticks, goal, 卍解]
    related_skills:
      - coding-hermes-plus-ultra
      - coding-hermes-quorum
---

# 卍解 BANKAI — The Final Release

## 卍解の精神 — The Philosophy of the Release

**卍解 (Bankai)** is two characters:

- **卍 (manji)** — the ancient Buddhist seal of auspiciousness; in the Soul Reaper tradition, the mark of the zanpakutō's **true form**. The power that lives beneath the sealed state.
- **解 (kai)** — to **untie, release, unseal, unbind**. The act of dissolving every restriction.

Together: **the final release.** The sealed sword becomes what it always was — full power, unbounded, until the battle ends. **This is the mode:** when Bane speaks the keyword **卍解 / bankai**, Hermes releases every seal:

- the seal of *waiting* — Hermes stops being a passive observer
- the seal of *the scheduler's cadence* — Hermes does not wait for ticks; **Hermes manages the foremen directly**
- the seal of *single-task* — the goal is finished ALL the way
- the seal of *asking* — full autonomy within the goal's frame

**The release is unbounded — but not a runaway.** It ends when the battle ends: the goal complete and verified. The bankai timer (progress gate + iteration cap) keeps the release a release.

## The Release Command

**Trigger:** the keyword "bankai" / "卍解" with a goal. Hermes enters the mode and becomes the **dispatcher**: it launches foremen directly, one after another, until the goal is done. Like `/goal` (standing intention) but more powerful — goal sets direction; 卍解 releases the fleet to make it happen now.

**Proven:** 2026-08-22 — Bane said bankai while seeding the BANKAI game task (Temple-Run-style endless runner). Project + spec + task injected, foreman driven until the deliverable exists. (The game is also NAMED BANKAI — the name and the mode are different; the keyword is the trigger.)

## The Loop — Hermes Manages the Foremen DIRECTLY

**The scheduler's tick loop is NOT the mechanism. Hermes is.**

1. **Capture the goal** → concrete deliverables + acceptance criteria (spec files in the project dir).
2. **Engage the fleet** → scheduler project created, but **paused for the daemon** (high cooldown or `enabled=false` on the scheduler side) so the daemon does NOT double-spawn — **Hermes owns the loop**. Coding model from the SUBS (ox-alpha-free @ opencode-go, glm/kimi/qwen flat-rate, gpt-5.6-* via openai-codex OAuth). Tasks injected on the JSONL board with pass criteria + events; commit.
3. **Launch the foreman — directly** — Hermes spawns the foreman session itself via the gateway API (the same spawn path schedulerd uses: `POST http://127.0.0.1:8642/v1/responses` with the foreman prompt + the project's model/provider + `require_approval: false`; gateway key from `API_SERVER_KEY`). No cooldown, no waiting for an evaluation cycle — the launch is immediate.
4. **Watch it fall** — wait for the foreman session to complete (committed / failed / timeout).
5. **Read the task list** — the moment the foreman finishes, Hermes reads the board / task list and judges the goal:
   - **complete** → verify the deliverable against the acceptance criteria (run it, screenshot it, test it) → mark tasks done with evidence → **the release ends** → report (MEDIA files, walkthroughs) → return the project to normal scheduling
   - **not complete** → update the board (mark done / inject the next sub-task) → **launch the NEXT foreman immediately** → back to step 4
6. **The cadence is purely completion-driven:** foreman falls → task list checked → next foreman launched. The only gap is the foreman's own runtime. This is the unbounded release.

## 卍解 × WORKTREES — the release RUNS in worktrees (Bane directive 2026-09-19)

**A release that edits a checkout the daemon might still hold, or that runs two workers at once, MUST
worktree.** One worktree per task, branched off the last known good commit, merged at the end. This is
not an optimisation — it is the difference between a release that can run in parallel and one that
serialises behind a single shared index.

- **One worktree per task.** `git worktree add ~/wt-<id> -b wt/<id> <base-sha>`. **Never two workers in
  one tree:** a shared index is merge-conflict-by-construction, and one stray `git reset` wipes the
  sibling's uncommitted work (the class this doctrine exists to kill).
- **Dispatch INTO the worktree, not the main checkout.** The brief names the worktree path as THE
  workdir and carries the isolation preamble: *commit normally — do NOT stash, reset or clean; never
  merge and never push; the dispatcher merges.*
- **Wave eligibility is a FILE-SET question.** Two tasks are wave-eligible only when they share no file
  and no import root (`coding-hermes-middle-out`). Genuinely disjoint file sets is also exactly the
  precondition that makes the later merge trivial — the two facts are the same fact.
- **Merge in a scratch integration worktree.** `git worktree add -b pu/integrate <main-sha>`, merge each
  feature branch there, run the FULL battery on the COMBINED tree, then fast-forward the real branch
  (`git merge --ff-only pu/integrate`). This is what lets a release keep working while the main checkout
  is still held by a live daemon tick.
- **Re-check the base before you merge.** A concurrent commit — an amend, a fixup, a rebase — **orphans**
  the commit your worktrees were branched from, and a plain `git merge` then reports conflicts in files
  your branch never touched, because the merge base silently falls back to an older commit. Test with
  `git merge-base --is-ancestor <base> <target>`; when false, `git rebase <target>` the branch FIRST
  (clean whenever the file sets are genuinely disjoint) and merge the rebased tip. Put the base sha in
  the dispatch note so this is one command, not archaeology.
- **Record it on the row.** Every task row the release touches carries `worktree`, `branch` and
  `sessions` (boardctl supports all three) — so the BOARD, not the dispatcher's memory, is the record of
  where the work happened and which Hermes session did it.
- **Reap at release end.** `git worktree list` → every worktree must map to a merged branch; then
  `git worktree remove` + `git worktree prune`. A leaked worktree is an unmerged branch nobody is
  tracking (a fleet repo carried nine).

Cost note: worktree-per-task is not free (setup plus a merge), so it is for releases with **≥2
independent tasks**, or any repo the daemon might touch. A single-task run in a quiet checkout does not
need one.

## ⚠️ The Release Does NOT Pause Between Waves (Bane correction 2026-08-22)

**Verify-only closure pitfall (proven 2026-08-31):** a foreman tick picking a
"verify + close with evidence" task whose fixes ALREADY landed at HEAD produces
0 file changes → `commit None → guard not_run → bookkeep REJECTED`, leaving the
row pending even though the work is done. When the dispatcher injects a
verification/closure task, either (a) expect to close the row directly with the
regression-test evidence (run the tests yourself, flip the row, commit the board
chore), or (b) make the task explicitly require a tiny docs/evidence artifact so
the worker has something to commit. The foreman run still proves the code — the
bookkeep just cannot represent "verified, nothing to change" as APPROVED.

The release is **all waves, one battle** — not wave-by-wave with checkpoints. Do NOT stop after a foreman completes to report a "wave done" and wait for Bane; intermediate progress notes are fine as background chatter, but the loop continues **immediately**: verify → launch the next foreman → repeat. The only legitimate stop points (each of which must end with a full report to Bane):
1. **Goal complete and verified** (deliverables run, tests green, board flipped, scheduler restored) → release ends.
2. **Progress gate tripped** — two consecutive zero-progress foremen → stop, escalate.
3. **Iteration cap reached** → report status, ask to re-engage.
If Bane says BANKAI and the goal has N tickets, plan N foreman launches from the start; briefs for the whole chain can be staged up-front so launches are instant.

## The Bankai Timer (safety — what keeps unbounded from becoming runaway)

- **Progress gate:** every completed foreman must move the goal forward. Two consecutive foremen with zero progress (same failure, no advance) → **STOP, escalate to Bane** — never spin.
- **Iteration cap:** max N foremen per release (e.g., 20–30). Reached → report status + ask to re-engage.
- **Honest loop:** timeouts and failures are reported and re-driven; never fabricated outcomes.
- **No double-spawn:** the bankai project is paused on the scheduler side while Hermes drives — the daemon and the dispatcher never race.

## The Dispatcher's Toolbox

- **Spawn a foreman directly:** `POST http://127.0.0.1:8642/v1/responses` — body: the foreman prompt (the project's tick prompt: read board → pick task → work/verify → commit → report), model/provider from the project config, `require_approval: false`. Auth: `API_SERVER_KEY`.
- `PUT /api/v1/projects/<name>` — create/update + **pause** the daemon side: `{"cooldown_s": <high>, "enabled": false}` while bankai drives; re-enable on release end.
- `GET /api/v1/ticks?limit=N` + `GET /api/v1/projects` — state checks.
- JSONL board writes: surgical append (git-tracked-jsonl-editing rules) + event rows; commit each cycle.
- Alternative spawn path: `hermes chat -q` (terminal, background) with the foreman prompt — same effect, direct process.

## Proven Waves (keep updating)
- **2026-09-01 task-router full release (12 tickets, one release):** 5 workers wave 1+2 (file-partitioned, zero overlap) + paired dispatch for coupled tickets (TR-032+TR-014 wiring; TR-015+TR-020 same-files) → suite 116→251. Lessons: (a) workers die silently sometimes — the TR-032 worker authored tests+doc then died pre-commit; its test contract was enough for the dispatcher to finish the implementation in ~4 surgical patches; (b) a concurrent external bot (totalwindupflightsystems) landed a real fix mid-release — verify foreign commits instead of reverting them; (c) export state vars in your OWN shell can leak into later probes (unset before live checks); (d) `terminal()` sleep-loops >420s time out the tool call — poll with shorter sleeps or process.poll.

## The Next Form — 多重卍解 (dagger takes the wheel)

The bankai workdir already carries `dagger.db`. **Soon: dagger does bankai** — the goal becomes a DAG of tasks (nodes = foremen/workers, edges = dependencies) executed **concurrently** by the DAG engine, with dagger managing the dispatch/retry/verify loop instead of Hermes launching one foreman at a time. Hermes defines the DAG; dagger runs the release — many blades, one will.

## Dispatcher operational lessons (2026-09-19, SCHED-GAP-170 release)

- **Check whether the fleet already did it, BEFORE dispatching.** Rows I filed were
  implemented and closed by foremen within hours: SCHED-GAP-143/170/171/173 were all
  `complete` (with tests green and the client correctly wired) by the time I opened the
  release. Recon the board row's status + the named source files first; a wave dispatched
  onto already-landed work burns a worker and a slot.
- **Spawn repo work with `hermes chat -q`, not delegate_task.** The brief-in-a-file
  recipe: write the brief to /tmp, then `hermes chat -q "$(cat /tmp/brief.txt)" -m <model>
  --provider <sub> --max-turns 250 --run-budget 2400 --yolo`, run it as a background
  process with notify. Measured: 16 min for a 8-file change with tests + docs + guard.
  `delegate_task` leaf workers hard-cap at 600s and die mid-run (twice today); use them
  only for read-only scouting.
- **The self-report is not verification.** Read the transcript's tail AND the tree: does
  the commit exist, is the working tree clean, is it pushed? Wave 1 committed `cb46046`
  and stopped there — the dispatcher pushed it. Then run the focused tests yourself.
- **A wave that finds the fix already implemented should pivot to the gap.** The real
  remaining work was not the fix but (a) it was not deployed and (b) nothing could answer
  "is the guard armed?" — one foreman closed that in 16 minutes.
- **Expect the invariants gate to flag your own pause.** Driving a project requires
  `enabled=false` on the daemon side (no double-spawn); `ops/check-fleet-invariants.py`
  then reports `target <name> is DISABLED` as a violation. That is expected and clears
  when the release restores the project — say so in the report instead of chasing it.
- **Commit mechanics that bite:** `git commit <pathspec>` silently ignores UNTRACKED
  files (git add first, then confirm the staged set), and backticks inside a `-m` message
  are evaluated by the shell — write the message to a file and use `git commit -F`.

## Proven Waves (keep updating)

- **2026-09-19 SCHED-GAP-170 gateway-health gate (Class-1 release, 1 wave + deploy).**
  Goal: the gateway-unreachable failure class (793 of 859 failures, 89%, one error
  string). Recon found the fleet had already merged the fix — what was missing was the
  deploy and any way to see whether the gate was ARMED. Wave 1 (glm-5.3-flash @
  zai-glm-default, 16 min, 8 files): boot log lines `GATEWAY-HEALTH-GATE: armed ttl=30s`
  / `NOT ARMED`, `GatewayHealthGateStatus()`, a `/api/v1/status` block, one event per
  unhealthy episode, docs + 11 focused tests, guard-green full suite. Dispatcher then
  pushed, extended the deploy script's symbol check to include the new gate, and ran the
  drain-restart. Lesson that generalises: a guard owes an ARMED surface, and the deploy
  verify must name every fix symbol.

## Doctrine — The Release Does NOT Suspend the Rules

- **chat = PAYG, work = subs** — bankai CODING rides the subs (opencode-go/ollama-cloud/neuralwatt/openai-codex/kimi-for-coding), never DeepSeek PAYG
- **Verify with evidence** — nothing is "done" until it runs (browser/vision for games/UIs, tests for code)
- **The release ends** — bankai ends with a complete report; don't linger in the mode
