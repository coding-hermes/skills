# Third-party: inbound webhooks

## What a complete webhook-receiver spec documents
- **Verification**: signature scheme per sender, the verification point
  (before parse), replay window, and the key-rotation handoff.
- **Idempotency**: delivery ID dedup window; the same event arrives 2-3x by
  design — what makes double-processing harmless.
- **Ordering**: out-of-order delivery assumed unless proven otherwise; state
  handling per event type.
- **Our availability**: what the sender does when we're down (retry curve,
  disable-after-N?) and our catch-up path (poll fallback? missed-event sync?).
- **The receiver's contract**: fast-ack then process (queue), never
  process-inline; the slow-handler failure mode is named.

## Rating checks
- FAIL if signature verification is absent or happens after side effects.
- FAIL if dedup relies on 'we won't send it twice'.
- FAIL if the catch-up-after-downtime story is unstated.
