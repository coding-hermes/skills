---
name: coding-hermes-specs
description: Write implementation-ready specs for coding-hermes workers. Exact Go interfaces, DDL, error paths, wiring, edge cases. A worker reading the spec must produce correct code with zero clarifying questions.
version: 1.0.0
category: software-development
---

# Coding Hermes Implementation Specs

**The standard:** A worker reading this spec must produce correct, compilable code without asking a single clarifying question.

Architecture paragraphs, component lists, and "we will need X" statements are **pre-spec notes.** Real specs eliminate ambiguity.

## The Rule

> If a worker can build two different things from the same spec, the spec is wrong.

## What Every Spec File Must Contain

### Required Sections

1. **Exact interfaces** — Not "a search service" but the Go/Python/TS interface with every method signature, parameter type, and return type
2. **Error paths** — Every error condition, when it triggers, what the caller sees
3. **Wiring** — How this component connects to CLI flags, HTTP routes, gRPC handlers, main.go
4. **Database** (if applicable) — Exact DDL with indexes, constraints, and model structs
5. **Config** — Exact env var names, types, defaults, validation rules
6. **Edge cases** — Empty inputs, nil values, timeouts, concurrent access, large payloads
7. **Testing** — Exact test scenarios, expected outcomes, edge cases to cover
8. **Hilo impact** — What depends on this code, what this code depends on

### Banned Patterns

- "We will add X later" — cut it or spec it
- "The system should handle Y" — HOW? Exact code in spec
- "Consider using Z" — decide. The spec IS the decision
- "TBD" or "Phase 2" in POC specs
- "The worker will figure it out" — the spec figures it out

## Spec Template

```markdown
# SPEC-NN — Component Name

## 1. Purpose
One sentence. What problem does this solve?

## 2. Interface
Exact signatures. Worker copies these exactly.

## 3. Data Model
Exact DDL. Exact Go/Python/TS structs with field tags.

## 4. Wiring
How this connects to the outside world:
- CLI flags: --name, --port, etc.
- HTTP routes: GET /api/v1/...
- gRPC: service registration
- main.go: import + wire-up
- Config: env var → config struct → injected

## 5. Error Catalog
Every error this produces, with conditions + HTTP/gRPC status.

## 6. Edge Cases
Empty, nil, timeout, concurrent, large, malicious.

## 7. Testing
Exact test scenarios. "Test that X when Y returns Z."

## 8. Hilo Impact
What depends on this? What does this depend on?
```

## Middle-Out Spec Writing

**The most common failure:** specs describe the engine but not its connection to the world. Every spec MUST answer:

| Question | Section |
|----------|---------|
| How does a user invoke this? | 4. Wiring — CLI flags |
| How does an API client reach this? | 4. Wiring — HTTP routes |
| How does main.go wire this in? | 4. Wiring — imports + DI |
| What config does it need? | 4. Wiring — env vars |
| What breaks if this isn't wired? | 5. Error Catalog |

## Spec Quality Checklist

Before committing:

- [ ] Every interface has exact signatures
- [ ] Every function lists its error conditions
- [ ] Every DB table has exact DDL
- [ ] Every config value has exact env var name + type + default
- [ ] Every edge case is documented
- [ ] Wiring section connects to CLI/HTTP/gRPC/main.go
- [ ] No "TBD", "Phase 2", "future", "consider"
- [ ] Testing section lists exact test scenarios
- [ ] A worker can read this and produce correct code without asking questions

## Anti-Pattern: DuckBrain Prose ≠ Specs

Writing architecture prose into DuckBrain and marking "specs done" is the #1 failure mode. A 200-word DuckBrain entry CANNOT produce correct code — the worker has to invent types, DDL, error handling, and wiring on its own.

**The test:** Hand the spec to a worker. If it asks a clarifying question, the spec failed.

**The fix:** Specs live as FILES under `specs/`. DuckBrain stores architecture decisions, patterns, and cross-project context — not implementation specs.
