# Hosted CI creates no run at all — probe ladder

For the state where the branch moves but the provider evaluates nothing. Distinct from a run that
EXISTS and failed (a code blocker) and from a run that failed pre-step with `steps: []` (runner/
infrastructure — probe it per `gate-red-classification.md` and count it as neither absent nor red). Here every commit has zero check-suites.

## Probe ladder, in order

Each probe removes one class of cause. Stop when the remaining class is the one you can name.

| # | Probe | A positive reading rules out |
|---|---|---|
| 1 | `gh api repos/<o>/<r>/commits/<sha>/check-runs --jq .total_count` and the same on `/check-suites` | "one workflow failed". `0` means no workflow was ever EVALUATED for that sha — a different state from failed or skipped. |
| 2 | `gh run list --repo <o>/<r> --limit 5 --json databaseId,status,conclusion,headSha,createdAt` | bounds when the gap STARTED: the newest executed run's `createdAt` is the last verified tip. |
| 3 | `git rev-list --count <last-good-sha>..<branch>` | sizes the blast radius: how many commits are unverified. |
| 4 | The workflow file's `on:` block, `state`, and `paths:` filters | wrong-branch or path-filter explanation. `state=active` from `gh api repos/<o>/<r>/actions/workflows`, a branch listed in `on.push.branches`, and no `paths:` filter together mean a push MUST produce a run — with two exceptions that are NOT defects, so rule them out here before climbing further: (a) a **skip directive** anywhere in the head commit's message (`[ci skip]`, `[skip ci]`, `[no ci]`, `[skip actions]`) suppresses the whole push event, so a repo with no `paths:` filter legitimately shows `total_count: 0`; (b) a **batched push** evaluates only its head commit, so when a lane pushes its artifact commit and its board commit together, the earlier sha in each batch has no run of its own and an empty result for it is expected. Census the window (`git log --format='%h|%s%n%b' <base>..<tip> | grep -c -i 'ci skip\|skip ci\|no ci'`) and compare against the commit count before calling absence a defect. |
| 5 | `gh api repos/<o>/<r>/actions/permissions` | an admin-disabled Actions setting: `enabled:true` and `allowed_actions:all` clears it. Also check `gh api repos/<o>/<r>` for `archived`/`disabled`, and the repo's DEFAULT branch — a report about the default branch is not a report about your release branch when a tag or workflow only fires on one of them. |
| 6 | `gh api repos/<o>/<r>/actions/runners` | a self-hosted-runner explanation. A repo-level `total_count:0` is expected and harmless when workflows use `ubuntu-latest`. |
| 7 | `gh api "repos/<o>/<r>/events?per_page=30"` filtered to `PushEvent` | push delivery. A recorded `PushEvent` for the branch proves the provider received the ref, so the failure is RUN CREATION after the event, not a push, credential or hook problem. This is the probe that most often converts a vague "CI is broken" into an actionable owner. |
| 8 | One stuck run: `gh api repos/<o>/<r>/actions/runs/<id>/jobs --jq .total_count` | "runs are just slow". A run `queued` for weeks with 0 jobs never reached a runner. |
| 9 | Same-day differential across 2–5 sibling repos under the same owner | account billing, spending limits, quota and outage. Siblings executing runs the same day exclude all of them and make the block repo-specific — quote their run ids and conclusions, not just "others are fine". |
| 10 | Sample commits ACROSS the dead window, not only the tip | a tip-only defect. Uniform `0` across the window bounds the start date. |
| 11 | **Your own push**: land a bookkeeping-only commit and probe `check-runs`/`check-suites` at the pushed sha ~30s later | "nobody has pushed lately". A `0` at a sha you pushed minutes ago means the defect reproduces on demand. |

## A batched-push intermediate SHA is unverifiable by construction — advance the candidate

