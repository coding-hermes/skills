---
name: coding-hermes-dogfood
description: >-
  Value discovery through real use. Picks a random fleet project and does a
  DEEP hands-on dogfood run — not test scripts, but actually USING the system
  the way a real user would: integrate the library into something, sign up for
  the website and do a real task, run the CLI end-to-end, drive the API. Then
  judges whether it delivers value, how hard it is to use, and feeds every
  finding back: tasks on the board, docs and integration guides, skill
  directories in the project so other agents learn how to use it, and a
  diagnostic trail (how things were built, errors hit, the right way) that
  lets a user later ask "is this project worth anything / does it actually
  work?" and get a real answer from the repo records — not "all tests are
  green".
version: 1.0.0
category: software-development
---

# Coding Hermes Dogfood — Value Discovery Through Real Use

**Core principle:** "All tests are green" means almost nothing. The only
honest way to know if a project works is to USE it — as a real user would —
and record what happened. This skill does that, then turns every friction
point into board tasks and every lesson into repo documentation that teaches
future agents how to use the thing.

## When This Runs

- A cron job fires every few hours: picks ONE random enabled project, runs
  this skill against it, delivers the verdict to the origin chat.
- The **Stand-In Gap-Pusher cron** fires HOURLY (human stand-in while the
  user is away): picks 2 projects that LOOK done, does the gap-sweep mode
  below, WRITES tasks to wake the foremen. See
  `references/stand-in-gap-pusher.md` for the full recipe.
- Manually: `Load skill coding-hermes-dogfood. Field-test <project>.`

## Gap-Sweep Mode (Stand-In / Hourly Variant)

**Purpose:** when foremen report "idle tick" but the project has real gaps,
the fix is to WRITE the gaps as tasks — the same effect as the user poking
the project by hand (which provably spins up hours of foreman work). The
stand-in is the poke, never the worker.

1. **Pick 2 targets** (via `~/.hermes/scripts/standin-pick.py`): weighted
   toward self-paused foremen (CooldownS ≥ 14400) with clean boards — the
   "thinks it's done" prime targets. Never re-picks within 8h, never touches
   disabled projects.
2. **Ask the basic questions** a user would, then answer by LOOKING: README,
   AGENTS.md, docs/ (does an integration guide exist? API docs? examples?),
   run the build/dev server, check test-suite duration. **20 min/project max**
   — this is the light sweep, not the 2h deep run.
3. **Find REAL gaps**: integration (nothing shows how to use it), docs/API
   reference missing, tests too slow or absent on critical paths, UX friction,
   spec-vs-reality drift. A 2-minute probe that finds 3 gaps is a success —
   e.g. hermes-canopy claimed "Phase 4-7 COMPLETE" yet had NO integration
   guide, NO API docs, and `go test -short` hanging past 120s.
4. **WRITE 2-6 concrete tasks** (IDs `GAP-001`...) onto the board in the
   board's existing format, commit them. THIS is the critical step — the
   foreman sees new tasks and spins up real work. No tasks written = the run
   did nothing.
5. **Wake the foreman** if self-paused (CooldownS ≥ 14400 → PUT 900). Never
   re-enable `Enabled=false`.
6. **Log to DuckBrain** via MCP (namespace=coding-hermes,
   key `/stand-in/YYYY-MM-DD/<project>`), then report to origin.

**Proof (2026-08-04, hermes-canopy):** all board phases green, but basic
questions exposed GAP-001 (no integration guide), GAP-002 (no API docs),
GAP-003 (`go test -short` > 120s). Tasks committed, foreman woken at 900s —
the loop works end-to-end.

## The Problem You Fight Is Researched: Premature Completion

