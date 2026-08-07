# Wrong-Cadence / Missing-Fleet-Pin Diagnosis (2026-08-02)

Symptom: Bane says a project's foreman "isn't running every 12 hours" (or
any cadence) even though the scheduler looks healthy. **Proven on helios**
(tick #147 era): entry was `Enabled=true` with `CooldownS=900` — never the
intended 12h — and the namespace was NULL.

## Checklist — three independent things must all be right

### 1. scheduler.db entry (live source of truth)

```
sqlite3 ~/.hermes/coding-hermes/scheduler.db "SELECT name, enabled, namespace_id, cooldown_s, weight, priority, deliver FROM projects WHERE name='<proj>'"
```

Common failure: `namespace_id` is **NULL** (namespace-mode allocator skips
the project entirely — see starvation-ghost-projects.md §2) and `cooldown_s`
is the default 900 instead of the intended 43200 (12h).

Fix (direct DB update — no daemon restart needed for DB values; verify via API):

```
UPDATE projects SET namespace_id='coding-hermes', cooldown_s=43200, deliver='telegram:<chat>:<thread>' WHERE name='<proj>';
```

### 2. fleet.toml entry (durable pin across restarts)

DB values revert on daemon restart unless the project is pinned in the
fleet config. Add a `[[projects]]` block (mirror existing pins like
<project>, hermes-canopy):

```toml
[[projects]]
name = "<proj>"
repo_url = "https://github.com/<org>/<proj>.git"   # or local:/path
workdir = "~/<proj>"
weight = 10
priority = 8
cooldown_s = 43200
model = "deepseek-v4-flash"
provider = "deepseek-foreman"
namespace_id = "coding-hermes"
deliver = "telegram:<chat>:<thread>"
enabled = true
```

### 3. Daemon must be started with `--config <fleet.toml>`

**The #1 silent gotcha:** fleet.toml pins are ONLY applied at daemon boot
via `--config`. Check the actual running process:

```
ps aux | grep schedulerd     # look for --config
cat /etc/systemd/system/coding-hermes-scheduler.service   # ExecStart
cat ~/.hermes/scripts/scheduler-watchdog.sh               # restart command
```

On this host BOTH the systemd unit AND the watchdog restart command
omitted `--config` — so fleet pins (including new helios entry) never
took effect on restart. If the flag is missing, add it to both, then
`sudo systemctl daemon-reload && sudo systemctl restart coding-hermes-scheduler`
(sudo may need Bane's approval in chat).

## Verify (no restart needed for DB-only changes)

```
curl -s http://127.0.0.1:9090/api/v1/projects | python3 -c "import sys,json; [print(p) for p in json.load(sys.stdin)['projects'] if p['Name']=='<proj>']"
```

Confirm `Enabled=True`, `NamespaceID=coding-hermes`, `CooldownS=43200`.
Note: the API reports `LastTickCompleted` as null on a fresh entry — the
next tick fires ~cooldown after the previous completed tick, not from now.

## Also check

- `deliver` must match the Telegram chat+thread Bane wants reports in
  (helios → `telegram:-1003310984808:4297`). NULL deliver = reports go nowhere.
- Weight/priority affect packing; a 12h-cadence project doesn't need high
  weight (helios: w10/p8) — cooldown does the pacing.

## API PUT field names — Go-style, not snake_case (proven 2026-08-02, <project>)

`PUT /api/v1/projects/<name>` decodes into `database.ProjectUpdates`, whose
fields carry **no JSON tags** — Go matches on the Go field name. So the API
accepts `{"CooldownS": 43200, "Enabled": true}` but **silently ignores**
`{"cooldown_s": 43200}` (200 OK, nothing changes). This burned a full
fix attempt on the <project> project: the snake_case PUT returned the project
JSON with `CooldownS` still 900 and no error.

Correct body (PascalCase field names):

```json
{"CooldownS": 43200, "Enabled": true}
```

Also: the daemon can hang mid-tick and swallow the request — always add
`--max-time 6` to the curl so a hung PUT surfaces as a timeout instead of a
blocked terminal. Verify after the PUT by GETting the project and checking
`CooldownS`.

## Duplicate case-variant entries (<project> vs <project>)

The scheduler treats project names case-sensitively, so a project can have
TWO entries: `<project>` (old, often disabled, has `deliver` set) and `<project>`
(newer, enabled, carries the per-project GatewayKey). When tuning cadence,
check BOTH variants — the enabled one with a GatewayKey is the live ticker.
Disable the stale duplicate and pin cooldown on the live one. The duplicate
is why "I paused it but ticks keep firing" happens: you paused the wrong
case variant.
