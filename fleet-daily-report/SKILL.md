---
name: fleet-daily-report
description: "Generate a narrative fleet report — not a scorecard. Each project card tells a story: what happened, why, what's blocked, what needs attention. Designed for offline reading with judgment-ready analysis."
version: 2.1.0
category: coding-hermes
---

# Fleet Daily Report — Narrative Edition

This is NOT a dashboard of task counts. It's a narrative report. Every project card answers: **why is this project winning or losing right now?**

Bane downloads this HTML, reads it offline, and writes Telegram responses that send when connectivity returns.

## What Makes This Different

- **Not a scorecard.** The headline is the story, not the numbers.
- **Judgment, not data.** Subagents already gathered the raw data. The report agent synthesizes it into analysis.
- **"Why" not "what."** Not "consensus has 0 pending tasks" — "consensus has been idle for 13 ticks despite 20 stale GitReins tasks untouched since June, burning $0.128 on empty sweeps while cooldown reverts 7x."
- **Actionable.** Every narrative ends with what needs to happen next.

## Data Gathering — Already Done by Subagents

The report agent receives rich per-project data from subagents. Don't re-query. Synthesize what they found.

## Project Card Narrative Template

Each active project card should tell this story (as narrative prose, not bullet-point tables):

### 1. Headline (one sentence)
The single most important thing about this project right now. Example: "HEADING is burning $5.07 on 500 zombie ticks because of a duplicate scheduler entry."

### 2. What Happened (2-3 paragraphs)
- What work was actually done recently (commits with context)
- What the foreman is actually doing (tick pattern — productive vs spinning)
- What's blocking progress (specific blockers, not vague)

### 3. What's At Stake
- What happens if this stays blocked/frozen/idle
- Money being burned on empty ticks
- Risks accumulating (stale deps, CI decay, DuckBrain drift)

### 4. What Needs to Happen
- Concrete next action (can be "Bane needs to X" or "foreman will Y")
- Who/what unblocks it
- Timeline urgency

### 5. Supporting Data (collapsible)
- Last 5 tick outcomes with model/commits/duration
- Git log summary (not full log — narrative of what changed)
- CI status with context
- Task board snapshot (real pending only)

## Idle Projects — Compact but Narrative

Don't just list "idle, 43200s." For each idle project:
- Why is it idle? (Completed? Blocked? Abandoned?)
- What would reactivate it?
- Any risks from being idle? (CI decay, stale deps, never-done missing)

## Problem Dashboard

Group issues by TYPE, not by project:
- **Burning Money:** projects running empty ticks, zombie loops, cooldown reversion
- **Blocked:** human-gated, billing, permissions, infrastructure
- **Drifting:** NEVER-DONE missing, CI decaying, cooldown anomalies
- **Board Lies:** GitReins/coding-hermes discrepancies, tasks claimed done but not

Each issue links to the relevant project card.

## HTML Template

Use `references/report-template.html` — dark theme, collapsible `<details>` cards, narrative-first layout.

## Delivery

1. Save HTML to `~/.hermes/reports/fleet-YYYY-MM-DD-HHMM.html`
2. `MEDIA:[path]` for inline Telegram rendering
3. Text summary: 1-line highlight per problem category

## Scheduling

Cron: `0 8,14,20 * * *` — three times daily. Each run is a complete narrative snapshot.
