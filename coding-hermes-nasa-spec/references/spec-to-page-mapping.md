# Spec → handbook page mapping

The `nasa-handbook` skill owns the page. This file is the handoff: which spec
artifact supplies which block, and what must never cross the boundary.

## Block sources

| Handbook block | Supplied by | Rules |
|---|---|---|
| running head (system, section, page id) | `00-frame.md` system name + section number | numbering is global to the set; one sheet owns one number |
| intro paragraph (3 lines) | `00-overview.md` purpose + the one idea | no new facts in the intro — it may only compress ledger rows |
| hero general-arrangement figure | actors + boundary + surface inventory | draw the boundary as a line and the surfaces as stubs on it; every stub has a flow id |
| numbered functional paragraphs | one flow, one paragraph per step | step wording follows the flow table; a step with no module may not be drawn |
| underlined mechanism paragraph | an invariant, or the single non-obvious mechanism | exactly one per page; it is the sentence a reader should leave with |
| secondary figure (sequence/timeline) | flow diagram + timing table | time axis labelled with units; retries drawn as a return loop, not a note |
| block diagram (set-wide sheet) | module tree + collaborators | callouts carry `MOD-nn`; nesting must match `flow:` in the module files |
| performance data table | contract limits: rates, sizes, timeouts, capacities | every value has a unit and a `FACT-nn` behind it; 6-8 rows maximum |
| NOTE | non-obvious behaviour worth flagging | never a hedge, never a to-do |
| CAUTION | recoverable consequence of misuse | names the consequence, not the mechanism |
| WARNING | destructive or irreversible outcome | reserved; a page with three warnings has none |
| Flight Data File checklist card | acceptance criteria R-table, ordered by execution | one card line per runnable check; no R number without a command or test name |
| footer date | spec freeze date + ledger measurement date | two dates when they differ: "spec vX · data as of Y" |
| thumb tab / change bar | spec version | a render-only change does not bump the spec version; a fact change does |

## What does not cross

- **A figure may not introduce a fact.** If drawing the hero figure forces you to
  decide something not in the spec, stop: that decision belongs in a module file
  and an `R-nn`, and the render happens after it lands.
- **The render loop may not change a number to fit the page.** Cutting a table
  row is allowed (and is the handbook's own remedy); changing a value is not.
- **A visual criticism is not a spec defect.** Label collisions, tile crops,
  font fallbacks and period styling are the handbook's triage rules; they never
  justify editing a statement, a limit, or an acceptance criterion.

## Re-render after a fact change

1. Edit `_facts.md` (new `FACT-nn`, or supersede the old row and say so).
2. Edit every requirement and contract that cited it.
3. Run `scripts/spec_coverage.py specs/` — must exit 0.
4. Grep the set for the OLD value: `grep -rn '<old value>' specs/` must return
   nothing in normative sections.
5. Re-render every sheet that carries the value. A set that argues with itself is
   worse than no set.
