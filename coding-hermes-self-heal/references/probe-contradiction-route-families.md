# Probe Contradictions: Route Families & Surface Counts (Anti-Fabrication Refinement)

Two refinements to Step 0.5 ground-truth verification, both proven on
coding-hermes-scheduler tick #223 (2026-08-03).

## 1. Route-family mismatch — probe BOTH families before correcting a prior claim

Servers expose parallel route families for the same resource. The scheduler
daemon (:9090) has at least two:

- **HTML dashboard routes (no prefix):** `/`, `/health`, `/queue`, `/ticks`,
  `/projects/{name}`, `/namespaces/{id}`, `/dashboard/partial`
- **REST API routes:** `/api/v1/{resource}` (health, status, projects,
  namespaces, ticks, queue, events, openapi.json)

The SAME path suffix resolves differently per family. Proven: the board
claimed `/namespaces/1 → 500` (dashboard route on the pre-#215-fix binary).
The first probe of `/api/v1/namespaces/1` returned **404** — which looked
like a fabricated prior claim. Ground truth: the dashboard route
`/namespaces/1` → **500** (bin/schedulerd mtime predates fix d765c5d; daemon
not restarted), while the API route correctly 404s. The prior claim was
CORRECT; the probe was on the wrong family. Same family split:
`/openapi.json` → 404 but `/api/v1/openapi.json` → 200.

**Rule:** when a fresh probe contradicts a board claim, enumerate route
families (prefix vs no-prefix; also port variants) and probe ALL of them
BEFORE declaring fabrication. A "correction" that ignores route families is
itself a fabrication risk — and so is a missed correction when both families
really are broken.

## 2. MCP/API surface counts — verify against source registration, not prior ticks

Tool/endpoint counts are numeric claims and must be re-verified every tick
like any other. Proven: tick #221 claimed `POST /mcp tools/list 30 tools`;
tick #223 ground truth = **14 tools**. The live response matched source
exactly — `internal/mcp/server.go` registers exactly 14 (fleet_status,
fleet_projects, fleet_project_detail, fleet_set_weight, fleet_set_priority,
fleet_set_cooldown, fleet_set_decay, fleet_pause, fleet_resume, fleet_add,
fleet_ticks, fleet_evaluate, fleet_pause_scheduler, fleet_resume_scheduler).
The "30" was a miscount/copy of a prior claim.

**Rule:** any tool-surface count must be checked against BOTH (a) the source
registration (grep the registration code for the tool/route list) and (b) a
live probe response. When both agree, that is ground truth — correct the
board entry, and do NOT propagate the prior number. This is the MCP analog
of the endpoint-count gates already in the NEVER-DONE audit.

## Related

- `fabrication-patterns-2026-07-24.md` — the 14 original patterns
- coding-hermes-board `live-tables-no-pk-insert-or-replace.md` — board write
  pitfall hit on the same tick (INSERT OR REPLACE BinderError; use plain
  INSERT or SELECT-then-INSERT/UPDATE) — already documented, no new fix
