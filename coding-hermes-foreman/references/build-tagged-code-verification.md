# Build-Tagged Code Verification

When a task creates code behind a Go build tag (e.g., `//go:build dwg`) that
depends on an external C library (libreDWG, CUDA, etc.), the standard
verification loop needs adjustment — the tagged code can't be compiled without
the external dependency installed.

## Detection

- Task creates files with `//go:build <tag>` where `<tag>` is not in the
  default build tags
- `go build ./...` passes because the tagged files are excluded
- `go build -tags <tag> ./...` fails with linker errors (missing C library)

## Verification Steps (adjusted from standard loop)

1. **`go build ./...`** — must pass (untagged code only)
2. **`go vet ./...`** — must pass
3. **`go test ./... -count=1 -short`** — must pass (tagged tests excluded)
4. **`gofmt -w <tagged files>`** — verify Go syntax of the tagged files
5. **`gitreins guard`** — must pass (secrets/build/lint/tests on untagged code)
6. **Skip GitReins judge** — can't compile tagged code, would produce false
   negatives. Note "judge skipped — CGO code requires <lib> not installed"
7. **Manual code review** — verify:
   - Interface implementation (compile-time check with `var _ Iface = (*Impl)(nil)`)
   - Error handling (proper wrapping with sentinel errors)
   - Context cancellation respected
   - Build tag syntax correct (`//go:build dwg`, not `// +build dwg`)
   - CGO preamble uses correct `#cgo LDFLAGS` and `#include` directives
   - Test file has matching build tag
   - Existing non-tagged tests are not broken

## Commit

Same as standard flow. Files are committed with `--no-verify` since the guard
already ran. Board update notes the skip reason.

## Proven

- Imhotep Phase 5 DWG/DXF extraction (2026-07-16) — 2 files (+483 lines)
  behind `//go:build dwg`. libreDWG not installed. Guard PASS, judge skipped,
  manual review verified interface compliance, error wrapping, context
  cancellation, and test coverage.
