---
name: coding-hermes-plus-ultra
description: "PLUS ULTRA: finish ALL tasks, then improve the system."
version: 1.1.0
author: Bane + Hermes
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [plus-ultra, mode, full-auto, fleet, self-improvement, 越, beyond]
    related_skills:
      - coding-hermes-bankai
      - coding-hermes-quorum
---

# 越 PLUS ULTRA — The Further Beyond

## When to Use

Say **"plus ultra"** (or プラスウルトラ) when a goal deserves more than bankai: the tasks must ALL finish AND the system must be left better than it was — findings filed, knowledge recorded, skills patched, recurring work wired into crons. Use bankai when the goal is the battle; use Plus Ultra when the goal is the battle *and* the next battle must be unnecessary.

## 越の精神 — The Philosophy of the Beyond

**PLUS ULTRA** is two layers of meaning, both real:

- **PLUS ULTRA (プルス・ウルトラ, Purusu Urutora)** — Latin for **"further beyond."** U.A. High's motto, Spain's national motto, from Virgil's *nec plus ultra* — the warning written at the Pillars of Hercules, the edge of the known world. To go Plus Ultra is to **sail past the edge of the map**. In the series it is the rallying cry: "Go beyond! Plus Ultra!"
- **越 (koshi) — "go beyond, cross over"** — the kanji of the motto's meaning, and literally **the kanji in Horikoshi's own name** (堀越耕平). The translator's verified shower-thought: the motto is the author's self-insert — the series itself is the act of going beyond. 越す is distinct from 超す (going OVER a limit): 越 means going **beyond** — physically, irrevocably, to the other side.
- **雄英 (U.A.)** — the **inverted kanji of 英雄 (hero)**: the school's name is heroism standing on its head. The ordinary arrangement of a hero's kanji is not enough — flip it, and it becomes the school that trains the ones who go beyond.

**BANKAI (卍解) is the final release — everything unsealed, everything within the battle, ending when the battle ends. PLUS ULTRA is what comes AFTER the release: the battle ends, and the fleet is still better than it was before it began.** Where bankai finishes ALL the tasks, Plus Ultra finishes the tasks **and then goes beyond the task list** — the acceptance criteria are a floor, not a ceiling; the goal is the map's edge, and the map gets redrawn.

## The Release Command

**Trigger:** the keyword "plus ultra" / "Plus Ultra" / "プラスウルトラ" with a goal. Hermes enters the mode and runs the **bankai loop** (see coding-hermes-bankai — capture goal → pause daemon → launch foremen directly via the gateway API → completion-driven cadence) **plus one extra phase**: after the goal is complete and verified, the **Beyond Pass** runs before the release ends.

**Bare trigger (no goal):** a bare "plus ultra" = **CONTINUE the standing goal** (same as bare bankai). Do NOT treat it as a fresh goal — find the standing goal's outstanding deliverable first: check the last plus-ultra/bankai session via session_search for what was left mid-delivery, check the kanban boards (`env -u HERMES_DELEGATED_CHILD_CONTEXT hermes kanban ls`), and read the project boards (`.coding-hermes/board/tasks.jsonl`) for open items. Proven 2026-08-28: bare "plus ultra" resumed the dagger review package ("report and code of each of the daggers") that the previous release had cut off mid-assembly — the daggers were all committed/pushed; only the review deliverable was outstanding.

**Proven:** 2026-08-27 — the QA foreman build (this session) was Plus Ultra energy without the name: the goal was "build the QA cron"; the beyond-pass was the bunker CLI timeout root-cause (committed 380292e/c578969), the act+rootless-docker finding (recorded to /qa/observations/), the QA-002 finding filed on sdk-python's board, and the ledger that makes tomorrow's discovery smarter. The task was done; the system left better.

## The Loop — Bankai, then Beyond

