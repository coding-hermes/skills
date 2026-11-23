# Value-audit fleet recipe (READ-ONLY)

When the operator asks whether a program (CoS, cards, a lane family, any standing automation)
delivers value or burns cycles: dispatch a fleet of parallel READ-ONLY audit subagents, one
dimension each, structured JSON outputs. Never edit boards/cards/configs during an audit.

## The five dimensions
1. **Better-than-before** — pick the program's go-live date as the seam; compare the window
   before vs after on: throughput (closes/week), % closes carrying real proof
   (evidence_run_id/commit-hash), repeat-filing rate, time-to-close for equivalent row
   classes. Verdict per metric: better/same/worse WITH the numbers.
2. **Focused-vs-scattered** — % of open rows citing an initiative card or subgoal id;
   duplicate-row rate; filed-vs-drained per week; filing-spike outliers. Watch the confound:
   `-sync`/`-ops` lanes legitimately produce 0 commits (deliverable = records) — exclude
   before quoting dry/no-work rates.
3. **Artifact value** — for every card/artifact the program mints: did it spawn work, did
   that work close WITH evidence, how many minted artifacts are idle overhang, and how many
   CONCRETE catches (drift repairs, false closes rejected) did the shepherd layer make?
   Cite the evidence records per catch.
4. **Cost vs value** — tokens (and USD where priced) burned by the program's sessions over
   the window ÷ initiatives advanced and proven closes; compare against the top non-program
   spenders' tokens-per-outcome. Quote cache-read share separately — re-reading unchanged
   state is the usual trim candidate.
5. **Expectation compliance** — mine chat history for the operator's verbatim directives
   about the program; grade each COMPLIANT/PARTIAL/VIOLATED with evidence; include the
   operator's corrections as findings.

## Framing laws
- Verdicts need ROI numbers + named waste, never stats alone.
- Report PROGRESS against intent (DONE/ADVANCED/STUCK-with-cause/CHANGED/ASK), not a census.
- Record the merged verdict as a DuckBrain record under the program's domain so the next
  audit diffs against it instead of re-deriving.
