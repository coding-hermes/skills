# Privacy: the rules engine (regulations -> system requirements)

Privacy law is not prose — it compiles into system requirements. A spec
that says 'we comply with GDPR' without the compiled artifact has compiled
nothing. This file defines the translation.

## The compliance inventory (per regime the system touches)
Per regime — GDPR, CCPA/CPRA, HIPAA, COPPA, PIPL, LGPD, the local ones —
the spec lists: does it apply (the applicability decision, written), and
the REQUIREMENTS it compiles to:
- **Lawful basis / notice**: per processing purpose, the basis (consent,
  contract, legitimate interest) and where it is recorded.
- **Data subject rights**: access, erasure, rectification, portability,
  objection — each as a FLOW (who requests, identity proofing, the SLA —
  GDPR: one month; CCPA: 45 days —, what stores it sweeps, what the
  response letter contains).
- **Consent management**: the consent RECORD (what, when, version of the
  policy shown), withdrawal as a first-class flow propagating to every
  consumer, and the pre-ticked-box prohibition (GDPR) class rules.
- **Breach duties**: the notification clock (GDPR 72h to authority, CCPA
  to residents), what triggers it, and the decision owner.
- **Transfers**: cross-border mechanisms (SCCs, adequacy, the Schrems
  answer), per data class, with the residency enforcement point.
- **Processors**: every third party touching personal data has a DPA/SCC
  on file, and the sub-processor list is monitored.

## The spec artifacts privacy law demands
- **ROPA** (record of processing activities): per processing purpose —
  data classes, lawful basis, recipients, retention, transfers. The
  registry that an auditor asks for first.
- **DPIA** (data protection impact assessment): mandatory for
  high-risk processing (profiling, large-scale sensitive data, novel
  tech — AI features are novel tech); the template, the trigger list,
  and which features require one BEFORE build.
- **Privacy-by-design checks**: data minimization per feature, purpose
  limitation per datum, the default-private rule.

## The wiring into this skill set
- cross-privacy.md owns the PII lifecycle mechanics; THIS file owns the
  REGULATORY overlay (which rules, which clocks, which artifacts).
- thirdparty-apis.md: every external API handling personal data links its
  DPA here.
- cross-data-traffic.md: the privacy-border crossings cite the transfer
  mechanism.
- telemetry-logs.md / telemetry-audit.md: PII rules apply to logs and
  audit trails — the scrubbers cite this file's inventory.

## Rating checks
- FAIL if any regime is named 'applicable' without its compiled
  requirements appearing as spec sections.
- FAIL if a data-subject right has no flow with an SLA.
- FAIL if high-risk processing (per the DPIA trigger list) started without
  a DPIA.
- FAIL if any processor lacks a DPA on file.
- FAIL if consent exists without withdrawal, or withdrawal without
  propagation proof.
