# Parallel Spec-Worker Spawning on openai-codex

Proven pattern: GPT-5.6-terra workers on `openai-codex` can run **concurrently**,
not just serialized. When 9 workers are spawned simultaneously for spec-writing
tasks, they all make API calls in parallel and complete within ~7 minutes total.

## Pattern

```bash
# Write each spec's prompt to a temp file (avoids shell quoting issues)
# Keep prompts focused: ~1500-2700 bytes each, targeting exactly what that spec covers

# Spawn all workers simultaneously in background
for prompt in /tmp/spec-worker-*.txt; do
  cd /home/kara/<project> && \
  hermes chat -q "$(cat $prompt)" -m gpt-5.6-terra --provider openai-codex \
    --ignore-rules --cli -Q &
done
```

## Proven Instance: Heading Spec Phase (2026-07-15)

- **9 workers** spawned simultaneously on `gpt-5.6-terra @ openai-codex`
- **Tasks:** SPEC-1 through SPEC-9 (API, Data Model, Agentic Loop, Preference Engine, Transcript Layer, Disruption Intel, Amadeus Integration, Customer Export, Mock Data)
- **Output:** 7,367 lines across 9 files in ~7 minutes
- **Provider behavior:** openai-codex accepted all 9 concurrent sessions — no rate limiting, no queuing
- **Cache hit rates:** 45-99% across workers (higher on later calls within each session)
- **Prompt format:** Short targeted prompts (1,500-2,700 bytes each) referencing `specs/prd.md` for shared context, with task-specific detail

## Per-Worker Prompt Structure

Each spec worker prompt (~100-150 lines):
1. Role: "You are a senior [domain] engineer/architect"
2. Task: "Write `specs/<file>.md`"
3. Context: "Read `specs/prd.md` for full context first"
4. Coverage: Bullet-pointed sections to cover with specific detail
5. Format: Output format requirements
6. Guard: "Write the file and exit. Do not run build commands, tests, or git operations."

## Why This Works

- **openai-codex** is not rate-limited per-session — each `hermes chat` process gets its own session
- GPT-5.6-terra handles the spec-writing task reliably (no silent exits, no stuck generations)
- Short, focused prompts mean each worker doesn't waste tokens re-reading PRD sections it doesn't need
- Workers self-manage: each reads the PRD, plans, writes its file, and exits

## When to Use

- Spec/doc writing phases with 3+ independent files
- Any task where multiple workers write to different output files
- When time matters: 9 serial workers would take ~70 minutes; 9 parallel took ~7 minutes

## When NOT to Use

- Code tasks where workers write to the same package (concurrent file edits cause merge conflicts)
- Tasks that depend on each other's output
- Providers with known session limits (test first with 2-3 workers)
