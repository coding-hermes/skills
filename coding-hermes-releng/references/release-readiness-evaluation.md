# Readiness evaluation for a recurring releng tick

Depth for the case where a releng satellite fires on a schedule and no cut is requested. The deliverable is a readiness VERDICT with receipts; the tag is not on the table until authorization exists. Rules live in SKILL.md; this file is the recipe.

## 1. Order of operations

1. Resolve identity before probing: scheduler row for the lane, then its parent/foreman row, then the canonical remote. A satellite often stores a `local:/path` carrier while the parent holds the forge URL. Match the checkout's `git remote -v` against the parent row before running any other probe.
2. `git fetch origin`, then pin the candidate: `git rev-parse HEAD`, `git rev-parse origin/main`, `git rev-list --left-right --count origin/main...HEAD`. Candidate is only valid at 0/0. Resolve and verify the baseline/tag peel before the range census with `git rev-parse <tag>^{commit}` and `git ls-remote <remote> 'refs/tags/<tag>*'`, then assert the peeled SHAs match; never hand-type or repair a baseline SHA from memory, because one wrong hex digit silently changes the release history being measured.

   Parity with the branch you are standing on is NOT parity with the branch the world clones. Resolve the forge default and repeat the count against it before the commit census means anything:

   ```bash
   gh repo view --json defaultBranchRef,visibility,pushedAt
   git fetch origin <default>
   git rev-list --left-right --count origin/<default>...HEAD
   git log --oneline HEAD..origin/<default>        # shipped work the candidate lacks
   git diff --stat HEAD origin/<default>           # material size of the gap
   ```

   A non-zero LEFT side means the default carries commits the candidate does not, so no single tree contains the project and the verdict is NO CUT regardless of a clean 0/0 on the active branch — a bump computed there describes a tree that is missing shipped work. Make it concrete rather than abstract: probe whether a file or a documented `make` target that exists on the default is absent at the candidate (`git ls-tree -r --name-only HEAD -- <path>`), because a `scripts/<name>.sh` living only on the default makes the documented first release step FAIL at the candidate. Print both directions in the verdict with their counts. A prior sweep that pinned the wrong baseline leaves this divergence standing indefinitely while every later reading of the active branch returns a clean 0/0 — re-derive the baseline from the forge default, never from the last row.

   Divergence is not only commits. Probe what the release GATE needs at the sha you would tag: `git ls-tree -r --name-only <candidate> -- .gitreins/ | wc -l`. A harness config that lives only on the other branch means the gate cannot be reproduced from the release branch at all, and every stored verdict belongs to a tree you are not releasing — a blocker of its own, not a stale-verdict footnote, because the first post-tag verification cycle has nowhere to run.

   Two remotes each carrying their own default branch is a different failure from a stale candidate, and the divergence is usually RECORDS, not source. Classify it before filing: `git diff --stat <authority> <mirror>` — a few insertions confined to the board/records/docs tree means both tips hold the same product with different bookkeeping, so the remedy is a replay of the missing record commits onto the other side, never a merge and never a force-push, and the row must say so in those words. The verdict is NO CUT either way: tagging one tip drops the other's records from the released lineage, and the sharper reason is that the commits unique to the non-authority side carry NO run on the authority's CI, so no sha is simultaneously the default tip and CI-proven. Bind the finding to that pair — list the unique commits and show the zero-run count per sha (`gh api repos/<o>/<r>/commits/<sha>/check-runs --jq .total_count`) — and let one parity row own the replay. Do not average the two sides into a "mostly reconciled" reading; a tag names exactly one sha.

   Contamination also diverges, and its CLASS decides the remedy. Inventory the non-harness files the other branch carries (`git diff --name-status <release-sha>...<other-sha> | grep -v '^\.gitreins/'`) and bucket them: committed state files (`*.db`, `*.db-wal`, `*.db-shm`), build residue (`__pycache__/*.pyc`, `*.bak-*`), captured host output (`scripts/raw/`, dumps, inventory snapshots). Scan exactly those paths with the secret scanner before writing the finding. Zero credential-pattern hits makes it a hygiene/PII finding — a forward delete plus `.gitignore` rules; any hit makes it a leak — history rewrite, credential rotation, incident path instead of a release row. State which class the evidence supports: "contaminated branch" that conflates the two either escalates a cosmetic mess into a rewrite or buries a real key.
