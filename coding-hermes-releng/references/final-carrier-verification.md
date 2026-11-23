# Final carrier verification

Use this after an artifact commit and board carrier have both been pushed.

1. Re-fetch the canonical default branch and record its full SHA. Confirm the carrier is the remote default-branch tip or explicitly explain intervening commits; a temporary branch or pre-landing carrier is not the final carrier.
2. Read the exact artifact bytes from the remote tree and recompute its digest. Confirm the pass count or section marker increased exactly once and prior sections remain present. When a re-fired tick appends a section to an artifact it already shipped, amend the header in the same commit: an appended `## Pass N` under a header still naming the earlier certified candidate makes the first line a reader audits false, and the two claims (certified code tree vs re-anchored tip) belong on separate labelled lines rather than one overwritten value.
3. Read the exact target row and audit event from the remote default-branch tree. Confirm candidate SHA, artifact commit, artifact digest, decision, and evidence fields are internally consistent. Treat a successful local writer or push as transport evidence only.
4. Query CI by the full final carrier SHA, not by branch or the earlier candidate. Classify the result as terminal success, terminal failure, in progress, or absent. Candidate CI never certifies a later carrier.
5. If a post-carrier audit append or row correction creates another commit, update the row's carrier and carrier-CI fields together, land the correction through the normal default-branch path, and repeat steps 1–4. Do not leave the row naming the superseded carrier.
6. Deliver only after tag/release state, board readback, artifact digest, final carrier CI, and memory disposition are settled. If the memory leg stopped after a schema refusal, state UNVERIFIED; do not manufacture a readback.

## Terminating the carrier-CI chain

Every board or row commit you push starts its own run, so "bind the carrier's terminal CI" never converges on its own — each bind commit is a new carrier with a new run, and a lane that keeps binding produces an endless commit chain. Plan the pass as ONE bind, and make that bind terminal:

- Push only what the evidence requires: the artifact commit, then a single row carrier.
- In that carrier, record the terminal result for EVERY SHA the pass pushed (run id, SHA, conclusion) plus one sentence of material-tree equivalence: those diffs are board/evidence-only against a SHA that already has a green run, so the pass's green verdict is not a moving-target claim. That sentence is what lets the next pass stop re-binding.
- Then probe the carrier's OWN run and state the result. Material-tree equivalence is an argument, not a substitute for querying the run; never leave the final carrier IN_PROGRESS while a bounded probe can settle it, and never reuse the predecessor's green run.
- The carrying commit cannot name its own SHA — a commit cannot contain itself. Name every SHA the pass pushed with its run, state in the payload that the carrying commit is deliberately unnamed, and report the carrier's own run id in the delivery message and the memory record instead. Once that run is reported, stop: a further run id appearing on the bind commit is not a reason to push a second bind.

### When the bound probe cannot settle

A run that will never start can be polled forever. The signature is `pending` status, every job `runner: null` with `started_at: null`, and a project runner census returning zero online entries. Two or three readings plus that census is the whole evidence; more polls add nothing and cost the next pass its time budget. Classify the run ABSENT — not in progress — and end the pass on that classification.

Absence closes the EVIDENCE chain, never the release gate: absent is not green. The release stays blocked on "no executed run at the candidate", and the report says that, not "CI is red" — a red claim implies code that was tested and failed, which points the next reader at the wrong fix.

```bash
GL=https://gitlab.example.com/api/v4; gid=<project-id>; pid=<pipeline-id>
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" "$GL/projects/$gid/pipelines/$pid/jobs" \
  | jq -r '.[]|"\(.name) runner=\(.runner.id // "null") started=\(.started_at // "null")"'
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" "$GL/projects/$gid/runners?status=online" | jq 'length'
```

```bash
for i in $(seq 1 14); do
  out=$(gh run list --repo <org>/<repo> --limit 1 --json databaseId,headSha,status,conclusion \
        | jq -r '.[]|"\(.databaseId) \(.headSha[0:8]) \(.status)/\(.conclusion)"')
  echo "poll $i: $out"
  case "$out" in *completed*) break;; esac
  sleep 30
done
```

