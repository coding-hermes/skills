# Shell Quoting Pitfall: `hermes chat -q` with Code-Heavy Prompts

## Problem

When passing a worker prompt to `hermes chat -q`, the prompt string is interpreted by the shell before reaching Hermes. If the prompt contains Go/Rust/C++ code blocks, backticks, single quotes, dollar signs (`$`), parentheses, or other shell metacharacters, the shell parser breaks:

```bash
hermes chat -q '...go code with func() and $variables...' ...
# bash: syntax error near unexpected token '('
# hermes: error: unrecognized arguments: block others
```

Even single-quoted strings can break when nested quotes, backticks, or dollar signs appear inside Go import paths, struct literals, or function calls.

The error manifests as `bash: syntax error near unexpected token` or `hermes: error: unrecognized arguments:` — and the worker never starts.

## Fix: Temp File Approach

Write the prompt to a temp file first, then pass it via `$(cat file)`:

```bash
# Write prompt to file (avoids ALL shell interpolation)
write_file(path="/tmp/task-prompt.txt", content="...full prompt...")

# Pass via cat — the prompt content never touches the shell parser
cd /home/kara/<project> && hermes chat -q "$(cat /tmp/task-prompt.txt)" \
  -m <model> --provider <bucket> --ignore-rules --cli -Q
```

The `$(cat file)` substitution happens after shell parsing — the prompt content is read as a literal string, not parsed for shell syntax.

## Prevention Checklist

When the worker prompt contains ANY of these, use the file approach:
- Go code blocks (imports, structs, functions with parentheses)
- Backticks (markdown code fences, Go struct tags)
- Single quotes inside the prompt
- Dollar signs (`$VAR`, Go string interpolation `fmt.Sprintf`)
- SQL queries with single-quoted strings (`WHERE status = 'completed'`)
- Pipe characters or redirects

## Proven Instances

- **Scheduler 2026-07-15** — OBS-006 worker spawn with inline Go code blocks (imports, struct definitions, SQL queries with single-quoted strings) failed with `bash: syntax error near unexpected token '('`. File-based approach succeeded immediately with glm-5.2 @ zai-glm.
