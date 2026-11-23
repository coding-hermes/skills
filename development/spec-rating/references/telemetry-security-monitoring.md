# Telemetry: security monitoring (the detection fleet)

Distinct from the audit trail (the record) — this is the DETECTION system
that watches for the attack while it happens.

## What a complete security-monitoring spec documents
- **The data sources**: which feeds the detection reads — auth logs,
  API access logs, privilege changes, audit trail, network flows,
  third-party security notifications (the provider-breach feed).
- **The detection set (as code)**: per threat-model entry (security-
  lifecycle.md) — the rule that detects it, written, versioned, tested
  (detection-as-code: rules have tests, a staging replay, and an owner).
- **The alert triage flow**: per detection — severity, the on-call path,
  the expected triage time, and the false-positive budget (a noisy rule
  is tuned or killed; alert fatigue is an attack surface).
- **The anomaly layer**: baselines for the known-noisy signals (login
  volume, export sizes), what counts as deviation, and who tunes it.
- **The security metrics**: MTTD/MTTR per incident class, detection
  coverage (what % of the threat model has a live detection), the
  top-alert review — the monitoring of the monitoring.
- **The IR hook**: every detection's runbook link, and the incident
  lifecycle (cross-failures.md rows + security-lifecycle.md stage 4).

## Rating checks
- FAIL if the threat model lists a threat with no detection and no
  accepted-risk signature.
- FAIL if any detection rule is untested (a rule that never fired in a
  drill is a hope).
- FAIL if no one owns alert triage (detections that page nobody are
  theater).
- FAIL if MTTD for the canonical breach class is unknown.
