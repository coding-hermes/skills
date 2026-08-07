# DuckBrain HTTP Sync Failure — Silent Memory-Write Loss (2026-08-01)

## Symptom

Every tick's post-tick DuckBrain memory write fails silently. The scheduler
log (once logging exists) shows repeated:

```
SYNC: post tick <project>-<ts>: http post: Post "http://localhost:3000/api/memories?namespace=coding-hermes":
dial tcp 127.0.0.1:3000: connect: connection refused
```

148 occurrences accumulated before discovery. Nothing surfaced in tick
reports — the sync layer logs at WARNING and moves on, and the foreman's
DuckBrain writes "succeed" via the MCP bridge (stdio) while the scheduler's
HTTP sync silently dies.

## Root Cause

The scheduler's sync layer (`internal/sync/duckbrain.go`) POSTs to
`http://localhost:3000/api/memories` — it expects DuckBrain's **HTTP API**.
DuckBrain's default deployment runs as **stdio MCP only**
(`node bin/duckbrain.js stdio` via hermes-mcp-wrapper). Nothing listens on
:3000, so every scheduler sync attempt is refused.

Two independent write paths exist:
- **MCP bridge (stdio)** — what foremen use via the `duckbrain` MCP tools.
  Works fine.
- **Scheduler sync layer (HTTP :3000)** — what the daemon uses to push tick
  events. Was dead.

## Fix

Run DuckBrain's HTTP server as a permanent systemd user unit:

```ini
# ~/.config/systemd/user/duckbrain-http.service
[Unit]
Description=DuckBrain HTTP API (memory server for fleet sync)
After=network.target

[Service]
Type=simple
WorkingDirectory=~/duckbrain
ExecStart=/usr/bin/node bin/duckbrain.js http --port 3000
Restart=on-failure
RestartSec=15
Environment=HOME=~

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now duckbrain-http.service
curl -s http://localhost:3000/health   # → {"status":"healthy",...}
```

**Port conflict:** if a background `node duckbrain.js http` is already
holding :3000, kill it first (`process kill`), then let systemd own the port
— otherwise the unit starts, fails to bind, and stays inactive.

## API payload shape

The scheduler's payload is correct and unchanged:
`POST /api/memories?namespace=X` with body
`{"key","domain","content","attributes"}`. Do NOT send `embedding_text` —
the HTTP API rejects it (`Missing required fields: key, domain, content`).
`content` is the required field (may be a JSON string).

## How the bug was found (the meta-lesson)

The scheduler had **no persisted logging** — stdlib `log` to stdout only, no
log file, no journald unit entries. Adding a `-log-file` flag to `schedulerd`
(commit 4e54fe6: `io.MultiWriter(os.Stdout, lf)` on the log output, flag
defaults to `~/.hermes/coding-hermes/scheduler.log`) surfaced the DuckBrain
failure within 30 seconds of the daemon restart. **Always add log
persistence before debugging a fleet — the answer is already in the log you
don't have.**

## Verification

- `grep -c "connection refused" ~/.hermes/coding-hermes/scheduler.log` —
  count stops growing after the fix.
- Post a test memory via curl (see payload shape above) and confirm a UUID
  comes back.
- Next tick: scheduler log shows no new `SYNC: ... connection refused`.
