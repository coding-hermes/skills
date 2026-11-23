# SDLC: module spec template (the unit of work for a workhorse model)

A module spec is small enough for one workhorse session and complete enough
to build from. Every module (package, service, component) gets one.

## The required sections (each maps to resource files)
1. **Purpose**: what it owns, one paragraph — and the boundary: what it
   deliberately does NOT own.
2. **Home**: its path in the layout (sdlc-repo-layout.md rule applied), its
   import surface (what it may import, what may import it).
3. **Interface**: the public surface — every exported function/type/endpoint
   with signatures and one usage example. The interface is the spec; the
   implementation may change freely under it.
4. **State**: what it holds, where it lives (memory/store), who may write it.
5. **Dependencies**: what it calls, per call the failure answer (timeouts,
   fallback, what the caller sees when this dep dies).
6. **Errors**: the error taxonomy it returns, each mapped to caller action.
7. **Tests**: what the test file proves (per interface method: the success
   case, the failure case, the edge case), the fixtures used.
8. **Docs**: the doc lines it owes (README section, runbook entries).
9. **Open questions**: explicitly listed; a module spec with an empty open
   list was not read carefully.

## Rating checks
- FAIL if the interface section shows signatures without failure modes.
- FAIL if a dependency appears without its failure answer.
- FAIL if the tests section doesn't cover every public method's failure path.
