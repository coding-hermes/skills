# Why no mandate (design note)

The toolkit's adoption doctrine, in one place.

## The call (Bane, 2026-09-19, verbatim)

> For the coding-hermes-tools the idea is that we are providing tools with proper
> descriptions and settings logging's metrics monitoring ... But we are not forcing it the
> agent should be looking at its task of editing core or a file and see the tool just like
> any other tool and decide that tool is the best room for the job

## What that rules OUT

- Routing rules in a skill that REQUIRE `toolsd` for a given edit.
- An "adoption" workstream measured by forcing invocations.
- Any gate that fails a task because it did not use the toolkit.

## What that REQUIRES

1. **Descriptions that carry the decision.** Each verb states not only what it does but
   *when it is the right choice*. Syntax-only descriptions are why a good tool goes unused.
2. **A surface where an agent looks.** A tool/MCP surface plus `--help`/`describe`, so the
   verbs sit alongside every other tool the agent has.
3. **Settings** (flag > env > file > default) so a repo or lane can express a preference.
4. **Logging** — one structured record per invocation.
5. **Metrics** — chosen / refused / rollback / conflicts caught counters, so value is a
   number.
6. **Monitoring** — a surface to watch it.

## How success is measured

By **choice**, not compliance: invocation counts that grow because the tool is the best
answer, with refusals counted as wins (a refused write that prevented corruption is the
product working). Zero invocations is a discoverability or an obviousness problem, never a
compliance problem — and is fixed by making the tool visible and clearly the right fit,
not by mandating it.
