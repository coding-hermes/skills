# Sudo Blocked in Cron Context — Workaround Pattern

## Problem

When a foreman tick discovers a system-level issue (systemd unit misconfiguration,
binary not in PATH, missing package) that requires `sudo` to fix, the cron
security scanner blocks all `sudo` commands pending approval. In cron context,
there's no user to approve — the fix is stuck.

```
# These all get blocked:
sudo cp file /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart service
```

## Detection

- `terminal()` returns `exit_code: -1` with `status: "pending_approval"`
- The `approval_pending: true` field confirms it's an approval block, not an execution error
- Common blocked patterns: `sudo cp`, `sudo systemctl`, `sudo tee`, `sudo mv`

## Workaround

1. **Write the fixed file to `/tmp/`** — no sudo needed:
   ```bash
   write_file(path="/tmp/fixed-unit.service", content="<corrected unit>")
   ```

2. **Document the fix in the board task** with exact commands:
   ```
   Fix: `sudo cp /tmp/fixed-unit.service /etc/systemd/system/<service> &&
        sudo systemctl daemon-reload &&
        sudo systemctl restart <service>`
   ```

3. **Mark the task as `[ ]` (pending)** — do NOT mark `[x]` since the fix isn't applied.

4. **Note in the foreman report** that the fix is written to a temp file and awaiting
   manual sudo approval.

5. **The user or supervisor** applies the fix manually when they see the report.

## When NOT to Use

- If the fix can be applied without sudo (e.g., user-level configs, git operations),
  apply it directly.
- **Go toolchain directive** — For Go stdlib vulnerabilities, use the `toolchain`
  directive in `go.mod` instead. The Go toolchain auto-downloads the specified
  version; no system install or sudo needed. See
  `references/go-toolchain-sudo-free-vuln-fix.md`.
- If the systemd unit is user-scoped (`~/.config/systemd/user/`), no sudo is needed.

## Proven

Scheduler 2026-07-16: systemd unit missing `Environment=PATH=...` caused 5,163
spawn failures. Fix written to `/tmp/coding-hermes-scheduler.service`, board task
created, report documented the pending manual step.
