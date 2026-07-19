# DuckBrain Namespace Cross-Reference

**Pitfall:** DuckBrain namespaces can be architectural DESIGN NOTES for an existing project — not a declaration of a new project to build.

## Detection

When you discover a DuckBrain namespace with entries like:
- `/project/collect`
- `/project/classify`  
- `/project/express`
- `/project/competitors`
- `/project/concept`

These appear to describe a product with architecture layers, but they may be design-thinking entries for an EXISTING project.

## Cross-Reference Checklist

Before creating ANYTHING (repo, specs, foreman) from a DuckBrain namespace:

1. **Search for HTML PRDs:** Search the filesystem for `.html` files matching the namespace name:
   ```bash
   find /home/kara -name "*{namespace}*.html" -type f 2>/dev/null
   ```

2. **Check existing project references:** Look in existing projects' `AGENTS.md` and spec `_index.md` files for references to the namespace:
   ```bash
   grep -r "{namespace}" /home/kara/*/AGENTS.md 2>/dev/null
   grep -r "{namespace}" /home/kara/*/specs/_index.md 2>/dev/null
   ```

3. **Match concepts against existing specs:** Read the DuckBrain entries' concepts and compare against existing spec files. If the architecture described in the namespace matches an existing project's scope, the namespace is that project's design memory — not a new project.

4. **Check the HTML title and meta:** If an HTML PRD is found, read the `<title>` and `<meta name="description">`. The codename-to-product mapping is often in the title: `Project {codename} — {product} PRD`.

## Proven Incidents

### Rabbit-Hole / H3 (2026-07-12)

- **DuckBrain namespace:** `rabbit-hole` with 5 entries: `/project/concept`, `/project/collect`, `/project/classify`, `/project/express`, `/project/competitors`
- **What the entries described:** Three-layer architecture (collect → classify → express), competitive landscape, killer features
- **What was actually found:** `rabbit-hole-prd.html` at `/home/kara/get-h3/h3/rabbit-hole-prd.html` — title: "Project Rabbit Hole — H3 PRD & Spec Summary"
- **The truth:** "Project Rabbit Hole" was H3's codename. The DuckBrain entries were H3's architectural design thinking.
- **The mistake:** Created an entirely separate `rabbit-hole` project with 6 axiom-level specs, GitLab repo, and coding foreman — duplicating what was already H3.
- **User correction:** "Read that html file it says rabbit hole but it is H3 project." and "Is this for project rabbit hole or a H3 because you Named one thing hut contents different"
- **Lesson:** A DuckBrain namespace with project-like entries does NOT mean "create a new project." Cross-reference with HTML PRDs first.