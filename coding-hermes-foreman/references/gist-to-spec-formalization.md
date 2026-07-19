# Gist-to-Spec Formalization Pattern

When a conversational design document (gist, DuckBrain entry, chat transcript) needs to become formal spec files in a repo.

## When to use

- User shares a gist/design doc and says "build the specs"
- A DuckBrain entry captures architecture that needs file-level formalization
- A design conversation produced enough detail that it's ready for spec files
- Extending an existing system with a major new feature (e.g., flat pool → multi-namespace)

## Workflow

### Phase 1 — Ingest

1. **Fetch the design document.** If it's a gist or URL, `curl -sL <url>` or `web_extract`. Don't rely on web_search for this — it's search-only.
2. **Read ALL existing specs in the repo.** You can't know what to patch vs what to create without understanding the current state. Use `search_files(pattern="*.md", target="files", path="specs/")` then `read_file` on each one.
3. **Read the task board.** `.coding-hermes/tasks.md` — what's already checked off, what's pending.

### Phase 2 — Triage

4. **Identify what needs a NEW spec vs what needs PATCHING.** The design document usually maps to one major new spec. Everything else that touches the new feature (data model, packer, API, architecture) gets patched — NOT rewritten.
5. **Number the new spec correctly.** Follow the existing numbering scheme. If S01-S06 exist, the new spec is S07. Don't renumber existing specs.

### Phase 3 — Write the new spec FIRST

6. **Write the comprehensive new spec.** This is the primary deliverable. It gets the full 10-section treatment (Overview → Dependencies → Interface → Behavior → Data → States → Errors → Testing → Security → Performance). Every Go interface, every DDL fragment, every algorithm step, every error condition, every edge case, every test scenario. See `axiom-implementation-specs` and `exhaustive-specification` skills for the format standard.
7. **Write it completely before touching existing specs.** Don't interleave — the new spec defines what the existing specs need to cross-reference.

### Phase 4 — Back-patch existing specs

8. **Patch existing specs with minimal cross-references and updates.** For each existing spec that touches the new feature:
   - **S01 (Architecture):** Update the architecture diagram (Mermaid), add new components to the Scheduler struct, add new config fields
   - **S02 (Data Model):** Add new DDL (new tables, ALTER TABLE migrations), new Go structs, new query patterns, new DuckBrain keys. Renumber sections if needed.
   - **S04 (Packer):** Add a new section at the END (e.g., "## 11. Multi-Namespace Extension") with the new interface, algorithm summary, and a pointer to the full spec. Don't rewrite the existing flat-pool logic.
   - **S06 (API):** Add a new section at the END with new endpoint OpenAPI, schemas, error messages, behavior, and test scenarios. Update the route count in section 1.
   - **Specs that are unchanged (S03, S05):** Don't touch them.

9. **Each patch is targeted.** Use `patch` tool with specific old_string/new_string. One logical change per patch call. Verify the diff looks right after each one.

### Phase 5 — Update the task board

10. **Add implementation items to `.coding-hermes/tasks.md`.** New section with a clear header ("MULTI-NAMESPACE EXTENSION" or similar). Each task gets: ID, priority, weight, dependency chain, and a concrete description of what files to create/modify.

## Principles

- **New spec first, patches second.** The new spec is the source of truth; patches just point existing specs at it.
- **Don't rewrite existing specs.** Add sections at the end. A spec that worked before the extension should still work after — just with a new section at the bottom.
- **Cross-reference, don't duplicate.** The DDL lives in S02. S07 references it by section number, not by copying it.
- **The task board bridges specs to implementation.** Each spec section that needs code becomes a task item with a weight, dependency, and file path.
- **One pass through each spec.** Don't go back and forth between specs — the new spec is written completely, then each existing spec gets one pass of patches.

## Proven

Scheduler 2026-07-12 — Multi-Namespace Weight-Budget Extension formalized from Bane's gist:
- Created S07 (26KB, 10-section format: Overview → Dependencies → Interface → Behavior → Data → States → Errors → Testing → Security → Performance)
- Patched S01 (architecture diagram + Scheduler struct + Config)
- Patched S02 (namespaces DDL, namespace_ticks DDL, projects FK, Go structs, query patterns, DuckBrain keys)
- Patched S04 (new "## 11. Multi-Namespace Extension" section)
- Patched S06 (new "## 11. Namespace API Endpoints" section + route count update)
- Updated tasks.md (8 new NS-001 through NS-008 items, 119 weight points)
- S03 and S05 untouched (urgency calculator and spawn lifecycle unchanged by the extension)
