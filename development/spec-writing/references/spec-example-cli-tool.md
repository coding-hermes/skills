# Spec: `gh-cal` — GitHub Contribution Calendar CLI

**Status**: draft
**Author**: foreman
**Date**: 2026-07-11

## Problem Statement

Developers want a quick terminal view of their GitHub contribution graph without opening a browser. `gh-cal` prints an ASCII contribution calendar for any public GitHub user, color-coded by commit density. Target: devs who live in the terminal.

## Acceptance Criteria

1. Given a valid GitHub username, when `gh-cal <username>` runs, then print a 52-week ASCII grid with color-coded cells (0=gray, 1-3=green shades, 4-6=dark green, 7+=bright green).
2. Given `--year 2024`, when the command runs, then display that year's calendar instead of the current year.
3. Given an invalid or non-existent username, when the command runs, then exit code 1 and print "Error: user '<name>' not found" to stderr.
4. Given no network, when the command runs, then exit code 2 and print "Error: cannot reach GitHub API" to stderr.
5. Given a username with zero contributions for the year, then print the grid with all gray cells and a summary line "0 contributions in <year>".

## Edge Cases

- **Empty input**: Print usage and exit 1.
- **Private/org account**: Gracefully handle 404 from GitHub API.
- **Rate limiting**: If GitHub returns 403 with rate-limit headers, print remaining quota and reset time, exit 3.
- **Year before 2008**: Print "Error: GitHub did not exist before 2008" and exit 1.
- **Unicode usernames**: Support per GitHub's username rules.
- **Terminal too narrow**: If stdout width < 70, print "Warning: terminal too narrow, output may wrap" to stderr, then proceed.

## Non-Goals

- No OAuth or authenticated requests (use unauthenticated API only).
- No contribution graph for private repos.
- No SVG/PNG/image output — ASCII only.
- No streak counting or stats beyond the grid + total.
- No caching of API responses.

## Dependencies

- Go 1.22+ stdlib (`net/http`, `encoding/json`, `flag`)
- `github.com/fatih/color` v1.17 — terminal color output
- GitHub REST API v3 (`/users/{username}/contributions`) — unauthenticated, rate limit 60/hr

## Test Plan

**Framework**: Go testing (`go test`)

| # | Test | Type | Covers AC# | Scenario |
|---|------|------|------------|----------|
| 1 | `TestParseContributions_Normal` | unit | 1 | Parse a valid JSON response into grid cells |
| 2 | `TestRenderGrid_AllLevels` | unit | 1 | Render grid with cells at each color level |
| 3 | `TestFlagYear` | unit | 2 | `--year` flag sets correct API query param |
| 4 | `TestUserNotFound` | unit | 3 | HTTP 404 → exit 1 with error message |
| 5 | `TestNetworkError` | unit | 4 | Connection refused → exit 2 |
| 6 | `TestZeroContributions` | unit | 5 | All-zero response → all gray + summary |
| 7 | `TestRateLimited` | unit | — | HTTP 403 + headers → exit 3 with quota info |
| 8 | `TestNarrowTerminal` | unit | — | <70 cols → stderr warning, still produces output |
| 9 | `TestEndToEnd_RealUser` | integration | 1,5 | Run against live GitHub API with known user |

**Test infrastructure needed**: None for unit tests. Integration test needs network access.
