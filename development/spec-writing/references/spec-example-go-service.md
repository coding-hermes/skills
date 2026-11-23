# Spec: `urlshr` — URL Shortener Service

**Status**: draft
**Author**: foreman
**Date**: 2026-07-11

## Problem Statement

Internal tooling needs a self-hosted URL shortener. No external dependency on bit.ly or similar. Must handle ~100 create requests/minute, ~10k redirects/minute. Runs as a single Go binary with SQLite backing.

## Acceptance Criteria

1. Given a POST to `/shorten` with `{"url": "<valid URL>"}`, then return `{"short": "<6-char code>", "url": "<original>"}` with status 201. Subsequent POST of the same URL returns the existing short code (200, not 201).
2. Given a GET to `/<code>`, then 302 redirect to the original URL and increment the access counter.
3. Given a GET to `/<code>` where code doesn't exist, then return 404 with `{"error": "not found"}`.
4. Given a GET to `/<code>/stats`, then return `{"short": "<code>", "url": "<original>", "created_at": "<iso8601>", "access_count": <int>}`.
5. Given a POST to `/shorten` with `{"url": "not-a-url"}`, then return 400 with `{"error": "invalid URL"}`.
6. Given concurrent requests to `/shorten` with the same new URL, then exactly one code is created (no duplicates).

## Edge Cases

- **Empty body**: POST `/shorten` with no body → 400.
- **URL > 2048 chars**: 400, "URL too long".
- **Malformed JSON**: 400, "invalid JSON".
- **Concurrent redirects**: Atomic increment of access counter — no race condition on read+write.
- **SQLite locked**: Retry up to 3 times with exponential backoff, then 503.
- **Graceful shutdown**: Drain in-flight requests on SIGTERM, close DB.

## Non-Goals

- No authentication/authorization.
- No custom short codes (auto-generated only).
- No expiration/TTL on links.
- No analytics dashboard beyond `/stats` endpoint.
- No horizontal scaling — single process, single SQLite file.

## Dependencies

- Go 1.22+ stdlib (`net/http`, `database/sql`, `encoding/json`)
- `github.com/mattn/go-sqlite3` v1.14 — SQLite driver
- SQLite 3.35+ on host

## Test Plan

**Framework**: Go testing (`go test`) + `httptest` for HTTP handlers

| # | Test | Type | Covers AC# | Scenario |
|---|------|------|------------|----------|
| 1 | `TestShorten_NewURL` | unit | 1 | POST valid URL → 201 + short code |
| 2 | `TestShorten_DuplicateURL` | unit | 1 | POST same URL twice → 200 + same code |
| 3 | `TestRedirect_Found` | unit | 2 | GET known code → 302 + correct Location header |
| 4 | `TestRedirect_NotFound` | unit | 3 | GET unknown code → 404 |
| 5 | `TestStats_Found` | unit | 4 | GET /stats → JSON with all fields |
| 6 | `TestShorten_InvalidURL` | unit | 5 | POST bad URL → 400 |
| 7 | `TestShorten_EmptyBody` | unit | — | POST empty body → 400 |
| 8 | `TestShorten_LongURL` | unit | — | URL > 2048 → 400 |
| 9 | `TestConcurrentShorten` | unit | 6 | 100 goroutines POST same URL → single code |
| 10 | `TestConcurrentRedirect` | unit | — | Concurrent GETs → counter accurate |
| 11 | `TestGracefulShutdown` | integration | — | SIGTERM during requests → all complete |

**Test infrastructure needed**: None (in-memory SQLite for unit tests).
