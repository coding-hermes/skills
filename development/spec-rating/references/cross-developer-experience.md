# Cross-cutting: developer experience (the build/run/debug loop)

The spec succeeds if the NEXT developer (or workhorse agent) can build, run,
and change the system without the author. It fails if any of this is missing:

- **The bootstrap**: fresh-clone to running in stated time, with the exact
  steps (and the CI job that proves they work — bit-rot is found by machines,
  not new hires).
- **Local dependencies**: what runs locally vs needs stubs/mocks; the seed data
  story; the third-party sandbox for local dev.
- **The debug story**: how to attach/trace locally, the fixture that reproduces
  the canonical bug, and the log location per machine.
- **Contribution rules**: the review gate, the commit convention, the test
  expectation per change class — stated once, enforced by machines.
- **The agent-friendliness note** (new, and load-bearing for us): does the
  repo have the structure an autonomous agent needs — discoverable entry
  points, machine-readable errors, guard rails that name their failure? If a
  workhorse model is the maintainer, its environment IS the design.

## Rating checks
- FAIL if bootstrap hasn't been proven on a clean machine (documented-command
  verification, not memory).
- FAIL if local dev requires production credentials.
- FAIL if the canonical bug cannot be reproduced from a committed fixture.
