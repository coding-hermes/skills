# Project archaeology — mining a project's history before CoS takes it

When the operator asks the CoS plane to absorb a long-lived project ("read the specs and old chat
history of how we tried to get this to work, the fights we had"), run this recipe. The output is a
war-history document the initiative cards cite, so the CoS inherits the LESSONS instead of re-fighting
them.

## Inputs (three sources, parallel agents or parent-inline)

1. **Specs in the repo** — the design fight is recorded in the specs' own clarification/critique
   files: read north-star + architecture + MVP + tech-stack + critique + SPEC_CLARIFICATIONS fully,
   skim the rest (title + first 60 lines). Extract: the vision (quoted with file:line), every
   reversal/clarification-after-disagreement/"must never"/lesson, recurring failure themes, open
   questions. Date each fight from the spec's own stamps.
2. **Session DB** (`session_search`, discovery = `session_search(query='...', limit=8, sort='oldest')`,
   scroll = `session_search(session_id=..., around_message_id=<match>)`) — project name variants,
   feature-name queries, "not working / start over / rewrite" phrasings. Persist big result dumps to a
   scratch file and page through them; quote only text actually present, and say when the archive is
   thin on direct quotes.
3. **DuckBrain namespace inventory** — `curl "http://localhost:3000/api/keys?namespace=<ns>&limit=400"`
   (x-api-key from the token file, values never echoed); group key paths by prefix to get the key
   census and the era boundaries (stale vs active namespaces are themselves historical facts — record
   which namespace is canonical and when it changed).

## Synthesis shape

1. The vision (spec-quoted) · 2. Dated eras · 3. The fights (verbatim quotes with session links;
   spec-recorded clarifications labeled as such) · 4. Decisions stuck vs reversed · 5. Recurring failure
   themes (name the CURRENT board manifestation of each) · 6. Where it stands today (landed vs open vs
   parked). Close with a sources-and-evidence-boundary section: which claims are spec-cited, which are
   session-quoted, which are inventory-derived, and which lack direct evidence.

## Wiring the output into the plane

- Deliver the doc as BOTH markdown (citable) and dark mobile-first HTML (attachment) — same content.
- Map every recurring theme to its owning artifact: foreman rows + an initiative card, or a NEW card
  when a theme never had one. A theme with no tracked initiative is the archaeology's most valuable
  finding — file the card (triage/parked, ACs as proofs, the theme's lesson as the user-story context).
- The deliverable HTML/markdown gets re-verified before any re-send: patch corruption (e.g. a stray
  word pasted into a CSS value) happens in scratch files too — grep the artifact for its own sentinel
  strings before attaching.
