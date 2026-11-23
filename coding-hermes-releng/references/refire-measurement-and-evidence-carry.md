# Re-fire measurement and evidence carry

A releng lane commonly fires again at the SAME tick id while a sibling lane is committing into the same repo. The second pass must re-measure, not re-decide, and must be able to say which of the previous pass's receipts still hold, on what grounds, at what SHA.

## Anchor resolution in a shared checkout

Resolve the anchor to a FETCHED remote ref inside the same command that consumes it, and print the resolved SHA:

```bash
git fetch origin -q && git rev-parse origin/main && git rev-list --left-right --count origin/main...HEAD
```

Never hand `HEAD` to the measurement worktree (`git worktree add --detach HEAD`) in a checkout other lanes write to. A sibling commit landing between your census and your probe makes the worktree materialize a tip you never censused, and every subsequent receipt silently describes the wrong tree. When the anchor moves mid-tick, re-anchor and re-run the measurement rather than reinterpreting the failed one.

## Which checkout you measure: the carrier resolves as a repo too

A stand-in workdir can hold a REAL git repo that carries only the board, the evidence artifacts and the
release notes — no remote, no tags. `git -C "$BOARD" rev-parse --show-toplevel` succeeds there, so the
anchor looks authoritative and every release-channel read (tag list, `gh release list`, CI) comes back
empty for reasons that have nothing to do with the release.

Detect it before you read the channel:

```bash
ROOT=$(git -C "$(readlink -f .coding-hermes/board)" rev-parse --show-toplevel)
git -C "$ROOT" remote -v | wc -l     # 0 ⇒ this ROOT is the CARRIER, not the product
git -C "$ROOT" tag -l   | wc -l      # 0 with 0 remotes confirms it
```

Zero remotes means you resolved the evidence carrier. An empty `git tag -l` there is NOT "no tag", and
the absence of CI reads there is NOT "no CI" — both are reads of the wrong repo, and either one
published as a release fact misreports the channel. Resolve the product checkout (the prior pass's
committed artifact names the path it actually measured; otherwise the lane's `repo_url`/workdir config,
or the evidence paths the board rows cite), then re-run the tag, release-channel and CI reads THERE,
with org/repo derived from that repo's own remote. Name both paths in the report and say which reading
came from which: a table that mixes carrier reads into a product row is how a clean channel gets
reported as missing.

## A row count is a field projection, not a file grep

Authorization and blocker counts are ROW counts. Completed rows routinely quote the row id they are
reporting the ABSENCE of ("no cut-authorization row exists"), so a whole-file `grep -c` over the board
counts that prose and reports authorizations that do not exist — and a pass that trusts the number may
proceed toward a cut nobody authorized.

```bash
jq -r 'select(.id|test("^RELEASE-")) | "\(.id)\t\(.status)"' <board>/tasks.jsonl   # the rows
jq -r 'select(.id|test("^RELEASE-.*cut")) | .id' <board>/tasks.jsonl | wc -l     # authorizations only
```

When the grep count and the row count disagree, the ROW count is the fact and the remainder is quoted
text: publish it as "N literal hits, all prose inside completed rows". Derive every "0 X rows" claim in
a report from `.id`/`.status`/`.title` projections rather than from `grep -c` over the file, so the
negative result is a measurement instead of an artifact of prose.

## The product-subtree predicate, and the advance that lands mid-pass
The cheap test for "same release, different bookkeeping" is a product-path diff — not a tree crawl:

```bash
git fetch origin -q
git diff --name-only <certified-sha> origin/main -- . ':!releng' ':!.coding-hermes'
git diff --name-only <certified-sha> origin/main | grep -c -v -E '^(releng/|\.coding-hermes/)'
git diff -w --stat <certified-sha> origin/main -- . ':!releng' ':!.coding-hermes'
```

