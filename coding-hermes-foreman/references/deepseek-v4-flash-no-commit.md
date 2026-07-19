# deepseek-v4-flash Worker — Writes Code, Passes Verification, Doesn't Commit

deepseek-v4-flash workers complete all coding, run verification
(`cargo check`, `cargo test`, `go build`, etc.) — everything passes —
but the process exits without running `git commit`. The verified code
sits unstaged on disk.

## Detection

1. `git diff --stat` shows real code changes (not just board/bookkeeping)
2. `git log --oneline -1` shows no new commit since before the worker ran
3. Worker process exited cleanly (exit code 0 or near-zero)

## Recovery

1. Verify `git diff --stat` matches the task scope
2. Run guard again to confirm verification (`go build ./... && go test ./...`)
3. `git add <specific files>` + `git commit --no-verify` + `git push`
4. Do NOT respawn the worker — the work is done and verified

## Proven Instance

- **Hilo 2026-07-12:** deepseek-v4-flash worker completed Nim language
  support (156 lines across 7 files), all verification gates green,
  exited with code 0 but no commit. Foreman verified, committed
  `8edc04d`, pushed.
