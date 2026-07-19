# Python CI Workflow Creation — Use Make Targets, Not Inline Python

When creating `.github/workflows/ci.yml` for Python projects, **use Makefile targets** (`make lint`, `make build`, `make test`) instead of inline `python -c` or `python -m` commands.

## Why

The `write_file` tool runs YAML validation that rejects inline `python -c` with mixed quotes:

```
run: python -c 'import h3_harness; print("build: OK")'
# YAMLError: mapping values are not allowed here (line 33)
```

Both single-quote (`-c '...'`) and double-quote (`-c "..."`) variants fail because the Python string inside contains the opposite quote type, and YAML's parser gets confused.

The `cat` heredoc terminal workaround also gets blocked by the cron security scanner (`script execution via -e/-c flag`).

## Solution

Use the project's existing `Makefile` targets:

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: ${{ matrix.python-version }}
  - name: Install dependencies
    run: make install
  - name: Lint
    run: make lint
  - name: Build
    run: make build
  - name: Test
    run: make test
```

This avoids ALL quoting issues, keeps CI in sync with local development (`make build` is the same command everywhere), and passes the `write_file` YAML validator on the first try.

## Pre-requisites

The project's `Makefile` must define the targets. If it doesn't, create the Makefile first (see `references/empty-board-build-tooling-gap.md` and `templates/Makefile-go` for Go; for Python, a canonical `Makefile` should have `install`, `build`, `lint`, `test`, `fmt`, `clean`).

## Proven

H3 SDK Python 2026-07-14 — three failed `write_file` attempts with inline `python -c`; switching to `make` targets passed YAML validation on first try. CI ran successfully on Python 3.10/3.11/3.12.
