# Demo / Seed User Protection from Test Suite `clear()`

## Problem

A SaaS platform shares one PostgreSQL database between development, test, and demo environments. The test suite calls `authRepository.clear()` (or equivalent) in `beforeEach`/`afterAll` hooks to reset state. This `DELETE FROM users` wipes demo/seed users (teacher, admin, student accounts) that were created by the seed script — they vanish after the first test run.

This is a recurring pattern. EduOS hit it 4 times in 6 days (DOCKER-002 through DOCKER-005, Jul 9–15, 2026).

## Root Cause

The `clear()` method runs against the admin/Superuser pool (to bypass RLS), but the WHERE clause is a bare `DELETE FROM users` with no protection for seed accounts.

## Detection

| Signal | What to check |
|--------|---------------|
| Login fails for demo users | `curl POST /auth/login` returns 401 for known demo emails |
| No demo users in DB | `docker exec <postgres> psql -U <user> -d <db> -c "SELECT email FROM users"` shows only test-fixture users |
| Test suite just ran | Demo users exist before tests, vanish after |

## Fix Pattern

In the `clear()` method (or equivalent), add WHERE clause filtering to exclude protected users:

```typescript
// TypeScript / Node.js example (PostgreSQL)
async clear(): Promise<void> {
  const admin = await getAdminPool().connect();
  try {
    // Delete tokens/sessions for non-protected users
    await admin.query(
      `DELETE FROM password_reset_tokens
       WHERE user_id NOT IN (
         SELECT id FROM users
         WHERE email LIKE $1 OR email = $2
       )`,
      ['%@demo.eduos.app', 'browser-test@test.co']
    );
    await admin.query(
      `DELETE FROM sessions
       WHERE user_id NOT IN (
         SELECT id FROM users
         WHERE email LIKE $1 OR email = $2
       )`,
      ['%@demo.eduos.app', 'browser-test@test.co']
    );
    // Delete unprotected users
    await admin.query(
      `DELETE FROM users
       WHERE email NOT LIKE $1 AND email != $2`,
      ['%@demo.eduos.app', 'browser-test@test.co']
    );
  } finally {
    admin.release();
  }
}
```

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| Admin pool (Superuser bypasses RLS) | The app pool's anonymous context is blocked by RLS delete policy — `DELETE FROM users` returns success but deletes 0 rows |
| `LIKE` glob, not a list | A pattern like `%@demo.eduos.app` covers all demo users with one condition. Adding individual emails is fragile |
| `OR email = $2` for exceptions | Users from a different domain (e.g., `browser-test@test.co` vs `@demo.eduos.app`) need an explicit exception |
| Subquery `OR`, outer `AND` | The token/session queries use `OR` inside the subquery (protect users matching either condition). The user DELETE uses `AND email != $2` (exclude specific non-matching email) |

### Multi-Language Variants

| Language | Pattern | Example |
|----------|---------|---------|
| TypeScript / Node (pg) | Parameterized query with LIKE | `WHERE email NOT LIKE $1 AND email != $2` |
| Python / psycopg2 | `%(domain)s` parameter | `WHERE email NOT LIKE %(domain)s` |
| Go / database/sql | `COALESCE` pattern | `WHERE email NOT LIKE $1 AND email != $2` |
| Raw SQL migration | Hardcoded WHERE in migration | `DELETE FROM users WHERE email NOT LIKE '%@demo.eduos.app'` |

## Prevention

When writing the seed script (`reset-and-seed.mjs`, `seed.ts`, etc.), create protected users using a consistent email domain (e.g., `%@demo.eduos.app`). The `clear()` method's WHERE clause should reference this domain.

If multiple domains are needed (admin on `@test.co`, demos on `@demo.eduos.app`), add explicit `email != 'admin@test.co'` conditions for each — but **prefer consolidating all protected users under one domain**.

## Verification

After applying the fix:

```bash
# 1. Run the full test suite
npm test  # or equivalent

# 2. Verify demo users survived
docker exec <postgres> psql -U <user> -d <db> \
  -c "SELECT email, role FROM users WHERE email LIKE '%@demo.eduos.app' OR email = 'browser-test@test.co'"

# 3. Verify demo login still works
curl -X POST /api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"teacher@demo.eduos.app","password":"Edu0sDemo!}"'
# Expect: HTTP 200 with JWT
```

## Proven In

- **EduOS** DOCKER-004 (Jul 15, 2026): Added `NOT LIKE '%@demo.eduos.app'` protection. 1681 tests pass, 6 demo users intact.
- **EduOS** DOCKER-005 (Jul 15, 2026): Extended to also protect `browser-test@test.co` (different domain). Added `OR email = $2` to subquery. 7 demo users intact.
