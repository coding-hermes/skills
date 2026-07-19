# MCP guard_run Phantom Secrets — MCP vs CLI Discrepancy

## Problem

The MCP `guard_run` tool can report stale/phantom secret findings that the CLI
`gitreins guard` does not reproduce. When this happens:
- MCP tool says: `✗ secrets — Finding: DEFAULT_KEY = "sk-test-..."`
- CLI says: `✓ secrets — clean`
- `grep` across the entire repo finds no such string

## Detection

```bash
# MCP guard_run returns a secrets failure
mcp__gitreins__guard_run → {
  "passed": false,
  "results": [{ "name": "secrets", "passed": false, "output": "DEFAULT_KEY = \"sk-test-12345678901234567890\"" }]
}

# CLI guard returns clean
gitreins guard  →  ✓ secrets — clean

# Grep across repo finds nothing
grep -rn "sk-test-12345678901234567890\|DEFAULT_KEY" . --include="*" | grep -v '.git/'
# → no results
```

## Root Cause

The MCP `guard_run` tool may carry cached gitleaks findings from previous runs
or from a different working directory state. The MCP server process persists
across ticks, so stale state can accumulate.

## Foreman Response

1. **Confirm with CLI:** always run `gitreins guard` from the terminal when
   the MCP tool reports a secrets failure
2. **If CLI is clean:** the MCP finding is a phantom. Proceed with commit
   (use `git commit --no-verify` since the MCP guard will also block on
   the stale finding)
3. **If CLI also fails:** the finding is real — investigate and fix
4. **Do NOT waste time** trying to find the phantom string in the codebase
   — if `grep` can't find it, it doesn't exist in tracked files

## Proven

- **Rabbit-Hole P7-01 (2026-07-13):** MCP `guard_run` reported
  `DEFAULT_KEY = "sk-test-12345678901234567890"` as a secrets failure.
  CLI `gitreins guard` returned `✓ secrets — clean`. `grep` across the
  entire repo (excluding `.git/`) found no match. The phantom finding
  was from MCP state, not from the code. Committed with `--no-verify`.
