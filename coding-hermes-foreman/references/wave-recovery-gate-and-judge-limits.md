# Wave recovery: gate-of-record wiring and gitreins judge limits

Proven on wojons-mythos tick 2026-11-22-21-22-22 (recovery of wave 14-46-47).

## 1. LOCAL-CI script is hardwired to origin/main — mirror trick for pre-push gating

`scripts/local-ci.sh` (wojons/mythos, gate of record) fetches and tests `origin/main` only.
A wave merge produces a green-able LOCAL main that must NOT be pushed before green
(no-push-before-green). To run the exact gate script on the unpushed local tip:

```bash
git clone --bare --single-branch -b main /home/kara/<repo> /tmp/lci-mirror.git
git -C /tmp/lci-mirror.git update-ref refs/remotes/origin/main refs/heads/main
MYTHOS_REPO=/tmp/lci-mirror.git scripts/local-ci.sh /home/kara/<wt>-recover
```

The mirror's `origin` is the real checkout, so the gate's own `git fetch` keeps grading the
local tip. Evidence line keeps the script's own LOCAL-CI PASS `<sha>` banner — a genuine run,
not a re-factored gate. Cite "mirror run" in the closeout note so nobody mistakes it for an
origin/main run.

## 2. gitreins judge: 260s kills the run silently; ephemeral persists nothing by default

- A standalone `gitreins judge <id>` wrapping the guard (gitleaks ~2min + full turbo tests)
  needs 400-540s; a `timeout 260` wrapper kills it BEFORE any verdict is written — no
  history dir, no output. Budget 500s+ per named judge.
- `gitreins judge --ephemeral` stores NOTHING (no task, no verdict) unless you pass
  `--persist-verdict`. It then lands in `.gitreins/verdicts/verdict.json` — NOT
  `.gitreins/history/`. boardctl `--evidence-run-id` only resolves dirs under
  `.gitreins/history/<date>/<run-id>/`, so copy the persisted verdict into a
  `history/<date>/<short-slug>/verdict.json` before binding it to a row close.
- Named `gitreins judge <id> --skip-tier2` grades the LIVE tip and writes a proper history
  dir (tier1-only). Use it for fast closes when the tier2 reviewer lane is dead
  (wojons/mythos: empty/unparseable reviewer replay, INT-JUDGE-412).

## 3. Post-merge closeout order with gitreins 0.21.x (task complete grades live tip)

`gitreins task complete` grades the CURRENT tree, not the worker commit. Close order:
rebase branch onto current main -> merge -> gate on merged tree -> boardctl update
`--status complete --commit-hash <product-sha>` -> commit board -> repoint rows'
commit_hash to the post-board tip via `update --commit-hash <tip>` (with a disclosure note
naming the real product sha) -> `gitreins task complete <id> --skip-tier2`. boardctl
0.21-era builds may lack `--repoint-commit`; plain `--commit-hash` on a completed row is the
same write path.
