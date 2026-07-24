---
name: coding-hermes-model-router
description: Task decomposition and model routing — break projects into independently executable tasks, score by priority/complexity/capability, route each to the least expensive model that can complete it reliably
version: 1.2.0
category: coding-hermes
---

# Model Router — Task Decomposition & Model Selection

Break a project into independently executable tasks, rank by impact, estimate complexity, identify required capabilities, and route each task to the least expensive model that can complete it reliably. Do NOT use the most capable model — use the cheapest model that works.

## Task Routing Process

1. Identify core purpose + minimum viable functionality
2. Break work into small, independently assignable tasks
3. Identify dependencies + assign priority (Critical/High/Medium/Low/Trivial)
4. Estimate complexity (1-10 ± uncertainty)
5. Assign capability tags (+/++/+++ required, -/--/--- unnecessary)
6. Exclude models lacking essential capabilities
7. Score remaining models against task tags
8. Choose cheapest model with acceptable reliability
9. Select lowest sufficient reasoning level (Minimal/Low/Medium/High/Maximum)
10. Assign fallback model for uncertain tasks

## Priority

| Priority | Meaning | Examples |
|----------|---------|----------|
| Critical | Cannot perform core purpose, can't start, corrupts data | Won't boot, auth broken |
| High | Important capability can't be demonstrated/released | Demo path fails, deployment blocked |
| Medium | Affects most users but core usable | Unreliable common operation |
| Low | Uncommon workflows, edge cases | Rare browser issue |
| Trivial | Little effect on functionality | Docs, log wording, comments |

## Complexity (1-10 ± uncertainty)

| 1-2 Simple | 3-4 Moderate | 5-6 Complex | 7-8 Very Complex | 9-10 Exceptional |
|------------|--------------|-------------|------------------|------------------|
| Local, deterministic, low-risk | Several conditions, solution clear | Multiple components, integration | Architectural impact, concurrency, security | System-wide redesign, novel research |

## Capability Tags

**Code:** code-generation, code-review, debugging, architecture, refactoring, testing, security, performance, concurrency, distributed-systems, frontend, backend, infra

**Tools:** terminal, repository-search, database, browser, api-use, file-editing, test-execution

**Perception:** basic-vision, advanced-vision, ui-analysis, diagram-analysis

**Reasoning:** long-context, planning, algorithmic-reasoning, multi-step-reasoning, requirements-analysis

**Communication:** documentation, concise-output, user-facing-copy, structured-data, spec-writing

Tag strength: `+++tag` essential, `++tag` important, `+tag` useful, `-tag` unnecessary, `--tag` strongly avoid

## Reasoning Levels

| Level | When |
|-------|------|
| Minimal | Mechanical edits, formatting, simple lookups, one-file changes |
| Low | Straightforward implementation, limited branching |
| Medium | Multi-file work, debugging, normal integration, moderate uncertainty |
| High | Difficult debugging, architecture, migrations, security, complex state |
| Maximum | Extensive exploration, deep planning, novel reasoning |

## Model Profiles — Fleet Workers

### DeepSeek V4 Pro
- **Complexity:** 1-8 | **Cost:** $0.44/$0.87/1M | **Speed:** Fast (2-3x Claude) | **Context:** 1M
- **++:** code-generation, debugging, terminal, refactoring | **+:** architecture, long-context
- **-:** basic-vision, advanced-vision, ui-analysis
- **Provider:** ollama-cloud (flat-rate) | **Levels:** Low-High-Max
- **Best:** Daily driver, large refactors, math/algorithm, bug fixing

### DeepSeek V4 Flash
- **Complexity:** 1-5 | **Cost:** $0.10/$0.20/1M | **Speed:** Fast | **Context:** 1M
- **++:** code-generation, terminal, test-execution | **+:** concise-output, file-editing, testing
- **-:** advanced-vision | **--:** architecture, complex-debugging
- **Provider:** opencode-go (flat-rate) | **Levels:** Minimal-Med
- **Best:** Boilerplate, mechanical tasks, routine fixes, test running — budget test runner

### Kimi K3
- **Complexity:** 2-6 | **Cost:** $0.40/$0.80/1M | **Speed:** Medium | **Context:** 262K
- **++:** agentic-coding, autonomous-work | **+:** code-generation, debugging, multi-step-reasoning
- **-:** advanced-vision, ui-analysis | **--:** long-context
- **Provider:** kimi-for-coding | **Levels:** Low-Med-High
- **Best:** Autonomous coding, Go/TS generalist, set-it-and-forget-it

### MiniMax M3
- **Complexity:** 1-5 | **Cost:** Flat-rate (prepaid) | **Speed:** Medium | **Context:** 128K
- **++:** code-generation | **+:** debugging, terminal, api-use
- **--:** architecture, complex-reasoning, long-context | **-:** advanced-vision
- **Provider:** minimax | **Levels:** Minimal-Low-Med
- **Best:** Python/TS features, bounded implementation

