# Gate scripts shipped with this skill

`scripts/acceptance_gate.py` — repo-scoped acceptance gate over a JSONL board.
Open rows whose acceptance criteria name a path or flag that the repo cannot
show are flagged; that is what keeps a foreman from chasing an invented file.

Two arms are deliberately exempt, and both exemptions are exact-subject only:

* **Absence assertions.** A criterion may name a path in order to prove it is
  GONE — `test ! -e <path>`, or a history query that should print nothing
  (`git log --all -- <path>`). Such a path can never be in `git ls-files`, so
  an existence check would fail that arm forever.
* **External flags.** A real flag shipped by a tool the repo merely consumes
  (e.g. `gitreins guard --quality-async`) appears in no tracked file. Each such
  flag needs a live-provenance entry in the gate's external-flag list, scoped to
  the verb that owns it — a bogus flag on the same verb, or the same flag on a
  different tool, must still fail.

Usage:

```
python3 scripts/acceptance_gate.py validate <repo> <row.json>    # one row
python3 scripts/acceptance_gate.py audit <repo>                  # whole board
```

`scripts/gate_fixtures.py` — regression suite for the gate. Nine cases, each
declaring PASS or REJECT, printed as `ok`/`FAIL`; exit 0 only when every case
matches its expectation, so both directions stay proven:

```
python3 scripts/gate_fixtures.py <repo>
```

The `exemption-does-not-leak-across-arms` case exists because a first version
matched any prefix before the token: `test ! -e ~/<repo>/specs/AGENTS.md`
silently exempted an unrelated `specs/AGENTS.md` cited in the next arm, so the
whole-row audit reported zero failures while that arm still failed on its own.
When you touch the exemption, re-run this suite and also run the suspect arm's
text alone through `validate` — a green aggregate is not proof an arm is
satisfiable.
