# Spec: `snippd` — Code Snippet Sharing App

**Status**: draft
**Author**: foreman
**Date**: 2026-07-11

## Problem Statement

Team needs a quick way to share code snippets internally — paste some code, get a link, share it. Like a minimal, self-hosted Pastebin. Single-page web app with a Node.js backend. No accounts, no persistence beyond the current process restart (MVP).

## Acceptance Criteria

1. Given I load the app at `/`, then I see a code editor (textarea), language selector (dropdown), and "Create Snippet" button.
2. Given I paste code, select a language, and click "Create Snippet", then a POST to `/api/snippets` creates the snippet and redirects me to `/<id>`.
3. Given a GET to `/<id>`, then display the snippet with syntax highlighting for its language, a copy button, and the raw text.
4. Given a GET to `/<id>/raw`, then return the raw snippet text with `Content-Type: text/plain`.
5. Given an invalid snippet ID, then show a "Snippet not found" page with status 404.
6. Given I click the copy button on a snippet page, then the snippet text is copied to clipboard.
7. Given an empty code submission, then show inline validation error "Code cannot be empty".

## Edge Cases

- **Very large snippet** (>500KB): reject with "Snippet too large (max 500KB)".
- **XSS in snippet content**: All snippet output is escaped — no script execution.
- **Concurrent creation**: Each POST returns a unique ID, no collisions.
- **Language not in dropdown**: Store as "plaintext", syntax highlighting falls back gracefully.
- **Browser back/forward**: Single-page navigation works with history API.
- **Mobile viewport**: Editor and controls stack vertically below 768px.

## Non-Goals

- No user accounts, login, or authentication.
- No snippet editing or deletion (create-only for MVP).
- No comments, likes, or social features.
- No database — in-memory storage only (lost on restart).
- No expiration/TTL — snippets live until restart.
- No search or listing of all snippets.

## Dependencies

- **Backend**: Node.js 20+, Express 4.19, `highlight.js` 11.9
- **Frontend**: vanilla JS, no framework. Prism.js 1.29 for client-side highlighting.
- **No build step** — serve static HTML/CSS/JS directly.
- **No external services**.

## Test Plan

**Framework**: Jest (backend unit + integration), Playwright (e2e)

| # | Test | Type | Covers AC# | Scenario |
|---|------|------|------------|----------|
| 1 | `POST /api/snippets with valid body` | unit | 2 | Returns 201 + snippet ID |
| 2 | `GET /:id returns snippet page` | unit | 3 | Renders highlighted snippet |
| 3 | `GET /:id/raw returns plain text` | unit | 4 | Correct Content-Type and body |
| 4 | `GET /nonexistent returns 404` | unit | 5 | Error page rendered |
| 5 | `POST with empty code returns 400` | unit | 7 | Validation error message |
| 6 | `POST with >500KB body returns 413` | unit | — | Size limit enforced |
| 7 | `XSS content is escaped` | unit | — | `<script>` tags rendered as text |
| 8 | `Concurrent POSTs get unique IDs` | unit | — | 50 parallel requests → 50 unique IDs |
| 9 | `Homepage renders editor` | e2e | 1 | Editor + dropdown + button visible |
| 10 | `Full create-and-view flow` | e2e | 1,2,3 | Create snippet → redirected → see it highlighted |
| 11 | `Copy button works` | e2e | 6 | Click copy → clipboard has snippet text |
| 12 | `Mobile layout stacks` | e2e | — | 375px viewport → vertical layout |

**Test infrastructure needed**: Node.js, Playwright browsers (chromium).
