# Cross-cutting: security

## A spec fails security rating if any of these is missing
- Threat model: who the adversary is, what they want, what is in scope (STRIDE-lite per
  surface is enough; 'we use HTTPS' is not a threat model).
- AuthN/AuthZ matrix: every principal (human role, service, job) x every resource, the
  allowed verbs, and the enforcement point.
- Secrets: where they live, how they rotate, what a leak triggers; nothing in code/env
  dumps; secret scope per consumer.
- Input trust boundaries: every place untrusted data enters and the validation at each.
- Audit log: which actions are logged immutably, retained how long, reviewed by whom.
- PII: what data is personal, where it flows, deletion path (right-to-erasure is a flow
  through EVERY store that holds it, including caches and backups).

## Rating checks
- FAIL if any endpoint's authorization is 'the frontend hides it'.
- FAIL if secrets rotation is possible only by redeploying everything.
- FAIL if user deletion exists without a per-store deletion path (cache/backups included).
