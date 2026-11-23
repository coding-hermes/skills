# Third-party: messaging providers (email, SMS, push)

## What a complete messaging spec documents
- **Per channel**: provider, sender identity (domain auth: SPF/DKIM/DMARC;
  sender IDs), template ownership, and the content review flow.
- **Deliverability**: bounce/complaint handling (the suppression list),
  warmup plan for new sending domains, and the metrics watched.
- **Volume & cost**: the send-volume model at stated traffic patterns,
  burst behavior, cost per class of message.
- **Failure**: provider outage (the alternate provider or the degrade-to-
  nothing decision, stated), queue semantics for retry, and the
  duplicate-suppression answer.
- **User control**: per-class unsubscribe (transactional vs marketing
  legally distinct), preference center, and the suppression honor path.

## Rating checks
- FAIL if transactional and marketing mail share a sending domain/reputation.
- FAIL if bounce handling is unstated (spam-trap death spiral follows).
- FAIL if any user-visible state depends on a push/SMS arriving (push is
  best-effort; the fallback is the design).
