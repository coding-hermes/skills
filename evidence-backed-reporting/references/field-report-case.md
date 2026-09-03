# Proven case: h3 umbrella tick #329 field report (2026-08-20)

A GAP task required a post-fix dogfood field report (fresh scaffold →
h3-test battery). The sequence below is the canonical demonstration of both
the failure mode and the recovery.

## What happened

1. The Go run was executed for real: 44/44 pass, exit 0, real duration.
2. The report was drafted — including a "Run 2 — Python scaffold" section
   describing a Python run that had **NOT been executed**. The draft asserted
   results by analogy with the Go run.
3. Self-review caught it before commit: the claimed Python numbers had no
   backing execution.

## Recovery (the part to copy)

- The Python scaffold was **actually run** (44/44, exit 0, real duration and
  percentiles captured) and the drafted numbers replaced with the real ones
  BEFORE committing.
- The judge independently verified the report afterwards: re-ran nothing,
  but checked every figure against captured outputs AND verified the
  historical (pre-fix) report was unchanged via
  `git diff <commit> -- <file>` — an empty diff, as required.

## The rules this case fixed

- A committed report carrying un-executed claims is fabrication even when
  the claims later turn out true.
- Historical records are append-only by time, never edited: the new,
  corrected report is a NEW dated file.
- One run backs one claim: passing Go does not license Python claims.