Zero paths ⇒ identical product subtree ⇒ carry the verdict, mint no artifact, no readiness row, no
carrier. A non-empty product diff that collapses under `-w` is formatting-only (blank line after a
docstring, re-wrapped raise, trailing comma): non-material, so no re-census and no semver change, but
re-run the suite — "suite green" is a claim about the SHA you name, not about an ancestor. Run it via
the repository's interpreter (`.venv/bin/python -m pytest -q`); collection errors from the system
python are a missing-dependency environment and reporting them as a broken suite misstates the repo.

The trap specific to a shared checkout: the tip can advance AFTER your measurement and BEFORE or
DURING your carrier push, so the sentence you publish names a candidate that no longer exists. Re-assert
`git rev-parse origin/main` immediately before the push and again after it. When it moved, classify the
delta, then append ONE audit event re-anchoring candidate, delta class and fresh suite receipt — that
correction is the only second carrier a no-cut pass may mint, because it replaces stale evidence rather
than restating an unchanged verdict. Never leave a pushed record naming a tip that is no longer the tip,
and never repair it by amending or force-pushing a carrier another lane may already have read. A push
range whose left side is someone else's commit is the sibling landing mid-pass: read
`git log --oneline -4` before narrating which commit carried what.

## A preflight CI refusal is three different realities with one sentence

A repo-owned release preflight that gates on "CI green on HEAD" prints the same refusal for: no run registered yet (seconds after a push), a run still `in_progress`, and a genuinely red or absent run. Only the third is a gate failure.

```bash
gh run list --repo <org/repo> --commit <sha> --limit 10 \
  --json databaseId,workflowName,status,conclusion
```

Read `status` and `conclusion` as separate facts. `in_progress` means poll the exact SHA and then re-run the preflight for a clean receipt; recording it as red misreports the repo, and recording it as "no CI" misreports the evidence. Same rule applies to a run set that is only partially observed. Pass the FULL 40-character SHA — `--commit` matches `head_sha` exactly, so an abbreviation returns empty and that empty reads as "no CI" (see `ci-run-absence-diagnosis.md`).

## Reading the failing leg of a matrix run

A `go test ./...` style leg keeps running after a package fails, so the job log's TAIL is the remaining
green packages plus `Process completed with exit code 1` — a tail read reports a red leg with no failing
test, and the assertion sits at the failing package's own position earlier in the stream. `--log-failed`
selects failing STEPS, not failing LINES, so it has the same shape:

```bash
gh run view --repo <org/repo> --json jobs \
  --jq '.jobs[] | select(.conclusion=="failure") | "\(.name) \(.databaseId) \(.steps[] | select(.conclusion=="failure") | .name)"'
gh run view --repo <org/repo> --job <job-id> --log | grep -E '\-\-\- FAIL|^.*FAIL\s|Error Trace|Error:' | head -20
```

Quote the assertion verbatim (`"144.25µs" is not less than or equal to "142µs"`) instead of paraphrasing
the mechanism: the BOUND TYPE is what classifies the red as a gate-margin defect rather than a product
finding, and the next pass needs the numbers to tell a repeat instance from a new one. Name the file and
line the trace points at; a flake class is identified by test, assertion and line, not by job name alone.

One schema note that costs a round trip in this same read: the board's `detail.evidence[]` entries carry
a `ts` field, while the memories view's column is `timestamp` — projecting `ts` against `memories` is a
binder error whose candidate list names the real columns. Two surfaces, two names; when unsure, select
`*` once and read the shape.

## Carrying a scanner census forward

Hash the captured scan log and compare it across passes. A byte-identical log at a new tip converts a carried advisory census into a fresh measurement equal to the prior one, which is stronger than tree identity alone because it proves the scanner saw the same inputs.

```bash
govulncheck ./... > <log> 2>&1; echo "rc=$?"; sha256sum <log>
```

`govulncheck` exits 3 when it finds vulnerabilities — that is a finding, not a tool failure. Record the exit code, the advisory count, the offending module version and its fix version, and the reachability path; when the log hash matches the prior pass, say so instead of restating the list as if newly discovered.

## Proving a tip delta carries no material change

Step down until the differing leaf is named — do not stop at "the tree differs":

