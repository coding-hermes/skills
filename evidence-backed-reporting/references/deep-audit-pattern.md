# Deep-audit pattern: multi-judge + verification dives + paper

When a claim set is too large for one reviewer, run REAL adversarial audits
and ship an evidence-cited paper — not a chat summary.

## Pipeline (all steps run live)

1. **Brief**: write the verify-me claims brief to a temp file (doctrine
   groups; safety rails declared up front: read-only, no real-mode actions,
   no board writes).
2. **Judge fan-out**: 3–4 independent models run the brief; each produces a
   full verdict file on disk.
3. **Verification dives**: re-check the judges' CONSENSUS findings against
   actual source (file:line quotes) + hunt for what they missed. Expect two
   catch classes: a real find the judges missed, and a judge complaint that
   a newer commit already fixed ("OVERTAKEN BY EVENTS" — check git log for
   fixes landed after the judge's session before marking CONFIRMED).
4. **Merge discipline**: every CONTRADICTED claim is re-verified against raw
   source before it enters the report.
5. **Paper shape**: title+byline, abstract with numbers, stats grid,
   failure-taxonomy table (class → manifestation → closing SHA),
   architecture/enforcement catalog, adversarial-audit section with
   CONFIRMED / OVERTAKEN / MISSED-BY-JUDGES callouts, trusted-vs-computed
   thesis table, honest limitations, and a footer citing the provenance of
   EVERY number (commands + file paths + date).

## Delegate lanes fail — in-session fallback is first resort

Subagent dispatch can die in seconds with an auth error (HTTP 401, stale
key), and the failure can arrive disguised as "completed". On 401: do NOT
re-dispatch; run the dives in-session with small script files (giant inline
commands get blocked — write the script, execute the file). Same evidence,
full command transcript, and the paper footer notes the lane note.

## Pitfalls

- Judge output files can carry earlier failure noise in their heads — read
  the BOTTOM of each verdict (the final line/summary) to confirm real
  completion.
- Distinguish "judge wrong" from "judge stale": check git log for fixes
  landed AFTER the judge's session before marking a finding CONFIRMED.
- Heredocs inside inline shell get hardline-blocked on some harnesses;
  write scripts to files first.