An empty result for a SHA that rode in the middle of a multi-commit push is not a defect and not a
pending run: the provider only ever evaluates the pushed HEAD, so that SHA will NEVER acquire a run,
and re-querying hours or days later returns the same `0`. "Wait longer" is not the remedy and
"queued" is the wrong word for it. Confirm the shape before anything else: the intermediate has no
run of its own while a later commit in the same push has terminal runs (`git log --oneline
<sha>..<head>` plus a `head_sha` query for the head).

Moving the candidate is a legitimate repair, not a re-run of the gate:

1. **Advance the candidate to a graded descendant** — the next commit the provider actually
evaluated, typically the lane's own bookkeeping carrier. The gate then has a receipt instead of a
hole, and the release decision can finally be taken on evidence.
2. **Prove the move is bookkeeping-only by per-entry tree comparison**, not by an exclusion diff:
   `git ls-tree` the two commits, require the same entry count, the same entry names, and an
   identical object id for every entry outside the bookkeeping directories. "38 entries each, only
   `.coding-hermes/` and `docs/` differ, 0 product paths" is the sentence that licenses carrying the
   earlier census and build receipts onto the new candidate.
3. **Read the descendant's own runs per job**, and classify skips rather than ignoring them: a job
   skipped by a tag-only condition is expected, an unstarted required job keeps the gate UNPROVEN.
4. **Report the transition in those words** — state that the earlier UNVERIFIED was structural (a
   SHA the provider could never grade), that the candidate advanced bookkeeping-only, and cite both
   SHAs with the descendant's run ids. Never present the descendant's green as if it were a re-run of
   the same gate, and never attribute the intermediate's zero to a fix or to the new commit.

Never borrow the descendant's green for the intermediate itself: the receipt belongs to the SHA the
run names, and a candidate with no run of its own stays unverifiable no matter how identical its
tree is. When the only available descendant is too far ahead to be bookkeeping-only, the honest
output is UNVERIFIED plus a row asking for a carrier landed on that candidate.

## A run you just pushed is briefly invisible

Do not record absence against a sha you pushed in the last minute or two. Run creation lags the ref
update, and `gh run list --commit <sha>` filters on an index that lags further still — it can return
empty while the run already exists and is `in_progress`. A phantom absence here is the worst possible
reading: it manufactures a CI-defect row out of a healthy gate.

1. Poll the UNFILTERED recent list for the sha before concluding anything:
   `gh run list --repo <o>/<r> --limit 5 --json databaseId,status,conclusion,headSha,createdAt` and
   grep `headSha` — this is what actually finds a run the `--commit` filter missed.
2. Cross-check `gh api repos/<o>/<r>/commits/<sha>/check-runs --jq .total_count`, and only then read
   `check-suites`.
3. Allow a couple of minutes of grace for a heavyweight matrix. Budget the wait by the repo's own
   observed run duration (`created_at`/`updated_at` of a recent completed run) rather than by a fixed
   sleep, and say in the row "run created, still executing" instead of "no run".

Keep a poll loop shorter than the tool's own timeout and re-issue it: a foreground loop that outlives
the call loses its accumulated readings and reads as a hang. Sleep-and-recheck in bounded batches,
printing each reading with a timestamp so the sequence survives.

## `--commit` matches the FULL SHA only

`gh run list --commit <sha>` filters on an exact 40-character `head_sha`. A 7-character
abbreviation — the form every report, board row and commit message uses — returns EMPTY for a run
that exists and is already green, and the empty output is indistinguishable from genuine absence.
That is the worst misreading in this file: a CI-defect row manufactured out of a healthy gate, plus
a NO-CUT carried by a phantom red.

- Resolve the abbreviation first (`git rev-parse <rev>` in the same call) and pass the full SHA.
- Treat every short-SHA empty result as an UNRESOLVED QUERY, never as ABSENT. It is not a reading.
- Recover through the unfiltered recent list grepped on `headSha` (step 1 below), and quote both the
  run ids you found there and the abbreviation that hid them, so the next pass does not repeat it.

A commit ref can also be a tag name: query the tag's commit SHA rather than the tag string, because
the run indexes the commit the tag points at, not the tag object.

## Absence is PER-WORKFLOW, not per-commit

