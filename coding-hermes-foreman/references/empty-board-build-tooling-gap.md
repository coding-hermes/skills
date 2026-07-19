# Empty-board discovery: missing build-tooling files

Detection pattern and fix for when a foreman discovery sweep finds that README / AGENTS.md / quality-gate sections reference a build file that does not exist on disk.

## When to suspect

- Board is empty after Step 1.
- `README.md` or `AGENTS.md` says things like "run `make build`", "use `just test`", or "quality gates: `make lint`".
- The referenced file (`Makefile`, `justfile`, `Taskfile.yml`, `package.json` with a script, `pyproject.toml` target) is absent from the repo root.

## Detection commands

```bash
# README references
ls -la Makefile justfile Taskfile.yml package.json pyproject.toml 2>/dev/null
# grep for "make ", "just ", "npm run" in docs
grep -E "make\s+|just\s+|npm run\s+|pnpm\s+|poetry run\s+" README.md AGENTS.md CONTRIBUTING.md .coding-hermes/*.md 2>/dev/null
```

## Decision

If the referenced file is missing and the project otherwise has source code, create a `## [ ] BUILD` or `## [ ] DOC` task. Use the **shortened investigation loop** (no worker spawn): the foreman writes the build file directly, verifies it with the real toolchain, runs `gitreins guard`, and commits.

## Canonical Go Makefile targets

A reasonable starter for a Go project:

- `build` — build all binaries (`go build -o ./bin/... ./cmd/...`).
- `build-daemon` / `build-cli` — split binaries.
- `test` — `go test ./... -count=1`.
- `test-short` — `go test ./... -count=1 -short` (CI friendly).
- `vet` — `go vet ./...`.
- `fmt` — `gofmt -w .`.
- `lint` — `vet` + build + gofmt check.
- `proto` — `buf generate` (or equivalent).
- `clean` — remove built binaries.
- `e2e` — run the live E2E battery.
- `install` — copy binaries to `/usr/local/bin`.
- `ci` — full lint + test-short.

## Verification recipe

```bash
make clean
make build
make vet
make test-short
make lint
```

All must exit 0 before the commit.

## Proven instance

**Bunker, 2026-07-13.** README.md instructed `go build -o bunkerd ./cmd/bunkerd` and the board's "Quality Gates" section listed `Makefile` workflows, but no `Makefile` existed. Foreman created WI-070 with the targets above, verified the recipe, and committed directly. CI run `29276759363` passed.