3. Release surface: `git tag | wc -l`, `git ls-remote --tags origin | wc -l`, `gh api repos/<org>/<repo>/releases --jq length`, `gh release list`. Report all four, even when all are zero — 'never cut' is a finding, not an absence of one.
4. Exact-SHA CI: `gh run list --repo <org>/<repo> --limit 12 --json databaseId,headSha,status,conclusion,createdAt`, then `gh run view <id> --json status,conclusion,jobs` for the run bound to the candidate. Cite run ids. Separate older reds by SHA so nothing is inherited onto the candidate. When the candidate has no run at all, first establish that CI EXISTS at all: `git ls-tree -r --name-only <sha> -- .github/workflows | wc -l`. Zero workflow files makes `gh run list` return `[]` by absence, not by path filtering — write NO_CI (and file the CI row), never "CI green", and skip the filter analysis entirely. Only when workflows are present do you read the `on.push.paths` blocks before calling CI absent: a fully path-filtered suite produces no run for a board/docs-only tip by design, and jobs that failed with `steps: []` in seconds are pre-step infrastructure/billing, not verdicts on the tree.

   A tag is not a trigger unless a workflow says so, and the workflow that fires on a tag is usually a
   PUBLISHER, not a test gate. Inventory the trigger surface before judging any criterion of the form
   "CI green on the tag commit":

   ```bash
   grep -rn 'tags:' .github/workflows/*.yml
   grep -rn -A4 '^on:' .github/workflows/*.yml | grep -E 'push|tags|branches|pull_request|workflow_dispatch'
   ```

   Classify each hit as TEST (runs the suite) or PUBLISH (tags → build/release object). When the suite
   listens only on `push: [main]` + `pull_request`, a tag push mints NO test run, so the tag commit's
   test receipt is the main-push run at that same sha — cite its id — and the tag's own run is the
   publisher's. Say which receipt answers the criterion instead of writing "no CI on the tag", and say
   plainly that a green tag-push publisher does not re-test the bytes it publishes.

   Sharper absence probe and classification: `gh api repos/<o>/<r>/commits/<sha>/check-runs --jq .total_count` answers the question `gh run list` blurs. `0` means no workflow was even EVALUATED for that commit (nothing queued, nothing skipped) — a different state from "a run exists and failed/skipped". Probe a handful of commits across the dead window, not just the tip, so you can bound when it started. Then classify the cause by differential: run the same `gh run list --limit 2` against 2-3 sibling repos under the SAME owner. All-green siblings the same day exclude account billing/quota and make the block repo-specific (fork Actions toggled off, a stuck queue, repo-level settings) — record that reasoning in the row, because "CI is dead" with no scope is unactionable for whoever has to fix it. One run stuck `queued` with `jobs: []` for weeks is the signature of a broken queue, not a slow runner.
   Measure the RED STREAK, not only the tip run. A bounded window answers "no successes in the last N runs", which reads like "this repo has never had a green run", while the truth is a streak longer than the window. Fold the conclusions, then widen until the first success appears:

   ```bash
   gh run list --repo <o>/<r> --branch <default> --workflow <CI> --limit 60 --json conclusion \
     --jq '[.[]|.conclusion]|reduce .[] as $c ({n:0,stop:false}; if .stop then . elif $c=="success" then .stop=true else .n+=1 end)| "consecutive_failures=\(.n)"'
   gh run list --repo <o>/<r> --branch <default> --limit 40 --json databaseId,headSha,conclusion,createdAt \
     --jq '[.[]|select(.conclusion=="success")][0]| "\(.databaseId) \(.headSha[0:8]) \(.createdAt)"'
   ```

   Cite both numbers: the streak length and the last green run's id/SHA/date. A window that returns `null` for the last success is a WINDOW artifact, not a finding that no green run exists — report the streak and say how many runs the tree has been unverified for.

