# Cross-cutting: configuration surface

## What a complete configuration section documents
- **The full config inventory**: every knob, its type, default, valid range, and
  WHO may set it (operator-only vs user vs per-tenant).
- **Precedence & source**: flags > env > file > defaults; the discovery order; and
  the precedence TESTS that keep it true.
- **Validation**: parse-and-fail-loud at load, with the error naming the bad key —
  config errors are found at startup, not mid-request.
- **Change mechanics**: what needs a restart vs live-reload; the audit trail of
  who changed what; the per-config rollback.
- **Secrets separation**: config that IS a secret goes to the secret store, with
  the rotation path — never a value in a plain config file.
- **The kill switches**: per feature, the off-switch and its reach (does disabling
  actually disable, or only hide?).

## Rating checks
- FAIL if any config value is validated nowhere.
- FAIL if an undocumented knob exists (the config file is the contract).
- FAIL if a kill switch's full reach is untested.
