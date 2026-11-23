# SDLC: the project manifesto (philosophy of how THIS product is written)

Every project has a philosophy whether it states one or not; an unstated
philosophy is applied inconsistently by every contributor (and every
workhorse model). The spec opens with the manifesto:

## What a complete manifesto documents
- **Identity**: what this project is and is not (the one-paragraph core idea,
  sharpened into rules: 'this is a library before it is a framework').
- **Values in order**: when two goods conflict, which wins — correctness over
  speed? simplicity over features? operator-debuggability over elegance? The
  ORDER is the manifesto; the rest is commentary.
- **Error philosophy**: how this codebase handles failure (fail-fast vs
  degrade; wrap vs propagate; what logs at what level). Stated once, applied
  everywhere.
- **Dependency stance**: minimalist (standard library + few deps) or
  batteries-included; what earns a dependency (deps-selection.md owns the
  per-dep record; the manifesto owns the BAR).
- **Complexity budget**: what this project will NOT build (the non-goals with
  teeth), and the allowed complexity per area.
- **The names we use**: domain vocabulary fixed here (a 'task' vs a 'job' vs
  a 'tick' is a decision, not a synonym).

## Rating checks
- FAIL if two contributors would resolve a values-conflict differently.
- FAIL if the manifesto contradicts any other spec section (a 'simplicity
  first' manifesto over a 15-service diagram is a finding).
- FAIL if domain vocabulary is undefined (every spec drifts into synonym soup).
