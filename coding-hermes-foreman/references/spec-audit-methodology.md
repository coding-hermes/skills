# Spec Audit Methodology (Method B — Interface/Type Deep Audit)

Use this pattern when Step 1.5c's TODO/FIXME grep (Method A) is too shallow. This methodology finds spec-vs-code gaps that grep for "TODO" cannot — missing interfaces, incomplete struct fields, unimplemented backends, and abstraction layers that exist only on paper.

## Detection Pattern

When the board has a `## [ ] SPEC — Audit specs vs implementation` task, use this checklist:

### 1. Read Spec Interfaces

Read each spec file looking for:
- `type X interface { ... }` blocks — interfaces with method signatures
- `type X struct { ... }` blocks — data structures with field names and types
- Function signatures — public API surface
- Backend implementations named in prose (e.g., "Two implementations: LocalBackend and RemoteBackend")

### 2. Grep for Each Spec Type

```bash
# Check every spec-defined interface exists as a Go type
grep -rn "type SpecInterface interface" internal/ pkg/ --include="*.go"

# Check every spec-defined struct has matching fields
grep -rn "type SpecStruct struct" internal/ pkg/ --include="*.go"

# For field count parity — spec says 9 fields, code has 5 → gap
# Read the struct and count export fields
grep -A30 "type SpecStruct struct" path/to/impl.go | grep -cE "^\s+[A-Z]"
```

### 3. Check Method Coverage

For each interface in the spec, check that all methods exist on the concrete implementation:

```bash
# List all methods on the concrete type
grep -n "func.*SQLiteStore\." internal/storage/sqlite.go | head -20
```

If a spec defines 14 methods but the code has fewer — gap for each missing method.

### 4. Classify Each Gap

| Finding | Task Type | Action |
|---------|-----------|--------|
| Interface defined in spec but no Go type | SPEC-GAP — abstraction | Create task for interface definition + at least one implementation |
| Backend named in prose but not in code | SPEC-GAP — implementation | Create task for that backend |
| Struct has fewer fields than spec | SPEC-GAP — completeness | Create task listing each missing field |
| All methods exist but no exported interface | SPEC-GAP — refactor | Low priority — task to extract/export the interface type |
| Framework-provided feature (Cobra help, auto-completion) | Not a gap | Test with `--help` flag instead of grepping for command struct |

### 5. Write Actionable Task Descriptions

Bad: "Classification layer gaps"
Good: "S03-GAP-001 — ClassificationBackend pluggable interface: Spec defines ClassificationBackend interface with Classify/Health/Info/Close methods and LocalBackend+RemoteBackend implementations. Actual code has hardcoded *GemmaModel field with no backend abstraction. Need: interface definition, LocalBackend wrapper, move GemmaModel behind it."

### 6. Pre-Existing vs New Issue Detection

When finding a gap, check if it was intentionally deferred:
```bash
git log --oneline --all -- internal/ --diff-filter=A --name-only | head -10
git show <prior-commit> --stat | grep -c "<gap-package>"
```
A gap where the spec says "two implementations" but only one was ever committed is a deferred task, not a regression — still needs a task, but tag it as `[deferred]` in the description.

## Proven Instances

- **Rabbit-Hole 2026-07-15**: Method B found 4 gaps (S03 ClassificationBackend interface, S03 remote gRPC backend, S03 ModelInfo partial fields, S05 Storage interface not exported). Method A only found 1 TODO.