`paths:` / `paths-ignore:` are per workflow, so one tip can be ABSENT for the gate you happened to
check and RED for another. Never write "CI absent by path filter" from a single workflow's run list.

1. `ls .github/workflows/`, then read the `on.push` block of EVERY workflow for `paths` /
   `paths-ignore`. The set that runs on bookkeeping-only diffs is usually a different workflow from
   the product suite, and it is the one nobody re-checks.
2. `git diff --name-only <parent>..<tip>`, then per workflow ask: does its filter cover ANY changed
   path? A filter that excludes `docs/` and board paths means the product suite is legitimately
   absent; a filter that INCLUDES only those paths means that workflow MUST have run.
3. For each workflow that should have run: no run on the exact sha is genuine absence (ladder above);
   a run that exists and failed makes the tip RED. That workflow is an exact-head gate regardless of
   how bookkeeping-only the diff is — a product suite filtered away while a board-evidence workflow
   failed is a RED tip, not an absent one.
4. Only when NO workflow's filter covers the diff may the tip be called absent, and then state the
   mechanism: "no workflow's `paths:` covers this diff", never "CI was skipped".
5. Absence is also per-CARRIER, not per-range. A verdict measured on one commit does not transfer to
   the next: a docs-only commit that produced no run says nothing about the board/evidence commit
   pushed after it, whose changed paths the same filter may well cover. Re-run the `git diff
   --name-only <parent>..<tip>` per-workflow check for each carrier you push, and when the measurement
   contradicts an absence already written into a row, correct that row in place rather than letting
   the earlier claim stand for the whole range.

Correcting a previously filed row on this point is a reconciliation, not a new finding: append an
`audit` event to the row that carried the wrong premise, put the correction in one field of the
payload, and cite the run ids on both sides of it.

## Your evidence push churns the CI receipt it just cited

The commit that lands the artifact cancels the pipeline pending on the tip the artifact names, and
creates a new pending one on the evidence commit. The artifact therefore goes stale within minutes
BY YOUR OWN WRITE, and appending a correction churns another pipeline — a loop with no terminal
state. Break it by ordering and by phrasing:

1. Probe CI AFTER the last push of the pass whenever the artifact will state pipeline ids; a probe
taken before the push is stale in a predictable direction, not random.
2. Phrase the conclusion so id churn cannot invalidate it: "no pipeline in this window reached a
   terminal success and the runner pool has zero online entries" stays true across pushes, while
   "pipeline <id> is pending" is false two commits later.
3. When the artifact is already delivered and digest-bound, record the transition as an appended
   note (pipeline A pending → canceled by the evidence push; pipeline B on the evidence commit
   pending) rather than rewriting the body and re-binding. Disclose it and stop — the decision does
   not move, because absence before and absence after are the same absence.
4. `canceled` on the sha you superseded and `pending` with `finished_at: null` on the sha you just
   pushed are both consistent with zero online runners: the pass did not break CI, it pressed on a
   gate that never had an executor. Say that in the note so a later reader does not attribute the
   cancellation to the change.
5. **Store run IDS in the row, never a status string.** A row carrying `ci_run: <id>` stays true
   forever, because the run itself is the receipt and any reader can resolve its terminal conclusion;
   a row carrying a status word is false within the hour. When a cited run flips after your write
   (`in_progress`→`success`, or `pending`-with-zero-jobs→`completed/cancelled`-with-zero-jobs), report
   the transition in the delivery and leave the row alone — re-writing the row to chase a moving
   status costs one full row write per flip and re-churns the digest the first write settled. A run
   that reaches `cancelled` with zero jobs is the SAME absence the `pending` reading described, not a
   new fact and not a red: the verdict does not move either way.

## A cited run id is not evidence until `gh run view <id>` resolves it

Any run id written into a report, board row, commit message or ledger must be resolved first:
`gh run view <id> --repo <o>/<r> --json databaseId,headSha,status,conclusion`. An id that returns
`HTTP 404: Not Found` does not exist, and any claim resting on it is fabricated no matter how
plausible its provenance — ids get mis-transcribed from crowded list projections, sibling records,
or an earlier pass's own prose.

