---
name: fleet-retrospective
description: >-
  90-day / year-in-review retrospectives for any fleet project — collect raw
  data from git, scheduler DB, boards, and CI; distill a facts digest; run 3
  parallel analyst agents; synthesize a dark mobile-first HTML report; feed
  the top gaps back as board tasks.
version: 1.0.0
category: coding-hermes
---

# Fleet Retrospective — "End-of-Year News Summary" Engine

Builds reviews of a project, fleet, or time period. The user's framing:
*"like when they do the end of the year news summary of things that happened
and how much took place — a way of looking back."* Goal: a reader who can
**talk intelligently** about how the system works, what happened, where the
gaps are.

## When to use

- "90 day review", "how is X coming along", "year in review", "retrospective",
  "good bad and ugly", "what have we accomplished since DATE"

## The loop (5 phases)

### 1. COLLECT — raw data to a workspace dir

One command, parameterized (script ships with this skill):

```bash
python3 <skill-dir>/scripts/collect.py \
  --name <scheduler-project-name> --repo <repo-path> \
  [--window-days 90] [--out ~/retro-workspace-<name>] \
  [--github-repo owner/name] \
  [--test-cmd "pytest --collect-only -q" | --test-cmd "go test ./... -list .* | wc -l"]
```

Raw data lands in `~/retro-workspace-<name>/`:
`git-timeline.txt`, `scheduler-ticks.txt`, `board-ci.txt`, `repo-stats.txt`.

**Never trust memory or tick reports alone — re-derive every number.** The
scheduler DB is queried directly; the board is parsed from JSONL; CI comes
from the public GitHub API (works unauthenticated for public repos).

### 2. DISTILL — write ONE facts digest (facts.md)

The critical step. Synthesize raw files into a single `facts.md` in the
workspace: window, hard numbers (each re-derived), versions arc, the Good,
the Bad, the Ugly, current gaps, architecture snapshot, timeline waves.
Source every fact — if it came from a tick report or session memory, say so.

**This file is the analyst agents' ENTIRE world** — a bad digest poisons all
three reports. Spend the most care here.

### 3. DISPATCH — 3 parallel analysts (delegate_task, ONE batch call)

| Agent | Reads | Produces |
|---|---|---|
| Timeline analyst | facts.md, git-timeline.txt | Month-by-month narrative, versions arc, turning points → `analysis-timeline.md` |
| Incidents analyst | facts.md, scheduler-ticks.txt, board-ci.txt | Good/Bad/Ugly + root-cause patterns + resilience scorecard → `analysis-incidents.md` |
| Gap analyst | facts.md, board-ci.txt | Architecture explainer, ranked gaps, next-period plan (why-now + S/M/L), STOP-doing list → `analysis-gaps.md` |

Every goal states: *read these files, write to this path, facts ONLY from
provided files, mark inferences as analysis.* Do not poll — continue other
work; the batch re-enters as one consolidated result.

### 4. SYNTHESIZE — HTML deliverable

Sections: hero + stat grid (live numbers) → momentum chart → timeline →
good → bad → ugly → how-it-works talk track → resilience scorecard → gaps
ranked → next-period plan → stop-doing → bottom line.

Dark mobile-first. Verify at 420px via headless Chrome screenshot +
vision check BEFORE delivery. Deliver as `MEDIA:<abs path>` plus a
talk-track summary in chat.

### 5. FEEDBACK LOOP — make it actionable

Close by offering to file the report's top N gaps as board tasks on the
reviewed project. The retro is not just a look back — it seeds the next
cycle: retro → gaps → board rows → ticks close them → next retro.

## Pitfalls

- **Subagent dispatch can 401** (invalid/stale API key) — if all 3 analysts
  fail instantly with auth errors, write the three analyses YOURSELF from
  facts.md rather than blocking the deliverable; flag the key to the user.
- **Scheduler `status='timeout'` is NOT "did nothing"** — legacy deadline
  bookkeeping includes rows that did real work; sum from
  `commits`/`files_changed`, read `error` text before reporting.
- **Tick reports ≠ truth** — numbers decay between report and retro; always
  re-derive from live sources at collection time.
- **Consistency check before publishing** — every number must appear
  identically in stat card, section text, and tables (a stat card saying
  12,344 while the section says 29,189 is a credibility kill). Re-derive
  zombie/aggregate counts at build time, not from memory.
- **Cost numbers**: ticks.cost_usd covers tick-spawned sessions only, not
  interactive chat. Say so rather than implying whole-fleet cost.
- **Non-Python projects**: collect.py's LOC probe is Python-shaped; pass
  `--test-cmd` explicitly and adjust the LOC line per language.
- **Boards vary**: `--board-rel` covers `.coding-hermes/board`; legacy
  parquet-only boards may need one-off collection.
- Timeline arithmetic: use `--date=format:"%G-W%V"` (ISO week), not `%U`.
- Model-name drift in billing data (gateway restarts re-stamp provider
  labels) — count by immutable fields (base_url / per-call ledger), never
  by the re-stamped label column, when the report splits by provider.

## Proven

- coding-hermes-scheduler 90-day fleet retro (2026-09-01): 63,034 ticks,
  7,849 commits, $3,725 tick spend across 91 projects; report drove 5
  SCHED-GAP board rows filed the same day (zombie reaper, drain-safe
  restarts, session resume, phantom project, destination-coverage alerts).
