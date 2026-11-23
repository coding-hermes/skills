# Security: supply chain & build pipeline

The code you RUN is produced by a pipeline; an attacker who owns the
pipeline owns the product without touching a line of source.

## What a complete supply-chain section documents
- **The build inventory**: every artifact that reaches production, and the
  exact pipeline that produces it (source -> build -> sign -> deploy), with
  the trust boundary at each hop.
- **Provenance & signing**: builds are reproducible from source; artifacts
  are signed (provenance attestation: which commit, which builder); the
  deploy gate VERIFIES the signature (verification at deploy, not just
  signing at build).
- **SBOM**: per artifact, the component list is generated and stored — the
  answer to 'are we affected by CVE X' is a query, not an archaeology dig.
- **Dependency intake**: the gate new dependencies pass (license, CVE,
  maintenance — deps-selection.md) and WHO can approve what tier.
- **CI credential blast radius**: per pipeline credential — what it can
  reach (deploy keys, cloud roles), the least-privilege scoping, the
  short-lived-token policy, and the answer to 'a compromised runner:
  what becomes reachable, and what contains it?'
- **The mirror/pin discipline**: builds pull from pinned, hashed sources
  (no floating tags in production paths); third-party artifacts verified
  against known digests.

## Rating checks
- FAIL if production artifacts can be produced outside the pipeline.
- FAIL if deploy trusts a name/tag instead of a verified digest/signature.
- FAIL if the SBOM claim is aspirational (no stored manifest per release).
- FAIL if a CI credential can reach more than its job needs.
