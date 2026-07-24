---
name: fleet-daily-report
description: Generate a comprehensive daily HTML fleet report using parallel subagents to gather per-project data, then compile into an interactive dashboard with collapsible cards and drill-down depth
version: 1.0.0
category: coding-hermes
---

# Fleet Daily Report

Generate a comprehensive, interactive HTML report covering all coding-hermes projects. Use multiple subagents in parallel to gather data, then compile into a single deliverable.

## Report Structure

### Header
- Generation timestamp, daemon status (health, uptime, active ticks, spawn stats)
- Fleet summary: total projects, active count, idle count, total tasks pending
- Quick stats: commits today, CI pass/fail, new tasks created, risks identified

### Per-Project Cards (one per enabled project)
Each card is a collapsible `<details>` element showing:
1. **Header row:** Project name, status badge (ACTIVE/IDLE/ZOMBIE/BLOCKED), pending task count, cooldown
2. **Expanded body:**
   - **Last 3 runs:** tick timestamp, outcome, commits, model used, tasks completed
   - **Recent work:** what was built/fixed in last 24h (from git log + DuckBrain)
   - **Board status:** real pending tasks with model assignments (from tasks.md)
   - **CI status:** pass/fail, last run URL
   - **Risks:** blocked tasks, zombie detection (idle ticks > 20), cooldown anomalies
   - **Never-Done findings:** gaps discovered by most recent audit

### Problem Dashboard
- Stuck/zombie projects (idle > 20 ticks but has pending)
- CI failures (grouped by cause — billing, test failure, config)
- Board discrepancies (GitReins vs coding-hermes disagreement)
- Cooldown anomalies (active at >2h, idle at <12h)
- Missing NEVER-DONE, missing board, missing foreman

## Data Gathering — Parallel Subagents

Dispatch 4 subagents simultaneously, each responsible for ~10 projects:

**Subagent instructions:**
For each assigned project:
1. Read `.coding-hermes/tasks.md` — count real pending, flag NEVER-DONE presence
2. Check GitReins board if available — count pending, note discrepancies
3. Run `git log --since="24 hours ago" --oneline` — collect commit messages
4. Check DuckBrain for recent entries about this project
5. Get last 3 ticks from scheduler API
6. Check CI status via `gh run list --limit 3` or report N/A
7. Detect: zombie (idle ticks > 20 with pending), blocked tasks, cooldown issues

Output format: JSON per project ready for compilation.

## HTML Template

Use `references/report-template.html` — a responsive dashboard with:
- Dark theme, fleet-color branding
- Collapsible `<details>` cards per project
- Color-coded status badges (🟢 active, 🔵 idle, 🟡 blocked, 🔴 zombie)
- Problem dashboard section at top
- Auto-refresh meta tag (every 5 min during active hours)
- Mobile-responsive grid layout
- CSS-only — no JS framework dependency

## Delivery

Generate the HTML file, save to `~/.hermes/reports/fleet-YYYY-MM-DD-HHMM.html`, and deliver via:
1. `MEDIA:` path in the response (shows inline in Telegram)
2. Text summary: "Fleet Report — [date] — [active] active, [idle] idle, [risks] risks"

## Scheduling

This skill is designed for cron: `0 8,14,20 * * *` (three times daily at 8am, 2pm, 8pm).
Each run is independent — the report is a complete snapshot, not a diff.