5. Verdicts: newest stored judge verdicts per task, latest-per-task (an earlier FAIL on the same commit is superseded by a later PASS on that commit). State explicitly when no verdict is bound to the candidate; that is UNVERIFIED, not red.

   Read the failing step's own fields before any row or ledger entry quotes it — `jq -c '.stages.tier1.steps[]|{id,passed,msg:(.message // .output)}' <verdict>` — and quote only the keys jq actually emitted. A drafted row that asserts an exit code the step object does not carry, or a commit sha recalled instead of grepped (`git log --oneline --grep='<subject>'`), becomes a fabricated receipt in durable state; re-read and correct before the append. Prefer the tool's own prose (the scanner's finding line, the suite's counts) over a paraphrase.
6. Dogfood/QA: newest record, its verdict word, its exact target SHA, and whether the defect it reports is INSIDE the candidate. Distinguish "stale measurement" from "failing pedigree" with ancestry, not with dates: run `git merge-base --is-ancestor <battery-target> <candidate>`. Exit 0 means the battery measured an ancestor of what you are about to tag, so a FAILED battery is the candidate's own lineage and blocks the cut; a non-zero exit means the battery predates a tree that was rebuilt underneath it, so it is stale-but-inheritable only if the defect paths are provably untouched in `<battery-target>..<candidate>` — prove that by grepping the range for the module the cell exercised (`git log --oneline <target>..<candidate> | grep -iE '<feature|module>'`) and reading each hit, because a perf commit in the same area is not a fix. A labelled-positive historical run is not a waiver, and a lone FAILED cell is not automatically the blocker: read every cell's status and engine (a `ci-pass` cell that could not read its input is unreadable evidence, not a red suite), then name the one cell that carries the decision with its measured ratio (for example N of M parallel invocations failed) and the single-shot result beside it. Also record the battery's agent id and its destroy state: an agent DESTROYED before evidence harvest makes the run unreproducible, which is its own dispatchable gap.
7. Version hygiene: every version surface (package metadata, module `__version__`, changelog headings, installed CLI `pip show`), and whether the changelog still holds an Unreleased section. Treat as a surface any constant a CI step GREPS or parses — a `--version` banner string, a badge line, a lockfile's own `version` field: a bump that moves `package.json` alone leaves the banner at the old number and the CI assertion grepping that banner is then a red gate on the tag commit. Mismatched or unreleased surfaces mean a version-prep commit is required before any tag, and the bump plus every surface must land in ONE commit.
8. Deployed staleness: the service PIDs and their start times versus the mtime of the module they run. A unit started weeks ago executes in-memory code older than the tree even when the file on disk is current; the CLI reporting the right version does not clear the daemons.

   Enumerate units on BOTH systemd buses before calling a daemon unmanaged. An unprivileged user unit is invisible to the system bus, so `systemctl list-unit-files '<svc>*'` returning 0 while the service is demonstrably serving is not evidence of an unmanaged process — it is the wrong bus:

   ```bash
   systemctl list-unit-files '<svc>*'                 # 0 here proves nothing on its own
   systemctl --user list-unit-files '<svc>*'
   systemctl --user show -p FragmentPath,LoadState,ActiveState,MainPID,ActiveEnterTimestamp,NRestarts <svc>.service
   ls ~/.config/systemd/user/<svc>.service.d/ && cat ~/.config/systemd/user/<svc>.service.d/*.conf
   diff -u ~/.config/systemd/user/<svc>.service <(git show origin/<default>:<repo-unit-path>)
   ```

   The drop-in directory holds the EFFECTIVE `Restart=`, `RestartSec=` and `MemoryHigh=`/`MemoryMax=`, so a repo-shipped unit that looks unsafe can be capped in practice and vice versa; quote the effective values, not the shipped file. Answer "is the running build the current build" with a stamp, never with mtimes: when the artifact mtime is AFTER the process start and `NRestarts=0`, the process runs the OLDER build while disk holds a newer one, and with no commit/built-at stamp in the artifact or the health endpoint the two cannot be proven equal. That is a STAMPING gap (ranked fix: bake commit sha + built_at into the artifact and expose it from `/health`) — file it as that, not as "stale" or "fresh", and never restart the daemon on this evidence alone, because a restart cannot be shown superior to the running process.

   **A stored note saying the deployed arm HOLDS is time-local, and a later artifact build silently falsifies it.** The note compared the artifact and process instants as they stood when it was written; nothing about writing it binds the pair afterwards. Re-measure the pair at check time before quoting any earlier acceptance:

   ```bash
   stat -c '%y %n' <deployed artifact>
   systemctl --user show -p ActiveEnterTimestamp -p MainPID -p NRestarts <unit>.service
   curl -sS /health      # uptime / start stamp, if exposed
   ```

   Artifact mtime AFTER `ActiveEnterTimestamp` with `NRestarts=0` and a live uptime matching the restart instant means the process serves the OLDER build: the earlier "arms hold" note has decayed, so REOPEN the row (acceptance owed again) and rewrite its note to carry the two measured instants plus the command that produced them, not the hold verdict. A verdict without its instants cannot be re-checked, which is exactly how a decayed acceptance passes for standing coverage. Compute the lag with shell arithmetic (`S=$(date -d '<artifact instant>' +%s)`) rather than by mental subtraction — the reported figure is a durable claim the next pass will quote back.
9. Release tooling: Makefile targets, `scripts/release*`, goreleaser, Dockerfile, publish/tag workflows, release docs. A docs-only procedure is a tooling gap worth its own row. Presence is not executability — on a never-tagged repo, RUN the documented prep step in a scratch clone at the candidate: a prep script whose no-op guard fires when the stamp already equals the implied first version leaves the first cut with no executable path, and a pre-cut CI check demanding an exact-HEAD run cannot pass on the resulting CHANGELOG-only commit when every workflow is path-filtered.   Both are dispatchable rows that publish nothing.

   When the repo documents its own prep checklist (CONTRIBUTING.md, RELEASING.md, a release section of the README), that checklist IS the gate list: execute every step it names, in its order, and cite each rc. A red documented step blocks the cut even when the suite would be green, and CI usually replicates the same scripts, so one defect shows up as a hosted red AND a documented-gate red under two row ids — file it once, naming both surfaces.

   Cross-check the recipe against the TREE before believing any run of it. Enumerate every package/directory path the publish target names and test each one exists at the candidate (`git ls-tree -r --name-only <sha> -- cmd/` beside the targets in the Makefile): a recipe listing `./cmd/<a> ./cmd/<b> ./cmd/<c>` while the tree carries `<a> <d> <c>` fails only at the second element, AFTER the first binary was already written, so `dist/` ends up partially populated and an operator reads it as success. Reproduce that failure per-element rather than running the whole loop once, so the row can name each element that does not resolve.

   Treat a dry run as NOT evidence. `make -n <target>` exiting 0, a `--help`, or any parse-only invocation proves the recipe is syntactically loadable, never that the pipeline produces artifacts; a tooling row closed on a dry run stays closed while the driver is broken. Required proof for closing such a row is an executed build (`make release-local`, `goreleaser build --snapshot --clean`) naming the outputs and their version stamps. Also compare the recipe against any second publisher in the repo (`.goreleaser.yml`, a tags-triggered workflow): when the declarative pipeline is correct and the Make target is the broken one, say which is authoritative and make the fix converge on ONE publisher, because two publishers disagreeing about package paths is how the row reopens.

   When your evidence REFUTES a row that is already closed, do not reopen or silently amend it — its closure is history. File a new row whose detail names the refuted row and quotes the acceptance evidence that was insufficient (here: a dry run). A refutation row is dispatchable because it publishes nothing. And check the contract's CREDENTIALS, not just its steps: list every secret the tag-triggered workflow references and prove each resolves — `gh api repos/<o>/<r>/actions/secrets --jq .total_count` plus the org-level endpoint, which routinely answers 403 to a repo-scoped token. Zero repo secrets where the workflow signs (cosign, notary, registry login) means a tag today either publishes unsigned or dies inside the signing step; a contract you cannot execute is a blocker, and an org endpoint you cannot read is UNVERIFIED — never write it as present.

   **Peel a gate refusal before you report it.** The driver's first refusing gate is often its own harness residue, not the release. Typical shape: a clean-tree gate that counts every untracked path while the agent harness leaves runtime state (`review-state.json`, its `.lock`, session caches) beside tracked config, with `.gitignore` covering the history/verdict trees but not the live state files — so a cut attempted after any guard or judge run refuses with "working tree is dirty" and the real blocker stays hidden.

   ```bash
   # 1. Would the gate actually trip? Reproduce its filter over the dirt, do not eyeball it.
   git status --porcelain | grep -vE '^\?\? \.(gitreins|coding-hermes)/(history|verdicts)/' | head
   # 2. Prove the false positive without mutating the checkout's history.
   mkdir -p <scratch>; mv .gitreins/review-state.json .gitreins/review-state.lock <scratch>/
   ./scripts/release.sh v<X.Y.Z> --dry-run; rc=$?          # now read the NEXT gate's message
   mv <scratch>/review-state.json <scratch>/review-state.lock .gitreins/   # always restore
   ```

   Peeling pays twice: the second gate (HEAD equal to the remote default) passing is an independent parity receipt you did not have to argue for, and the gate the dry run then refuses on is the one the report must lead with. Restore the runtime paths in the same step even when the run is interrupted — they are live harness state, not your files. File the defect as one row whose acceptance carries a RED CONTROL (a genuine source edit must still fail the gate) and a tracking invariant (tracked config beside the ignored state stays tracked); without both, a widened exemption silently disables the gate it was meant to unblock.
10. Open blockers: count and name P0/P1 rows; classify which are release-gating by doctrine and which are merely open.

    Reconcile STATUS against ANCESTRY before classing any row as open work or as closed coverage. A row whose implementation is already an ancestor of the candidate is LANDED, so its pending status is a reconciliation gap, not a blocker the cut can wait out — `git merge-base --is-ancestor <row-commit> <candidate>` plus `git log -1 --format='%h %s' <row-commit>`. If the stored verdict for that landed commit is a FAIL (`changes_required`), the candidate carries content a judge refused: that is a release blocker of its own, and the row closes only on a verdict re-graded at the landed SHA — never on a pre-fix attempt and never on the standalone verdicts path. File it as one row per group of landed rows, acceptance naming the landed SHA and the history verdict path.

    A COMPLETED row covering the same defect class is not standing coverage. When a gate is red and a closed row already fixed that class, re-measure the live numbers: if the defect is back, file a new row, quote the closed row's own closing numbers beside the live ones, and state the recurrence count. Amending the closed row erases the history that proves recurrence, and assuming its closure still holds is how a gate stays red while the board reads clean.

    A gate that depends on ANOTHER host is re-probed live every pass, and its recorded reading is not carried forward. Prior notes on the same row can disagree with each other and with the host (`83%` then `95%` in one lane's trail while `df -P /` answers `98%`), because each was true at its own instant: probe it, then make the LIVE value the reading and quote the superseded ones with their timestamps so the drift is visible instead of hidden. Record that on the row that OWNS the gate (`boardctl event --type audit --task-id <row>`), never by rewriting another lane's note, and never as a new row — the owner already holds the fix, and a fresh row dispatches a second worker at a server nobody can clean twice.
11. Decide, write, verify (sections 3-5).

### Running the CI-equivalent leg locally when hosted CI is absent

A local run is SUBSTITUTE evidence: it can convict the tree (a red here means a hosted run would also be red) but it can never clear the exact-SHA hosted gate. Run it anyway — "CI is dead AND the gate is red locally" is a far stronger decision record than "CI is dead".

- Read the workflow file and replay its steps verbatim, including per-directory installs. A monorepo suite that has its own `package.json` (tests/, cli/, e2e/) needs its own install step; skipping it does not fail — it silently no-ops.
- Treat a SKIP-with-rc-0 as UNVERIFIED, not green. Gate scripts commonly open with `[ -d <dir>/node_modules ] || { echo SKIP; exit 0; }`; run the bare command and read the message, never just `$?`.
- Capture the exit code BEFORE any pipe or redirect: `cmd > out 2>&1; rc=$?`. `cmd | tail` reports `tail`'s rc, so a red gate reads green in the transcript. Read BOTH the rc and the printed lines — a gate can exit 1 with nine FAIL lines, and can also exit 0 while printing FAIL (a wrapper swallowing the status). Quote `grep -c '^FAIL'` beside the rc and treat "rc=0 with FAIL lines" as red; rerun to a file rather than re-running inline with `tail`.
- A tool that exits non-zero naming a path it could not OPEN (`openBinaryFile: does not exist`, `No such file or directory`) measured nothing about that path. Drop the absent path from the invocation, re-run so the files that do exist get a real verdict, and record the absence as its own evidence line — a lint leg red only because a documented script is missing from this branch is a tree finding, not lint debt.
- Judge with the repo's own gate, not the raw test exit code: a catalogued known-fails baseline plus a regression checker (`verify-no-regression.mjs`, `gitreins-guard-tests.sh`, …) is the authoritative signal, and its pass→fail list is what you quote.
- Publish the numbers that make the receipt auditable: suite/test totals from the machine-readable report, the failing list, and the exit code.
- Tests that shell out to a script OUTSIDE the repo (a fleet harness under `~/.hermes/scripts/`, an installed CLI) make a local red environment-coupled. Record the external path, its mtime and sha256 beside the failure list and say the fail class needs triage before anyone calls it a product regression — a fork can be green in CI and red on a workstation whose harness moved.
- Build the evidence in a unique detached worktree at the candidate SHA, keep the small logs and the JSON report in scratch, then remove the worktree: a Node monorepo install is ~1 GB and scratch is not infinite.

### The blocker list must be reconciled against the LIVE checkout, not only the remote

A verdict that enumerates blockers from `origin/<default>` alone is complete about the TREE
and can be wrong about the WORK. The lane's real product checkout — the one the board is
symlinked into, the one sibling lanes commit from — can be ahead of the remote carrying
commits that no remote ref contains, and those commits hold exactly the newest, most severe
findings: the lane that produced them could not push them.

```bash
LIVE=<live checkout>
git -C "$LIVE" rev-list --left-right --count origin/<default>...HEAD        # behind<TAB>ahead
git -C "$LIVE" branch -r --contains HEAD                                   # empty => no remote has it
comm -13 <(git show origin/<default>:<board>/tasks.jsonl | jq -r '.id' | sort) \
         <(git -C "$LIVE" show HEAD:<board>/tasks.jsonl | jq -r '.id' | sort)   # rows only local
for p in <suspect evidence docs>; do
  git cat-file -e "origin/<default>:$p" 2>/dev/null || echo "LOCAL-ONLY $p $(git -C "$LIVE" show HEAD:$p | wc -c)B"
done
```

Rows and docs found only there are REAL blockers and belong in the verdict as a named gap —
"<n> rows and <m> evidence docs exist only in the live checkout; the remote record
understates the blocker list" — never dropped because the remote does not carry them, and
never counted as if the remote's board were the whole picture.

**Do not repair it by pushing the live checkout.** Its board is usually staler than the
remote's, so pushing reverts sibling events, and its history can carry superseded replays of
work that landed upstream in a different shape; a branch landing also reverts any board
events it predates. Reconcile row by row: diff the row ids and then the statements per id,
re-file only the genuinely missing rows against the freshly fetched remote board, and say in
reports which blockers were certified from the remote record and which stay unverifiable
until that delta lands.

### Retracting a blocker a prior pass wrote

A blocker resting on a NEGATIVE probe is the one most likely to be wrong, because the probe's glob defines the search. Derive the path from the thing that CONSUMES it, not from a listing: `git show <sha>:Makefile | sed -n '/^<target>:/,/^[^ \t]/p'` names `<dir>/<script>` even when the top-level `*.sh` listing is empty — a root-level `ls *.sh` then reads as "the documented prep step is missing" while the file sits one directory down.

When a re-measured probe contradicts an earlier pass, retract in the record explicitly: the refuted claim, the command that refutes it, and the wrong probe that produced it. Do not quietly drop the blocker from the next census — a reader comparing two passes cannot tell a retraction from an omission. Add in the same line whether the surrounding blocker still stands on its own evidence, so the correction does not function as a waiver.

## 2. Evidence payload

One audit event per sweep, carrying enough that a reader never needs the transcript:

- `sweep_id`, `project`, `repository`, `canonical_checkout`, `decision`
- `candidate_sha`, `remote_default`, `remote_parity`
- `release_baseline` (name the prior sweep head explicitly when the repo was never tagged)
- `delta_since_prior_sweep` (commits, feat/fix/chore split, breaking count) and `full_history` census as separate fields
- `semver` with `proposal`, `basis`, `authorization`
- `version_hygiene` per surface, with `status` DIRTY/clean
- `ci` with `candidate_run_id`, `conclusion`, per-step summary, `recent_failures` labelled by SHA, `tag_ci` state
- `gitreins` with the candidate binding (or its absence) plus superseded verdicts
- `dogfood` with verdict, staleness, and why it is not a waiver
- `artifact_probe` with command, rc, output names and sha256, plus the classification that these are strategy evidence, not publishable assets
- `deployed_staleness`, `release_tooling`, `open_blockers`, `required_next_gate`
- `security` with the scanner command and rc (`govulncheck ./...`, `pip-audit`, `pnpm audit`), the reachable total split module-versus-standard-library, the toolchain that produced it, and the rows it produced. An updater listing is not a scanner: `go list -u -m` / `pnpm outdated` never say the shipped bytes are vulnerable, so a sweep that only ran those reports "clean" on a tree carrying reachable advisories.
- `memory_leg` set to UNVERIFIED when the durable write was not attempted or not read back

## 3. Decision table

| Situation | Verdict | What you may write |
|---|---|---|
| Scheduler tick / readiness row only, a patch-minor is warranted, every gate green, and the release surface already exists | CUT | Version-prep commit, tag, Release, artifacts — this charter IS the authorization; no owner prompt needed |
| Scheduler tick, but a gate is red/pending/unknown, or the release surface has never been published | NO CUT | Audit event on the canonical row; refresh its primary fields; new rows only for gaps that publish nothing; one line to the owner naming the withheld decision |
| Authorization names repo + version + baseline, all gates green | CUT | Version-prep commit, tag, Release object, artifacts |
| Authorization present but a required gate is red/unknown | BLOCKED | Evidence only; name the failing gate and its run id |
| Never-tagged repo, release docs present but zero Release objects and no executable driver | NO CUT + driver row | The driver row is dispatchable because it publishes nothing; the FIRST cut is the one that creates the distribution namespace, so the owner names repo + version + baseline |

Whether a repo has a release surface is a fact about its ARTIFACTS, not its docs: `docs/releases/*.md` describing a cut procedure, a dated CHANGELOG section and a version stamp all exist in repos that have never cut anything. Measure `gh release list`, `git ls-remote --tags` and the presence of a `tags:` trigger, then say which layer is empty — "has release documentation" is routinely mistaken for "has releases" by the row that parked the first cut for weeks.

Semver on a pre-1.0 project: the `0.y` axis carries features, so any feat-bearing delta is a MINOR bump and any BREAKING footer or bang-marked subject is the only path to MAJOR — and MAJOR still needs explicit confirmation. Zero breaking footers across the whole history is a finding worth printing, not an assumption.

## 4. Writing the result

- Refresh the canonical pending row, do not mint a duplicate blocker row. Then verify the writer's field ownership: a note flag updates the note and `updated_at` only, so candidate/CI/sweep keys must be reconciled in the same single-line repair (see SKILL.md's Board evidence closeout). Treat a successful note update as insufficient until the structured fields and final artifact digest are read back; if they are unchanged, perform a separate sanctioned row-scoped structured update and verify the committed row, not merely the writer's success message.
- When the board has NO pending release row to refresh (every row is complete/closed), the sweep itself is the audit event, not a new task: write the audit payload plus only the rows that are genuinely dispatchable. A dated "sweep" task row cannot be closed either — `boardctl update --status complete` refuses without an `--evidence-run-id` that resolves to a stored run, and inventing one misattributes a sibling's verdict — so a minted sweep row either stays pending and gets dispatched as phantom work or is closed through a path that bypasses the writer. Say in the report that the audit event is the record of this tick.
- File a new row only for a different, actionable gap, with acceptance criteria a worker can be judged against. Include refusal paths and a dry-run requirement in anything that will one day mutate a tag.
- A re-fire over an unmoved gate produces no new measurement, so spend it on the BLOCKER ROWS instead of re-deriving the census: when the candidate SHA, the material delta and the CI state all match the prior pass, append an addendum to the existing artifact and fix what is wrong in the record — correct misattributed rows, file what is stranded in the live checkout, name the one gate that actually blocks. Say plainly that another sweep cannot produce new information and what specific state change would (an executed CI run at the candidate, the stranded rows landing, the executor coming back), rather than shipping a third identical verdict.
- An owner-gated row whose `acceptance` is null is UNDISPATCHABLE, and a lane that keeps refreshing it produces nothing while the owner stays silent. When authorization is the only thing you cannot grant, spend the tick on everything that does not need it: write the repair contract into that row (build + checksum + pin validation, the refusal paths each exercised, one proven publish path, a dry-run that creates no tag and no Release, and an explicit statement that nothing in it needs owner authorization). The board then reads as a queue rather than a parking lot, and the foreman has work the moment it looks.
- Commit only the board files, with a message that states the decision and what changed; leave unrelated dirty paths (caches, backups) out of the index.
- An evidence artifact written into a directory that is gitignored but already carries tracked files needs `git add -f <path>`. A multi-path `git add a b` ABORTS the entire add when one path matches `.gitignore` — exit 1, nothing staged — while the other path looks staged in the transcript until you check. Re-read `git diff --cached --name-only` after staging and force-add the ignored artifact.
- Prove the push with the `old..new  main -> main` transcript line plus `git ls-remote` equality, then read the COMMITTED tree (`git show HEAD:<board>/tasks.jsonl`) for the rows — a clean working copy is not evidence that the rows landed.
- A board-only carrier commit triggers its own CI run only when SOME workflow's `paths:` filter covers what it touched — and that workflow is as likely to be the board-evidence gate as the product suite. Enumerate every workflow's filter against the carrier diff (see `references/ci-run-absence-diagnosis.md`) before writing the carrier's CI state. On `[]` from `gh run list --commit <carrier-sha>` with no filter covering the diff, write carrier CI ABSENT (not green) and cite the last executed run set for the nearest code-bearing ancestor. If a workflow DID run and failed, the carrier is RED and the candidate's older green says nothing about it — never present the candidate's green as the carrier's.

## 5. Before the report ships

- Re-fetch candidate, parity, tags, releases; nothing may have advanced since the evidence was gathered.
- Both rows present in the committed tree with the fresh candidate and run id.
- Carrier CI terminal and green, or the verdict says otherwise with the run id.
- Durable memory: write, then read back the exact key and confirm the content matches; mark the leg UNVERIFIED when the write or readback did not happen. Prefer the cheap structural readback — `list_keys` on the namespace with the key-family prefix — over a semantic `recall`: a `recall` that stalls is an embedding-path timeout, not a failed write, and treating it as one either loses the record or talks you into rewriting what already landed. Name the degraded leg in the report ("write-then-verified, not read-first") instead of implying a read-first pass ran.
- Delivery: `deliver_mode=link` means the tick payload is the report of record — say so, and say plainly that no separate message was posted rather than implying transport you did not perform.
