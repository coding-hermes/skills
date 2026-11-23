# Caching: CDN / edge

## What a complete edge/CDN spec documents
- Per route/asset class: cache key (query strings? cookies? headers?), TTL, and the
  purge mechanism + who can fire it.
- Vary rules and the personalization boundary: what is NEVER cached at the edge
  (auth'd pages, per-user data) and how that is enforced (headers, not hope).
- Origin shield / request coalescing, and the origin-load model when the cache is purged.

## Rating checks
- FAIL if any authenticated response is cacheable without a stated Vary/auth-key rule.
- FAIL if no purge path exists for a 'quickly fix a bad deploy' story.
- FAIL if a full-cache-flush scenario has no stated origin capacity answer.
