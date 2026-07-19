# GLM-5.2 Type/Method Name Hallucination

GLM-5.2 workers sometimes generate plausible-but-wrong API calls — type names, method names, or function signatures that look correct but don't exist in the actual codebase. The code is structurally valid Go (compiles syntactically at the function level) but references non-existent identifiers.

## Detection

```bash
go build ./... 2>&1 | grep "undefined:"
```

Common patterns:
- Off-by-one character: `types.QuatIdent()` instead of `types.QuatIdentity()`
- Wrong package prefix: `types.Vec3Zero` instead of `types.Vec3Zero()` (missing call parens)
- Misspelled constants: `engine.SHIELD_MAX` instead of `engine.ShieldMax`

## Recovery

1. `go build ./...` — the compiler tells you exactly what's undefined
2. Search for the closest real identifier: `grep -rn "QuatIden" pkg/types/`
3. Apply a targeted `patch` to fix each undefined reference
4. Rebuild: `go build ./... && go vet ./...`
5. Do NOT respawn the worker — these are trivial one-line fixes the foreman handles directly

## Prevention

In the worker prompt for GLM-5.2 Go tasks, add:
> "Use ONLY functions/types that exist in the codebase. Before writing any call, verify the exact name with grep. Do not guess type names."

## Proven Instances

- **Kobayashi-Maru TODO-replay-groundtruth (2026-07-16):** GLM-5.2 worker wrote `types.QuatIdent()` (missing `ity` suffix). Correct name: `types.QuatIdentity()`. Caught by `go build`, fixed with single `patch`, build+vet+test green.