Run the poll in the foreground with a hard iteration cap, not as a backgrounded sleep: it returns as soon as the run settles, and the printed series is the receipt. A Python test matrix typically settles inside 3–6 minutes.

Pitfall: Do not reuse a green candidate run for a board-only carrier. Board-only commits still trigger CI, and the carrier can be red, absent, or still running independently of the candidate.

Pitfall: Do not report a temporary branch carrier as durable default-branch state. A board write can be correct on that branch while the canonical branch still lacks it; verify the landed default-branch tree and bind the row to that final commit.

## Carrier evidence in a checkout other lanes write

A shared product checkout is other lanes' landing site, not yours: other jobs run there, commit there, and may be mid-commit at any moment. Land evidence from a clean detached worktree at the candidate; never commit or push from the shared tree, whose unpushed commits belong to whoever is working in it.

When its `index.lock` exists, identify the owning process (`ps -eo pid,etime,cmd`), confirm the lock's mtime matches it, and poll `kill -0 <pid>` until it exits — removing another lane's index lock corrupts its commit.

A sibling can commit a board blob captured BEFORE your row correction, which would silently revert the carrier fields you just bound. The repair is restore-only: `git checkout origin/<branch> -- <board paths>`, confirm `sha256sum` matches `git show origin/<branch>:<path>`, leave the sibling's in-flight `events.jsonl` append alone, and make no commit and no push. Then write the watch as a field-level check in the ledger so the next pass can detect the regression mechanically: name the field and the expected value — an older carrier SHA on the row means the sibling's rebase kept its own side, and the row must be restored rather than re-derived.

## Prove the chain is bookkeeping-only, do not assert it

Name the measured candidate once and prove every later commit touched no product path:

```bash
git diff --name-only <candidate>..<carrier> -- . ':!.coding-hermes' ':!reports' | wc -l   # must print 0
```

Put that command and its `0` next to the carrier SHAs in the artifact, plus one line: any later commit touching only `reports/` or `.coding-hermes/` is another carrier receipt, not a product change. Prose claiming "bookkeeping only" without the path-set proof is an opinion; the proof is what tells a reader the certified tree is untouched and what lets the next pass stop re-anchoring.

## Quote the gate, never the interpretation

Copy the exact summary line the tool printed and nothing else: `Tasks: 10 successful, 10 total in 36.178s`, not `10/10, 0 cached`. A qualifier the tool never printed (`0 cached`, `all green`, `no warnings`) is an invented receipt that no later reader can reconcile against the log, and repairing the wording after the carrier costs another carrier — the chain the section above forbids. When a number matters, rerun the tool in a form that prints it instead of inferring it.

## Run the repo format gate after the last edit, never before

Formatting your own artifact IS the edit. A repo-wide `format:check` executed before `prettier --write` / `gofmt -w` / `ruff format` on that file fails purely because of the in-flight text. Sequence: edit → formatter `--write` → `format:check` green → confirm the working tree holds only the intended path → commit. A red produced by that ordering is not a gate finding and must not be reported as one.

## Reset suite-mutated fixtures before staging

Test suites that rewrite tracked fixtures leave the worktree dirty, and a broad `git add` ships them as release evidence. After the gate run, restore each mutated path named by `git status --porcelain`, then stage only artifact/board paths and assert `git diff --cached --name-status` equals the intended set. `boardctl update` rewrites `tasks.jsonl` only; `boardctl create` and event appends also touch `events.jsonl` — stage what the writer actually changed, not what the script intended.

## Compose the row text from captured output, before the first write

Build the summary/title/note strings from variables holding the exact tool output at write time, never from memory after the write. A wording fix discovered after the row lands is a second board carrier, so every receipt you would ever want to correct belongs in that string on the writer's first call.
