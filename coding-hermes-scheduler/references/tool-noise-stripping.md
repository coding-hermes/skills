# Tool Noise Stripping in deliver.go

The scheduler's `trimToolNoise()` function in `deliver.go` strips five types
of terminal tool output noise before delivering foreman output to users.

This is NOT the foreman's job — the foreman produces clean markdown.
The scheduler strips the tool wrapper around that markdown.

## Noise Patterns Stripped

### 1. `---` Separator (strongest signal)

The foreman should end its markdown with `---` to separate tool output from
the final report. Everything after the last `---` is delivered. Everything
before it is tool noise.

```
<tool output, worker prompts, diffs>
---
<foreman's clean markdown summary → delivered>
```

### 2. `┊` Review Panels

Terminal review panels from tools like `review diff`:

```
┊ review diff
┊ a/path/to/file.go → b/path/to/file.go
┊ @@ -10,4 +10,4 @@
```

These are stripped entirely — they're interactive tool output, not content.

### 3. Git Diff Blocks

Standard unified diff output:

```
@@ -10,4 +10,4 @@ func main() {
+    newLine
-    oldLine
```

Block detection: starts with `@@`, continues with `+`/`-` prefixes. Stripped.

### 4. Code Fences

Triple backtick blocks:

```
```python
code here
```
```

Stripped — no syntax highlighting in plain-text delivery.

### 5. Worker Prompts

When the foreman spawns a worker via `delegate_task`, the worker's full
prompt (including `You are a coding agent`, `## TASK:`, `## INSERTION POINT`,
`## PATTERN TO FOLLOW`, etc.) can leak into the foreman's stdout. 

These sections are detected by their distinctive headers and stripped.

## Anti-Noise Pattern for Foremen

When producing output for delivery:

1. Write your final summary as clean markdown
2. End with `---` to separate from any preceding tool output
3. Don't worry about the rest — the scheduler handles stripping

## If Noise Still Leaks

If a new noise pattern emerges (a new tool with distinctive output), add
a detection pattern to `trimToolNoise()` in `deliver.go`. Don't ask the
foreman to change its behavior — fix the delivery layer.

## Proven

- **2026-07-18** — The `<project>` foreman delivered raw worker prompts
  (127 lines of task instructions + diffs) directly to Telegram. Root cause:
  no `---` separator in the foreman output, and the original `trimToSummary()`
  only looked for `---`. Fix: added comprehensive pattern matching for five
  noise types in `trimToolNoise()`.