- **Resolve before citing, even when the id came from your own note earlier in the same pass.** A run
  list prints a dozen ids per screen; lifting one out of a column and attaching it to the wrong SHA
  is the failure mode, and neither the column formatting nor `--json` will catch it.
- **Bind the pair.** The resolved run's `headSha` must equal the SHA you cite it for. A run that
  resolves to a different commit is a mislabelled anchor, not a receipt.
- **Never infer a comparison SHA's CI state.** "The candidate is red, so the parent must be green"
  is a guess. Query the parent's own run by full SHA and report what it says. A parent that is red
  with the *same* signature converts a per-SHA red into a systemic one — a stronger blocker, not a
  weaker one, and the report must be rewritten to say so.
- **Bound a red window instead of sampling it.** Count conclusions over a large window
  (`gh run list --limit 100 --json conclusion | jq -r 'group_by(.conclusion)[] | "\(.[0].conclusion) \(length)"'`),
  then find the newest `success` in that window and cite its id, full SHA and timestamp. "N of N
  failed since <ts>; last success <run> at <sha>" survives re-reading; "run <id> failed" is one
  sample dressed as history.

### Read the ATTEMPT, not only the conclusion

`gh run view <id> --json` does not expose the rerun counter on every gh build — an `attempt` field
is dropped or rejected — so read it from the API:
`gh api repos/<o>/<r>/actions/runs/<id> --jq '[.id,(.run_attempt|tostring),.conclusion]|@tsv'`.
The attempt number decides what a green MEANS. `run_attempt: 1` green is a clean gate; a green at
attempt 2+ is a retry and must be reported as one, with both attempts' timestamps and the step that
failed, or the tip reads as reliably green when its colour is a coin flip. This is the only reading
that separates "the known flake did not recur on this tip" from "it recurred and the rerun masked
it" — a conclusion-only check cannot tell those apart.

### When a cited id 404s: retract in place, on every surface

A phantom id is a correction event, not a typo to quietly fix. A pushed artifact is already in the
foreman's reading path, so a silent edit leaves two live and contradictory claims.

1. Re-verify the underlying question from scratch (resolve the real runs, bound the window) before
   writing anything — the retraction must land with the corrected reading, not a bare apology.
2. Retract on every surface already written this pass: the artifact body and its evidence table, a
   dedicated `### Correction` section quoting the retracted sentence, the row's `foreman_note` and
   `reasoning`, structured `detail.evidence[-1].retracted_claim`, and the correction commit message,
   which names the commit it supersedes.
3. Retract in every ledger record that carries the old claim, including sibling namespaces: a
   namespace record that still asserts the green baseline keeps the phantom alive for the next pass.
4. Say plainly whether the corrected picture strengthens or weakens the decision. A systemic red
   discovered while repairing a per-SHA claim strengthens a NO-CUT; do not let the correction read
   as if the decision wobbled.
5. Re-fingerprint afterwards, and run the formatter BEFORE computing the digest — a reformat after
   the digest is recorded forces another supersession round on the row.

## A job that never started is ABSENT, not RED

GitLab badge signature: pipeline `status: failed`, the gate job `status: failed`,
`failure_reason: stuck_or_timeout_failure`, `started_at: null`, and `/jobs/<id>/trace` = 0 bytes.
That is an executor starvation timeout — the job sat in the queue and nothing ever picked it up — not
a code verdict. Label it UNPROVEN; calling it red sends the next agent to debug source that never ran,
and the misreading propagates into every downstream report that cites the pipeline.

### GitHub: `steps: []` — read the check-run ANNOTATION, do not infer

`gh run view <id> --json jobs --jq '.jobs[]|{name,conclusion,steps:(.steps|length)}'` showing
`steps: 0` on the gate job with the downstream jobs `skipped` is the GitHub form of "never started".
The reason is NOT in the run object; it lives on the check run:

