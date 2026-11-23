---
name: spec-writing
description: Write and audit implementation specs for Coding Hermes workers. Load when a foreman needs to produce or review a spec before spawning workers.
---

# Spec Writing

Load this when you need to write a spec from scratch or audit an existing one before delegating to workers. Specs are the contract between foreman and workers — ambiguous specs produce wasted cycles.

## When to load

- User says "write a spec for X"
- About to spawn workers on a new feature — verify the spec exists and is solid
- Reviewing a spec another foreman or agent wrote
- Feature is non-trivial (multi-file, multi-service, >1 acceptance criterion)

## What a good spec contains

Every spec must have these six sections. If one is missing, the spec is incomplete.

### 1. Problem Statement
One paragraph. What are we building and why? Who is it for? State the concrete problem, not the solution.

### 2. Acceptance Criteria
Numbered, testable outcomes. Each criterion must be verifiable — if you can't write a test for it, it's not an acceptance criterion. Use the form: "Given X, when Y, then Z."

**Every AC names its proof.** A criterion without an executable check is a wish. Use:

```
AC-n: Given <state>, when <action>, then <observable result> — proof: <command / test name / artifact / number>. (T|C|M)
```

T = automated test, C = command or probe with its expected output, M = manual artifact that must exist.

- **Coverage:** every user story (or requirement) maps to at least one AC. Fewer ACs than stories means part of the spec is unspecified.
- **Banned phrasings:** "works correctly", "is robust", "handles edge cases", "improves quality".
- **At least one anti-gaming AC:** something a green-but-did-nothing implementation cannot pass — a regression replay, a byte-diff, a counter only the real path increments.
- **Blocked is a state:** an AC that cannot run yet keeps its number and gains `BLOCKED-ON: <dependency>` so it is filed, never silently dropped.
- **ACs are the transfer format:** they go into the board row's `acceptance_criteria` and the worker brief VERBATIM.

### 3. Edge Cases
What happens when things go wrong? Invalid input, empty state, concurrent access, timeouts, missing data, large inputs. List each edge case with expected behavior.

### 4. Non-Goals
Explicitly what we are NOT building. Prevents scope creep and worker overreach. Examples: "No auth layer", "No persistence beyond in-memory", "No CLI flags beyond the ones listed."

### 5. Dependencies
What does this depend on? Libraries, services, APIs, data schemas, other features being complete. Include versions where relevant.

### 6. Test Plan
How will the worker verify correctness? List test categories (unit, integration, e2e), key test scenarios, and any test infrastructure needed. Reference the test runner and framework.

## How to audit a spec

1. **Completeness check**: Do all six sections exist? If not, reject — don't fill gaps yourself (that's the spec author's job).
2. **Clarity check**: Can a worker (Grok 4.5 / GLM 5.2 / MiniMax M3) understand every sentence without guessing? Remove ambiguous language.
3. **Testability check**: Does every acceptance criterion map to at least one test case in the test plan? **And does every AC name its proof (command / test / artifact / number)?** An AC with no proof line fails this check the same as an AC with no test.
4. **Scope check**: Are non-goals explicit? If a worker could plausibly build something outside scope, add it to non-goals.
5. **Dependency check**: Will all dependencies be available at coding time? Flag any that need pre-work.

## Configuration-contract verification

- Expand schema references into a field-path registry containing type, omission/default, constraints and change authority; compare the registry back to the schema, including typed maps and tuple elements. A passing example alone does not prove key coverage.
- Exercise required-field deletion and unknown-field insertion at every populated object, plus strict parser probes. JSON Schema treats `1.0` as an integer mathematically; a spec requiring integer tokens needs a separate parser/type-preservation check. Default annotations do not apply themselves: test omission, false, zero, null and derived-default overflow separately.
- Check grantor-without-use examples against all issuance bounds, not only capability membership. An empty downstream capability ceiling can accidentally make an advertised grantor unable to issue anything.
- When a pre-created integration task owns canonical promotion, stage a self-contained versioned schema/example/checker with the deliverable and explicitly name the old-contract contradictions it must reconcile. Do not claim package-wide conformance from candidate-only tests.

## How workers use specs

Workers receive the spec as part of their task prompt. They should:
- Implement acceptance criteria in order
- Handle all listed edge cases
- Run the test plan before marking done
- Not build anything in non-goals

Foremen should paste the relevant spec sections into the worker prompt, not the full file.

## Templates and examples

- **Template**: `references/spec-template.md` — blank template, copy and fill.
- **Examples**: See `references/` for realistic specs of each project type.

Load examples with `skill_view(name='spec-writing', file_path='references/<file>')`.
