# Lane uptime and outage triage (the ops lane's second question)

The census answers "is the ops surface present?". This file answers "is the family still running,
and which owner does a dark family belong to?". Run it after the census, every tick.

## 1. Family census, one GET per lane

`GET /api/v1/projects` is paginated (`{projects,total,limit,offset}`, page cap 500) and its list rows
carry no tick detail, so census lanes individually and read the OBJECT shape:

```bash
curl -s "http://127.0.0.1:9090/api/v1/projects/<lane>" \
  | jq -r '[(.project.name // "?"), (.latest_tick.status // "none"),
            (.latest_tick.id // "-"), (.latest_tick.spawned_at // "-")] | @tsv'
```

- `.latest_tick` sits at the TOP level; `.project.latest_tick` is null and reads as "never ran".
- Enumerate the lanes from the family prefix — never hand-pick — and print `enabled` beside the
  status: a disabled lane's failure record is not the same finding as an enabled lane's.
- A lane showing `running` with an EMPTY `session_id` is usually a spawn record, not a live session;
  do not stand down for it without a second signal.

## 2. Tick history (last ok, failure class, burst shape)

```bash
sqlite3 ~/.hermes/coding-hermes/scheduler.db "select project_name||' | last_ok='||coalesce(max(case when status='completed' then spawned_at end),'never')||' | age_h='||coalesce(round((julianday('now')-julianday(max(case when status='completed' then spawned_at end)))*24,1),'na')||' | last_status='||(select status from ticks t2 where t2.project_name=t.project_name order by spawned_at desc limit 1) from ticks t where project_name like '<family>%' and spawned_at>='<window-start>' group by project_name order by project_name;"
```

```bash
# failure classes today, fleet-wide — one row per class is the whole diagnosis
sqlite3 ~/.hermes/coding-hermes/scheduler.db "select case when error like '%unservable-rating%' then 'unservable-rating' when error like '%502%timed out%' then 'gateway-502-timeout' when error like '%429%' then '429' when error='' or error is null then 'empty' else substr(error,1,40) end cls, count(*) n from ticks where spawned_at>='<today>' and status='failed' group by cls order by n desc;"
```

**Get the column names right before writing the query — the two tables have different vocabularies.**
`projects` is keyed by `name` and carries `repo_url, workdir, weight, priority, cooldown_s, enabled,
model, provider, last_tick_started, last_tick_completed, consecutive_failures, disabled_reason`; it
has NO `latest_tick_*` columns (those live only on the HTTP `/api/v1/projects/<lane>` object). `ticks`
is keyed by `project_name` and carries `id, session_id, pid, status, outcome, spawned_at,
completed_at, exit_code, commits, error`; it has NO `name` or `project` column. A wrong name costs a
round trip — the error is a bare `no such column`, so print `pragma table_info(projects)` (or
`(ticks)`) once and re-filter instead of guessing a second spelling.

Invocation shape matters on the unattended surface: a large `.db` named with extra flags can be
refused by the command guard's scan budget. Keep the call minimal (`sqlite3 <db> "<one query>"`) and
format INSIDE the SQL with `||` concatenation instead of `-header`/`-sep`/`-column`.

Age arithmetic: `julianday('now')` is UTC and the stored timestamps carry an offset, so computing
against `julianday('now','localtime')` double-shifts and prints negative ages. Use `'now'` alone.

## 3. Attribution table

| error contains | class | owner board |
|---|---|---|
| `unservable-rating`, `no eligible model`, `chain_length": 0` | router cannot serve the classifier's requirement | task-router (pending rows already sit on the capability-vocabulary hole) |
| `hop-wall-timeout`, `degraded-wall-cap`, `502` | a single degraded hop burns its wall budget | task-router |
| `429` | provider capacity | task-router / provider row |
| `aborted by graceful shutdown — drain` | scheduler drain, infrastructure not project health | scheduler |
| `failure rate …threshold` in `disabled_reason` | auto-disable burst | scheduler + the family's own auto-disable row |

A project lane's failure record is almost never a project defect when the class is in the top four
rows above. Quote the class, link the owning row, and keep the project row for project-owned surfaces.

## 4. Before you recommend a mitigation

Split the fleet and quote both sides. Example shape: pinned vs unpinned lanes over the same window,
`select case when coalesce(p.model,'')='' then 'unpinned' else 'pinned' end, t.status, count(*)`.
If the failing share is the same on both sides, the mitigation does not exist and the report says so
in one line — that line is worth more than a recommendation nobody tested.

## 5. Where the evidence goes

Registered workdir for an ops lane is often the project checkout. Do not write into it during a
barrier. Write `~/.hermes/stand-in/<family>-lane/<lane>-<date>-evidence.md` (or the family's existing
per-tick series if one exists), append rather than rewrite, and cite it from the board row's
reasoning so the next tick can re-verify the quoted numbers against origin instead of trusting prose.