```bash
ID=$(gh api "repos/<o>/<r>/commits/<full-sha>/check-runs" \
      --jq '.check_runs[]|select(.name=="<gate-job>")|.id' | head -1)
gh api "repos/<o>/<r>/check-runs/$ID/annotations" --jq '.[0].message' | cut -c1-200
```

An annotation reading "job was not started because recent account payments have failed or your
spending limit needs to be increased" is an ACCOUNT-billing block: not a code verdict, no step to
re-run, no per-SHA signal. Quote the run id plus the annotation verbatim and classify infrastructure.
The sha belongs in the path — do not add a `?ref=<sha>` query-parameter variant of the
`commits/<sha>/check-runs` call, which returns nothing and reads like "no check-runs" (i.e. like
absence).

### A `failure` conclusion on a zero-step run is still ABSENCE

Re-derive the gate class from EXECUTED STEPS on every sweep, never from `conclusion`. A run object
that appears at a tip which previously produced no runs at all, completes in seconds, and reports
`conclusion: failure` with `steps: 0` and `runnerName: null` is the same absent gate an earlier
sweep recorded: the annotation names billing, and nothing about the tree was evaluated. Writing
"CI red" for it drifts the class in the direction that licenses the wrong remedy — the next pass
debugs source or files a CI-red row against an account block no commit can fix. Say "runs are now
created at this tip; still zero executed steps (billing annotation)", keep the gate ABSENT, and keep
the decision NO-CUT. The arrival of run objects is not progress toward green and does not change the
class until a step executes.

1. **Discriminate on `started_at` + trace bytes, never on status alone.** `started_at` non-null with
a non-empty trace is a real verdict. `started_at: null` with a 0-byte trace is absence. Downstream
jobs shown as `skipped` with `started_at: null, failure_reason: null` are neither for nor against —
the first-stage stall suppressed them, so do not count them as evidence in any direction.
2. **Bound the window before reporting.** The newest pipeline whose jobs have non-null `started_at`
and non-empty traces AND reached `success` is the last verified tip; its sha plus `finished_at` plus
the commit count since is the receipt. Everything after it is unproven regardless of how the badges
read.
3. **Census executors, not just the pipeline.** `GET /api/v4/runners?per_page=N`, then
`GET /api/v4/runners/<id>` for each: `active: true` with `status: stale`, `online: false`, and an old
`contacted_at` IS the cause — quote all four fields. `shared_runners_enabled: true` on the project is
a setting, not proof a shared pool exists; a tag-scoped runner (`tag_list: [vc]`) does not serve
branch pipelines at all.
4. **Never wait on a superseded run.** A later push cancels the exact-candidate pipeline mid-queue;
`canceled` is not a verdict in either direction, so it cannot clear the red-CI rule and cannot be
cited as a failure. Only re-run once a live executor exists, otherwise the next tick re-derives the
same absence.
5. **Remedy acceptance needs a red control.** Require (a) a runner with `online: true` and a fresh
`contacted_at`, (b) a full pipeline where every gate job shows non-null `started_at` AND a non-empty
trace AND success, (c) zero `stuck_or_timeout_failure` on the proving pipelines, and (d) a
deliberately broken commit that produces an EXECUTED failed gate job — without that red control a
repaired gate that never runs again looks green forever.

Record the correction explicitly when a prior pass called the same pipelines red: name the job ids,
the `failure_reason`, the null `started_at`, the trace byte count, and the runner census, and state
that the earlier "failed at <stage>" reading was wrong. A silent reversal leaves both claims live in
the record.

## A MINUTES-old queued run with zero jobs is a stall, not a verdict

Probe 8 above is the weeks-long case. The same signature at minutes old — `status=queued`,
`conclusion=null`, `updated_at == created_at`, `jobs` total_count 0 — is provider scheduling lag on
workflow runs on `ubuntu-latest`. It is neither red nor green, so it cannot carry a release decision
in either direction: do not override the red-CI rule to publish under it, and do not record it as a
failed gate.

