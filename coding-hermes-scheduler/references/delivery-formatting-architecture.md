# Delivery Formatting Architecture

**Bane-approved architecture (2026-07-18):**

```
Foreman → clean markdown (no platform knowledge)
Scheduler → strips tool noise (--- separator), adds _tick-id_ footer
         → passes through — NO formatting changes, NO char cap
Hermes → delivers raw markdown → platform
```

## Corrections Applied (evolution)

| Version | What | Problem | Bane's feedback |
|---------|------|---------|-----------------|
| v1 | Raw stdout passthrough | Diff noise, worker prompts visible | "output is not nicely formatted" |
| v2 | trimSummary() — last --- section | Still included tool output after separator | "still needs formatting help" |
| v3 | formatForPlatform() — strip code fences, convert tables | Over-aggressive, lost detail | "it is not a trim thing" |
| v4 | extractVerdict() + extractMetrics() + 3000-char cap | Too slim, lost detail | "output responses are too slim" |
| v5 (current) | Pure passthrough, foreman formats its own output | — | "just make sure the agent knows it should correctly stylize the data to match the delivery platform" |

## Key Rules

1. **Foreman outputs clean markdown** — tables, **bold**, blank-line sections
2. **Scheduler does NOT format** — no stripping, no capping, no conversion
3. **Foreman does NOT know the platform** — no "format for Telegram" in prompt
4. **When Hermes gets platform rendering, scheduler needs zero changes**
5. **Worker output goes before ---, foreman summary after**

## Foreman Prompt (spawn.go)

```
Format your final output as clean, well-structured markdown.
Use markdown tables for status summaries, **bold** for emphasis,
blank lines between sections.
```

## deliver.go (current)

72 lines. Strips only `\n---\n` tool noise. Adds `_tick-id_` footer.
No formatForPlatform(), no extractVerdict(), no convertTables(),
no stripCodeBlocks(), no char cap.
