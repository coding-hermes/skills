# Supervisor Auto-Pause Orphan Chain Detection

## Pattern

When the supervisor (or a prior foreman) pauses a cron with reason "Replaced by X", it creates
a handoff chain: cron A → cron B. If B also fails and gets paused, BOTH crons are dead — the
handoff never completed.

## Detection

```bash
# Find all paused crons with "replaced" reasons
python3 /tmp/check_paused_crons.py  # see scripts/check-paused-crons.py
```

Key signals:
1. A paused cron has `paused_reason` containing "Replaced by" or "supervisor auto-pause"
2. The replacement cron named in the reason is ALSO paused with error
3. Neither cron has run in days

## Recovery

1. Check the replacement cron's last error — if it's transient (gateway shutdown, rate limit), re-enable both
2. If the replacement cron has a real bug, fix it first, then re-enable
3. If the replacement concept was wrong (e.g., a dev-loop cron can't do browser E2E), re-enable the original

## Proven

**EduOS 2026-07-15:** Browser E2E Tester (d838ce4f5ddc) paused by supervisor on Jul 11 with reason
"Replaced by EduOS Alpha Dev Loop (supervisor auto-pause)". The Dev Loop (a3bfd8f8fe14) was ALSO paused
with error. Both crons dead for 4 days. Neither showed up in normal cron health checks because:
- The E2E Tester's pause was intentional (had a reason)
- The Dev Loop's pause just looked like a normal error

**Detection gap:** The discovery sweep in Step 1.5 checks CI, build, endpoints, and source code but
doesn't check sibling cron state. A `cronjob list` sweep with cross-reference for "replaced" chains
would have caught this immediately.
