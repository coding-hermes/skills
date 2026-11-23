# Third-party: ML/model APIs (LLMs, embeddings, vision)

## What a complete model-API integration spec documents
- **Per provider/model**: capability envelope (context window, modalities,
  reasoning effort), latency class, cost per unit at stated traffic,
  rate/quota shape, and the data-retention policy on our prompts.
- **Routing & fallback**: the lane chain (primary -> fallback per failure
  class), the health signal that trips it, and the sticky-session answer
  when a model swap mid-conversation changes behavior.
- **Determinism & drift**: model versions pin/float policy; output contracts
  (schema-validated? free text?), and the eval set that detects quality
  drift after a provider-side change.
- **Prompt & context management**: template ownership, injection defenses,
  PII policy for what we send upstream, and context-budget math.
- **Cost governance**: per-feature budget, the runaway loop guard (every
  agentic loop has a hard turn/token ceiling), and the alert on spend anomalies.

## Rating checks
- FAIL if any agentic flow lacks a hard ceiling (turns, tokens, wall time).
- FAIL if the fallback lane is untested (a fallback that has never served
  is a hypothesis, not a lane).
- FAIL if PII goes upstream with no stated policy.
- FAIL if output parsing assumes structure without a schema-validation
  failure path.
