### FLOW-01 — Mint a session token
trigger: POST /v1/tokens
exit: 201 with a signed token, or 401 with an error catalog entry
