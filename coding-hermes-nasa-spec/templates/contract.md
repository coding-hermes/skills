# Contracts

A contract is what a caller may rely on and a producer may not break. Ground
every external surface in `--help` or a live probe; an unmeasured surface is a
SPIKE with the named unknown, never a plausible-looking endpoint.

## CT-01 — <name>

producer: MOD-01
consumer: MOD-02

**Class:** module | service/API | data | config/event

### Shape

```
<exact signature, or route + request/response JSON schema with a COMPLETE example>
```

### Errors

| condition | result | caller action |
|---|---|---|
| <...> | <status/error type> | <retry / surface / give up> |

### Rules

- auth: <per route / per call>
- rate limit: <n per window, or none>
- timeout: <ms> (evidence: FACT-nn)
- idempotency: <key semantics>
- ordering: <per key, or unordered>

---

# Matrix — `_matrix.md`

| contract | producer | consumer | breaking-change policy |
|---|---|---|---|
| CT-01 | MOD-01 | MOD-02 | versioned; additive only within a major |
