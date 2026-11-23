# SDLC: CI/CD process

## What a complete CI/CD section documents
- **The pipeline stages**, per artifact type: build -> static gates (lint,
  typecheck, secret scan) -> unit -> integration -> E2E -> package/sign ->
  publish. Each stage: what runs, on what trigger, its timeout, and what a
  failure BLOCKS.
- **The gates that cannot be skipped**: the merge-blocking set (and the
  sanctioned loud-override path for red-fix pushes, with its audit trail).
- **Speed budget**: the target wall-clock for CI; the sharding/caching
  strategy; the flake quarantine lane (a flaky gate is a lying gate).
- **Environments**: what CI runs on (the runners), with version pinning per
  language/toolchain — CI tests what ships, on the toolchain it ships with.
- **Artifacts**: what CI produces (binaries, images, reports) and retention.
- **The trust boundary**: what CI credentials can touch (least privilege per
  job), and what a compromised runner could reach (the blast radius, stated).
- **Local parity**: which gates run locally pre-push (fast set) vs only in CI
  (full set) — the developer experience of 'it passed locally but not CI'
  is designed away, not tolerated.

## Rating checks
- FAIL if any stage can be skipped without a trace.
- FAIL if CI toolchains differ from production toolchains.
- FAIL if the pipeline has no flake policy (red is then ambiguous, and red
  that means nothing gets ignored).
