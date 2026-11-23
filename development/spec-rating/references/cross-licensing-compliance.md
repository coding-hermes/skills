# Cross-cutting: licensing & compliance

## What a complete licensing/compliance section documents
- **License inventory**: every third-party component's license, the compatibility
  decision against OUR distribution model (SaaS vs distributed binary differ), and
  the attribution obligations (NOTICE files, about-screens).
- **Copyleft boundary**: the interaction surface with any AGPL/GPL component, and
  the 'we may not ship X' list.
- **Regulatory scope**: which regimes apply (GDPR/CCPA if personal data; PCI if
  cards; HIPAA if health; export controls if crypto), stated per data class with
  the controlling artifact (DPA, SOC2 scope, BAA).
- **Data residency**: where each data class may live, and the enforcement at every
  storage and transfer point.
- **Audit trail**: what an auditor asks for first (access logs, change records) and
  where it lives.

## Rating checks
- FAIL if any dependency's license is 'probably MIT'.
- FAIL if personal data exists and no lawful-basis/residency statement covers it.
- FAIL if the compliance claim ('SOC2-ready') names no controlling evidence.
