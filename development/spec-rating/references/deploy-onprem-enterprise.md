# Deployment topology: on-prem enterprise (customer-run installs)

When CUSTOMERS run the software in THEIR datacenter, the spec inherits
constraints no SaaS has:

## What the spec must re-state
- **The support matrix**: OS versions, container runtimes, hardware/kernel
  requirements — the floor you commit to test, and the version-skew window
  you tolerate (customers run old; the N-2 policy is a promise).
- **The install/upgrade contract**: air-gapped installs (bundle format,
  checksum discipline), the upgrade path per supported version jump, the
  schema migration on THEIR data (with THEIR backup discipline), and the
  rollback that respects their data.
- **Their constraints**: customer network policies (egress may be blocked —
  no phone-home assumptions without the offline answer), their identity
  providers (SSO/LDAP integration points), their HA expectations (they will
  ask for the multi-node answer the architecture may not have).
- **Telemetry & support**: what diagnostics ship (the support bundle), the
  log/redaction policy for THEIR PII, and the remote-assist path with its
  consent gate.
- **Licensing/entitlement**: license enforcement mechanics, and the graceful
  behavior when entitlement lapses (data stays readable; stated).

## Rating checks
- FAIL if any flow assumes outbound internet without an offline path.
- FAIL if upgrades assume a support window the customer hasn't granted.
- FAIL if support diagnostics would exfiltrate customer PII unredacted.
