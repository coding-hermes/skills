# A DISABLED target: audit read-only, escalate, write NOTHING (G2)

When `projects.enabled=0` (or `GET /api/v1/projects` → `enabled=false`), the whole write half of the
cycle is off: no rows, no wake (`PUT` cooldown, `POST /api/v1/evaluate`), no board mutation —
even a hygiene fix. `enabled=false` is human intent, and a wake against it manufactures exactly the
churn that got the project auto-disabled. The cycle still earns its slot: run the reconciler, audit
the board read-only, verify the open ledger premises with real commands, log the cycle, and
**escalate the disable itself as the finding**.

Read the provenance before narrating it: `events` rows for the disable (`component='api'` →
`disabled_by=api, disabled_reason='disabled via API update'`; `auto-disable` carries the failure
rate; `api-pause` is a pause). Compare the disable timestamp against the last tick's `completed_at`
and `count(*) FROM ticks WHERE spawned_at > <disable>` — a disable with **zero** ticks after it and a
last tick that ended BEFORE it means the disable killed scheduler dispatch, not that the foreman
failed. Then check for non-scheduler drivers on the same workdir (`ps -eo pid,lstart,cmd` for
`e2e-*.sh` / `*-phase-driver.sh`, plus `/proc/<pid>/cwd`): a hand-driven push
(BANKAI/opencode/e2e proof scripts) is the usual reason a lane is deliberately suppressed, and it
turns the disable from suspected neglect into likely operator intent.

Escalate one decision, not a status report: is the disable intentional? If yes, say it should be
DURABLE — a disable that lives only in the SQLite row is regenerated from `fleet.toml` by the next
`fleet-cooldown-policy.py --apply` + restart, so it can silently re-enable. If no, name the
consequence: the board's whole open set is starving.

**The disable does not lengthen the ledger's life.** Re-minted rows close only when foreman ticks
keep running; a project disabled after a re-mint can leave every re-mint open forever. Keep their
ledger status at `added` (never stamp `verified` off a re-mint note alone) and fold the
can't-close argument into the escalation.
