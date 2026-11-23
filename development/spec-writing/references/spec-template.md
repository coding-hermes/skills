# Spec: [Feature Name]

**Status**: draft | in-review | approved | implemented
**Author**: [name]
**Date**: YYYY-MM-DD

## Problem Statement

[One paragraph. What problem does this solve? Who benefits? Why now?]

## Acceptance Criteria

1. Given [context], when [action], then [expected outcome].
2. Given [context], when [action], then [expected outcome].
3. ...

## Edge Cases

- **Empty input**: [behavior]
- **Invalid input**: [behavior]
- **Concurrent access**: [behavior]
- **Large inputs**: [behavior]
- **Network failure**: [behavior]
- **[other]**: [behavior]

## Non-Goals

- [Thing we are explicitly NOT building]
- [Another thing NOT in scope]

## Dependencies

- [Library name] ([version]) — [purpose]
- [Service/API] — [purpose]
- [Other feature] — [must be complete first]

## Test Plan

**Framework**: [pytest / Go testing / Jest / etc.]

| # | Test | Type | Covers AC# | Scenario |
|---|------|------|------------|----------|
| 1 | [name] | unit | 1 | [one-line description] |
| 2 | [name] | unit | 2 | [one-line description] |
| 3 | [name] | integration | 1,3 | [one-line description] |
| 4 | [name] | e2e | all | [one-line description] |

**Test infrastructure needed**: [docker compose, test DB, mock server, etc.]
