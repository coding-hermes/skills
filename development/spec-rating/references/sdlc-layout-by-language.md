# SDLC: language-specific layout requirements

Layout philosophy is universal; layout PRACTICE is per-language. The spec
states which language conventions govern, per language in use:

## Go
- The standard project layout discipline: cmd/ per binary, internal/ for
  non-importable code, pkg/ only if genuinely importable API. One package
  per directory; package names short, no util/helpers dumping grounds.
- Errors as values; the wrap discipline (%w, errors.Is/As) stated.
- go.mod hygiene: one module vs multi-module workspaces — decided, not
  drifted into.

## Python
- src-layout vs flat: chosen and enforced (src/ with installed package
  avoids the accidental-cwd-import class entirely).
- The packaging contract: pyproject.toml is the single source; extras/
  dependency groups named; the lock file story.
- Type coverage bar: full annotations at public boundaries minimum; mypy
  strictness level stated as a gate, not an aspiration.

## TypeScript
- The monorepo decision: single package vs workspaces (pnpm/turbo); boundary
  enforcement per package.
- strict tsconfig as the floor; the any-escape policy; ESM/CJS stance.

## Rust
- Workspace layout for multi-crate; the feature-flag policy per crate;
  the module tree as the API (pub visibility discipline).

## Any language — the cross-language rules
- Each language's layout file lives in the repo and is the tiebreaker.
- Multi-language repos: the language boundary map (what calls what, where
  the seams are — FFI, HTTP, gRPC — and the build order).

## Rating checks
- FAIL if a Go repo has no internal/ and exports everything.
- FAIL if a Python repo mixes src-layout and flat without a decision.
- FAIL if the language convention is violated by a branch that 'works'.
