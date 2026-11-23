# Third-party: identity providers (OAuth/social login/SSO)

## What a complete identity-integration spec documents
- **Flows supported**: which grants, for which client types, and the redirect
  allowlist management.
- **Token lifecycle**: access/refresh lifetime, storage on every client
  class, refresh collision handling, revocation propagation.
- **Identity mapping**: the local user record at first login, account
  linking/merging when the same human arrives via two providers, and the
  un-link path.
- **Failure**: provider outage at login (the lockout risk), clock skew on
  token validation, and the break-glass local admin path.
- **Deprovisioning**: what removes access when an identity is disabled
  upstream (SSO), and how fast.

## Rating checks
- FAIL if token storage per client class is unstated (localStorage is a decision).
- FAIL if account-merge is unhandled (duplicate humans corrupt the data model).
- FAIL if the IdP being down locks every user out with no workaround.
