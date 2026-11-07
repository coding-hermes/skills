---
name: coding-hermes-ops
description: Use when a lane must cover OPERATIONS — containers, orchestration, metrics, alerts, supervision, backup, deploy paths — or when new work is being deployed to the fleet and its ops surface would otherwise go unwatched.
---

# coding-hermes-ops

QA asks *"does it do what it claims?"*. Ops asks *"does anything keep it running, and would we
know if it stopped?"* A project can pass every test and still ship with no health endpoint, no
metrics, no restart policy and no deploy path — and no lane ever says so, because no lane owns
that question. This skill is the owner.

**Doctrine, in one line:** derive what a project IS from evidence in its tree, then judge only the
ops surfaces that kind of project actually needs. A docs repo needs no k8s; a service needs health,
metrics, supervision and a backup path. Getting this wrong is how an ops check becomes noise.

## The lane family

`<project>-ops` — a PROMPT lane on a 24h cadence (`lane_cadence.py` owns the number). It is a
normal lane: it wakes an agent, the agent runs this skill against its project, and it files or
fixes what it finds. It is **not** a shell command lane and must never be given a
`*-scheduler-tick.sh` command (those drivers are retired; the API's `isRetiredCommand` gate
refuses them, and writing one with raw sqlite bypasses the gate and silently converts the lane
into a dead script).

One fleet-wide lane, `fleet-ops-check`, reviews the whole census every 12h in a PROMPT session —
it reads the findings, decides which are real, and files rows. It is not a command lane: the four
utility command lanes are a fixed set of deterministic fixers, and judgement does not belong in
one of those. Each project's own `-ops` lane runs the census scoped to itself.

**Identity failure changes the tick's scope, not the census's value.** Make the scheduler identity gate the first project-state gate: query the registered project endpoint, prove the registered workdir's real Git root, and check the required handbook/board before reading board contents, prior evidence contents, memory, or selecting work. If the registered root is not a Git repository, the handbook is absent, or the mapping cannot be verified, stop all board, lifecycle, dispatch, commit, push, and memory writes; emit and validate the full identity-blocked record required by the foreman skill. After failure, permitted reads are limited to the scheduler registration/API, bounded path existence/stat probes, the live-process/host probes needed to explain the block, and one fleet census captured with `--json`; do not inspect a board, prior evidence body, or ledger entry to reconstruct a refire or manufacture a row. The fleet census is still a permitted read-only observation: capture its exit code before any formatter or summarizer, and preserve the artifact path and machine-derived gap counts in the blocked record. Do not turn those observations into unfiled P1 prose or invent board rows from the non-canonical checkout; the scheduler-row/root repair is the sole unblock action. This precedence prevents useful census evidence from being discarded while preventing a stand-in or non-repository path from authorizing project state.

**But scope that gate to the checkout a WRITE lands in, not to the lane's registered root.** A
fleet-wide lane — `fleet-ops-check` above all — legitimately registers a non-Git control root: its
`workdir` is the fleet control directory that holds the scripts, evidence chains and scheduler state
for every family, precisely because it spans families instead of owning one tree. Its board,
lifecycle, commit and push writes land in the PROJECT checkout that owns the row, where
`git rev-parse --show-toplevel` succeeds and the gate passes. A pass that reads the control root,
finds no `.git`, and closes BLOCKED has refused work it could have done — and when a sibling pass
already landed that work minutes earlier, the blocked record is a false statement about the tick, not
a safety measure. Emit the identity-blocked record only when the write TARGET has no verifiable Git
root (no owning checkout, an unresolvable `repo_url`, a stand-in whose board never resolves to a
repo). When a prior pass closed BLOCKED on a control-root workdir while its own
`downstream_legs_not_run` were in fact executed by an earlier pass, supersede the record in the
addendum — do not adopt its premise, and do not re-derive the legs it claimed were impossible.

**An ops tick is a foreman tick too.** The census is the product, but the lane runs on the generic
foreman prompt with dispatch budget, so spend the remaining window on ONE board row rather than
ending at the report. Rank candidates by mechanism-clarity, not by priority alone: a P1 whose
failure message names its own cause (an empty interpolated value, a named assertion, a cited run id)
is finishable inside the tick, while a P1 that needs live-host access or a >30-minute cycle cannot
close here and should be left filed with that reason stated. **Budget the full closeout before creating a
worktree or starting a worker:** include implementation, direct gates, judge completion/readback, remote
parity, board bookkeeping, and the evidence append. If that budget does not fit, do the read-only
reconciliation and append one evidence addendum; do not start work that will strand a lifecycle record
or leave an unverified branch. A dirty checkout with a clean board may still be usable only through a
separate worktree; foreign `.gitreins/` or generated residue remains untouched, and a short budget is
a reason to defer rather than to clean it. A single-file fix whose mechanism you measured yourself may
go foreman-direct with the full lifecycle (create → start → fix → gates → `task complete` → board close
on the verdict run id → push both remotes); anything multi-file goes to a worker as usual.

**Asynchronous QA is not verified at launch.** Treat a successful `launch` as dispatch only: retain the evidence path, run `collect` until the harness reports a terminal result, and parse the evidence artifact for at least one non-launch cell plus its project binding. `RUNNING`, a launch-only file, or zero verdict cells is pending/unverified even when the wrapper exits 0; count `FAIL` and `N/A` cells separately from missing cells before recording a pass. Preserve the `.meta` binding and the exact harness digest in the audit so a resolved stand-in can be distinguished from the original target-resolution failure.

**Capture checkout state before ranking the work slot; a dirty canonical checkout is not automatically a blocker.** Run `git status --porcelain=v1 -uall` plus a live-process census for every candidate family's registered workdir. A live writer or dirty board/source paths still block writes to that canonical checkout, and a `hermes chat` launcher naming it means the row is already in flight. But when the residue is foreign or abandoned and the full implementation-to-publication budget fits, use an isolated worktree from the published branch (`git worktree add -b ops/<ROW> <path> <remote>/<branch>`), leave the canonical residue untouched, and verify the census against the registered checkout after the fix lands. Do not reject a covered P1 merely because the canonical tree is dirty; reject it when no safe isolated worktree can cover implementation, gates, judge readback, board close, push, and family-scoped census proof inside the tick budget. Record the exact residue paths, writer result, worktree path, and final registered-checkout state. The delivery recipe for a `metrics` P1 (design, gates, negative-control arms, red proofs) is `references/metrics-endpoint-delivery.md`.

**Before ranking anything dispatchable, check whether a sibling lane already owns it.** A family's
`-foreman` lane runs its own worker against the same checkout, so the P1 you just ranked can be in
flight or already landed. Two probes settle it: `git log --oneline -6` for a commit whose SUBJECT
names the row id, and a live process census (`ps -eo pid,etime,args | grep 'hermes chat'`) for a
launcher whose `--query-file` names that row's worktree or brief. Either one means the row is
another lane's tick; the correct delta is to report the commit and its CI state, not to dispatch a
second worker on the same row.

## The census

```bash
python3 ~/.hermes/scripts/fleet_ops_check.py                 # rollup + projects needing work
python3 ~/.hermes/scripts/fleet_ops_check.py --json          # machine report
python3 ~/.hermes/scripts/fleet_ops_check.py --project X     # one project family
python3 ~/.hermes/scripts/fleet_ops_check.py --alignment     # list families with no -ops lane
```

Exit 0 = clean, 1 = a runnable project has a gap. The report groups findings by check, then lists
only P1/P2 projects; a compliant project is deliberately silent.

**Read the `--json` shape before you filter it.** A per-project element is
`{family, kind, workdir, gaps[], lanes[], evidence{}}` and each gap is `{check, detail, severity}`.
There is no `.project` and no `.findings[]`, so a jq filter written against those names answers
`{"project": null, "findings": []}` — which reads exactly like a clean census. When a `--json`
probe comes back empty, print `.[0] | keys` and re-filter; an empty list from a guessed field path
is a lookup error, never evidence that the family is clean.

**`--project … --json` returns a ONE-ELEMENT ARRAY, and a pipe rebinds `.` so a second positional
index dies.** `jq -r '.[0] | {family}, (.[0].gaps[]?)'` answers `Cannot index object with number`:
after the pipe `.` is already the family object, so the second `.[0]` is wrong. Write the filter as
`jq -r '.[0] | "gaps=\(.gaps|length)", (.gaps[] | "  [\(.severity)] \(.check)")'`, or bind
`. as $f` once and use `$f.gaps` throughout. A `keys` answer of `[0]` confirms the array shape —
read the filter before concluding the family has no gaps.

