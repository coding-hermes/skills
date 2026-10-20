# Resolved board ownership and harness-row escalation

Use this reference when a PM lane runs from a stand-in path or when open rows were produced by QA/dogfood infrastructure rather than the product.

## Resolve the real board

1. Resolve the project workdir from the scheduler database, then identify the board path under that workdir.
2. Compare `readlink -f` and inode (`stat -c %i`) for the DB-resolved board and any owning-repository copy.
3. If the files are the same inode and `git -C <repo> ls-files --error-unmatch` proves the board is tracked there, operate on that file. Never create a second board beneath the PM stand-in directory.
4. Before staging, run `git rev-parse --show-toplevel`. Stage with a pathspec relative to that actual top-level; an absolute path outside the top-level is rejected even when the file exists.
5. Commit only the board paths. Re-read the exact commit and the target row after commit.

A stand-in-looking path is not automatically invalid: ownership is established by the scheduler resolution, inode comparison, and git tracking. Conversely, identical content at two paths is not enough; atomic replacement can split their inodes and leave one stale.

## Keep reconciliation denominators separate

Treat the canonical reconciler's aged-item table and the current board as different measurements.

- A project absent from the reconciler's aged table means no aged ledger follow-up for that project; it does not mean the board is empty.
- Report all named reconciler buckets, then report the target board's raw status histogram and actionable rows separately.
- Use the ledger only for prior-cycle verification and the board for current dispatchability.
- Do not apply a fleet-wide residual count as the target project's open count.

## Escalate harness-owned rows

For a stale QA or dogfood row:

1. Re-run the row's exact failure probe where practical and run the named control path or a known-good toolchain/artifact variant.
2. Classify the result before editing: product defect, harness/provider defect, operator-gated work, or transient environment condition.
3. If the product control is healthy and the failure is harness-owned, keep the row on the consumer board for visibility but do not re-file it as a product defect.
4. Apply at most the board's permitted one-tier stale priority bump, updating the title prefix with the same new tier and adding a concise stale-escalation note.
5. Do not close the row merely because it is harness-owned; the harness still needs an owner and acceptance criterion.
6. Do not mint a second row for the same fingerprint while the original remains open.

Use source inspection plus a control result to distinguish a real harness bug from a setup-only failure. A source line that already contains the intended fix is not sufficient if the deployed or executed harness artifact is stale; verify the artifact actually used by the failing leg.

## Verification checklist

Before reporting the cycle, reparse every JSONL line, assert `unique_ids == lines`, run the board validator, read back the edited rows, and verify the exact commit SHA. Record the validator's warning/error distinction; legacy warnings are not a clean validation result, but they are not errors unless the validator labels them as such.
