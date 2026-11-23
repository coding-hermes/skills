# Publish-gate host-path remediation

Recipe for the posture class "a public repository's tracked tree carries absolute host-home paths and
internal worktree names" — measure it, stop the growth, gate it, and know which parts are residual.
The class is layout exposure, not secret leakage: run a credential-shape scan separately and report it
as its own leg, because "no secrets found" is not "nothing sensitive published".

## 1 — Measure with BOTH scopes, in ONE form

Use the repository-relative pathspec form everywhere, so the gate, the row and the artifact cannot
disagree about what is counted:

```bash
git grep -oIE '/home/[a-z][a-z0-9_-]*/' HEAD | wc -l                      # occurrences, all paths
git grep -lIE '/home/[a-z][a-z0-9_-]*/' HEAD | wc -l                      # files, all paths
git grep -lIE '/home/[a-z][a-z0-9_-]*/' HEAD -- . \
  ':!.gitreins/**' ':!.coding-hermes/board/**' | grep -c .                 # authored surface
```

Always report the two figures side by side (all / excluding the machine-generated bundle tree and the
board). The delta between them tells you whether the growth is authored prose or mechanical
bookkeeping, and only the second number is worth a remediation target.

If the same probe can be backed by an in-repo scanner (`gitleaks detect --no-git --redact` scoped to the
working tree), quote its byte count and its scope line: a working-tree scan says nothing about history
unless you passed `--log-opts`, and a history-scan figure is not comparable to a tree figure.

## 2 — Identify the mechanical producer before writing criteria

A growing count is almost always one producer, not many: every judge/verdict bundle commits a patch
and a verdict file that record the absolute worktree and guard-log path. Name the producer in the
row's reasoning, because the fix is "stop publishing that directory", not "sanitize a thousand docs".
Check `.gitignore` for the shape it already covers — a `.gitignore` that lists the tool's `logs/`,
`verdicts/` and `tasks.yaml` but not its `history/` is the usual gap.

## 3 — Un-publish without destroying the evidence

```bash
git rm -r --cached <bundle-dir>      # index only; the files stay on disk
```

Keep the on-disk copy. Anything that resolves a stored bundle by path (a board writer demanding an
evidence run directory, a reviewer reading the verdict envelope) keeps working, because it reads the
filesystem, not the index — verify that claim against the writer's source before promising it in the
record. Then add the ignore rule beside the existing ones, in the file's own style.

The removal is re-broken by every later rebase onto a tip where a sibling's bookkeeping commit re-added
files under that path — see the releng pitfalls entry. Re-measure after each rebase.

## 4 — Gate it, relative to a measured baseline, with a proved-red arm

A naive absolute gate ("fail when any path matches") reds on an existing tree and cannot land. Two
shapes work:

- **Baseline-relative**: a named constant holding the count measured at the tip, failing only when the
  current count EXCEEDS it. Report both numbers in the row's output so a reader sees legacy vs new.
- **Proved-red arm**: seed a fixture (a small scratch repo, or a committed fixture file) that carries
  one host-rooted path, show the gate printing its named `FAIL` row for it, remove it, show the clean
  `PASS` control. A gate that has never been seen failing is a claim, not a gate.

Write the fixture's path from PIECES (`printf '/%s/%s/fixture\n' home "${USER:-user}"`) rather than as a
literal, so the test file does not itself become the next match.

**Chicken-and-egg**: the gate grades `HEAD`, so the commit that removes the offending paths is refused
by the hook that runs the gate. Land that single remediation change with
`git -c core.hooksPath=/dev/null commit`, run the suite at the resulting tip, and disclose the bypass.

After a rebase lands a sibling's new doc carrying a host path, sanitize it in the same branch: replace
the checkout path with `~/<dir>` and the node/user home with `/home/<user>/`, keep surrounding numbers
and evidence untouched, and say in the commit subject that the sanitization is what restores the
baseline. That is the class's own rule applied to the class's own commit.

## 5 — Classify what remains

Three outcomes, never blurred into one:

| Outcome | Meaning |
|---|---|
| Authored docs still carry paths | residual cleanup; keep the row open with the measured count |
| Bundles re-added by sibling bookkeeping | residual; name the count and the single removal command |
| Gate green, count at baseline | landed; the gate now blocks growth even though legacy remains |

A row whose criterion is "a clone carries zero of X" is NOT met by "937 of 941 are gone". Say the
partition explicitly, keep the row open, and put the remaining single command in the note — an
approval-gated removal that was refused is a residual with a named unblock, not a completed criterion.