**The text renderer is LOSSY — never quote a count you grepped out of it.** It drops per-family
P2 lines, so a `grep -oE '\[[a-z-]+\]'` tally over stdout undercounts (`deploy-doc` read 28 when
the same run's JSON said 35) and can miss a check class (`lane-ops`) entirely. Every number that
enters an evidence file, a board row or the report comes from `--json`, and when a text-parsed
tally disagrees with the artifact, the TALLY is wrong — say so and correct it, never leave the
text number standing beside a JSON one. The two commands that produce the whole rollup:

```bash
python3 ~/.hermes/scripts/fleet_ops_check.py --json > $S/census.json   # capture once, then query
jq -r '[.[]|select((.gaps|length)>0)]|length' $S/census.json           # families with any gap
jq -r '[.[].gaps[].check]|group_by(.)|map("\(.[0]) \(length)")|.[]' $S/census.json   # per-check tally
```

**Re-prove a fleet of filed rows against their REMOTE blobs in one run** with
`scripts/verify_board_rows_remote.sh <spec-file>`, where each line is
`repo|remote|branch|row-id`: it prints HEAD, ahead/behind and the row's status read from
`git show <remote>/<branch>:<board>/tasks.jsonl`. Use it before concluding a P1 is "already covered" —
a row's note and its on-disk copy are claims; the published blob is the state. A repo that publishes
over a non-default remote (`github`, a GitLab mirror as `origin`) goes in the spec with THAT remote,
and a divergence there is a finding about the mirror, not about the row. **Resolve the BRANCH as
well as the remote before any blob read:** `origin/main` is not universal (fleet families publish on
`master`, and some name their remote `github`), so a guessed ref answers `fatal: path … does not
exist` and a `grep -c <row-id>` over that output reads **0 — which looks exactly like an un filed
row**. Print `symbolic-ref --short HEAD` and `remote -v` for the family first, then read
`<remote>/<branch>`; a per-family `ABSENT` verdict gathered on a guessed ref is an instrument error
and must be re-probed before it enters a report or a duplicate row.

**Read the `kind` column before believing any finding.** Kinds are derived, not declared:

| kind | derived from | judged on |
|---|---|---|
| `service` | container/orchestration files, or a server entrypoint in the source | health, metrics, container, supervision, scheduling, backup, deploy doc |
| `cli` | `go.mod` + `cmd/`, or an executable package | deploy/install doc, release path |
| `library` | a package manifest and no entrypoint | deploy doc, CI |
| `docs` | no build manifest | nothing — correct for a spec corpus, a FALSE NEGATIVE for a shell toolkit (below) |
| `unresolved` | workdir does not exist | the workdir itself |

**Stand-in workdirs are the number-one false negative.** A lane row's `workdir` is often a board
holder under `~/.hermes/stand-in/` while the real repo is named by `repo_url` as `local:/path`.
The scanner resolves `repo_url` first for exactly this reason; if you write your own probe, do the
same or you will classify ten running services as docs and report them clean.

**But verify the pointer lands on a Git root before believing it.** A lane's own `repo_url` can
ITSELF be a stand-in path (`local:~/.hermes/stand-in/<role>/<project>`), so resolve-first reads a
non-repo holder and the family's real checkout is reachable only through the `-foreman` row's
`workdir` and the `.coding-hermes/board` symlink target. Probe
`git -C <repo_url-path> rev-parse --show-toplevel` (plus `readlink -f <standin>/.coding-hermes/board`)
and, when that fails, take the `-foreman` row's workdir as the registered root, run the identity gate
there, and record both paths in the receipt. A `docs`/`unresolved` verdict on a family whose own
stored `repo_url` is the stand-in is the resolve-first rule misfiring, not a clean census.

**The other false negative is the shell toolkit.** `docs` is derived purely from the absence of a
language manifest (`go.mod`, `package.json`, `pyproject.toml`, `setup.py`, `Cargo.toml`,
`requirements.txt`), so a repo that ships only `scripts/*.sh` — a node provisioner, an installer, an
operator CLI — classifies as `docs` and is judged on NOTHING, not even the deploy doc it usually
already has. Before accepting a clean `docs` verdict, count the family's scripts: two or more
executable `*.sh` under `scripts/`/`bin/` (or a `tests/selftest.sh` gate) means it is a toolkit and
its whole operational surface is unwatched.

**That hole is closed in the shipped classifier — check for the fix before re-filing the class.**
`classify()` derives a shell toolkit: at least two TRACKED `*.sh` under `scripts/` or `bin/` (depth
≤3), or a `tests/selftest.sh` gate, returns `cli` with `evidence.kind_basis = 'shell-toolkit:<n>'`
naming the script count. So a manifest-less repo that still reads `docs` while shipping scripts means
the LIVE script lost the patch — re-apply `patches/fleet-ops-shell-toolkit.patch` from the
code-factory repo (the versioned copy of an unversioned file) instead of minting a second P2 for the
same class. Read `kind_basis` beside `kind`: it is the basis the verdict was derived from. Probe,
from the repository root:

```bash
python3 ~/.hermes/scripts/fleet_ops_check.py --project <family> --json | jq -r '.[0].kind'
find <workdir>/scripts <workdir>/bin -maxdepth 2 -name '*.sh' -type f | wc -l
```

**The third is `library` on a repo whose services are standalone scripts.** A Python package
manifest plus no `cmd/` classifies as `library`, so a project that runs three long-lived units from
`scripts/<name>_server.py`-style entrypoints is judged only on deploy-doc/CI while its health,
metrics and supervision go unwatched. Never accept a `library` verdict without asking what the host
is actually running from that tree — the listeners are the ground truth, not the manifest:

```bash
ss -ltnp 2>/dev/null | grep -E ':(9092|9093|9391) '          # who is up, and from which pid
for p in $(pgrep -f '<workdir>/scripts/'); do tr '\0' ' ' < /proc/$p/cmdline; echo; done
```

A listener whose `/proc/<pid>/cmdline` names the repo's own script disproves `library`; file the
kind-detection P2 with the pid/cmdline evidence and, until it is fixed, judge the family on the
`service` row set by hand — a clean rc=0 on a family with live listeners is the same lie as a
`docs` pass on a toolkit.

Census the class fleet-wide (the same `--json` run over every family) before filing: it is ONE
classifier hole with many victims, so the row quotes how many families sit in it — including the
scanner's own family when its workdir holds the scripts.

### Editing the census (or any unversioned fleet script) without losing history

`~/.hermes/scripts/` is not a git repository, so an in-place fix there has no history and no rollback.
A live script is still fixable — it just has to be made auditable in the same tick:

1. Prove no live writer before editing: `ps -eo pid,etime,args | grep '<script>' | grep -v grep`
   empty, plus the file's mtime. A script modified minutes before your tick is a concurrent writer —
   file the row instead of editing.
2. **Ship the pristine base INSIDE the repo — a patch whose target exists in no commit is inert.**
   Keep the tick-scratch copy for the diff, but also commit it as `patches/base/<file>.orig` and
   name that path in the patch header. A `--- a/<file>` header pointing at a filename that exists
   nowhere makes the patch's own acceptance probe (`git apply --check`) exit 1 forever and leaves an
   unversioned fix with no reproduction artifact at all — a reader cannot apply it, a judge cannot
   grade it, and the next tick re-files the same class. Use the `.orig` suffix, never `.py`: a guard
   lint lane grades staged `.py` (`ruff check --force-exclude` plus `ruff format --check`) and would
   grade a pristine input as tree source.
3. Make the edit, then capture it in a versioned repo with headers naming that base:
   `diff -u --label a/patches/base/<file>.orig --label b/patches/base/<file>.orig <pristine> <live>
   > <repo>/patches/<name>.patch`. From the repository root `git apply --check patches/<name>.patch`
   must exit 0 — that is the row's own reproduction probe, and it can only run against a base that
   exists at HEAD.
4. Prove the patch BOTH ways and quote both results: forward onto the pristine copy in a temp dir
   (`git apply --check`), and — durably, since it keeps working after the edit — reverse onto the
   LIVE patched file (`cd <script dir> && git apply --check --reverse <patch>`), which succeeds only
   when the live file equals the patched version.
5. **Ship the chain, not just the newest diff, plus a drift gate that grades it.** Patches
   accumulate, one per change, so record the module's sha256 after EVERY stage in a machine-readable
   `patches/<chain>.sha256` (stage, patch, digest) and commit a `scripts/verify-patch.sh` that
   rebuilds the chain in a scratch tree and compares the FINAL stage with the live file. Five rules
   make that gate insurance rather than theatre:
   - **Grade every stage, not only the end.** A per-stage digest is what catches a patch that
     "applied" with fuzzy context and silently produced the wrong module.
   - **Compare the chain's LAST stage with live, never one patch's output with live** — once a second
     patch lands on the same file, the older patch's output can never equal the live file and the
     gate reds on a healthy tree.
   - **Carry each stage's output into the next patch's own target path.** Patches written at
     different times name different paths (the bare filename vs `patches/base/<file>.orig`): copy
     the previous result to the path each header names, apply there, then digest.
   - **Print named rows and exit nonzero**: `PASS`/`FAIL`/`SKIP` per arm, both digests on a FAIL, and
     a `SKIP` arm for a checkout with no live script so the chain still verifies off-fleet.
   - **The gate is READ-ONLY on the live file.** Prove it by quoting the live sha256 before and after
     the failing arm, and take the negative control as `argv[1]` (a byte-appended copy) rather than
     mutating the live script.
   **Recover a missing base by reverse-applying the chain from the live file, then CHECK the result
   against digests already recorded in the tree** (the previous patch's own `Pristine:` header, a QA
   event's cited digest). A reconstruction that reproduces two pre-existing records is checked; one
   that only round-trips its own arithmetic is not.
5. Ship the regression arms next to the patch (`<repo>/patches/<name>.test.py`, target path as
   `argv[1]` defaulting to the live script). A repo whose gate cannot import a file outside the tree
   has nowhere else to put them, and the arms are what keep a silent regression from reading as a
   clean census. Three mechanics decide whether the harness is insurance or theatre:
   - **Save the pristine copy with a `.py` suffix before the arms load it.**
     `importlib.util.spec_from_file_location` returns a spec with `loader=None` for a suffix it does
     not recognise, so a diff base named `<script>.py.pristine` aborts the harness with `'NoneType'
     object has no attribute 'loader'` before the first arm runs — which reads as a broken harness,
     not as a red proof. Copy it to `<scratch>/pristine_module.py`.
   - **Run the arms against the PRISTINE copy FIRST and quote the failing arm names.** A harness
     that also passes on the pre-fix file proves nothing. The honest shape is `pre-fix N/M`
     (`failing A/C/D`) then `post-fix M/M`, with one arm that must stay green on both (the original
     behaviour) and one negative control that must still report the defect when it is present —
     that control is what makes the post-fix green mean "fixed" rather than "silenced".
   - **Format the arm file with the repo's own formatter before staging it.** A guard running
     `ruff format --check` / `gofmt` / `black` refuses the WHOLE commit on the new file alone, and
     the message names the formatter, not your change. Run the repo's format command on the file,
     then re-run the arms, because reformatting can move code across a line boundary.
6. Quote BOTH census numbers, and check they moved in the right proportion. `check==<key>` gaps
   before → after, plus the P1/P2 family count, which must NOT move when the retired findings were
   P3. A fix that also drops a P1/P2 family count silently removed real coverage.
7. Run the gitreins lifecycle from the REPO that holds the patch, not from the script's home.
   `gitreins task complete` grades the tree at its cwd, so a task created under the unversioned
   script's directory answers `tier1 FAIL (DEGRADED — no language detected)` and an overall FAIL
   even when tier2 PASSes on the merits. Either create and complete inside the repo, or say plainly
   in the report that tier1 graded an empty tree and that the authoritative gate is the commit-time
   guard log — never let a DEGRADED tier1 read as a red verdict on the work.

**Verify the fix from the CANONICAL checkout, not from whichever worktree your cwd lands in.**
A family often has several worktrees (a board-lane tree, a per-task `proj-wt-*` tree) on different
branches, and only the registered checkout is at parity with the remote; a patch commit is absent
from every other one by design, so probing the wrong tree reports "the fix was never pushed" about
a fix that is green on the remote. Resolve the registered root (`scheduler.db` `workdir`/`repo_url`
for the family's `-foreman` row), then prove the artifacts are in the REMOTE TREE:
`git -C <repo> fetch -q <remote>; git rev-list --count <remote>/main..HEAD` = 0 and
`git ls-tree -r --name-only <remote>/main | grep '<patch-or-test-name>'`. Disk presence is not
publication; the remote blob is.

**A pending tool row can describe a fix that is already LIVE — prove it before re-filing the class.**
An unversioned script's fix leaves its row pending while the behaviour has already changed, so the next
census re-derives the same class from a patched build and files it again. `cd <script dir> && git apply
--check --reverse <repo>/patches/<name>.patch` exits 0 exactly when the live file equals the patched
build; cross-check the live sha256 against the sha256 pair recorded in the row's note. When both agree,
the tick's job is the CLOSE — row status, the sha256 pair, and the measured before/after counts — plus
whatever residual the patched build still reports. Independently confirm the residual with a fresh
census run rather than trusting the row's own claim about what remains. The strongest close-out arm
is the census re-run scoped to the family that TRIGGERED the check: the patched build must report
the gap GONE for that family while the survivors you already refuted stay reported. A fleet-wide
before/after count proves the tool changed; the family-scoped run proves the change reached the
failure you were actually fixing.

### Closing the fix's row is its own two-part job

`boardctl update <id> --status complete` accepts `--guard/--ci/--completed-at` but only stores what
it is given on a pass it recognises: a first update that carries the evidence run can land
`status`/`commit_hash`/`detail.evidence` while `completed_at` stays null (re-read the row and look
for `guard_result`/`ci_result`/`completed_at` BY THOSE NAMES — `guard`/`ci` read null either way).
**A completion with no `--evidence-run-id` is REFUSED outright** — the gate wants the verdict's
history DIRECTORY name (`.gitreins/history/<date>/<dir>/`), not the verdict hash the CLI printed and
not the commit sha. Run the update UNPIPED: a refused close prints its reason and exits nonzero, so
`boardctl … | tail -3; echo rc=$?` reports `tail`'s status and turns a refused close into a
successful-looking report.

**Treat a successful `boardctl update` as a local mutation, not publication.** Read the updated row from the local board immediately, then resolve the repository's actual publishing remote and branch and read that exact blob with `git show <remote>/<branch>:<board>/tasks.jsonl`; if the remote blob is unchanged, label the result local-only and do not say the row was filed, annotated, or closed. A fleet-wide lane may legitimately write a project board locally, but it must either publish through the owning checkout's normal commit path or explicitly leave the local change for the owner; a tool exit of 0 is not remote-state evidence.

Where the completed timestamp names the verdict's `evaluated_at`, issue a second update with
`--completed-at` and the same evidence args rather than leaving a date no reader can trust.
**A completion can land with its EVENT missing, and boardctl says so in the same line.**
`boardctl update … --status complete` answering `task row updated but task_completed event failed:
<board>/events.jsonl: line N: unexpected EOF` (exit 1) means the ROW is written and the event
append died on a truncated line that was already in the committed blob. Do not re-derive the close
and do not revert the row: prove the corruption is pre-existing (`git show
HEAD:<board>/events.jsonl | sha256sum` equals the disk digest captured before your write), repair
that ONE line by preserving its recovered payload verbatim inside an `audit` event that carries the
id the line had plus a repair note, prove line count unchanged and whole-file `jq -c '.id'` parses,
then re-run the SAME update — it appends the event and adds a second `detail.evidence` entry for the
same run id, which is harmless bookkeeping rather than a double close. Build the replacement line
with `jq -cn --rawfile <file> …` (a `printf`-assembled JSON line mangles backslashes); `jq -Rs`
appends a newline that silently adds a line to the file — use `-j`.
In a checkout shared with other lanes, the ROW line can ride into a sibling's board commit while
the `task_completed` events stay unstaged — verify with
`git show <tip>:<board>/tasks.jsonl | jq 'select(.id=="<ID>")'` and then commit the events
file on its own, because two dirty board files re-arm the ownership barrier for every lane.
**Put the rich measured detail in ONE `audit` event, never a second `task_completed`.** `update
--status complete` already appends its own minimal `task_completed`, so a second completion event
for the same id is a duplicate closure no later reader can tell from a double close, while the arms
that make the close auditable (before/after digests, both gate arms, the verdict binding, what was
deliberately left untouched) belong in an `audit` event whose `--task-id` names the row. Stage the
detail JSON to a file and pass `--detail @<file>`; the event-type vocabulary is closed, so a
plausible-sounding type is rejected and appends nothing.

## Checks and severities

| check | severity | meaning |
|---|---|---|
| `metrics` | P1 | a service with no prometheus/otel/statsd instrumentation: it can fail invisibly |
| `health` | P1 | no readiness/liveness surface in the entrypoint |
| `backup` | P1 | the project OWNS a datastore (migrations, schema, a db file) with no backup/restore path |
| `container` | P2 | a service with no Dockerfile/compose |
| `supervision` | P2 | no systemd unit, no deploy dir — restart policy undefined |
| `scheduling` | P2 | neither an orchestrator nor a supervisor: nothing restarts it |
| `deploy-doc` | P2/P3 | no DEPLOY/RUNBOOK/OPERATIONS doc — the deploy path is tribal; matched case-insensitively, so `docs/OPERATIONS.md` counts (a `deploy-doc` gap on a repo that HAS the doc means the live script predates the `exists_ci` fix) |
| `ci` | P3 | no CI pipeline in the repo — a PROVIDER matcher, not a pipeline detector: `.github` plus the `.gitlab-ci.yml` / `Jenkinsfile` / `.circleci` / azure / bitbucket / drone / travis / cloudbuild markers. Verify the provider before believing it |
| `lane-ops` | P3 | the family has no `-ops` lane (rolled up fleet-wide, never listed per project). Circular for the fleet's OWN watcher lanes (`fleet-ops-check`, `lane-cadence-check`, `lane-repair`) — refute those, they are the watchers |

A datastore is `migrations/`, `schema.sql`, `init.sql`, or an actual `*.db`/`*.duckdb` file. A
postgres *client* import is not a datastore — a service that talks to someone else's database has
nothing of its own to back up. Do not "fix" a `backup` finding by adding a backup script for data
the project does not own; correct the classification instead.

## Reconciling census findings before you file

The census is a lead generator, not a verdict list — every finding is a heuristic over the tree.
Classify each one before it becomes a board row, because a phantom P1 buries the real one and
comes back on every tick.

**Two runs of the SAME command that disagree are an INSTRUMENT question before they are a repo
question.** `~/.hermes/scripts/fleet_ops_check.py` is a live, unversioned file that sibling lanes
rewrite, so a finding that disappears between two runs minutes apart — while the tree gained no
doc or code commit that could have closed it — is that edit, not a fix. `stat -c '%y'
~/.hermes/scripts/fleet_ops_check.py` and compare its mtime against both run times before
attributing the delta to the project, then quote BOTH numbers with the instrument version named.
Do not present that pair as a before/after regression measurement: the instrument changed, so
only the family-scoped refutation is a claim you can stand behind. Close the identity arm with a
DIGEST, not just an mtime: `sha256sum ~/.hermes/scripts/fleet_ops_check.py` against the last stage
recorded in the owning repo's `patches/<chain>.sha256` (read it from the repo that ships the patch
chain, not from the live file). A match names exactly which build produced both numbers; a mismatch
means the live script carries an edit no patch chain explains. A large class-level drop (one check
falling by tens of findings while the P1 classes hold steady) is the signature of a matcher
widening, and the patch's own commit subject names the class it fixed — quote that commit beside
the before/after counts instead of crediting fleet work.

- **`backup` is the known false-positive class.** `owns_store` matches `migrations`, `schema.sql`
  and `init.sql` as a path component ANYWHERE under the root, so it fires on
  `.coding-hermes/board/schema.sql` — the foreman board's own schema — for every project that has
  a board. The canonical board is git-tracked JSONL, so there is nothing to back up.  Prove the hit (locate the path with `search_files (target='files')`, then `git ls-files <path>`),
  then refute the finding in the report and in any row
  you file. Never "fix" it by writing a backup script for data the project does not own.
  **Measured scale, and the second mechanism behind the same check.** A per-family
  re-implementation of the census's own `owns_store` / `BACKUP` expressions over a whole
  fleet found `check=backup` on 26 of 88 families, of which 15 fired ONLY on
  `.coding-hermes/board/schema.sql` (or `.gitreins/state.db`) and 10 more owned a real
  migration set yet already shipped a backup/restore artifact that `rel_hits` cannot see:
  it matches whole path COMPONENTS, so `docs/backup-set.md`, `docs/runbooks/backup-restore.md`
  and `scripts/backup-db.sh` never equal `backup`, `restore` or `snapshot`. So "refuted" needs
  BOTH arms measured per victim — the trigger path (`jq` the family's census row, then walk it)
  and the miss (does a backup-ish artifact exist under a name the matcher drops?) — otherwise
  the refutation is a guess that the next tick re-derives. Count the victims fleet-wide before
  filing and file the class ONCE on the board that owns the tool, with negative controls (a
  genuine store must still report; a real store beside the board schema must still report) so a
  later fix cannot silence the check. **`deploy-doc` is narrow in the same way:** its seven
  accepted filenames exclude `README.md`, so a repo whose Prerequisites/Install section plus
  `docs/release-checklist.md` carry the whole deploy path still reports "the deploy path is
  tribal". Read the README before believing that sentence; refute it and describe it as a
  naming gap, not a tribal path.
  **The same matcher also misses the `INSTALL.md` / `SETUP.md` spelling**, which is the commonest
  name for a real deployment guide — probe `git ls-files | grep -iE '^(INSTALL|SETUP)'` plus
  `docs/` equivalents before filing, and check the shipped supervisor: a systemd unit whose
  `Documentation=` points at that file, or a Makefile `install:` target that quotes it, proves it
  is the deploy doc and nothing else needs to exist. Deliver the fix as an artifact under a name
  the matcher RECOGNIZES (`docs/operations.md`) rather than as a third refutation: one file then
  closes the real backup/runbook gap and retires the false flag for every later tick. Count the
  victims fleet-wide before editing the shared matcher — filter the full `--json` census for
  `deploy-doc` gaps and test each workdir for an unnamed deploy doc; a single victim is a
  refutation to record in the row, not a reason to touch a script every family depends on.
  **When the victim count justifies the fix, the matcher must key on the DIRECTORY as well as the
  basename.** `deploy/README.md` carries its whole convention in the `deploy/` component while the
  basename says nothing, so a widening that only adds basename hints (`runbook`, `install`, `setup`)
  still flags the fleet's commonest shape — the fix's own arm A stayed red after the first pass until
  the walk also accepted a doc sitting inside a deploy directory. Depth-limit that walk (root plus
  the next two levels) and prune build output and harness dirs, then keep BOTH negative controls in
  the arms: a tree with no deploy artifact at all must stay flagged, and a doc buried past the depth
  limit or under `dist/` must stay flagged. Without those two the widening trades a false positive
  for a false negative, which is worse — a silenced gap never reports again.
- **After the harness-dir and basename arms are fixed, `backup` and `metrics` still keep three
  residual false-positive shapes.** Verify each with the evidence named before filing anything:
  (1) a **mock/fixture store** — a `migrations/` under a package whose own manifest calls itself a
  mock database, and whose only importers are demo or test code, is test support, not an owned
  datastore; (2) a **derived store** — a database an export/seed script rebuilds from a git-committed
  corpus is a cache, and the corpus is the durable artifact, so there is nothing to back up;
  (3) a **CLI sampler classified as `service`** because it ships a unit file and an opt-in pprof
  listener — when the tool's own OUTPUT is the metric feed, a `/metrics` endpoint is not the gap, and
  the family's existing observability row already owns the real residue. A surviving hit of any of
  these shapes is the tool's residual class: file it ONCE on the board that owns the census script
  with negative controls (a genuine store still reports; a real store beside the mock still reports),
  not as a fresh P1 per family.
- **`ci` is a PROVIDER assumption, and the confident negative is the expensive error.** The check is
  a matcher, not a pipeline detector: it hits a `.github` directory, so a repo whose whole build
  lives in `.gitlab-ci.yml` reports "no CI pipeline — nothing gates a merge" on every tick, forever,
  and no amount of work closes it because the pipeline already runs. Probe the providers before
  filing: `git ls-files | grep -iE '^(\.github/|\.gitlab-ci\.yml|Jenkinsfile|azure-pipelines\.yml|bitbucket-pipelines\.yml|\.circleci/|\.drone\.yml|\.travis\.yml|cloudbuild\.yaml)'` —
  a hit refutes the finding, and the correct CI-health line is "CI exists on <provider>, GitHub
  Actions not used", never "unverified". **`gh run list --repo <slug>` returning `[]` proves only
  that GitHub Actions has no runs there**; it is not evidence of missing CI. Derive the slug from
  `git remote -v` and the workdir from the census `--json` row's `.workdir` — a path reconstructed
  from the family name is frequently not a Git root (`git rev-parse --show-toplevel` fails), and
  every probe after that silently answers about a directory that does not exist. Count the victims
  fleet-wide before filing: one shared matcher with many victims is ONE row on the board that owns
  the census script, with negative controls (a marker-less tree must still report), not a P3 per
  family.
- **A `*.db` in the repo root is not a datastore until a reader proves it.** Root-level
  `memory.db` / `dev.db` / `tasks.db` are often gitignored dev residue: `grep -rn '<name>'
  <source dirs>` returning zero hits plus `git check-ignore <path>` proves it. The action is then
  "delete the residue and note it in the ops doc", not "add a backup path".
- **A refuted in-tree hit can still hide a real store OUTSIDE the tree.** A CLI/service that opens its
  store at a resolved home path (`$<TOOL>_DB_PATH`, `<hermes home>/<project>/<store>.db`) leaves only
  residue in the checkout, so refuting every in-tree `*.db` answers the census and not the question.
  After the refutation, follow the documented default store path and check it for a paired
  `-wal`/`-shm` (proof it is live) plus a backup/restore path in the repo (`git ls-files | grep -iE
  'backup|restore'`). An unbacked live store is a genuine gap even when every census hit was a false
  positive — report it against the real path, and say which hits you refuted and why.
- **A finding the project's kind cannot action is a refutation.** `container` on a PyPI/CLI
  deliverable, and `supervision`/`scheduling` on a viewer nobody deploys, would have the lane ask
  for a Dockerfile on a library. Refute them in the reconciliation and point at the row that owns
  the real decision. `container` is likewise refuted for a service the host runs from a shipped
  systemd unit set (`deploy/*.service`, `deploy/*.timer`): that IS the deploy and supervision shape,
  and containerising a single static binary is a design change, not a gap. **The same reasoning runs
  the other way for a compose deploy:** a repo shipping `docker-compose.yml` with
  `restart: unless-stopped` and a `Dockerfile` `HEALTHCHECK` HAS supervision and scheduling — Docker is
  the supervisor and the orchestrator — so `supervision` and `scheduling` are refutations there even
  though the matcher (which looks for systemd units or a `deploy/` dir) keeps reporting them. Adding a
  systemd unit beside a compose deploy would double-supervise one process, so refute rather than fix,
  and put the refutation in the audit event so the next census does not re-file it as work. Record that refutation in
  the tick's evidence file AND as an audit event on the family's board row, because an unrecorded
  refutation returns as a phantom row the moment the next census prints the same gap. **When an
  ownership barrier covers the board leg, the evidence-file addendum IS that record:** write the
  trigger path, the measurement and the reason there, and name the board audit event as deferred.
  Satisfying this sentence by mutating the board during a barrier trades a phantom row for a broken
  ownership claim, and dropping the record altogether loses the refutation — both are failures.
  **The doc that clears `deploy-doc` does NOT clear `backup` — deliver the script too.**
  `docs/operations.md` is a recognized DEPLOY_DOC spelling, so writing the operations page
  retires that finding, but `backup_hits()` looks for a `backup|restore|snapshot` path
  COMPONENT or a basename carrying one of those words with a `.md/.sh/.py/.yaml/.yml`
  extension. A section headed "Backup" inside `docs/operations.md` still reads as no backup
  path, and the census keeps reporting P1 after the doc lands. Close both arms in one
  change: the doc for the procedure, and a real `scripts/backup-db.sh` (basename `backup`)
  that dumps and self-verifies — for example a `--drill` arm that restores the dump into a
  throwaway database and compares table counts — so the census stops flagging a genuine,
  now-closed gap rather than a renamed one. Never clear it by renaming a file.
  Delivery recipe for a `backup` P1 — the three arms a dump script needs, how to prove a real
  restore, the negative control that needs no destructive command, and dump/restore version skew:
  `references/backup-restore-delivery.md`.
- **A P1 row is only executable if its cited authority is committed.** When a row names a spec or
  doc section as design authority, run `git ls-files <doc>` first: an UNTRACKED design authority
  is itself the finding — land it in its own commit inside the same tick, or the row cannot be run
  once the working tree is cleaned.
- **A doc that defers work to a board row must be checked against that row's STATUS, not just its existence.** A fix's own doc routinely ends with "the residual is tracked on the board as <ROW>", and closing that row is what turns the sentence into an orphan: `docs/operations.md` §6 deferred the missing scheduled drill job to a row that was already `complete`, so the durable half of a P1 had no owner while the doc read as if it did. Grep the residual sentences the fix introduces for row ids, resolve each id in the committed board blob, and when it is closed, file the residual under its own id and rewrite the sentence in the same tick — a close-out check, not a later audit.
- **File one row per genuine gap**, with acceptance criteria the next tick can execute verbatim
  (a path that must exist, a `grep -c` with its expected count, a deletion that must report
  "No such file").
- **File only into a checkout no live lane is writing, and read the board before you commit it.** Two
  arms decide it: `git status --porcelain -- .coding-hermes/board/tasks.jsonl`, and a process census
  for the workdir (`ps -eo pid,etime,args | grep -F 'cd -- <repo>'`). Dirty board plus a LIVE writer
  means skip that repo this tick. Dirty board plus an abandoned writer means append and commit the
  file WHOLE, naming in the commit message every row id you did not author — otherwise a sibling's
  uncommitted rows ride inside your commit and your message claims work you did not do. Check the
  process census again right before you write: a sibling lane can spawn and start committing minutes
  after your opening probe.
- **A board push conflict is resolved by ID-UNION, never by taking one side.** A rebase over a moved
  remote tip conflicts on the JSONL tail, and `--ours`/`--theirs` silently drops either the remote's
  newer rows or yours. Merge by id — upstream lines first, then only the lines whose id upstream lacks,
  copied byte-for-byte — and normalize ids with `str()`, because boards carry integer ids, string ids
  and rows with no id at all in the same file. Full recipe: `git-tracked-jsonl-editing`.

## Stand-in workdirs: resolve the real root, never "repair" the lane

An ops/pm lane's `workdir` is often `~/.hermes/stand-in/<role>/<project>` — not a git root, so the
foreman identity gate fails there by design. Resolve instead of standing down:
`readlink -f <standin>/.coding-hermes/board` usually names `<real-repo>/.coding-hermes/board`, and
the family's `-foreman` row in `scheduler.db` carries the registered `workdir`/`repo_url`. **Prove
the pointer is the same FILE, not merely a resolvable link:** a stand-in board is routinely a bind
mount or a hardlink of the repo's board rather than a symlink, so `readlink -f` just echoes the path
you passed and proves nothing. Compare inodes —
`stat -c '%i %n' <standin>/.coding-hermes/board/tasks.jsonl <repo>/.coding-hermes/board/tasks.jsonl`
— because equal inodes are the mechanism behind the coupling you will hit later: a write through the
stand-in path dirties the repo checkout, and a sibling lane committing there is committing the very
file you just read. Run the
identity gate at that registered root, record both paths in the receipt, and leave the lane row
alone — a stand-in that mirrors a sibling role is a convention, not a defect, and
`fleet_lane_align.py` repairs cadence/command only (it will not re-point `repo_url`/`workdir` on
an existing lane, so a hand edit would be the only way and is not worth it).

**But measure the board before you call such a lane healthy.** Stand-in directories are created per
LANE, and most of them never get a board of their own: count `.coding-hermes` directories under
`~/.hermes/stand-in` against `tasks.jsonl` files inside them and the ratio is roughly 7:1 boardless
(377 directories, 53 boards on a mature fleet). A lane whose workdir holds no board is **board-blind**:
the scheduler's pending count at that path reads nothing, so admission cannot gate on work and the lane
fires on the clock forever. Grep the scheduler journal for `board-unreadable` before believing a family
is idle rather than merely unreadable, and treat a board-blind lane that still commits as productive by
accident, not by design.

The same directory also makes the lane **context-blind**: relative paths, `git`, and AGENTS.md/specs
discovery all resolve inside the scratch dir, so the lane only finds its project because the prompt
spells the absolute path out. Cost is real too — 6-7 GB and 150k+ files accumulate there.

The sanctioned forward shape (needs an owner decision, not an ops tick): give every lane the family
repo as its workdir, or a PERSISTENT per-lane worktree (`proj-wt-<project>-<role>` on branch
`lane/<project>/<role>`) refreshed before each tick, with evidence under
`.coding-hermes/evidence/<lane>/`. Persistent, not ephemeral per tick: a fresh worktree inherits no
gitignored files (`.venv`, `node_modules`, build caches), so an ephemeral tree repays the dependency
install on every tick — which is how a "clean isolation" change saturates the host it was meant to
protect.

## Deploying new work to the fleet

Adding a service to the fleet has an ops half that is easy to skip. Do it in this order — the
runbook with the exact commands and pitfalls is `references/fleet-deploy-and-alignment.md`:

1. **Lane family.** `fleet_lane_align.py --project <name> --roles ops` creates or repairs the
   lane from the canonical table. Never hand-write a cooldown.
2. **Both stores.** `fleet_toml_sync.py` appends the block to `fleet.toml`. The daemon re-pins
   from that file on restart, so a lane that exists only in `scheduler.db` loses its cadence at
   the next restart, and a lane that exists only in the file does not run at all.
3. **Cadence.** `lane_cadence.py check` must pass. If the family genuinely needs a different pin,
   change it in the table once — not in the creator, not in the DB by hand.
4. **Ops surface.** Run the census for the project and file the P1s as board rows with acceptance
   criteria; do not leave them as prose in a report.
5. **Prove it live.** A deploy is not done when the process starts. Health answers, a metric
   moves, a log line lands, and the thing restarts after a kill — see
   `references/observability-minimums.md`.
6. **The durability job is part of the fix, and it is proven by FIRING it, not by listing it.**
   A bound/alert that a P1 row demands (`a scheduled job trims X and fails loudly below Y`) is not
   landed until a job exists AND has run: `cronjob_manage action=run <job_id>` right after
   `action=create` returns `executed=true` with `execution_success`/`last_status`, which is the only
   cheap proof that the scheduler can actually execute the script — a job that has never fired reads
   identical to a working one in `jobs.json`. **Do not read `cronjob_manage action=list` inline:** it
   returns the whole fleet inventory (hundreds of jobs, ~180 KB) and spills to a file, so locate the
   job with one bounded read of that artifact — `grep -n -A14 '<job_id>' <spillover-path>` — and
   quote its `last_run_at`/`last_status`/`script` fields from there. Re-listing to "check again"
   re-buys the same 180 KB; a `sed -n '<line>,<line+14>p'` on the saved file is the cheap re-check. Author alarm-shaped scripts to the watchdog contract:
   silent (empty stdout) when healthy so nothing is delivered, a single alert line plus a non-zero
   exit when the threshold is crossed, and idempotent by construction (a second consecutive run
   changes nothing and stays silent) — then run it twice by hand and quote both return codes. State
   in the row which surface carries the alert: delivery target, log path, and the exit code that the
   cron engine turns into a failure record. When an isolated arm of that script cannot be exercised
   on the unattended surface, mark THAT arm unproven in the row and the report rather than calling
   the durability job done.
7. **Watch it.** An `-ops` lane exists from that moment, so the surfaces are re-checked on a
   cadence instead of being checked once by a human who then forgets.

## Container and orchestration work

`references/containers-and-orchestration.md` covers the docker/k8s specifics: healthcheck vs
readiness, resource limits, restart policy choices, why a compose file without `restart:` is a
P2, and the fleet rule that a containerised lane must not depend on host state it cannot see.

## A clean census is not an uptime check

The census judges ARTIFACTS in the tree. It never asks whether the family's own lanes are running,
so a family can score rc=0 while every lane is dark — and an ops lane that stops at the rollup has
answered the wrong question. Add the uptime leg after the census, every tick:

- **An `-ops` lane that EXISTS but is dark is coverage-absent, and `--alignment` cannot see it.** The
  alignment check only asks whether the lane row exists; it never reads `enabled` or
  `last_tick_completed`. Read all of them in one query before calling a family covered or unwatched:

  ```bash
  sqlite3 -header -column ~/.hermes/coding-hermes/scheduler.db "select p.name, p.enabled,
    coalesce(p.disabled_by,'-') by, coalesce(p.disabled_reason,'-') reason,
    coalesce(p.last_tick_completed,'NEVER') last_ok, p.disabled_at
    from projects p where p.name like '<family>-ops'"
  ```

  A family whose `-ops` lane is `enabled=0` — or `enabled=1` with `last_tick_completed` NULL — has no
  per-family ops coverage whatever the alignment output says, and its census P1s accumulate tick after
  tick because nobody files them. Those rows are THIS lane's to file; they are not a duplicate of a
  lane that is merely paused.
- **A fleet-wide standby is an owner action, and an ops tick does not lift it.** When many `-ops`
  lanes share one `disabled_at` and one `disabled_reason` (a stand-down while the host is focused on
  something else), that is a recorded decision: report it as the CAUSAL finding — how many lanes, the
  shared instant, the shared reason, and how many have never completed a tick — then file the P1 rows
  yourself for the families whose lane cannot. Re-enabling the family is an owner decision, and
  flipping `enabled` straight in the DB is the same defect this skill forbids for lane creation.
- **Per-lane last-ok and failure class**, from the scheduler: one single-project GET per lane
  (`/api/v1/projects/<lane>`) or `ticks` in `~/.hermes/coding-hermes/scheduler.db`. A family where most
  lanes have no completed tick in the last day is a **P1 ops finding** even when every artifact check
  passes — **but read each lane's `cooldown_s` before calling a quiet lane dark.** A family is
  routinely mixed-cadence: 6h sync, 12h qa, 24h pm/releng/ops, 3-day dogfood, 7-day
  docs/readme/review/perf. A weekly lane with no tick in the last day is running to spec, and
  filing it as dark mints a P1 that the next tick cannot close. Quote `cooldown_s` beside every
  last-tick age, and judge darkness only against the lane's own interval (a lane overdue by more
  than ~2x its cooldown). The dominant signal on a mature family is usually FAILURE, not silence:
  count `last_tick_status` per lane before writing up the uptime leg.
- **Prove the class is FLEET-WIDE before deciding the family board owns anything.** Count the same
  error class across ALL projects in one query and quote the top classes beside the family count —
  a family-only count cannot distinguish a project defect from a gateway/routing outage:

  ```bash
  sqlite3 -header -column ~/.hermes/coding-hermes/scheduler.db "select substr(error,1,45) as cls,
    count(*) n from ticks where status='failed' and spawned_at > '<cut>' group by cls order by n desc limit 8"
  ```

  When one class dominates every project (gateway 503 / 429 / 502, drain aborts) the family's reds
  are that outage's victims: report the family lanes as affected, name the owning lane, and file
  NOTHING on the project board. Re-run the same query over the last few hours to say whether the
  class is subsiding or still live — a resolved-class number is what stops the next tick re-filing it.
- **A short-cooldown lane that closes `dry_run`/`no_changes` over and over is WEDGED, not idle — and
  the cost is measurable.** `ticks` splits COMPLETED ticks by `outcome` (`dry_run` vs `committed`), so
  counting only `status='failed'` misses the most expensive failure mode: a lane with a
  seconds-to-minutes cooldown whose every tick closes dry since one instant is normally blocked by a
  barrier it cannot clear itself (its own staged residue, an unadopted split-brain pair, a board write
  it refuses). It re-wakes, hits the same wall, exits clean, and reports nothing — so it looks busy
  and healthy. Measure the burn instead of describing it:

  ```bash
  sqlite3 -header -column ~/.hermes/coding-hermes/scheduler.db "select count(*) dry_ticks,
    round(sum((julianday(completed_at)-julianday(spawned_at))*86400)) total_secs
    from ticks where project_name='<lane>' and outcome='dry_run' and spawned_at > '<cut>'"
  ```

  Correlate the FIRST dry tick's `spawned_at` against the mtime of the commit that dirtied the tree —
  a first dry closing minutes after that commit is the causal link, and quoting both turns "the lane
  looks quiet" into "the lane burned N seconds concluding nothing since <instant>". Then discriminate
  before blaming the project: the same count `group by outcome` across ALL projects usually shows
  `dry_run` as a normal terminal outcome fleet-wide, so the finding is the CONCENTRATION (N
  back-to-back in one lane, with a named mechanism), never the existence of dry ticks. A wedged
  delivery lane is a P1 for the same reason a dark one is: the family's only implementation lane has
  stopped producing while still consuming full agent ticks.
- **Group failures by CLASS, not by lane.** Twelve lanes failing on one error string is one outage
  with one owner, not twelve project defects. The class name is usually inside the error, but do NOT
  select the full column first: `ticks.error` embeds the router's entire decision document (matrix,
  ladder, deadline block, `_router_headers`) — several kilobytes per row — so a `select error` over
  twenty lanes dumps tens of kilobytes into the transcript and gets truncated before you can read it.
  Classify with a bounded projection in ONE query, then read one full error only when the class is
  still unknown:

  ```bash
  sqlite3 -json ~/.hermes/coding-hermes/scheduler.db "select project_name, id, status, outcome,
    spawned_at, completed_at, substr(error,1,90) as err_head
    from ticks where project_name like '<family>%' order by spawned_at desc limit 20"
  ```

  The same one query replaces N single-project GETs for the per-lane leg; keep the GET only when you
  need `latest_tick` fields the table does not carry.
- **Test the tempting mitigation before recommending it.** "Pin the lanes", "raise the cooldown",
  "disable the lane" are hypotheses: split the fleet (pinned vs unpinned, before vs after) and quote
  both sides. A mitigation that does not move the split is noise in the report.
- **Dedupe against the OWNING board before filing.** Fleet-wide outage classes are usually already
  pending on the board of the component that owns them (router/complexity → task-router; admission,
  cooldown, auto-disable → the scheduler; key/balance → the provider row). Search that board for the
  class keywords first. If it is filed, contribute a stronger fixture to that row — a family-level
  view, exact counts, a re-runnable probe — instead of minting a second id: that is liveness
  confirmation, and a second row splits the closure.
- **Write the lane evidence outside the repo.** An ops lane's registered workdir is often the project
  checkout itself; write `<lane>-<date>-evidence.md` into the directory the family's own evidence chain
  already lives in — the one you resolved in the re-fire step, never a freshly invented
  `~/.hermes/stand-in/<family>-lane/` — and keep the repo untouched while siblings share it. Continue
  that chain's naming (base file, then `-r2`/`-r3` addenda) instead of starting a parallel one.

Query recipes, the census shape and the attribution table: `references/lane-uptime-and-outage-triage.md`.

## The board's `in_progress` population is an ops surface too

Rows stuck `in_progress` block dispatch and hide work, and a fix already sitting on the published
branch reads identical to one that never landed. Census them every tick and settle each with TWO
arms — a row's own note is a claim, not evidence:

```bash
jq -r 'select(.status=="in_progress") | "\(.id)\t\((.foreman_note//"-")|tostring|.[0:120])"' <board>/tasks.jsonl
git merge-base --is-ancestor <cited-sha> origin/main && echo ON_MAIN || echo NOT_ON_MAIN
grep -rl '<ROW-ID>' .gitreins/history/ | grep 'verdict.json$'   # evidence binding that already exists
```

- **landed-but-unclosed** — the cited commit is an ancestor of the published branch and no verdict
  names the row: the code is done, the ROW is the gap. Close it through a verification run
  (`gitreins task create` → `start` → `complete`) and the verdict's run DIRECTORY name; never
  re-dispatch a worker at an implementation that already shipped, and never close on the note's
  claim alone.
- **work at risk** — the cited commit is NOT on the published branch, typically one that lives only
  in `wt/<row>`: the row is not merely unclosed, its only copy is one branch-cleanup away from
  deletion. Prove the branch still exists and land-or-discard it with a stated reason; its age in
  days is the urgency, and it belongs in the report even when it cannot be closed this tick.
- **merged-but-unjudged** — the implementation is an ancestor of the published branch but **no verdict
  names the merged commit**. Prove both halves: `git merge-base --is-ancestor <impl-sha> origin/main`
  succeeds AND `grep -rl '<impl-sha>' .gitreins/history/ | grep 'verdict.json$'` returns nothing. This
  masquerades as landed-but-unclosed, and the tempting close — reusing the verdict already on disk — is
  wrong. **A verdict grades only the tree its own `commit` field names, so read that field before
  grading anything.** When `verdict.commit` is the main head while the implementation sits on a branch,
  the judge graded a tree WITHOUT the work and `passed=false` is an instrument artifact, not a merit
  finding; a `complete` lifecycle flip written to `.gitreins/tasks.yaml` after such a run is a false
  completion claim, not a closeout. The order is merge → re-judge the merged tree → close the row on the
  NEW verdict's run directory. Once the merge has landed the same check inverts: the old verdict is
  stale in the other direction and must still not be reused. Closing also requires the merge on EVERY
  configured remote — a fast-forward published to `origin` alone leaves a mirror behind and the row's
  "landed" claim is then half-true.
- **evidence only** — a row whose note is an investigation with no commit: leave it open, and do not
  manufacture a close to make the population look clean.

A verification run needs a judge-free checkout. When a sibling lane is mid-judge in that checkout,
the honest delta is this census plus the disposition table in the evidence file — not a second
concurrent judge, which collides on fixture and coverage state and manufactures a false red.

**Preflight the judge handle, then correct the flip if it dies.** Before `gitreins task complete`,
run `ps -eo pid,etime,args | grep 'gitreins task complete' | grep -v grep`: a live handle with a long
`etime` is another lane judging the same checkout, and the evaluator's own probes read YOUR tree as
evidence. Defer and quote the handle rather than racing it. When a judge is then killed mid-run
(SIGTERM, exit 143 — routine at fleet load), the CLI has already flipped `.gitreins/tasks.yaml` to
`complete` while no `verdict.json` exists: that is a false completion claim, not a closeout. Revert
the record to `in_progress`, drop `completed_at`, add a one-line `note:` naming the tick and the kill,
and land it as bookkeeping with the correction disclosed in the commit message. Record
`verdict=none:<instrument reason>` in the row/event; never let a `complete` stand that no verdict
backs, and never re-dispatch identical work at a judge that merely died.

**A lifecycle status is not a verdict.** After `gitreins task complete`, read the exact
`.gitreins/history/<date>/<run>/verdict.json` named by the command, then compare its `commit` field
to the tree that was judged. Require `passed=true` and verify every acceptance criterion against the
verdict's evidence; a persisted `status: complete` with `passed=false`, missing criteria, or a
verdict bound to another commit is a failed close, not a successful one. Restore the lifecycle to
`in_progress` with `completed_at` removed when the implementation is not proven, preserve the failed
verdict as evidence, and rerun only after correcting the implementation or the missing regression
fixture. Focused unit tests are not a substitute for an acceptance fixture: when a criterion names a
pipeline, CLI, persisted record, or serialized field, execute that real path and assert the emitted
shape, including the negative control.

**Tier-1 grades the STAGED diff, so a fix that is already committed gets graded by nothing.** When
the commit has landed before you complete the lifecycle, the guard logs
`PASS (DEGRADED — skipped checks)` with `go_build`/`go_lint`/`go_tests` = `No Go files staged`. That
PASS verified nothing about your change: the substantive evidence is the direct gates you ran
(repeated package runs, `go vet`, `make lint`, the negative control), so quote those, say plainly that
tier1 was vacuous, and let tier2 carry the judgement.

**And when `guards.allow_skips` is unset, that same clean-index run is recorded as a FAILURE, not a
vacuous pass — read `stages.tier1.steps[]` before believing `verdict.passed`.** The guard keeps exit 0
only when `allow_skips` is true (TRUST-001); otherwise a DEGRADED run exits 2, the judge's `guard`
script step marks any nonzero exit `passed=false`, and the verdict renders FAIL while `stages.tier2`
PASSed every criterion. The discriminator is one config line, so measure it rather than arguing:
`grep -A1 allow_skips <repo>/.gitreins/config.yaml` plus
`jq -c '.stages.tier1.steps[]|{id,passed,exit:.data.exit_code}' <run>/verdict.json`. Two runs, same
instrument, same day: `allow_skips: true` → `guard passed=true exit=0`, verdict PASS; unset →
`guard passed=false exit=2`, verdict FAIL with tier2 green. Upgrading gitreins is NOT the fix (the
exit policy is identical at v0.18.1, which adds further `DEGRADED, not a pass (GR-169)` arms), and the
updater notice in the summary line is cosmetic — `_check_for_updates` writes to stderr and the judge
merges streams. Close on the guard log's `DEGRADED PASS` and the tier2 verdict, and file the class
once on the gitreins board (GR-183) instead of re-explaining it in prose each tick.
**The inverse also happens: a tier1 that renders FAIL while the guard PASSED.** The one-line tier1
summary is the gate's FIRST output line, so an always-on notice (`Update available: vX → URL`) or a
foreign-interpreter `pytest` failure can be what gets quoted while `.gitreins/logs/guard-<ts>.log`
says `overall: PASS` and the guard exits 0. Before recording a merit FAIL on a row you just
implemented, read that log's `overall:` line plus each arm; when the tree is green there, close on
`guard_result=PASS`, name the artifact in the row note and the audit event, and report the harness
upgrade as an owner action instead of re-deriving the fix. Mechanics: the `tier1-instrument-artifacts`
reference inside the `gitreins-guard-troubleshooting` skill.
**The same holds for a suite you would run for your OWN gates:** a tier-2 evaluator routinely polls
`ps aux | grep -c '<suite>'` while it waits, so your run becomes ITS evidence and can extend or
mis-grade its attempt, and fixed-port fixtures collide. Wait for the foreign pid with
`timeout <n> tail --pid=<pid> -f /dev/null`, re-issued per round, and start yours only once
`ps -o pid,etime= -p <pid>` answers nothing; quote that instant in the evidence file so the next
tick does not re-derive why the suite ran late.

## A standing ownership barrier does not cancel the ops legs

When the family repo carries unresolved dirty state, the foreman-side barrier forbids board
selection, commits, dispatch and push — but the census and the uptime leg are READ-ONLY and remain
the ops tick's job. **The barrier is absolute only while the producer is UNRESOLVED.** Once the
dirty paths are attributed to a live writer — a lifecycle record whose `created_at` matches the
file's mtime to the second, plus the `hermes chat --query-file` process whose cmdline names that
record's worktree — the barrier covers only the residue paths that writer owns, and disjoint paths
(the board this tick owns) may still be mutated. Do it with the commit path-limited (`git add <board
files>`, then assert `git diff --cached --name-only` names nothing else) and re-capture the porcelain
digest at the end: an unchanged digest is the proof you did not touch the residue, and a changed one
is a finding rather than a clean closeout. Do not stand down to a bare "blocked": run `fleet_ops_check.py --project
<family>`, the bounded `ticks` query, the observed-only CI listing and the status-pointer read,
write `<lane>-<date>-evidence.md` into the family staging dir (outside the repo), and report
BLOCKED **for the board leg only**, naming each skipped write. The reconcile/refute table and the
re-scoped `backup` finding are the tick's product; they are lost if the tick only republishes the
barrier.

**When the residue MOVES while you work, re-derive the receipt in one capture→classify→rebuild loop;
a class array from an earlier capture cannot reconcile.** A live sibling writer flips the path set
between minutes (a row withdrawn, events rewritten, an evidence file appearing), so the builder's
own `porcelain.txt` and the classification you hand it must come from the same instant. Stage a loop
that per pass (a) runs the builder with empty arrays to capture, (b) classifies THAT capture, (c)
rebuilds with it, and breaks only when the builder prints `reconciled=true`; every earlier pass is
capture history, never a promotion. Then attribute the writer from file CONTENT and mtime
progression, not from the process census — a gateway prompt lane's cwd is not the checkout, so
`checkout-writer-census.sh` answers `CENSUS_COUNT=0` while the lane is demonstrably writing, and its
zero-hit result proves nothing about handoff.

Two habits make that report trustworthy:

- **Re-derive the residue delta instead of inheriting the last note's count.** Normalize the
  porcelain capture (`cut -c4- | sort | sha256sum`) and re-capture at the end of the tick; an
  identical digest proves the barrier held while you observed it, and a changed digest is a finding
  (a bulk-copy class appearing under `.gitreins/` can multiply the path count by hundreds).
- **Attribute a changed digest PATH BY PATH — residue has several producers at once.** One live
  process census and one `git status` do not add up to one writer: a judge run owns the
  `.gitreins/` lifecycle paths while a completely different lane owns the board. Three bounded
  probes settle it, and they name different producers:
  `git status --porcelain=v1 -uall | grep -v '<known-bulk-dir>/'` (isolates the non-bulk delta),
  `git diff -- .coding-hermes/board/tasks.jsonl` (names the exact ROW that moved and, in the same
  read, which rows did NOT — so you can say whether the row you care about changed),
  `find .gitreins -newermt '<HH:MM>' -type f` (names the judge's own artifacts). Quote the producer
  per path group, never one lane for the whole digest, and state explicitly that the rows/paths you
  were tracking did not move. A foreign lane rewriting its OWN row's note is churn, not a status
  change — do not read it as the board being touched under you.
- **Cross-check your path count against a sibling's own log** when another lane is running in the
  same checkout: a gitreins guard log line (`Scanned N files`) is an independent measurement of the
  same tree, and an equal N is the cheapest proof that neither lane measured a half-written tree.

## The unstick decision: settle the barrier, don't wear it

Attributing a barrier is not the end of the tick — it is the input to one question: **can this lane
clear the barrier itself?** A barrier the lane can clear and doesn't is a burn loop: on a live fleet
one foreman re-proved the same three dirty paths for 31 consecutive ticks (131M tokens, 2 commits)
because its doctrine stopped at "report BLOCKED honestly". Honest repetition is still repetition.

Settle it in one commit when ALL of these hold, and prove each:

1. **The paths are generated, not authored.** Deterministic tells: the path is a cache/index
   (`.symbols_cache.json`, `coverage.json`, `graph.db`), its content is derivable from tracked
   sources, and its mtime is tool-run shaped (rewritten on access, not edited). When unsure, run
   the generator mentally: could `git checkout` + the tool reproduce these bytes? If yes, residue.
2. **No live writer owns them.** Two porcelain captures minutes apart with an identical digest,
   zero processes whose cmdline names the path, and no lifecycle record whose mtime matches.
3. **The repo's own convention already ignores the class.** If `.gitignore` carries siblings of
   the same generator (graph.db, edges.jsonl, .last_reconcile), the cache belongs there too — the
   gap is an old tracked copy or a missed pattern, not a policy question.

The settle commit, one per family, attributed in the message:

```bash
printf '.vfs/graph/.symbols_cache.json\n' >> .gitignore
git rm --cached .vfs/graph/coverage.json      # tracked-before-the-pattern case
git add .gitignore .gitreins/tasks.yaml       # a real ledger settles as a commit, not a rm
git commit -m "chore(<family>): settle generated vfs residue + gitreins ledger; clear
ownership barrier (N consecutive blocked ticks, ~XM tokens re-proving it)"
```

What does NOT qualify for self-settle, ever: source files, specs, manifests, anything another
lane's brief references, and anything whose generator cannot be named. When in doubt, the barrier
stands and the tick reports it — but the report must name the ONE decision that clears it, so the
next tick can execute instead of re-derive.

**Identity-gate barriers (registered `repo_url` vs checkout `origin`) settle the same way.** The
scheduler's row and the checkout's remote are both state, and one of them is wrong. Prove which by
the history rule — the checkout that has been committing to its remote is real; a registered
`local:` path that no longer exists as a git root is stale — then repair the wrong one in BOTH
stores (`projects` row + `fleet.toml` block) in one tick. A lane that reports "identity mismatch"
for the fourth consecutive day has been paying rent on a one-line fix.

## The cheap idle: never re-derive an unchanged conclusion

The other dry-run class is the legitimately idle lane that still spends 0.5–1.6M tokens per tick
re-reading its whole board and restating the same conclusion. The fix is a digest, not patience:

- Before scanning, read the board digest recorded in the family staging dir
  (`<staging>/<lane>-board.digest`: `git -C <board> rev-parse HEAD` plus the row count).
- If the board HEAD is **unchanged since the last tick** and the last tick concluded IDLE, the
  correct action is a bounded re-check — pending-row count, new events since the last tick id —
  and a one-line IDLE note citing the digest. No board re-read, no re-census of CI, no restated
  blocker table.
- If the digest changed, work normally.

Cost arithmetic that makes this non-optional: 129 consecutive IDLE ticks at ~0.8M tokens each is
~100M tokens to learn "still nothing to do" 129 times. A digest read is ~10 tokens.

## Anti-patterns this skill exists to stop

- **"It's deployed" without a metric.** A service nobody can see failing is not deployed; it is
  unreported. P1 by default.
- **A report instead of a row.** Findings that live in a chat message or an HTML page are lost at
  the next context window. File board rows with acceptance criteria.
- **Adding a lane family by hand.** Every family created outside `fleet_lane_align.py` has
  arrived with a hardcoded cooldown, a retired command, or `enabled=1` flipped over the daemon's
  auto-disable.
- **Judging a docs repo by service rules.** 81 of the fleet's 87 families are docs/spec repos;
  flagging them for missing metrics is how the real P1 on a service gets buried.
- **Trusting `workdir`.** Resolve `repo_url` first. Stand-in directories exist by design.
- **Ops as a one-time audit.** An audit fixes today. The lane is what keeps it fixed.
- **Reading `rc=0` as "the family is fine".** rc follows the checks; a misclassified family has no
  checks to run. Read the `kind`, then read the family's uptime.
- **Filing one fleet-wide outage on every project board.** One class, one row, on the board of the
  component that owns it. Project boards get the fixture, not the id.
- **A lane-config field that every sibling lane shares.** Before filing "lane X is missing field F",
  census F across the family's own scheduler rows: `sqlite3 -json … "select name,parent,enabled,
  admission_mode from projects where name like '%-ops'"`. When the majority of peers carry the same
  empty/default value (`parent=""` on every `<family>-ops` lane, for instance), that is the deploy
  path's convention, not a per-lane defect — filing it splits a class that belongs to whoever owns
  the  loader, and the next tick re-files it. Report it as a convention observation, or file nothing.
- **Retrying an approval-gated destructive command.** A `docker stop`, `rm`, or in-place edit that
  answers BLOCKED on an unattended surface means consent was NOT given — the file or process is
  untouched, and a second attempt (this tick or the next) burns the same window for the same answer.
  The correct output is an owner command: name the leaked resource, prove it is disposable (a `--rm`
  scratch container holding no project data, a regenerable cache, a scratch DB), and quote the exact
  one-line command to run. A resource left standing with a stated reason is a completed ops finding;
  a retried gate is not verification.

## A re-fired ops tick implements the row its first run filed

An ops tick is one-shot work under a fixed tick id, and the scheduler can re-fire the same id after
the first execution is killed mid-tick. Prove whether this tick already ran from the surfaces that
carry the id, in this order:

**Budget the tick backward from closeout before selecting a worker-sized row.** A worker dispatch is valid only when the remaining window can cover worker exit, commit inspection, direct gates, GitReins completion and verdict readback, push/parity, CI observation, and board bookkeeping. If that budget is not available, perform only read-only census/uptime reconciliation and leave the row pending with the exact budget block; an unfinished worker plus an in-progress GitReins record is not a completed ops tick.

1. **The receipts tree + the lane evidence file — as two BOUNDED greps, never one tree-wide one.**
   `~/.hermes/stand-in` is 150k+ files, so `grep -rl '<tick-id>' ~/.hermes/stand-in ~/.hermes/cache/scratch`
   spends the whole foreground budget before it prints anything and exits 124 with an EMPTY result — which
   reads exactly like "no prior execution". Grep the two places that actually hold the artifact instead:
   the family staging dir and the receipts dir
   (`~/.hermes/cache/scratch/<family>-receipts/`, or a tick-named scratch root). They hold the
   `<lane>-<date>-evidence.md` and the sanctioned `<tick-id>-unblock*.txt` addendum the first pass wrote.
   Search the receipts tree explicitly: a first pass that closed BLOCKED writes its addendum there and may
   never name the id in the stand-in tree, so a stand-in-only grep answers "no prior execution" for a tick
   that already ran. The board's committed blob (`git show <rev>:<board>/tasks.jsonl | jq`) is the third
   bounded source and outranks both. Search the receipts tree explicitly: a first pass that closed BLOCKED writes its
   addendum there and may never name the id in the stand-in tree, so a stand-in-only grep answers
   "no prior execution" for a tick that already ran. The evidence file's closeout section names the
   row the first pass filed, the commit, the verdict dir and the memory record id.

   **Never assume the staging dir's NAME — resolve it first.** `~/.hermes/stand-in/<family>-lane/` is
   only the common shape: a family whose lanes share a ROLE directory parks its evidence beside its
   siblings (e.g. `~/.hermes/stand-in/<role>-lane/<family>-ops-<date>-evidence.md`), so a grep of the
   guessed `<family>-lane` path answers empty for a tick that DID run — the precise false "no prior
   execution" this whole step exists to prevent. One bounded glob beats the guess:
   `ls -t ~/.hermes/stand-in/*lane/*<family>*evidence*.md 2>/dev/null | head -10`, then grep the dir
   that actually holds the chain. And **match the tick id INSIDE the file, never the date in its
   name**: the file is named for the day the streak started while its heading names the tick id
   currently executing, so `<family>-<yesterday>-evidence.md` is routinely the artifact for today's
   tick id.

   **When the first pass closed BLOCKED it filed no row, so there is nothing to implement.** Its
   artifact already carries the measurements; independently reproduce them (opening capture digest,
   census rc + `kind`, the bounded `ticks` projection) instead of re-deriving, and write a NEW
   uniquely named addendum (`<tick-id>-unblock-r2.txt`) whose value is its delta — never a second copy
   of the first pass. That receipts tree sits under a scratch root pruned on 24 h idle, so say in the
   note that the only record of the blocked streak evaporates unless someone lifts it out.
2. **The filed row's own `reasoning`.** First-pass rows quote their own tick id
   (`… measured by the <lane> tick <tick-id>`). Slurp the board — an unslurped filter runs once per
   input line and cannot index a row:
   `jq -s -r '.[]|select(((.reasoning//"")|tostring)|contains("<tick-id>"))|.id' <board>/tasks.jsonl`
3. **The DuckBrain record the evidence names.** `jq -r '.key, (.embedding_text // .content // "")' <file>`.

**Before splitting, decide whether this is a RE-FIRE or a COMPACTION CONTINUATION — they demand
opposite work, and the surfaces above cannot tell them apart.** A re-fire is a NEW session under the
same tick id: nothing of the first pass is in context, so the row it filed is yours to implement. A
continuation is the SAME execution resumed after its context was compacted, and it hides in plain
sight: `skill_view` answers `status: unchanged … loaded earlier in this conversation` for the very
skills the tick loaded at its start, and the tick's own commit sits on the published branch with this
exact tick id authored inside the same tick window. **mtime proximity is necessary but NOT sufficient, because a transport retry can re-fire the same id minutes after its predecessor closed.** Run `date` next to
`ls -l --time-style=full-iso <tick-scratch-root>/` and read the newest artifact; then settle the class on the PREDECESSOR'S OWN FILE rather than on the gap. A predecessor that ends with a terminal outcome (an `**Outcome: …**` header plus a `## Not done / next` section) CLOSED its execution, so a later session under the same id is a RE-FIRE owing verification plus a delta however small the gap; only an artifact that stops mid-leg — no outcome, no closeout section, a launch log with no exit marker — leaves the execution open, and only there does minutes-scale proximity mean continuation. The streak length is legible from the evidence-file chain itself (`…-evidence.md`, `…-evidence-r2.md`, `-r3`, `-r4`) paired with the receipt chain (`/project/<ns>/…` base key plus `-r2`/`-r3`): count the suffixes before deciding, and carry a predecessor's measurements forward as VERIFIED or CORRECTED, never restated as your own work.
Decide it HERE, before choosing a branch: the board and the scheduler row look identical either
way, and one wrong branch either re-implements closed work or abandons a live pass. Finish only
the legs the pass had not reached (evidence file outside the repo, memory receipt, CI
classification, push parity) and leave its decisions standing — an earlier pass normally justified what it deferred ("worker-sized, not a tick
edit"), and reversing one re-opens work it deliberately parked.

**A continuation killed before it delivered its report leaves the REPORT as the open leg** — the
measurements are already in the evidence file, so re-deriving them is the waste, not the missing
step. Close it by appending one numbered addendum rather than rewriting the file: stage the text with
`write_file` to `<scratch>/addendum-rN.md`, append with `cat <staged> >> <lane>-<date>-evidence.md`,
and prove the append was append-only by quoting `wc -c` before and after (the delta must equal the
staged file's size) plus `grep -c '^## Addendum rN'` returning 1. **A previous append that ended
without a trailing newline glues your heading onto its last line**, so the byte delta is right while
`grep -c '^## Addendum rN'` answers 0 and the file now has one unnumbered heading — check the anchored
count, not just the size, and repair the junction by rewriting through a temp copy (`awk '{sub(...)}'`
to `<file>.tmp` then `mv`), never with `sed -i`/`perl -i` on an unattended surface.
**Never revise the staged addendum with an in-place editor.** `perl -i`, `sed -i` and `rm` are
destructive-action gated on an unattended surface: the call spends the whole approval window and
returns a no-consent verdict with the file untouched, so the correction still owes itself and now
has cost a timeout too. Re-stage the corrected text with `write_file` to a NEW path and append that
file — the append-only proof above is what the chain needs, and a superseded scratch file left
behind costs nothing.

**The continuation's delta is CLOSE-STATE RE-VERIFICATION, and it is five bounded arms — not a
re-derivation.** Run all five, quote each result beside the tick id, and let the addendum be the
table they produce: (1) the census re-run with `--json` and its per-check tally (the one number that
moves is usually the predecessor's own work); (2) the landed row read from the REMOTE board blob
plus `git rev-list --count <remote>/<branch>..HEAD` in both directions; (3) the judge verdict file
under `.gitreins/history/<date>/<run-dir>/verdict.json` parsed for `passed`/`task_id`/`commit`;
(4) the `gitreins` record's own `status`/`completed_at` in `.gitreins/tasks.yaml`; (5) the memory
receipt read back over HTTP. A predecessor that claims a close but fails any of (2)-(4) did not
close it, and the continuation's job becomes the close rather than the report. Take the arms from
the PREDECESSOR'S assertions — every claim it made in prose is a claim this pass measures — because
a compacted pass leaves you its conclusions without its evidence.
**Number every addendum with the SAME heading shape from the FIRST pass onward** (`## Addendum rN —`,
the level this evidence file already uses). An unnumbered opening heading (`## Addendum —`) makes
the count-arm fire on a token no later pass emits, so `grep -c` answers 2 on a four-pass file and
the ordering proof reads as a missing section. The `wc -c` delta is the append-only proof and the
grep is only the landed-once proof — quote both, never let one stand in for the other. Do NOT mint a DuckBrain record
per continuation: one record per tick id carries the substance, later passes supersede it by naming
the prior record id, and a record per three-minute delta makes the chain harder to read, not safer.

**A prior pass that recorded CI `in_progress` hands the continuation that leg still open.** Re-list
the runs for the final pushed SHA and record the RESOLUTION as the continuation's delta: copying an
earlier `in_progress` forward reports a state that has since been decided. A `failure` none of your
passes created is then a row to file, not a footnote — but attribute it first: a prior-head control
worktree running the same package test in the same wall-clock window decides pre-existing versus
yours, and a red that only appears inside a configured time window (quiet hours) is a real defect
even when no commit caused it. Recipe: the `suite-state-pollution-attribution` reference inside the
`flaky-test-elimination` skill.

**A prior pass's deliberate HOLD-BACK is a fact about ITS tip, not a standing decision.** When an
earlier pass declined to publish — a foreign commit sitting in its local lineage that it would not
push on another lane's behalf, a red gate it did not own, a mirror it was told not to touch — do not
carry that sentence into your report. Re-probe at close: `git merge-base --is-ancestor <held-sha>
<remote>/<branch>` plus `git rev-list --count` in BOTH directions. Ancestor-confirmed means a sibling
lane has published the whole lineage since that pass, so the hold-back resolved itself, the row you
filed already reads on the published board, and the correction belongs in the addendum and the
superseding receipt, named as superseding the earlier prose. Still-unpushed means the hold-back
stands — say so with the fresh counts and the sibling's tip at that instant. Restating a resolved
hold-back as still-open is the same defect as reporting a landed row as pending.

**A shared checkout moves under you mid-tick, so every measurement carries its own tip.** Read
`git rev-parse --short HEAD` in the SAME call as each parity or CI probe and quote it beside the
result: sibling lanes commit into the checkout between your own calls (a perf lane's board commit
and a foreman worker's fix can both land inside one ops tick), so a parity reading taken at the
opening probe describes a tree that no longer exists. Never attribute a foreign commit to your
pass, never revert one, and re-read HEAD plus `git rev-list --count origin/main..HEAD` immediately
before you write the report — the tip in your report must be the tip at close.

**A guard FAIL on a cell your diff cannot reach is a concurrent writer until proven otherwise.** The
pre-commit gate reads the WORKING TREE, so a sibling lane mid-write makes an unrelated cell (a docs
section mapping, a board lint, an audit script) fail inside your commit while your own paths are
clean. Attribute it before editing anything: re-run that exact cell by hand with your change still
staged and `HEAD` unchanged — green means the gate read a half-written tree, so re-commit and do not
"fix" the code. `HEAD` unchanged plus identical staged diff plus a green rerun is the whole
argument; without it you are changing code to satisfy a measurement that described someone else's
tree.

**A prior pass's prose number is a CLAIM; its saved artifact is the measurement.** An addendum can
state a count its own `census-after.json` contradicts (41 families with gaps written up as "32"),
and a continuation that copies the prose forward propagates the error into the report. When your
fresh run disagrees with an earlier addendum, resolve it against the saved artifact first: if the
artifact agrees with YOU, the prose was wrong — append a CORRECTION block (same staged-file +
`wc -c` delta proof as any addendum, never a silent rewrite), state which pass owned the error and
why the instrument was at fault, and supersede the DuckBrain receipt naming the prior record id.
Never leave two different numbers for one tick id in the ledger, and never edit the earlier block
to match: an evidence file that changes under a reader is worse than one that is visibly corrected.

**A prior pass's evidence prose can be FORWARD-DATED relative to its own mtime.** The mtime
proximity test settles continuation-vs-re-fire, but it does not validate the timestamps INSIDE the
file: compare `stat -c '%y' <evidence-file>` against the newest time written in its text, and when
the prose runs ahead of the file's own mtime, say so in the addendum and carry measured stamps
only. A reader who trusts the prose quotes a "measured at" time that had not yet happened, which
is indistinguishable from a fabricated measurement.

**If it is still `in_progress`, classify at JOB level before recording it.**
`gh run view <run-id> --repo <org>/<repo> --json status,conclusion,jobs` names which arms have
finished and which one is outstanding: five of six jobs `completed/success` is still
**pending/unverified, not "nearly green"**, and the outstanding job is routinely the regression arm
that grades the very change under review. Quote the job table and say which arm is unread, so the
next pass reads that job's outcome instead of re-listing the run from scratch.

Then split the result: work the earlier pass CLOSED gets verified plus an addendum, never
re-implemented or re-judged; work it merely FILED — a still-pending row naming this tick id — is THIS
execution's task: implement that row additively on the published tip and do not re-do the commits
already pushed.

**Neither the board event log nor the tick's own scheduler row can prove absence.** A board whose
writer stores a minimal `{"status":"complete"}` detail answers empty to
`jq -r 'select((.detail // "")|tostring|contains("<tick-id>"))|.id' <board>/events.jsonl` even when
the first pass filed the row, published its verdict bundle and pushed — and an empty hit reads
exactly like "no prior execution". Likewise a re-fired tick still shows `status=running` with
`last_tick_completed` empty after a first pass that landed commits. Use both only to CORROBORATE a
filing you already found by row id, never to conclude the tick is fresh. Never attribute a tick with
`sqlite3 ~/.hermes/state.db "… where content like '%<tick-id>%'"`: that scan over the message table
times out, and a timeout reads as "no prior execution".

A memory key alone may not be enough to detect your own receipt: `/…/<date>`-scoped keys replace
each other and the content of an earlier pass can name only the date. **Put the tick id in the
CONTENT of every receipt you write**, and when you supersede, name the prior record id — otherwise
the next execution of a re-fired tick cannot prove it already ran from the ledger, and re-derives
(or worse, duplicates) the whole filing.

**Build, inspect, and freeze the memory-write payload before invoking the tool.** After
`tool_describe`, construct one complete `arguments` object explicitly and pass that exact object to
`tool_call`: for example `{"key":"/project/ops/tick","domain":"event","attributes":{"tick":"<id>","outcome":"blocked"},"embedding_text":"<concise evidence>","namespace":"<resolved namespace>"}`. A valid payload must contain a leading-slash `key`, an allowed `domain`, an object-valued `attributes`, a string `embedding_text`, and the resolved `namespace` when required. Never invoke `remember` with `{}`, omitted fields, or a guessed partial payload; schema validation rejects it before the provider runs, so repeating the same malformed call cannot make progress. Do not use an empty invocation as a schema probe: `tool_describe` already provides the schema, so build the complete payload before the first `tool_call`. **Before dispatch, inspect the actual serialized `arguments` object, not merely the schema or a locally prepared payload; it must visibly contain the leading-slash key, allowed domain, object-valued attributes, string embedding text, and resolved namespace when required.** If validation rejects the payload, correct it once from the schema and invoke the corrected complete payload once; if the corrected call cannot be constructed or fails, stop the memory leg rather than issuing another empty or unchanged retry. Treat the tool-call arguments as frozen after construction: retrying an unchanged malformed call only burns the tick and creates no receipt. Never report or read back a receipt unless the tool returned a write result; a validation rejection is not a transport failure and must not be recorded as a memory write or described as an attempted save. This keeps the memory leg auditable and prevents malformed calls from becoming unverified-memory claims or duplicate attempts.

**Verify a receipt readback by parsing its content FIELD, never by substring-matching the response
body.** A JSON envelope escapes non-ASCII, so a stored em dash comes back as `\u2014` and a raw
`CONTENT[:80] in body` check answers False on a record that is byte-perfect — that false negative
invites a second POST, which answers KEY_EXISTS. Compare `len(content)` and `content == expected`
after `json.loads`. Two envelope quirks are normal and are not scoping failures: `namespace` can
read null on the returned record, and an UNSCOPED key read can answer 200 across namespaces on
some builds. Prove scoping differentially instead — read the same key with `?namespace=<other>` and
require a 404 — and only then call the record namespace-bound.

## Working a P1 from a worktree when the canonical checkout is dirty

A dirty registered checkout is not a reason to skip the work slot: create `git worktree add -b ops/<ROW> <path> origin/<branch>` and build there, leaving the residue untouched and uncommitted. Four traps follow from that shape:

- **The worktree has no `go.work`/`go.work.sum`** (both gitignored): copy them from the canonical checkout or every build answers `missing go.sum entry ... <sibling module>`. Say so in the ops doc you are already writing.
- **A judge tier1 that fails on a toolchain or module-resolution line your diff cannot reach is an ENVIRONMENT cell, not a merit finding.** The gitreins guard inherits the caller's env, so re-run `task complete` with the pin exported (`GOTOOLCHAIN=go1.26.10`) instead of editing `go.mod`; read `.stages.tier1.steps[].output` from `verdict.json` to name the cause before acting. A REAL lint failure can hide behind it (unused declarations), so fix that and re-run rather than declaring the cell instrumental.
- **A board-only commit can exit 0 without creating a commit.** Assert `git log -1` after every commit; retry once, then `--no-verify` and disclose it in the message. The `create` subcommand and the `update` subcommand of a given `boardctl` build do not carry the same flags — check `update --help` before promising `--evidence-run-id`; put the run id in `--note` plus an `audit` event when the flag is absent.
- **The census reads the REGISTERED workdir, so a fix pushed from a worktree leaves the family's gap reported.** Prove the clearing with the census's own matcher on both trees (`grep -rIl -E '(prometheus|/metrics|otel|opentelemetry|statsd)'`) and record the stale-checkout distance as the residual, with  the exact repair. When you take that repair, do it in this order and prove each step: preserve the
  checkout's dirty board line OUTSIDE the repo first (`git diff -- <board>/events.jsonl >
  <evidence-dir>/<family>-<date>-events-orphan-line.patch`) rather than committing it back — the line
  is usually a duplicate whose id upstream now belongs to a different event, so merging it mints a
  duplicate id while the row it names already exists; `git restore --source=HEAD --worktree --
  <board>/events.jsonl`; `git merge --ff-only <remote>/<branch>`; then prove the clearing with the
  FAMILY-SCOPED census (`--project <family> --json` shows the P1 gone) plus the fleet count moving by
  exactly that one family. Land the annotation as an `audit` event, not a re-close, and expect the
  board-only commit to be refused by the guard (`DEGRADED PASS`, `allow_skips` unset) — commit with
  `git -c core.hooksPath=/dev/null` and disclose it in the message, then verify the event id is on the
  REMOTE blob and that every line still parses.

## Definition of done for an ops tick

1. Census run, exit code read (not assumed) — run it UNPIPED, or under `set -o pipefail`:
   `python3 … | head -c 3000; echo RC=$?` reports `head`'s status and manufactures a clean rc on a
   census that exits 1, which is the worst possible read (a gap-finding census recorded as green).
   Read the `kind` too: a `docs` verdict on a shell
   toolkit is a finding, not a pass.
2. Lane uptime read for the family: every lane's last completed tick age and its failure class
   quoted. A dark lane set is a P1, filed or linked to the owning row.
3. Every P1 either fixed with proof, or filed as a board row naming the evidence and the
   acceptance criteria. **A finding that already maps to a PENDING row this lane owns is the tick's
   WORK, not another report** — read that row's acceptance criteria and land them (a docs/cleanup
   row goes foreman-direct when the lane envelope names no worker model; disclose the choice in the
   row note). Re-run the census in the SAME tick and quote the cleared check as the closure proof.
4. Any lane-family defect repaired through `fleet_lane_align.py` (both stores), never by hand.
5. The census re-run at the END of this tick shows the finding gone or the row linked — no silent
   re-reporting of the same item tick after tick. A finding you only re-worded is still open.
