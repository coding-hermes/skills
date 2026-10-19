# Board close-out — the summary shape

The close-out is the only artifact a later session reads. Write it so a stranger can
re-litigate the row without rerunning anything: every claim carries its measurement,
and every hole is named.

## Shape

```
MEASURED (<where>: branch build / deployed container / two instances / browser):
<case A> -> <status> <named code> <recorded effect>
<case B> -> ...
CONTROL: <the same test on pre-change code> failed <how> — so the test can fail.
CODE: <the one or two lines that carry the guarantee, with file:function>.
SUITES: <packages> green; build/vet clean.
NOT MEASURED BY ME: <the door that needs a handshake / the backend not run / the flake>.
<THE CONSEQUENCE the operator must know, if any — e.g. "this deployment must run with
X=false or the page cannot send">
```

## Rules

- **Numbers, not adjectives.** `0.05s`, `409 TASK_EVIDENCE_REQUIRED`, `hook 1 → 1`,
  `delivered: 2`. "Works well" is not a measurement.
- **Name the surface.** Say whether it was the branch, the merged tree, or the
  deployed instance. They are different claims and reviewers know it.
- **Quote the refusal verbatim.** The exact string the operator sees is part of the
  contract; a paraphrase hides a bad wording.
- **Separate what you measured from what the branch's tests measured.** Both are
  legitimate; conflating them is the lie.
- **Close-and-push together.** Board commit + code push in the same action, so the row
  never claims a commit that is not public.
- **Superseded rows are closed honestly**: re-verify the walkthrough on the *current*
  build and say "superseded-verified", with what you re-ran — not "stale, closing".

## Filing new rows from a review

Every finding becomes one row, in the session that read it, with:

- the measured defect and its file:line,
- severity that reflects who can be hurt (a stranger with network access > a confused
  operator > a cosmetic label),
- an acceptance statement phrased as behaviour, and
- the words "addressed by" only when a row exists — never a promise in prose.

Prose findings evaporate; rows get scheduled.
