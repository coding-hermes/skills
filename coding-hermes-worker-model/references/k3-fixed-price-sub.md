# Kimi K3 Fixed-Price Subscription

## Provider Config

The Kimi K3 subscription runs through `kimi-for-coding` provider (NOT OpenRouter):

```yaml
provider: kimi-for-coding
model: k3            # or kimi-k3 (both work)
base_url: https://api.kimi.com/coding/v1
api_key_env: KIMI_API_KEY
```

## Key Behaviors

- **Fixed-price, not per-token**: This is a flat-rate subscription. No rate-limit or bucket-exhaustion concerns.
- **Available models**: `k3`, `kimi-k3`, `kimi-k2.6`, `kimi-k2.6-fast`
- **k3 strengths**: Long context, code review, security audits, multi-file analysis. Good for gap audits and comprehensive code reviews.
- **k3 weaknesses**: Can be slow (10-minute timeout on complex frontend tasks). Workers timing out should have their work checked — they often complete the code changes but fail to commit before the timeout.

## Cron Job Configuration

```yaml
model:
  provider: kimi-for-coding
  model: k3
```

## GitReins Configuration

```yaml
evaluator:
  defaults:
    model: k3
    api_key_env: KIMI_API_KEY
```

Base URL must be set to `https://api.kimi.com/coding/v1` via `GITREINS_LLM_BASE_URL`.

## Pitfalls

- **OpenRouter `moonshotai/kimi-k3` is also available but pay-per-token** — always use `kimi-for-coding` provider when the user says "Kimi sub" or "fixed price"
- **k3 workers timeout at 600s on complex tasks** — the actual code changes are usually done, just uncommitted. Check `git status` after timeout.