### GLM-5.2
- **Complexity:** 2-8 | **Cost:** $0.30/$0.60/1M | **Speed:** Medium | **Context:** 1M
- **++:** code-generation, code-review, terminal | **+:** debugging, long-context, architecture
- **-:** creative-writing, user-facing-copy
- **Provider:** zai-glm | **Levels:** Low-Med-High-Max
- **Best:** Primary coding, code review/critic, SWE-bench Pro 62.1%

### GPT-5.6 Sol
- **Complexity:** 3-8 | **Cost:** $100/mo flat-rate | **Speed:** Medium | **Context:** 1M
- **+++:** architecture | **++:** complex-reasoning, debugging, planning | **+:** code-generation
- **-:** fast-mechanical, concise-output (verbose/bloat)
- **Provider:** openai-codex | **Levels:** Low-Med-High-Max
- **Best:** Complex reasoning, architecture design, deep debugging

### GPT-5.6 Terra
- **Complexity:** 2-5 | **Cost:** $100/mo flat-rate | **Speed:** Medium | **Context:** 1M
- **+++:** spec-writing, documentation | **++:** structured-data, testing | **+:** code-generation
- **-:** complex-architecture, concurrency | **--:** performance
- **Provider:** openai-codex | **Levels:** Minimal-Med-High
- **Best:** Spec/documentation writing, test authoring, bounded implementation — primary spec writer

### GPT-5.6 Luna
- **Complexity:** 1-4 | **Cost:** $100/mo flat-rate | **Speed:** Fast | **Context:** 1M
- **+++:** test-execution, testing, vision, browser, screenshots | **++:** debugging, terminal, CLI-automation | **+:** code-review, file-editing
- **-:** architecture, spec-writing | **--:** complex-reasoning
- **Provider:** openai-codex | **Levels:** Minimal-Med
- **Best:** Test running, test debugging, CI verification, regression hunting, browser-based E2E testing, visual regression testing, screenshot comparison — primary test runner with vision

### Step 3.7 Flash
- **Complexity:** 1-4 | **Cost:** $0.09/$0.30/1M | **Speed:** Fast | **Context:** 256K
- **++:** agentic-coding, testing, test-execution, browser, CLI-automation | **+:** code-generation, terminal, vision, screenshots
- **-:** architecture, complex-reasoning | **--:** long-context
- **Provider:** stepfun | **Levels:** Minimal-Med
- **Best:** C++/Rust features, Python tests, infra/CI, test authoring + execution — fastest budget test runner

### Grok 4.5
- **Complexity:** 2-7 | **Cost:** Flat-rate (prepaid) | **Speed:** Medium | **Context:** 128K
- **++:** advanced-vision, creative-writing | **+:** architecture, code-generation, basic-vision
- **--:** fast-mechanical | **-:** concise-output, routine-tasks
- **Provider:** xai-oauth | **Levels:** Med-High-Max
- **Best:** GenAI/research, creative architecture, vision — NOT routine coding

### Hy3 (OpenCode Go)
- **Complexity:** 1-3 | **Cost:** Flat-rate | **Speed:** Fast | **Context:** 128K
- **++:** frontend, ui-work, html-css | **+:** file-editing, concise-output
- **--:** backend, architecture, complex-reasoning | **-:** debugging
- **Provider:** opencode-go | **Levels:** Minimal-Low
- **Best:** Frontend/HTML/CSS, UI implementation, dashboards

## Routing Formula

```
fit = complexity_fit + capability_match + tool_match + context_fit 
      - cost_penalty - latency_penalty - weakness_penalty
```

Essential capability failures override numeric score.

## Test Runner Hierarchy

For test-running tasks, prefer in order: **Luna** (primary, $100/mo flat) → **Step 3.7 Flash** ($0.09/1M, fastest) → **V4 Flash** ($0.10/1M, catches missing imports). For spec writing, prefer: **Terra** (primary) → **GPT-5.6 Sol** (complex specs) → **V4 Pro** (fallback).

## Escalation

Escalate when: touches more components than estimated, complexity exceeds model range, tests reveal architectural issues, missing essential capability, 2+ failures for different reasons, security/data-loss risk, context exceeds model capacity.

## Expected Usage

**Foreman loads this skill when:**
- First tick on a new project → decompose into task matrix
- Board is empty + NEVER-DONE audit → re-assess with model routing
- Worker selection → match task tags to model profiles above

**Output format:**
```
Core purpose: [one-liner]
ID | Task | Priority | Complexity | Deps | Tags | Model | Reasoning | Fallback
Assumptions: [only routing-relevant ones]
Routing Notes: [explain unusual selections]
Execution Order: [prioritized IDs]
Escalation Conditions: [when to reroute]
```