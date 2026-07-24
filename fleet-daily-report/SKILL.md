---
name: fleet-daily-report
description: "Hybrid fleet report — narrative analysis for decisions + deep project data for context. Read the story to know what to fix, expand the details to know exactly what's happening before jumping into a chat."
version: 2.2.0
category: coding-hermes
---

# Fleet Daily Report — Hybrid Edition

Two layers per project card. Read top-down for decisions, drill down for context.

## Layer 1 — Narrative Analysis (always visible)

The story. Why is this project winning or losing? What needs a decision? What's at stake?

- **Headline** — one sentence, the single most important thing
- **What's happening** — what the foreman is doing, what was built, what broke
- **What needs attention** — concrete decisions Bane needs to make, or risks accumulating

## Layer 2 — Deep Data (expandable `<details>`)

The ground truth. Read this BEFORE jumping into the project chat so you're informed.

- **Recent work** — what was actually built (commits with messages and files changed, not just counts)
- **Task board** — every real pending task with model, priority, complexity, dependencies
- **Foreman ticks** — last 5 with model used, commits produced, duration, outcome
- **CI status** — recent runs with URLs, pass/fail, what broke
- **DuckBrain state** — what the foreman knows about this project (status, architecture, model choices)
- **Risks** — zombie detection, blocked tasks, cooldown issues, board discrepancies
- **What needs to happen next** — the foreman's next task + any blockers

## Problem Dashboard (top of report)

Group issues by TYPE so you know where to focus:
- **Needs Decision:** issues only Bane can resolve (billing, permissions, architecture)
- **Burning Money:** zombie ticks, cooldown reversions, duplicate entries
- **Blocked:** human-gated, infrastructure, CI down
- **Drifting:** NEVER-DONE missing, CI decaying, skills stale

## Delivery

1. Save HTML to `~/.hermes/reports/fleet-YYYY-MM-DD-HHMM.html`
2. `MEDIA:[path]` for Telegram
3. Text summary: 1-line per problem category + standout projects

## HTML Structure

```
┌─ FLEET DASHBOARD ─────────────────────┐
│ Active: 14  Idle: 28  Risks: 6         │
├─ PROBLEMS ────────────────────────────┤
│ 🔴 Needs Decision: CI billing for 3 orgs
│ 🔴 Burning: HEADING $5.07 on zombies  │
│ 🟡 Blocked: rethinkdb CDC-08 review   │
├─ ACTIVE PROJECTS ─────────────────────┤
│ ┌─ hermes-canopy 🟢 ─────────────────┐ │
│ │ Phase 4 at 11.5/12. Tick storm.     │ │
│ │ ┌─ What needs attention ──────────┐ │ │
│ │ │ Bane: approve architecture?      │ │ │
│ │ └─────────────────────────────────┘ │ │
│ │ ▼ DETAILS (click to expand)         │ │
│ │   Recent work: BE-10d MLS (35 tests)
│ │   Board: BE-11d, BE-12, INFRA-001  │ │
│ │   CI: no CI configured              │ │
│ │   DuckBrain: 25+ entries, active    │ │
│ └─────────────────────────────────────┘ │
├─ IDLE PROJECTS ───────────────────────┤
│ bunker: 2 blocked (root, multi-host)  │
│ consensus: 7 INT tasks pending 33 days │
└───────────────────────────────────────┘
```