The rules that follow from that:

1. Classify it as a stall and file it as its own row (acceptance: at least one job starts within a
   bounded window AND the run reaches a terminal conclusion) instead of folding it into the release
   row as an unexplained blocker.
2. Never publish on the strength of the EARLIER tree while the run for your tag commit is stalled.
   Keep the tag local/unpublished while the gate is unproven; a tag you created minutes ago whose
   Release object never materialized can be deleted and re-cut later — that is remediation of a
   failed attempt, not the forbidden force-move. Decide by `gh release view`, never by tag age.
3. Probe the next push rather than the stalled one: the stall this signature describes is per
   push-event, so a later ordinary commit can spawn runs that execute normally while the older
   queued ones sit untouched. Quote the new run ids as the recovery receipt, and cancel or
   abandon-watch the abandoned queued runs explicitly so later audits do not read them as live.
4. State which runs are stalled and which are executing in the delivery report. A reader who sees
   only "six jobs success" on a later SHA cannot tell that the earlier candidate was never gated.

### Zero jobs that persist across SHAs: probe the runner HOST

A queued run nobody claims is usually read as provider lag. When it REPEATS on every sha — the same
job pending with `jobs` total_count 0 at the candidate, at a bookkeeping commit, and at a lane
artifact commit — stop polling the run and go to the machine that owns the runner. A self-hosted
runner whose working filesystem is full cannot write its heartbeat or its job record: the
registration still lists it while it accepts nothing, and every workflow naming that runner sits
pending indefinitely.