1. **Bankai phase — exactly the bankai loop.** Capture the goal → concrete deliverables + acceptance criteria → engage the fleet (paused for the daemon) → launch foremen directly (POST `http://127.0.0.1:8642/v1/responses`, `require_approval: false`, gateway key from `API_SERVER_KEY`; coding rides the SUBS, never DeepSeek PAYG) → completion-driven cadence, no pauses between waves → verify every deliverable with evidence (run it, test it, screenshot it) → mark tasks done.
2. **The Beyond Pass — the Plus Ultra phase (this is what makes it Plus Ultra, not bankai).** The goal is done. Now, one pass over the SYSTEM the goal touched:
   - **Findings** — every obstacle hit during the run (tool failures, environment quirks, API surprises) becomes a record: file bugs/gaps to the project board (QA-xxx or GAP-xxx rows per pm-injected-board-rows conventions), not just a note in the report.
   - **Knowledge** — the interesting issues, observations, and their **data sources** go to DuckBrain (`/qa/observations/<date>` or the project's namespace) so future runs start smarter.
   - **Self-improvement** — patch the skill that misled you (skill_manage patch), fix the script that broke, add the pitfall that cost you time. If the run surfaced a recurring pattern, the output is a NEW cell/checklist/guard, not a paragraph.
   - **Wiring** — if the work is recurring, it becomes a cron (hermes-cron-development) or a guard, so the fleet does it without the mode.
3. **The release ends** — full report: what was built (MEDIA files), what was found, what was improved, what now runs without you.

## 越 × WORKTREES — one worktree per task (Bane directive 2026-09-19)

The bankai phase **runs in worktrees** — this is now part of the loop, not a nicety. Full doctrine
lives in `coding-hermes-bankai` (§卍解 × WORKTREES); the short form:

- **One worktree per task, off the last known good commit.** Dispatch the worker INTO it (the brief
  names the worktree as THE workdir, with the isolation preamble: commit normally, never
  stash/reset/clean, never merge or push). Never two workers in one tree.
- **Wave only genuinely disjoint tasks** — no shared file, no shared import root. That same property
  is what makes the merge trivial, so it is one decision, not two.
- **Merge in a scratch integration worktree**, run the FULL battery on the combined tree, then
  fast-forward the real branch. This is how a release keeps moving while the main checkout is still
  held by a live daemon tick.
- **Re-check the base before merging** (`git merge-base --is-ancestor <base> <target>`): a concurrent
  amend or rebase ORPHANS your base and a plain merge then conflicts in files you never touched.
  Rebase onto live HEAD first when it does. Pin the base sha in the dispatch note.
- **Record `worktree`, `branch` and `sessions` on every task row** the release touches, so the board —
  not the dispatcher's memory — says where the work happened and which Hermes session did it.
- **Reap at the end:** every worktree maps to a merged branch → `git worktree remove` + prune.

Cost note: worktree-per-task is for releases with **≥2 independent tasks**, or any repo the daemon
might touch. A single-task run in a quiet checkout does not need one.

## ⚠️ The Beyond Pass is NOT busywork

The same rigor applies to improvements as to tasks:

- **Only real, verified improvements count** — a filed finding must reproduce from evidence (exact commands, logs); a patched skill must be the one that misled you; a new cron must have run once (proven pattern: build → smoke → then register).
- **No churn edits** — the Beyond Pass is not an excuse to refactor unrelated things. Scope: the system as the goal touched it.
- **Quality over quantity** — one root-cause fix (the 30s transport) beats five surface patches. The QA foreman today: 10 harness iterations, 4 real fixes, 2 commits, 2 DuckBrain records — every one traceable to evidence.
- **The release still ends** — the Beyond Pass is bounded (one pass, not open-ended polish). When the improvements are verified, the mode ends.

## The Timer (safety — beyond is still bounded)

- **Progress gate:** same as bankai — two consecutive zero-progress foremen → STOP, escalate. The Beyond Pass cannot rescue a failed battle; it happens only after a VERIFIED completion.
- **Iteration cap:** same as bankai — max N foremen per release (20–30). Reached → report + ask.
- **Beyond-cap:** the Beyond Pass itself is capped (e.g., max 5 improvement items per release). Reached → list the rest as "next release" candidates and stop.
- **No double-spawn:** the project stays paused for the daemon until the release (including the Beyond Pass) ends; then the scheduler is restored.
- **Honest loop:** timeouts and failures reported and re-driven; never fabricated outcomes — and never fabricated improvements.

## The Toolbox

Bankai's toolbox (gateway spawn, scheduler API, JSONL board writes, `hermes chat -q`) **plus**:
- `skill_manage` patch — the skill that misled you gets the pitfall added before the release ends
- `cronjob` create/update — recurring work becomes a cron with a proven script
- DuckBrain remember — observations + data sources, `--namespace=coding-hermes --domain=event`
- Board injection — pm-injected-board-rows conventions (QA-xxx/GAP-xxx, reasoning = cycle marker, identity commit)
- `hermes-model-router` — the Beyond Pass is also the moment to feed the routing registry what the run measured (ledger fields: served pair, hop, reason, cache, error class)

## Doctrine — Beyond Does NOT Suspend the Rules

- **chat = PAYG, work = subs** — same as bankai; the Beyond Pass rides the subs too
- **Verify with evidence** — a finding without a repro line is a rumor; an improvement without a run is a wish
- **The release ends** — Plus Ultra ends with a complete report: built, found, improved, automated. Don't linger in the mode.
- **The map gets redrawn** — every release leaves the next one cheaper: the ledger fills, the crons run, the skills remember. That is the difference between bankai and Plus Ultra — bankai wins the battle; Plus Ultra makes the next battle unnecessary.