Foremen declaring "done" on green tests while real gaps remain is a named,
studied anti-pattern (four independent teams, 2025-26: SRI Lab/ETH
"fixing correct code", ForgeCode "premature completion", SWE-EVO "premature
termination", LangChain). "All tests green" ≠ done; agents are systematically
overconfident and assert success without verifying environment state (false
success, 9,876 trajectories).

**Proven to fail:** "be thorough" instructions, longer reasoning, CoT.
**Proven to work:** reproduction-first (run it before believing any claim),
externalized stopping criteria (done = observable state, not "looks fine"),
the three-layer termination check (L1 syntax → L2 it RUNS → L3 it WORKS for
a user end-to-end — foremen stop at L1-2, L3 is where integration/UX/
usability gaps live), and worker/checker separation (you are the independent
nitpicky checker; the builder is biased to call it good).

Full evidence pack: `references/premature-completion-research.md`

## The Dogfood Loop

```
Pick project → Learn what it promises → USE IT FOR REAL → Judge value
→ Findings → (a) tasks on board  (b) docs  (c) skills/ in repo  (d) diagnostic trail
→ Wake the foreman if it was paused → Report verdict to user
```

## Step 0 — Pick the Project (cron mode)

The cron script (`~/.hermes/scripts/dogfood-pick.py`) already chose the
project and its briefing is in your prompt context. If you ran manually,
pick one: any enabled project from `GET http://127.0.0.1:9090/api/v1/projects`
with `Enabled=true` and an existing `Workdir`. Prefer projects not recently
dogfooded (check `.coding-hermes/dogfood-log.md` in the workdir).

## Step 1 — Learn What It Promises (15 min max)

Before touching anything, answer: **what does this project claim to do?**

1. Read `README.md`, `AGENTS.md`, `specs/_index.md`, `docs/` — extract the
   stated purpose, the primary user, the promised workflow.
2. Read `.coding-hermes/tasks.md` — what has the foreman been working on?
3. Identify the **entry point**: CLI binary? HTTP server? Library/package?
   Website? Game? MCP server? Cron job? API?
4. Note the **build/run commands** from AGENTS.md or Makefile.

Write a one-paragraph "Promise" statement. This is your null hypothesis:
*"This project claims that a user can <do X> by <using Y>."*

## Step 2 — USE IT FOR REAL (the heart — 45+ min)

**This is NOT running the test suite.** Tests are written by the people who
built it — they prove the code does what the code does. You are a USER who
doesn't care about the code. The depth required:

| Project type | Real use = |
|---|---|
| **Library / SDK** | Write a real consumer. Create a scratch project OUTSIDE the repo, import/install the library, build something genuine with it (a CLI tool, a script that solves a real problem, a small app). Follow the documented API. Do NOT use internal helpers. |
| **Website / SaaS** | Sign up / log in as a real user. Do a real task end-to-end (create, edit, delete, search, share). Test the happy path AND the path the docs don't mention. Note every friction point. |
| **CLI tool** | Run the documented commands. Then run the commands a real user would NEED that aren't documented. Check help output, error messages, exit codes, tab-completion, flags. |
| **HTTP service / API** | Start it. Curl every documented endpoint. Then do a real workflow across multiple endpoints. Check error responses, auth, pagination, validation. |
| **MCP server** | Connect it to a real MCP client and use the tools it exposes for a real task. |
| **Game / interactive** | Play it. Actually play it. Reach the end state. |
| **Infra / script** | Run it against a scratch copy of the environment. Do the thing it automates, manually first, then with the tool. |

**While using, capture (in a scratch notes file):**
- Every place you got stuck, guessed, or had to read source to proceed
- Every error message that was confusing, missing, or wrong
- Every promise from Step 1 that held up vs. fell apart
- What a NEW user would need that isn't documented
- What you'd tell the maintainer to fix FIRST if you had 1 hour of their time

**Integration depth (critical for libraries):** the value of a library is
how it feels to integrate. Document the actual integration: what you had to
wire up, what broke, what the docs didn't say, what the "aha" was once it
worked. THIS is the most valuable output — a real integration report.

## Step 3 — Judge Value (be brutal, be specific)

Answer four questions with evidence from Step 2, not vibes:

1. **Does it work?** Did the promised workflow complete? Quote the exact
   failure if not.
2. **Is it useful?** Does the thing it does have real utility for a real
   user — or is it solving a problem nobody has? Would YOU use it again?
3. **Is it usable?** Time-to-first-success, friction count, how much you had
   to read source, how much prior knowledge the docs assumed.
4. **Is it trustworthy?** Did data survive restarts? Did it corrupt anything?
   Did errors leave bad state?

**Verdict labels:**
- ✅ **SHIPPABLE** — promised workflow works, friction is low, real value
- 🟡 **PROMISING-BUT-ROUGH** — value is real, usability is the blocker
- 🔴 **DOES-NOT-DELIVER** — the promise doesn't hold up in real use
- ⚪ **UNKNOWN-VALUE** — couldn't complete a real use (blocked, undocumented)

## Step 4 — Write the Findings as Tasks

Add a `## Dogfood Findings (YYYY-MM-DD)` section to the JSONL board
(`.coding-hermes/board/tasks.jsonl` — append one task object per line; or
append a `dogfood_findings` event to `events.jsonl`). Match the board's
existing task format. One task per
finding, each with: the concrete problem, how you hit it, the fix direction.
Prioritize: P0 = breaks real use, P1 = major friction, P2 = polish/docs.

Also record the run in `.coding-hermes/dogfood-log.md` (append): date,
verdict, promise statement, top 3 findings, time-to-first-success.

## Step 5 — Leave the Knowledge Behind (this is the force multiplier)

The project should TEACH itself. Leave in the repo:

1. **`docs/dogfood/<date>-integration.md`** — the integration report: how to
   use it for real, the working example, the errors hit and their fixes.
2. **`skills/<project>-usage/SKILL.md`** (or `.opencode/skills/` if the
   project uses OpenCode) — a skill that teaches OTHER agents how to use this
   project: what it does, entry points, run commands, common pitfalls, the
   "right way" patterns. Agents that land in this repo later load this skill
   and instantly know how to use the system.
3. **`docs/dogfood/diagnostics.md`** — the diagnostic trail: how the thing is
   built, why, the errors encountered along the way (yours AND the project's
   own history), and the right way to do things. This is the "not raw
   diagnostics, but explaining the thing and how it was built" record.
4. If the project has no docs/ or skills/ dir yet, create them.

Commit all of this in the project repo. This turns a one-time dogfood run
into a permanent asset: the next agent (or the user's Hermes in a chat) can
answer "is this project valuable / does it work" by READING these records.

## Step 6 — Wake the Foreman (if it was paused)

First, check registration health — a project can look correctly registered yet
never tick: NULL/dead `NamespaceID`, `decay_rate=0` (flat urgency), a
case-insensitive ghost duplicate, or a zombie tick row (`status='running'` +
`session_id IS NULL`). See
`coding-hermes-never-done/references/scheduler-registration-health.md`.
**Proven:** ring-runner (2026-08-02) was registered perfectly (900s,
coding-hermes, deepseek-v4-flash) but a zombie tick from a mid-restart spawn
blocked it → zero ticks for 2 days. Clear the zombie row, then
`POST /api/v1/evaluate`.

Then, if the project was idle/slow (cooldown ≥ 43200s or 14400s) but you just added
real work to its board, temporarily speed it up so it does the work:

```bash
curl -s -X PUT "http://127.0.0.1:9090/api/v1/projects/<NAME>" \
  -H 'Content-Type: application/json' -d '{"CooldownS":900,"DecayRate":1.0}'
```

The foreman will pick up the dogfood tasks, work them, and its own
self-pause logic (idle counter → escalate cooldown) will slow it back down
when the board is clean again. That's the "speed up temporarily, do the work,
slow back down" loop. Do NOT re-enable a project that is disabled (`Enabled=false`)
— that's a human decision; just note it in your report.

## Step 7 — Report the Verdict (to the user)

Deliver a compact verdict message:
- Project, verdict label, one-line promise vs. reality
- Time-to-first-success + friction count (evidence)
- Top 3 findings (with task IDs if you added them)
- What you left behind (docs, skills, diagnostics paths)
- Whether you woke the foreman

This report is the answer to "is this project worth anything" — based on a
real use run and the records now in the repo, not test colors.

## References

- `references/stand-in-gap-pusher.md` — full recipe for the hourly Stand-In
  cron (picker weights, per-target procedure, hermes-canopy worked example).
- `references/github-api-skill-push.md` — pushing this skill to
  `coding-hermes/skills` via the GitHub Contents API without a local clone,
  including the `-f data=` double-encoding pitfall.

## Rules

- **NEVER fix code during the dogfood run** — you are a user, not the
  maintainer. Findings become tasks; the foreman does the fixing. (Exception:
  if the project is a cron/infra job with no foreman and the fix is a 1-liner
  that unblocks the use, note it and move on — still don't fix.)
- **NEVER run destructive commands** on the project's real data. Use scratch
  dirs (`/tmp/dogfood-<project>`), test accounts, throwaway DBs.
- **DO NOT create a whole new project outside the repo** just to avoid using
  the real one — the point is using the REAL thing. Scratch dirs are for the
  library-consumer pattern only (you can't import a library into itself).
- **Time-box each phase.** Promise 15m, Use 45-60m, Judging 10m, Writing 20m.
  A dogfood run is ~2h max. If you're stuck for 10m on one thing, note it as
  friction and move on — getting stuck IS data.
- **Commit the knowledge artifacts in the project repo** with a clear message:
  `dogfood: <project> <verdict> — <top finding>`.
- **Never commit credentials, tokens, or real user data** in the dogfood
  artifacts. The integration example must use placeholder values.
- If the project has NO README and NO AGENTS.md, that itself is finding #1.
- A project with zero tests AND zero docs AND a broken happy path gets the
  🔴 verdict — and the diagnostics trail records exactly why.

## Pitfalls

- **"I ran the tests, all green" is NOT a dogfood run.** If your report is
  mostly test output, you did it wrong. Real use means you did something the
  tests never do: integrate, sign up, deploy, play, query, fail.
- **Don't review the code as a substitute for using it.** Reading source is
  allowed only when stuck — and "had to read source to proceed" is itself a
  finding (docs gap).
- **Don't dogfood a project you've already dogfooded this week** unless the
  cron picked it — the picker script tracks last-run dates.
- **Don't wake foremen that are admin-disabled.** `Enabled=false` in the
  scheduler API = human said stop. Respect it.
- **Don't write the diagnostic trail as raw logs.** It must be explanation:
  "this is how X works, this is why, this is the error I hit, this is the
  right way." Raw log dumps are noise; explained lessons are knowledge.
- **Don't skip the skills/ directory.** The integration skill in the repo is
  what makes the knowledge reusable — without it, the docs are just read-once
  prose.
