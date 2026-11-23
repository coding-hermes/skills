# Dependencies: selection (choosing external libraries)

Choosing a library is a system decision with a failure story, not a
footnote. A spec is incomplete if any third-party library is load-bearing
and none of this is recorded:

## The selection record (per load-bearing dependency)
- **License**: which one, compatible with our distribution model? Copyleft
  contamination checked? (cross-licensing-compliance.md owns the policy.)
- **Maintenance reality**: last release date, commit activity, maintainer
  count, bus factor; is it funded/chartered or one tired person?
- **CVE history**: past vulnerabilities, response speed, SECURITY.md presence.
- **API stability**: breaking-change cadence, semver honesty, migration pain
  of the last major (that's the preview of the next one).
- **Fitness**: does it cover the need or 90% of it — and the missing 10% is
  the part we exist to do? The wrapper-vs-fork line.
- **Exit cost**: how hard to replace (isolated behind an interface, or fused
  into 200 call sites?). The interface boundary is part of the decision.

## Spec obligations once chosen
- Every load-bearing dependency appears in the machines/dependencies
  inventory with its role, version policy (pin/floating), and upgrade owner.
- The 'if it dies' row in the failure matrix: who notices, what is the
  replacement plan (a named alternative or an interface that makes writing
  one cheap).

## Rating checks
- FAIL if a framework-level dependency has no maintenance evidence.
- FAIL if a license is unknown at spec time.
- FAIL if replacement cost is unstated for anything the product cannot ship without.