1. `git ls-tree <old>` and `git ls-tree <new>` to scratch files; compare entry counts.
2. Diff them, filtering the bookkeeping dirs (`.coding-hermes`) out of the comparison.
3. For each remaining top-level difference, `diff <(git ls-tree <old>:<dir>) <(git ls-tree <new>:<dir>)` and repeat on subdirs.
4. Name the leaf: which blob was added/changed, and whether it is product code or evidence.

Quote the entry counts and the leaf in the report. "Bookkeeping only" is a measurement, not an impression.

### A named leaf still has to be adjudicated for SHIPPEDNESS

The product-path diff excludes only the bookkeeping trees, so `scripts/`, `ci/`, docs and tooling all sit
INSIDE the predicate: a non-empty product diff therefore does NOT mean the release changed. The cheap
test answers "did the tree move"; the release question is "did the artifact move". Adjudicate every
differing leaf against the surfaces the artifact is actually built from, with independent arms, and
report the arms rather than an impression:

1. Build-graph arm — read the release workflow's build steps and the Makefile targets they invoke, then
   the sources those targets compile. A leaf no target opens is not compiled in.
2. Embedding arm — `git grep -n 'go:embed' <tip> -- '*.go'` (or the language's asset-embed equivalent).
   Embedded trees ship; a sibling script beside an embedded tree does not.
3. Packaging arm — read the packager config (`deploy/nfpm.yaml`, goreleaser archives, `package.json`
   `files`, Dockerfile `COPY`) and list the exact paths it installs. A leaf absent from that list is not
   packaged. Check for DIRECTORY-GLOB installs specifically (`COPY scripts/`, `files: ["scripts/*"]`,
   an embed of a whole dir): one glob is enough to ship a leaf that every per-file arm cleared.
4. Reference arm — `git grep -l '<filename-or-symbol>' <tip> -- ':!<leaf-own-dir>'`; zero hits outside
   the leaf's own directory means nothing loads or invokes it.

Non-shipped leaves carry the verdict verbatim: no re-census, no semver change, no new carrier. Say
"scripts/ops helpers, not shipped" and name the arms — "scripts only" reads as a guess, and the next
pass cannot tell a proven non-shipped delta from an unexamined one. The mirror error matters as much: a
leaf that IS in the embed tree, the packager list or a build target is material even when the delta is
one file, so run the same arms before calling a small diff non-material.

Quote the subtree identity on BOTH ends (`git ls-tree -r` entry counts plus the only differing leaves)
so "the rest of the tree is unchanged" is a count, not an inference from a short filename list. An
ops/probe script is neither product code nor bookkeeping — label it non-shipped, because "bookkeeping
only" invites the next pass to exclude that path structurally and lose a later change that DOES get
wired in.

## Proving the prior pass was the SAME tick

Classification of a double fire (six outcomes, and what each licenses) is owned by
`tick-double-fire-and-judge-failover.md` — its `events.jsonl` tick-id count is the primary
discriminator. Two extra probes find the same thing when the event log is bulky or unreadable, and
they read the surfaces a filed pass actually leaves behind:

```bash
ls <board>/evidence/ | grep '<tick-id>'        # this tick's evidence artifact, if one was written
jq -r 'select(type=="object") | select(.detail.evidence?) | .id +" "+ (.detail.evidence[]?.run_id // "")' \
  <board>/tasks.jsonl | grep '<tick-id>'
```

A hit means an earlier firing of THIS tick already filed the row and artifact — carry them instead
of authoring a parallel record. The tip will usually have advanced by exactly the filing commit;
confirm with the per-entry tree comparison above and say in the report that the re-measurement is
local while the remote artifact and row were not rewritten.

A third and fourth firing is normal on a cooldown satellite; the ordinal is not the decision, only
the record's provenance. Two cheaper probes than the event log, both reading surfaces a filed pass
leaves behind:

```bash
# 1) the rolling row's own tick binding
 git show origin/main:<board>/tasks.jsonl | jq -c 'select(.id=="<ROW>")|{status,updated_at,tick:.detail.tick}'
# 2) the memory family the prior pass wrote under this exact tick id
 mcp__duckbrain__query(namespace='releases',
   sql="select key, timestamp, attributes->>'decision' as decision from <view> where key like '%<tick-id>%' order by timestamp desc limit 3")
```

A `detail.tick` equal to your id, or a memory key containing it, means the pass is a carry: name the
fire ordinal in the report and do not re-litigate the decision. Read the memory record back with
`attributes->>'<field>'` projections against the text column the store actually exposes — aliasing a
column the view does not have (`content`) is a binder error, and an empty result from a mistyped
projection looks exactly like "no prior record".

The memories view exposes exactly `id, key, domain, timestamp, author, action, embedding_text,
attributes` — there is no `content` and no `created_at`, so projecting either returns a binder error
twice in a row before you learn the schema. Select `*` once on the oldest known key to read the shape,
then project `attributes->>'decision'`, `attributes->>'fire'`, `attributes->>'candidate_sha'` for the
ordinal and the carried facts:

```
SELECT key, timestamp, author, attributes->>'decision' AS decision, attributes->>'fire' AS fire
FROM memories WHERE key LIKE '/releng/ticks/<project>/<tick-id>%' ORDER BY timestamp
```

Two rows under one key with adjacent timestamps are a write plus its own correction, not two fires —
the last row for a key is the record of that fire. Read back your own write the same way (project `attributes->>'decision'` and `attributes->>'fire'`) before reporting it landed; the write ack
carries an id and a timestamp but not the stored body.

A semantic `recall`/`search` that times out has measured NOTHING: it is not evidence of absence, and
retrying it burns the tool budget while a concurrent instance of the same tick lands its own record.
When it returns a timeout inside a fire, stop that leg, switch to `list_keys` plus the query above, and
record in the pass note that the semantic read leg was unavailable while the storage leg answered — the
next pass needs to know which reads were unverified, and a silently-skipped read is later read as "no
prior record existed".

## Where the release-memory family actually lives

A lane's prior decision is not always under `releases`. Two shapes are in live use, and a project can
carry only the second:

- `/releases/<project>/<date>-<topic>` in namespace `releases` (the shared releng family), and
- `/project/<project>/release/<date>-<hhmm>` in the PROJECT's own namespace (written by that
  project's foreman and sync lanes).

Enumerate before concluding absence:

```
list_namespaces()                                              # is there a namespace for the project?
list_keys(namespace='releases',  prefix='/releases/<project>')
list_keys(namespace='<project>', prefix='/')
```

An empty `/releases/<project>` while the project namespace holds `/project/<project>/release/<…>` is
the NORMAL case for a project whose own lanes also keep ledgers. Treating the empty shared family as
"first fire" launders a re-fire into a first pass and mints a second narrative beside the existing
one — the board grep for the tick id, not the memory read, is what catches it. `dbq ns list` cannot
answer this question: the CLI is bound to one configured namespace and prints that one name only, so
its single-line output is the CLI's scope and never the inventory. Use the MCP `list_namespaces` for
the inventory and the MCP prefix listings for the family.

Write the current fire under an explicit suffix beside the prior key (`…-<date>-<hhmm>-fire-b`, or `…-<tick-id>-pass-2` when the prior pass signed its key that way — match
the family's existing vocabulary instead of introducing a second ordinal scheme), then
recall that exact key and treat the returned body as the stored record rather than trusting the write
ack. A transport failure — the stdio MCP server exiting and announcing an auto-retry window — is a
transport event, not a refusal: wait out the announced window and resend the SAME populated payload
once, instead of marking the memory leg UNVERIFIED on the first error. That key is the only durable
artifact that lets the next firing prove it was a carry, so abandoning it on a respawn is how a lane
loses its own ordinal.

## One repo, sibling releng lanes

Two satellites on one project (for example `<project>-releng` and `<project>-chaos-releng`) share the
checkout and the rolling row. Before filing, grep the fleet configuration for both names and read
their `repo_url`/workdir:

```bash
grep -n -E 'name *= *"<project>[a-z-]*(releng|release)' /home/kara/.hermes/fleet.toml
```

When a sibling exists, the row is shared: refresh it in place, never mint a parallel readiness row,
and say which lane owns it. A run of carriers from both lanes over a byte-identical `.coding-hermes`
product tree is the fingerprint of duplicated schedule, not of new work — report the carrier count
and the zero product delta as the lane-value finding, and propose the cooling as an owner decision
rather than changing cooldown, admission mode, or the lane definition yourself. Prove the zero delta
with `scripts/product-digest.sh` over the carrier chain (same digest and same product-file count at
every SHA); a differing root tree hash is expected and is not evidence of change.

## A live surface is not the candidate tree

An HTTP 200, a passing smoke probe, or a running dev server proves the bytes THAT PROCESS loaded,
never the tree you are certifying. Order the three clocks before citing it: process start
(`ps -o lstart=` / `/proc/<pid>` mtime), the artifact's own mtime (`node_modules`/`dist`/bundle/binary),
and the newest source commit on the material path set.

- Artifact mtime AFTER process start ⇒ the process is running a pre-rebuild module graph; every
  response is stale evidence and must be labelled as such, not carried as dogfood/QA for the candidate.
- Newest source commit AFTER artifact mtime ⇒ the build itself is stale; say which commit it predates.
- Only process-start > artifact mtime > source commit licenses "this surface serves the candidate".

For an INSTALLED binary — any executable on PATH that a closed deploy row already reconciled — read the version triple and the file mtime TOGETHER:

```bash
command -v <bin>; ls -l --time-style=long-iso "$(command -v <bin>)"
go version -m "$(command -v <bin>)" | grep -E 'vcs.revision|vcs.modified'
```

A copy reporting `dev` proves only that it is not a release asset. A `dev` copy whose mtime is LATER than the commit that closed the deploy-drift row proves a REBUILD happened after the reconciliation — that is what falsifies the closed row's "both copies now report vX" as a live state, and the mtime is the receipt, not the version string. Classify before filing: a closed row whose live numbers came back wrong is a recurrence to file when it GATES the release; when the tag, the published assets and the release-true copy are all intact it gates nothing, so carry it as a deploy-freshness reading under the deploy topic (mtime + `vcs.revision`), name the closed row whose claim is now stale, and mint no duplicate row — a second row for a defect class that already owns one is the churn the board cannot absorb. Say explicitly that the release surface is unaffected, or the next reader inflates a host-install drift into a release blocker.

Re-read those mtimes on EVERY pass rather than carrying a prior pass's build-age verdict. A sibling
lane sharing the checkout can rebuild or mutate build output between your passes with no commit: a
"build is stale" receipt can therefore become false without you doing anything, and the pass that
notices it must correct the earlier claim explicitly (in the note and the report) instead of silently
carrying or silently dropping it. When the rebuild, the fixture, or the running process is demonstrably
the sibling's, attribute it (pid lineage, cgroup scope, scratch dir, owning session) and describe it as
such — never as your own measurement.

Reaping a sibling's leaked harness process is not releng's call: the owner may be mid-run, and a killed
fixture destroys the evidence a later review needs. File ONE row carrying the reproduction facts (pid,
parent, scope, port, log path), the reason it blocks evidence integrity (a fixed port the fix under test
exists to conflict on; a pre-rebuild module graph answering health checks), and acceptance written
against the harness (ephemeral/OS-assigned port plus a trap-kill on EXIT/INT/TERM) while preserving the
negative assertion that a bind conflict still fails loudly. Say in the report that you did not kill it
and why.

## Reconciling your commit census against a prior pass's counts

Two different things move a census between passes and they take different explanations. Bookkeeping
commits inflate the range total (attributed under Re-fire hygiene below). The other is PARSER PARITY,
and it is the one that manufactures a false contradiction: a stricter parser reports FEWER typed
commits than the prior pass because it rejects capitalised subjects (`Fix:`) and prose-plus-colon
subjects, and the pass that inherits the older number can read the drop as lost work or as a broken
parser. Publish your number as authoritative, name the older number beside it, and say in one clause
which forms your parser refuses. Never adopt the looser count and never leave the difference
unexplained.

A third shape is not a parser difference at all: the prior pass's total reproduces EXACTLY at that
pass's own carrier tip rather than at the SHA it labelled. That is a labelled-ENDPOINT difference, not
lost work — publish both numbers with their endpoints spelled out (`<tag>..<certified>` = N,
`<tag>..<that pass's carrier>` = N+1), note that the bump-driving classes are identical, and reserve the
parser-parity explanation for a gap that survives endpoint alignment. Regenerate both arms instead of
reasoning about which endpoint the old number came from.

Restrict buckets to the closed Conventional Commit type set (feat, fix, perf, refactor, docs, test,
build, ci, chore, style, revert). A project-scoped prefix such as `board:`, `dogfood:` or `<project>:`
matches the `^[a-z]+(\([^)]*\))?!?: ` shape and silently creates a bucket named after the project, so
every bucket still sums to `git rev-list --no-merges --count` while the typed set is polluted and the
bump proposal is computed over the wrong classes. Report those prefixes as one named non-type group
instead of letting them pass as commit types.

State the unparsed residual WITH the buckets, not just their sum. On a repo whose history is mostly
prose subjects, the typed minority is the entire basis of the semver proposal — a dozen typed subjects
inside several hundred commits — and a reader given only the buckets reads the bump as far better
evidenced than it is. Record both numbers: the typed subjects that drove the proposal, and the total
commits examined.

## Re-fire hygiene

- Do not write a second carrier on pass N. Confirm the prior carrier is on the remote and that the rows/docs it cites still cite the certified candidate; extend only if a material fact changed — a stale candidate named in text you already pushed IS such a fact, and it takes a small re-anchor audit event, not a rewritten artifact.
- An unused wave budget on a verify-only lane is correct, not a shortfall: with no authorized cut, a wave can only produce duplicate work. State that as the reason rather than reporting "0 workers dispatched".
- When several open rows carry FALSIFIED premises about one owner action — three stale-install rows describing binaries that have since been rebuilt, or criteria pinned to a release that has moved — do not edit or close the siblings and do not append another sibling. File ONE row whose reasoning names each superseded id and what changed, and let the foreman close the older rows against it. That supersession statement is durable because it rides the carrier; rewriting three titles costs three carriers and still leaves the old acceptance criteria able to be graded as written.
- Registered worktree count is another lane's hygiene, not a release gate. Check prunability only far enough to confirm your own scratch tree is gone.
- A bookkeeping-only tip still GROWS the material range total: board, artifact and readiness
  commits are non-merge commits inside `<tag>..<tip>`, so pass N+1 counts more commits than
  pass N over the same product tree. Attribute the delta by class first (the added entries
  should be exactly the bookkeeping commits since the prior anchor) and confirm the
  bump-driving classes did not move, then publish the new total with the delta explained.
  Printing the larger number beside the previous pass's bump reasoning, or calling the
  difference a contradiction, makes a clean range look unexamined.
  Run the census TWICE in one pass and label each reading by its own endpoints — `<tag>..<certified-candidate>`
  for the bump proposal, `<tag>..<carrier-tip>` for the current range total — so the record carries the pair
  rather than one number the next pass has to reconcile against the prior pass's count. Measure the second
  arm instead of adding the bookkeeping commits to the first: the derived delta is exactly what a missing
  material commit would hide, and the measured one either matches the bookkeeping count or names the commit
  that broke the assumption.
- Do not mint a commit whose only content is "the carrier's CI was green". That receipt
  belongs in the delivery message and the row's carrier-CI field: an appended evidence
  artifact becomes a NEW CI subject that then needs its own disclaimer, and the append moves
  the artifact's digest, so any row binding `artifact_sha256` now cites stale bytes. If the
  artifact genuinely must carry it, rebind the digest in that same commit and say in the
  report that only the carrier's run is claimed.
- Every pass writes its own verdict key under the project's release-memory family (`/releases/<project>/<date>-<topic>`) even when it decides nothing. The no-op key is the only durable artifact that lets a later firing prove it was a carry, and its absence reads as "no prior decision on record" to the next pass — so a pass that decides nothing still owes one write. Resolve the family before writing: the family is per PROJECT, not per tick id, and a re-fire must extend it rather than open a namespace. It lives under one of two shapes — `/releases/<project>/…` in the `releases` namespace, or `/project/<project>/release/<date>-<hhmm>` in the PROJECT's own namespace — so check BOTH (see "Where the release-memory family actually lives" above) and never read an empty shared family as "no prior record".
- Delivering the same NO-CUT verdict twice is acceptable; delivering it with receipts that were not re-measured is not. Every carried item needs one of: a fresh identical measurement, tree identity, or a named reason the prior measurement still binds.

## Multi-SHA product fingerprint, and the exclusion set that ages

Comparing more than two passes is cheapest as a fingerprint per SHA, not a matrix of pairwise diffs:

```bash
for c in <certified> <prior-tip> <current-tip>; do
  printf '%s ' "${c:0:8}"
  git ls-tree -r "$c" | grep -v -P '\t(\.coding-hermes/|\.gitreins/|\.vfs/|docs/releases/)' | sha256sum | cut -c1-16
done
```

Equal digests across SHAs are tree identity for the product subtree. Identity carries the GATES; it does
not carry the movable surfaces (exact-tip CI, tags/releases, board counts, carrier persistence), which are
re-measured every pass.

Keep every exclusion STRUCTURAL — the board tree, vcs-state caches, the readiness/evidence trees, and the
specific carrier paths a prior pass added. Never exclude a named file because it happened to be untracked
residue on the pass that built the list: once another lane commits it, it is a product path, and the
carried exclusion reports a false zero over the very commit that changed the tree. Re-derive the set per
fire; when a path graduates out of it, publish it as a measured product change with its commit and say
whether it is version-neutral (docs-only) or bump-bearing.

## Landability of a preserved branch on a moved tip

A fix preserved on its own branch is stale the moment the tip advances, and "still lands cleanly" must be
proven rather than assumed. `git merge-tree` proves it without touching a worktree, the index, or any ref:

```bash
git fetch origin -q && git merge-tree --write-tree "$(git rev-parse origin/main)" origin/<fix-branch>; echo rc=$?
```

rc=0 prints the RESULTING tree OID (record it: it is the expected tree for the eventual merge); rc≠0 prints
the conflict list. Re-run it on every fire that touches the branch or the tip, and report the pair
(branch tip, merge tree) so the landing owner does not rediscover a conflict after the CI question clears.

## Exit codes and SHA binding in receipts

Capture a gate's exit status BEFORE any pipe. `sh <gate> v1.2.3 | tail -20` returns tail's status, so a
FAILED gate publishes rc=0 and reads as a pass:

```bash
sh <gate> v1.2.3 >"$out" 2>&1; echo "rc=$?"; tail -20 "$out"
```

A helper that REFUSED its arguments is not a helper that ran. Census and audit scripts commonly print a
multi-line USAGE/HELP banner and exit 0, so a `tail` reader sees plausible output and `echo rc=$?` reports
success while nothing was measured. Confirm a helper executed by grepping for a required output token
(`non_merge_total=`, `bump_rule=`, `sum_check=`) and treat its absence as a refused invocation. Invoke
the releng census by POSITIONAL arguments — `<repo> <base-ref> <tip-ref>` — never as a single `A..B`
range string, which is exactly the malformed form that produces the rc=0 usage banner.

Bind SHAs by command substitution inside the command that filters on them — `gh run list --commit
"$(git rev-parse <ref>)"` — never by retyping or reconstructing a digest from memory. `--commit` matches
`head_sha` exactly, so an abbreviation OR a well-formed 40-character value that is not the tip returns an
EMPTY list, indistinguishable from "CI never ran here". That empty is the most dangerous false absence in
a readiness pass: it reads as evidence and gets published as one.
