# Third-party: payments & billing providers

## What a complete payments-integration spec documents
- **Money paths**: every place value moves (charge, refund, dispute,
  subscription change, proration) as a flow with terminal states — money
  flows with vague states become support tickets and accounting holes.
- **Idempotency & reconciliation**: client-side retry vs server-side
  intent; the daily reconciliation job that finds drift between our ledger
  and theirs.
- **Webhook truth**: the provider's webhooks are the source of truth for
  status; our DB stores projections. Stated, because every bug comes from
  trusting the client.
- **Failure & rollback**: partial payment states, double-charge defense,
  refund path per failure class, and who handles chargebacks (person + SLA).
- **Compliance surface**: what we may store (last-4 yes, PANs no), the PCI
  scope statement, tax handling, and the invoice/receipt contract.

## Rating checks
- FAIL if any money-moving flow lacks a reconciliation control.
- FAIL if the client is trusted for any amount.
- FAIL if refund/cancel flows are undesigned (they will be used more than
  the purchase flow in bad weeks).
