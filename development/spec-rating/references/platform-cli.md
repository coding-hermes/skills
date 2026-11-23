# Platform: CLI tool

## Decisions that must be stated
- Output contract: stdout = data (machine-parseable), stderr = diagnostics — or an explicit deviation.
- Exit codes: the full table (0 success, per-failure-class codes), not just nonzero.
- Config precedence: flags > env > config file > defaults, stated with the discovery paths.
- Interactivity: what runs non-interactively (CI) vs prompts (TTY), detected how.

## Contracts a builder needs
- Machine-readable output format (--json or equivalent) with one full example per command.
- Long-running behavior: progress reporting, Ctrl-C semantics (partial state? clean abort?).
- The command grammar: every verb/flag, or the rule that derives them.

## Failure paths
- Partial completion: which operations are atomic, which can leave half-state, and how the
  user detects and repairs it.
- Network/tool dependencies missing: the error message text and the hint it gives.
- SIGPIPE/closed-stdout: no crash, no hang.

## Rating checks
- FAIL if exit codes are undocumented — scripts cannot use the tool.
- FAIL if any command's output format is shown only by accident in an example.
- FAIL if a destructive verb lacks a --dry-run or a stated confirmation policy.
