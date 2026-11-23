# Triage of a GitHub secret-scanning alert on a public repo

A public repo with an open alert is a posture defect until someone RECORDS a judgement. "Probably a fixture" is the judgement; leaving it unrecorded across ticks is the defect.

## 1. Measure before deciding

```bash
gh api 'repos/<owner>/<repo>/secret-scanning/alerts?state=open' --jq 'length'
gh api 'repos/<owner>/<repo>/secret-scanning/alerts?state=resolved' --jq 'length'
gh api repos/<owner>/<repo>/secret-scanning/alerts/<n> --jq '{number,state,secret_type,resolution,created_at,resolved_at}'
gh api repos/<owner>/<repo>/secret-scanning/alerts/<n>/locations --jq '.[] | {path:.details.path,start_line:.details.start_line,commit_sha:.details.commit_sha}'
```

Also record `security_and_analysis` (scanning + push protection enabled?). Push protection means a NEW push of the shape is blocked at the door, which raises the bar for how sloppy an in-tree fixture may be.

## 2. Decide: fixture or credential

Inspect the named blob **without printing the value**:

```bash
git cat-file -e <commit>                      # is the history still reachable?
git ls-files --error-unmatch <path>          # does the path exist in the current tree?
git show <commit>:<path> | sed -n '<n-4>,<n+4>p' | sed -E 's/(<prefix>)[A-Za-z0-9-]+/\1<<REDACTED>>/g'
```

Classify on the NEIGHBOURS in the same table, which is the only reliable evidence:

| What you see around the hit | Reading | Resolution |
|---|---|---|
| AWS's published example key id, sha1/sha256 of the empty string, `Sup3rFakePassw0rd`, `EXAMPLE`, `fake`/`test` markers | scrubber / detector fixture | `used_in_tests` |
| The file is the secret scanner or its test table itself | self-referential fixture, by construction | `used_in_tests` |
| A real-looking value with a consumer, a provider record, or `validity: active` | real credential | `revoked` after rotating out-of-band, and escalate: rotation is an owner act |
| Shape only, no consumer, no provider — and the owner rules it noise | accepted risk | `wont_fix` with the reason recorded |
| Genuinely cannot decide | stop and escalate one row naming the evidence | — |

Two facts that change the shape of the fix and must be stated in the record:

- **Path gone from the tree but present in history** — the alert stays legitimate because public history is not retracted by deleting a file. Say so; it is why "the file does not exist any more" is not an answer.
- **No in-tree successor carries the shape** — then there is nothing to rotate, no consumer to re-key, and the remedy is dismissal plus documentation, not a code change.

Never rotate a fixture: rotating it breaks the test that proves the scrubber works and changes nothing about exposure.

## 3. Dismiss with a self-documenting comment

```bash
gh api -X PATCH repos/<owner>/<repo>/secret-scanning/alerts/<n> \
  -f state=resolved -f resolution=used_in_tests \
  -f resolution_comment="<path>:<line> @<short-sha>. <why>. <what is / is not in the tree>. <triager + tick id>"
```

Keep the comment under ~280 characters; it must name the **path**, the **commit**, the **reason**, and the **triager**, because it is the only part of the dismissal a stranger sees. Dismissal is reversible from the provider UI — it is auditable, which is exactly why it is the right instrument and deletion is not.

## 4. Record it in-tree so the next tick re-measures instead of re-deciding

One file (e.g. `docs/SECURITY-TRIAGE.md`), append-only, one section per alert: alert number, secret type, provider, opened/resolved timestamps, path + line + commit, whether the path is in the current tree, resolution, resolved-by (tick id), why the dismissal is correct, and the two re-measure commands with their expected outputs.

Authoring constraints for a PUBLIC repo:

- **No absolute host paths.** Write `~` or a placeholder.
- **Do not spell a detector prefix literally** if the doc must name it: write it as a bracket expression (`xox[bprs]-`) so the documentation cannot match its own pattern, then prove it with `git grep -nE '<pattern>' -- <file>` returning nothing.
- **No token-shaped placeholder values**, not even obviously fake ones — push protection blocks the push and a new alert is the reverse of the fix.
- Add a standing instruction: do not "fix" this by rotating anything; do not reintroduce a token-shaped literal.

## 5. Verify, then close

| Check | Command | Expected |
|---|---|---|
| open | `gh api '…/alerts?state=open' --jq 'length'` | `0` |
| resolved | `gh api '…/alerts?state=resolved' --jq 'length'` | `1` |
| reason readback | `gh api …/alerts/<n> --jq '.resolution'` | `used_in_tests` |
| tree clean | `gitleaks detect --no-git` and the repo's own suite | 0 findings; `SELFTEST: PASS` or equivalent |

The row's acceptance is the readback pair, not the PATCH's exit status. A PATCH that 200s but reads back the old resolution proves nothing.

## Anti-patterns

- Deleting the alert (or disabling the scanner) to make the open count 0 — destroys the audit trail and is not acceptance.
- Closing the row with `resolution_comment` empty and the reasoning only in the board: the next releng tick has to re-decide, which is the cost the row exists to remove.
- Publishing the raw scanner transcript into the repo: it reintroduces the shapes you just dismissed and can trip push protection.
- Bundling the dismissal with an unrelated code change: one commit, one surface, so the verdict binds what it graded.
