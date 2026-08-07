# fleet.toml — Cooldown Pinning Done Right

Bane's explicit correction (2026-08-01): **"Your only patching the fleet for
this one workload not all workloads."** When a cooldown keeps reverting after
scheduler restarts, add the fleet.toml entry — but add ONLY the one project
being pinned. Do NOT enumerate every project or copy all rows from
`fleet.example.toml` as placeholders.

## The two fleet files (don't confuse them)

| File | Purpose | Managed by |
|------|---------|------------|
| `~/.hermes/fleet.toml` | cooldown-policy auto-gen (fleet-cooldown-policy.py) | script |
| `<scheduler-repo>/coding-herms-scheduler/fleet.toml` | **schedulerd project-seed config** (`--config fleet.toml`) | agent/hand |

## Key facts

1. **Format** — see `fleet.example.toml` in the same dir. A minimal entry:

```toml
[[projects]]
name = "<project>"
repo_url = "local:~/<project>"
workdir = "~/<project>"
weight = 15
priority = 9
cooldown_s = 43200          # 12h = 43200; 2h = 7200; 45m = 2700; 15m = 900
model = "deepseek-v4-pro"
provider = "deepseek-foreman"
namespace_id = "coding-hermes"
deliver = "telegram:-1003310984808:92897"
enabled = true
```

2. **It only takes effect on scheduler restart WITH the flag.** The running
   daemon is often launched WITHOUT `--config fleet.toml` (it reads
   scheduler.db via the API). Check `ps aux | grep schedulerd` for the flag
   before claiming the file will do anything. If the flag is absent, either
   restart with it or tell Bane the API PUT is the live source until then.

3. **API PUT is the immediate path; fleet.toml is the durability path.**
   `curl -X PUT http://127.0.0.1:9090/api/v1/projects/<name> -d
   '{"CooldownS":43200}'` applies now. The TOML makes it survive restarts.
   Do both; verify with GET after.

4. **scheduler.db is ground truth.** Foreman board headers drift (<project> ticks
   claimed CooldownS=43200/1350 while the DB showed 900 — 9+ documented
   reversions). Always confirm with the API GET or a direct DB query before
   trusting a board claim.

5. **Reversion symptom:** cooldown resets to a default (e.g. 7200s) after
   every scheduler restart → fleet config or policy script is re-applying.
   The board entries saying "reversion #N" are the paper trail; the fix is
   the fleet.toml entry + restart-with-flag, not repeated API PUTs.