1. Read the registration (`gh api repos/<o>/<r>/actions/runners`) and then the host: `df -h` on the
   runner root, `du -xhd1 /` when `/`, `/var` and `/home` share ONE filesystem (so a full root fills
   the runner's work dir too), the listener's `systemctl status actions.runner.*` / journal, and
   `ls -ld <runner>/_diag` plus the newest `_diag/*.log` for the last write it attempted. A root
   filesystem at zero available bytes whose `_diag` stops hours earlier IS the diagnosis; quote bytes
   used/available, the filesystem layout, and the last `_diag` write time.
2. Bind the finding to the campaign, not to one job: the receipt is the pairing of every run id that
   topped out at zero jobs (all naming the same runner group) with the host reading taken at that
   time.
3. File the host fault as its own row (acceptance: the runner host has free space AND at least one
   job starts within a bounded window AND the run reaches a terminal conclusion) and keep the release
   gate UNPROVEN pointing at it. Host capacity is a verdict in NEITHER direction: it never justifies
   tagging, and it never indicts the candidate — say which, so the next reader does not inherit it as
   a code blocker.
4. Do not re-run "to be sure" while the host is full; the rerun queues exactly like the original and
   burns a tick. Re-run only after the disk row closes, and cite the new run id as the recovery
   receipt.

### The byte-identity argument, and where it stops

When the workflows that ran are not the product gate, you can still say what the shipped bytes are:
`git diff --name-only <last-green-sha>..<tip> -- . ':!.coding-hermes' ':!.gitreins' ':!docs' '
':!skills'` returning empty proves the product tree is exactly the tree the green run tested. Quote it
as CONDITIONAL, with the green run id and its sha, plus the commit count and file/byte split of the
delta.

It cannot clear a gate that DID run on the tip — that gate is red or green on its own — and it never
substitutes for the tag commit's own run, which has no prior green to inherit from. Name which gate
the argument covers; an unqualified byte-identity claim reads as "CI passed" to the next reader.

### The same argument runs in the RED direction, and only that far

Byte identity carries a RED finding FORWARD: a failing leg on an earlier sha whose product diff to
the current tip is empty is still open at the tip, so the row keeps its blocker. Cite the earlier
sha's run id plus the empty product diff; the tip's own run may not exist yet, and its absence is
not a contradiction. It never runs in the reverse direction — identical bytes do not make an
in-progress tip green, and a green run on an earlier sha is not the tag commit's gate.

But an EXECUTED green at a product-identical tip PAYS the carried red. Carry-forward is only a
substitute while the tip has no run of that gate of its own; once the tip's own run exists and the
same gate passes there, the earlier red stops being evidence against the candidate and becomes one of
two things you must name separately: (a) a flake on a superseded carrier — quote both run ids, and
(b) — when the failing step is a known lane defect (coverage floor, vuln index, toolchain pin) — an
OPEN defect on its OWN row, because a gate that passed by luck at the tip does not retire the reason
it reds elsewhere. Write "red PAID at <tip-sha> (run <id>); root cause still owned by <row-id>" and
keep the release decision driven by the blockers that remain — a paid red is not a green certificate
for the tag commit, which still has no run until a workflow triggers on it.

Recurrence across at least three product-identical shas is the flake discriminator: the same leg
failing on each of them is a defect to file, while a leg that fails once and passes on the next
identical tree is a flake to re-run rather than a code blocker. Quote the run ids on both sides of
that comparison.

When the tip's own runs are still executing at report time, deliver the verdict off the
product-identical sha's TERMINAL runs, labelled with that sha and the empty-diff proof, and name the
tip's runs as IN PROGRESS with their ids. Do not hold the pass open waiting on them, and do not
call the tip green.

## Reproducing it on demand (probe 7 upgraded)

Probe 7 reads a PushEvent the provider already recorded. Making one yourself is stronger: it converts
"no runs have appeared this month" — which an owner can dismiss as inactivity — into a defect that fires
in front of them.

1. Push a diff that is provably bookkeeping-only (board/evidence paths, no source files), so nobody can
   blame the test signal on an untested code change.
2. Capture the transcript (`old..new  branch -> branch`) and confirm `git ls-remote` equals local HEAD.
3. Wait ~30s, then `gh api repos/<o>/<r>/commits/<pushed-sha>/check-runs --jq .total_count` and the same
   on `/check-suites`. Both `0` is the finding, bound to a sha you created and can cite.
4. Record the pushed sha, the push transcript, the elapsed time and the measured counts in the owning
   row as an audit event — the pair (push, zero suites) is the receipt, not the prose about it.

Do this ONCE. Repeating the probe on every tick manufactures commits that re-open the same finding and
tells the reader nothing new; the first reproduction is the evidence, later ticks cite it.

## Remedy order (repo-owned first, no escalation needed)

1. **Re-register the workflow** — `gh workflow disable <id>` then `gh workflow enable <id>`. A workflow
   whose trigger config is correct but that the scheduler no longer knows about is fixed here and
   nowhere else. Reversible, so it needs no owner.
2. **Give the repo a side-channel** — if the workflow only listens on `push`/`pull_request`, there is no
   way to request a run at all; a `workflow_dispatch:` trigger makes the gate forceable. This is a
   dispatchable gap, worth its own row with the acceptance "a dispatch run completes green bound to the
   head sha".
3. **Cancel the stuck run** with a recorded reason. Leaving it queued keeps the gate permanently
   "in progress" in every later audit.
4. Only then treat it as platform-side and escalate with the full probe transcript.

## What the row must carry

- The gap start (newest executed run's id, sha, conclusion, timestamp) and the commit count since.
- `check-runs`/`check-suites` total_count at the tip AND at the parent, plus the sampled window.
- The `PushEvent` evidence, so the next reader cannot re-litigate push delivery.
- The sibling differential with run ids, so billing is closed rather than re-checked every tick.
- The remedy ladder as ordered acceptance criteria, and what the release decision becomes once it
  clears. Before that, cover "red but unrelated doesn't block" does NOT apply: no run means the gate is
  absent, not red, and absence is a hard invariant.

## While the gap is open

Every release decision taken during it is NO-CUT under Decision-1 rule 2 regardless of how
release-worthy the delta looks — a minor-sized `feat` count does not outrank an absent gate. Say
plainly that tagging would publish bytes nothing tested, and keep the pointer to this row in the
readiness row so the two blockers do not get re-derived separately.
