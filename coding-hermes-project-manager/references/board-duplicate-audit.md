# Board duplicate-id audit

G8's background: why raw-line audits exist, the duplicate classes, and the collapse
procedure. (G8's operational commands live in SKILL.md; this file carries the depth.)

## Why raw lines, not the loader

A PM cycle reported "0 ids with >1 open copy, 0 content clusters >0.40"
while the raw board carried **22 ids across 36 extra lines** (`QA-CRIER-1` ×7,
`DF-CRIER-2` ×4, `CR-GAP-053` ×3). The report was not a lie — it was taken through
a keep-last loader, where every id collapses to one row by construction. **A dedupe
claim computed through the loader is tautological.** That is why G8 audits the RAW
lines.

## Fleet scan (same command as G8, run over every enabled project's board)

101 boards scanned, 20+ distinct boards carried duplicate-id lines. Sibling lanes
(sync/dogfood/qa/pm) share one board, so the counts below collapse to ~10 distinct
boards:

| board | lines | unique | extra dup lines | worst id |
|---|---|---|---|---|
| heading | 165 | 126 | 39 | QA-HEADING-1 ×12 |
| hermes-canopy | 365 | 329 | 36 | QA-HERMES-CANOPY-1 ×8 |
| bunker | 233 | 208 | 25 | QA-BUNKER-1 ×7 |
| <project> | 185 | 161 | 24 | QA-CHIMERA-V2-1 ×7 |
| 9router | 185 | 162 | 23 | QA-9ROUTER-1 ×9 |
| <project> | 1125 | 1107 | 18 | QA-HERMES-DAGGER-1 ×6 |
| h3-shim-foreman | 104 | 89 | 15 | QA-H3-SHIM-FOREMAN-1 ×4 |
| off-by-one | 129 | 118 | 11 | QA-OFF-BY-ONE-1 ×5 |
| crier (post-cleanup) | 417 | 417 | **0** | — |

## Two classes hide inside "duplicate id" — classify before collapsing

On the cleanup target, of 22 duplicated ids: **16 were true duplicate lines** (identical title)
and **6 were ID REUSE** (distinct findings sharing a per-cycle slot id, carrying 15 distinct
findings).

- identical content → collapse, keep the LAST line (that is what every reader resolves)
- distinct content → the id was reused: give each finding its own stable id
  (`<PREFIX>-<PROJECT>-<next free>`) and record `re_id_from` + the origin in the row,
  per G7. Never let the collapse silently delete a distinct finding.

Remedy applied: 133 duplicate lines collapsed to one line per id,
97 premise-dead/duplicate/verdict rows retired with per-row evidence, 2 out-of-vocabulary
statuses fixed (`duplicate`→`complete`, `open`→`pending`), 15 reused-id findings re-ided.
Result: `boardctl validate` **OK** (was FAIL 99 errors; pre-cleanup baseline 57), lines ==
unique ids, and `boardctl` no longer refuses "ambiguous id" writes — which is how fixed rows
were getting stuck re-pickable.

## Contract gaps that let this rot

1. **G1–G7 is a pre-add gate.** It only judges candidate rows against open rows; no
   step ever audited the existing board's structure. Nothing in the cycle was wrong —
   the audit simply did not exist (now G8).
2. **G7 is id-blind by design** (ids rotate as cycle slots), so id multiplicity is
   structurally out of its scope.
4. **Fold status must stay in vocabulary.** `status='duplicate'` and
   `status='superseded'` are outside boardctl's vocabulary
   `{blocked,complete,failed,in_progress,pending,review}`, so validate flags them as
   errors and validate-gated audits skip them. Use `complete` only when the canonical
   row's acceptance criteria genuinely resolve the losing row; otherwise keep the row
   open and link it without pretending the work is done.
4. **`boardctl validate` was never in the doctrine.** No cycle command ever called it,
   so a FAIL was never seen.

## Third dup class — a dup set that lands at DIFFERENT states over time

Beyond identical-content dups and id-reuse, a working foreman can re-land a closed
row's id from its OWN slate: the earlier copies then sit `pending` while the LAST
copy is `complete` carrying the close verdict (merge hash, artifact path,
verified-on-merged-result). Every reader resolves the id to the terminal last line,
so the stale earlier copies are pure validate-error residue. Collapse rule for this
class: byte-preserving keep-last of the raw lines; assert (a) every kept line
byte-identical to its source, (b) per-id semantic equality of the re-parse against
the intended keep-last, (c) `unique_ids == lines`, (d) `git diff --numstat` shows
pure deletions (0 added). Do NOT collapse when the duplicated ids are still genuinely
open (all copies pending/in_progress) — that deletes pickable work.

Before trusting any kept close-note, verify its merge hash is an ancestor of main
(`git merge-base --is-ancestor <hash> main`) and remote parity is clean (`git
rev-list --count origin/main..main` = 0) — a close-note hash not on main is a claim
the board cannot back; say so instead of collapsing over it.

Always quote the `boardctl validate` [error] count delta (pre-collapse vs post) as
the collapse's verification line.

## Fingerprint structured rows by their payload, not their title

For boards whose rows are machine-shaped (route manifests, endpoint sweeps), dedupe on the
STRUCTURED payload extracted from the title — for routes, `verb + normalized path`
(`(GET|POST|PUT|PATCH|DELETE)\s+(/[\w/{}/.-]+)`, trailing slash and `/api` prefix stripped) —
not on the normalized title string. Lane prefixes (`[P2]`, `[dogfood:P2]`) and label drift
(`MISSING route` vs `BROKEN route`) make title normalization either over-match distinct rows
or miss true dups; the verb+path pair is invariant across all of them. Same principle for any
row class with an extractable key: fingerprint the key, fall back to normalized title only
when no key parses.

## Do not reverse-engineer a seeded row's `detail.fingerprint`

Seed-time rows carry a `detail.fingerprint` hex value whose input convention is not
reproducible (not sha256 of title, description, or acceptance criteria in any common
serialization) — matching attempts burn calls and always fail. G7 duplicate detection
is the content-dedupe Jaccard over title+description, never fingerprint equality. When
minting a new row, set `detail.fingerprint = sha256(title + acceptance_criteria)` and
move on; the value only needs to be present and self-consistent, not compatible with
the seeded convention.

## Alert-slot boards: the resolution evidence may already be ON the board

Alert-router boards auto-inject one pending row per firing alert with a built-in
close contract ("close it when the alert is resolved; a resolution event is
appended automatically"). Consequences for G8/verification:

- Before treating a pending alert row as open work, grep the board for
  `<row-id>-RESOLVED` (an `alert-resolved`-typed event row beside the task row)
  and probe the alertmanager live (`ssh <monitor-host> 'curl -s
  http://localhost:9090/api/v1/alerts'` — the monitor's Tailscale IP may refuse
  direct connections; go through the host). A resolution event dated after the
  row plus an alert absent from the live firing set = the row is a closure
  candidate, not backlog. The probe command and both results go in the close
  note.
- A row's title/labels repeat on every cycle the alert refires, but the ids are
  date-stamped (`...-YYYYMMDD`, `...-YYYYMMDD-RESOLVED`) — id equality means
  same alert DAY, nothing more. Fingerprint by `alertname + host`, never by the
  shared stem.
- These rows never appear in the PM ledger (the router writes them directly),
  so a zero-ledger-follow-up count says nothing about them; the board census is
  the only source.

## A newer writer commit may already contain your repair

A foreman tick that lands between your raw audit and your commit can perform the
very collapse you planned (its commit replaces the duplicated lines). Before
committing a board edit, re-derive the dup census from HEAD (`git show
HEAD:<repo-root-relative board path> | <dup census>` — the path is relative to
the REPO ROOT, which may be the user's home, not the workdir) and diff your
working-tree edit against it. If HEAD's dup census is already clean and the
commit's board diff shows the same rows dropped, DISCARD your working-tree
collapse (do not commit it, and remove your snapshot/backup files): committing
it would fight the writer's own repair and can resurrect a shadowed line. Report
the collapse as the foreman's commit, verified by your own census.

## Weekly habit

Run G8's two commands on every board you own; report `lines == unique ids` and a
validate result in the cycle log. A cycle that only says "no duplicates found"
without those two numbers has not audited anything.
