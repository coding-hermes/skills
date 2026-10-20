# Verification premise shapes (Step 5 depth)

## Stale-premise verdicts on another lane's row: reproduce before refuting

- **A "cited symbol/package does not exist" stale-premise verdict is void until you grep WIDER than the lane's own repo.** A "not found here" grep runs against ONE checkout; the cited symbol may live in a sibling project's tree — `grep -rln '<Symbol>' ~/*/ --include='*_test.go'` (or a file-name glob over the code dirs) finds a wrong-board fact in seconds, and it is exactly the check that converts a false refute into a locator correction. Only a swing over the plausible repos below ~ (or the home the fleet code lives in) entitles "the symbols do not exist" as a written verdict.

- **When the cited symbols EXIST but in the WRONG repo, the finding converts from stale-premise to wrong-board filing: annotate a locator correction, do not refute, do not dispatch.** The row's substance (which tests fail, on what conditions) usually survives verbatim — only the "where does this code live" locator is wrong. Stamp the row with the found path(s) (file:line) and a note that ownership/next action belongs on the repo the code actually lives in, and surface the cross-board ownership correction prominently in the cycle report; a tracked-somewhere-else row left pending on this board still reads as local work to the next reader unless the note says otherwise. If the owning lane's own battery has since re-verified the same tests green on a fresh battery (their commits are a closure candidate), name that too — it is cross-cycle evidence the premise is handled, not abandoned.

## Local-daemon deploy-gap rows

- **Verify a LOCAL daemon's deploy-gap premise by its PROCESS, not its endpoint.** For a 'live
daemon predates HEAD' row on the local host: confirm the PID is alive (`pgrep -f <binary>`),
read its process start time (`ps -o lstart= -p <pid>`) to prove WHICH build it executes, take
the running version string from the service's own status API (e.g. `/api/v1/status` →
`.version`), and compare against `git describe --tags --always` at HEAD. A `-dirty` suffix on
the running version means the binary was built from an uncommitted tree — itself deploy
deploy evidence worth naming. PAIR the process start time with the binary's own
mtime (`ls -la --time-style=full-iso <binary>`): start ≈ mtime proves the running process booted
on the current on-disk build; mtime NEWER than the process start means a rebuild landed without a
restart — the version string describes the OLD binary and the row's remaining work is 'restart
pending', not 'still behind'. A live HTTP 200 on an endpoint the row cites is NOT deploy evidence:
the endpoint may predate the fix, so version containment is the proof, and a fresh HTTP probe
belongs in the report only as a liveness side-note.

- **When a deploy-gap premise NARROWS instead of resolving, refresh the gap
  measurement, do not re-prove the row from scratch and do not close it.** The
  premise drifts in one direction only: `git merge-base --is-ancestor
  <deployed-commit> origin/main` flips to true while `git rev-list --count
  <deployed-commit>..origin/main` keeps growing — containment alone proves the
  deployed build contains the old gap, not that the tip's newer work is
  deployed. Stamp the row with the NEW behind-count and both command outputs as
  an evidence note (run_id-deduped), and keep it open; the row's remaining work
  is the operator restart, which the PM never performs itself.

The SKILL.md body carries the always-on core: a fix is only `verified` when a
command proves it — never trust the board status or ledger status alone; run the
row's exact pass-criteria command and record its output as
`verification_evidence`. This file carries the per-shape rules that decide a
row's verdict without re-deriving them every cycle.

## Published-surface rows (docs/releases/links)

- **Probe the PUBLISHED surface, not the repo copy, when the row's premise is
  about what users see.** A docs/releases/links row cites the deployed site
  (GitHub Pages etc.), so the repo tree is not evidence either way: fetch the
  live page (`curl -sL <published-url>`), then verify the row's exact claim
  against THAT fetch — a stale Tags/versions table is proven by grepping the
  fetched page's tag strings and comparing to `git tag`, and a broken-link
  premise is proven by extracting the cited link targets from the fetched page
  and probing each with `curl -o /dev/null -w '%{http_code}'` (a link the row
  names may differ from the targets actually rendered — grep the fetched page
  for the real ones). Cheap: two or three curls per row, no clone, no build.

## Runner green-zeros

- **A runner filter that matches nothing is a green zero, not a pass.** `go test
  -run TestGuessedName` exits 0 printing `[no tests to run]` when the guessed
  name matches no test — that output reads as green without executing anything.
  Grep the cited test file for its real function names (`grep -n '^func Test'
  <file>`) and run THOSE; confirm with `-v` that a `--- PASS:` line appeared, not
  just an `ok` package line (the same guard applies to any filter-based runner,
  e.g. `pytest -k`).

## Access premises across surfaces

- **A 404 on one surface does not prove an access premise on another — probe the
  transport the consumer actually uses.** For a 'repo is private / not publicly
  fetchable' premise, `api.github.com/repos/<o>/<r>` anon 404 and a package-proxy
  (proxy.golang.org) 404 both 404 while anonymous `git ls-remote
  https://github.com/<o>/<r>` succeeds: metadata and registry listings are gated
  independently of the git smart-HTTP transport, and a proxy 404 can just mean
  never-requested. Re-run the exact access path the premise is about (module
  fetch, anon clone, release download), and record on the row WHICH surface
  fails — 'private' is not one test.

## Scheduled-task premises (installer shipped vs unit armed)

- **A committed installer is not an installed unit — check the ACTIVATED state before treating
  the fix as live, and arm it when arming is trivial.** A repo commit shipping
  `deploy/install-*.sh` can sit unexecuted for days (the commit merges, nothing schedules
  anything). During any verification walk over shipped timers/services: if
  `systemctl --user list-timers` lacks the unit the fix installs, run the repo's own installer
  (idempotent, host-local, no secrets) yourself, then verify `list-timers` shows it scheduled
  and hand-start the service once (`systemctl --user start <unit>`) to confirm exit 0. A
  silent-success service may log NOTHING on a green run — exit code via
  `systemctl --user show <unit> -p ExecMainStatus` is the evidence, not journal presence.
- **A wrapper whose required env lives only in the systemd unit false-WARNs when hand-run.**
  If a scheduled script needs an env var (repo dir, config path) and the unit's `Environment=`
  line is its only source, a manual invocation takes a different code path than the scheduled
  one and can emit a misleading WARN (or silently no-op). Probe BOTH: run it bare AND with the
  unit's env (`systemctl --user cat <unit>` gives the line); if the bare run misbehaves, that
  is a distinct finding (bake the env into the wrapper or add a lookup fallback) — file it
  separately, never fold it into 'the scheduled run works'.

## Premise already satisfied at HEAD

- **Close, don't dispatch, a pending row whose premise is already satisfied at
  HEAD.** Re-run the row's premise probe before assuming it needs work; when the
  evidence shows the fix landed BEFORE the row's `created_at` (a broad work item
  — release wiring, a doc sweep — carried it), the row is bookkeeping lag: flip
  it `complete` with the fix commit hash + containment
  (`git merge-base --is-ancestor <hash> origin/<resolved-default>`) + the
  verification command in the close note. A proven-satisfied premise closes the
  row whatever the premise is about — dispatching it manufactures fake work the
  foreman cannot act on.

- **A fix landed mid-flight with an ACTIVE worker/wave session is bookkeeping
  lag to VERIFY AND REPORT, not to close.** The close-on-satisfied rule above
  applies when nobody is working the row; when the row still carries
  `worker_status: dispatched` and a live wave session, the foreman owns the flip
  — verifying the merge is contained (ancestor of default) and the probe passes
  is the PM's evidence refresh, and touching the row mid-wave risks a split
  write against the worker's own close. Distinguish by the row's `sessions`
  / `worker_status` fields, not by merge recency alone. A standalone worker
  spawn (`hermes chat -q <brief>` naming the repo) is invisible to the ticks
  table — it is not a foreman lane — so confirm the tree is empty of workers
  with `pgrep -af 'hermes chat -q'` BEFORE treating staged code + a restaged
  board as a dead writer; staged implementation files (new source, not row
  edits) are the tell that a worker, not a foreman bookkeeping pass, holds the
  tree.

## Multi-claim rows verify claim-by-claim

- **A row citing N measured failures (miss phrasings, endpoints, links) is only
  as fixed as its WEAKEST claim — probe each claim separately at HEAD.** A fix
  commit that satisfies two of four cited inputs leaves the row live; probe every
  quoted input with the row's own command (`<cli> match "<each phrasing>"`, one
  curl per cited URL) and read a partial pass as `in progress`, never as fixed.
  A partial pass on a row with an active worker is an evidence refresh naming
  WHICH claims still fail; on an idle row it is a reopen note with the failing
  claim's output.

- **A compound premise that is only PARTLY stale gets narrowed, not closed and
  not re-filed.** When one clause of a multi-claim row is already resolved by a
  DIFFERENT task's landed fix (prove containment of that commit) while another
  clause still holds, closing the row wholesale retires real work and minting a
  replacement row re-numbers existing work. Keep it `pending`, stamp a
  run_id-deduped evidence entry naming the resolved half + its fix commit and
  the surviving half + the probe that proved it, and restate the remaining
  scope on the row so the foreman works only the unresolved part.

## Dispatch-gate premises (wake ≠ spawnable)

- **A 200 from `POST /api/v1/evaluate` plus a cooldown read back at 900 proves
  the scheduler will CONSIDER the project, not that a tick CAN spawn** —
  dispatch can still die at the task-router hop after the gate opens (router
  503 `no open hop for this request` with the whole model chain excluded: model
  down, provider circuits open, quota-gated, no key). After waking, wait ~1 min
  and query the newest tick; a fresh `failed` tick whose error is a router 503
  with hop exclusions = fleet routing outage: escalate as infra (name the P0
  rows blocked behind it), do NOT file a project stall, and do NOT count the
  wake as failed. The silent variant — a 200 with NO new tick row while
  cooldown is expired and fleet dispatch is healthy — is a dispatch-gate
  suspicion, not a filed stall: one observation proves nothing; verify
  fleet-wide liveness for contrast, name the pending rows blocked, and arm the
  escalation ('if the next cooldown-expired tick still no-ops with rows on
  scope, escalate as dispatch-gate').

## Count-coverage premises (battery/suite misses a case)

- **A 'the suite lacks X' premise is verified by a single grep of the cited
  suite source, not by running the suite.** A pass or fail tells you the suite
  runs, not what it covers; the premise is about content. Count occurrences of
  the cited verb/endpoint/fixture in the suite file (`grep -c DELETE
  <test_battery.py>`) — zero occurrences with the suite otherwise healthy
  proves the coverage gap exactly. Spend the saved slot probing another row.

## Operator-imposed content rules outrank a row's premise

- **Before re-proving an old open row, check the user's standing rules for the
  artifacts the fix would create.** A row whose pass criteria are a class of
  artifact the user has since forbidden proposing (repo instruction files like
  AGENTS.md are one such class) verifies TRUE on the premise but must NOT be
  re-filed, re-scoped, or routed to a foreman for execution — leave it pending
  with a note naming the rule that blocks it, and surface the conflict in the
  cycle report so the operator decides close vs supersede. The rule wins even
  when the row's evidence still checks out.

## Recurring dated-sweep rows: fold oldest into freshest

- **A producing lane that re-files the same structural premise as a dated row each cycle (`<ROW>-YYYYMMDD` ids) creates a fold, not a backlog.** Each new sweep row is evidence, not a distinct task; gate the write by folding the older sweeps IN PLACE into the FRESHEST one — keep-last wins as canonical, so the newest holds the current evidence while the older ones become `status=complete` + `superseded_by=<newest>` + an explicit NOT-FIXED note (do not let status-gated readers count the fold as a resolution); the newest gains a deduped `supersedes` array. The underlying premise stays open on the newest row. When that premise is an owner-decision unblock path (remote+push decision, release tooling+stamp, CI on a candidate sha, an authorized cut), name it as such on the row and in the cycle report — no lane authorizes the decision, and a PM/releng lane files readiness evidence only.

## Where a verified finding goes: the covering open row wins over a new row

- **NO DUPLICATE ROWS, EVER.** A PM cycle that verifies a real gap must still check the board
  for a live row whose premise covers the same substance BEFORE writing anything: matching by
  content, never by id. The most common near-miss is an umbrella row whose own
  `foreman_note` already names the missing sub-work as its next action (a phase split, an
  out-of-scope follow-up) — filing the sub-work as a parallel row duplicates the umbrella and
  doubles the queue for one fix. Cite the covering row id in the report as the reason the
  candidate was NOT filed; a cycle that reports real findings and zero rows gated-in is a
  correct cycle, not an empty one.
- **A finding whose fix belongs to an ALREADY-OPEN row is a note for that row's owner, not a
  row you file.** When the gap is the open row's own outstanding request (an attribution it
  asked for, a package name its evidence truncated, a proof it could not complete), re-filing
  or annotating from a satellite lane is noise: state the finding in the cycle report so the
  row's own dispatcher picks it up, and leave the row untouched. Filing is for gaps with NO
  owner.
- **Never write a row, event, or annotation onto another lane's board.** A satellite lane's
  workdir is not the product repo — resolve the target and operate on
  `<target_workdir>/.coding-hermes/board/tasks.jsonl`. The one exception in kind, not in scope:
  a board stranded in the PM's OWN worktree is a landing task, gated by this file's
  sibling-write rules.

## Batch premise sweeps: cheapest per-row probe, not the full suite

- **When several small rows land together and all premises are code-shape claims, verify each
  with its cheapest sufficient probe — a grep for the cited symbol/fix, a CLI build + `--help`,
  or a single-package `go test -short ./internal/<pkg>/` — never a full-suite run.** The foreman's
  gates own the full suite; the PM's job is premise truth, and a targeted package test that
  exercises the cited fix is stronger evidence per minute than a monorepo `-short` sweep. Probes
  that each close a premise in seconds: `grep -n 'fix: chmod' <stateroot.go>` (error-hint
  premise), `go build ./cmd/<cli> && <cli> <verb> --help` (spec-mandated verb premise),
  `go test -short ./internal/<pkg>/` run from the main tree where a pass where the premise
  predicted a failure proves the fix (e.g. a tests-fail-under-path premise probed from the normal
  checkout). Re-derive the failing condition from the row text and run the probe where that
  condition would reproduce, not wherever is convenient.

## Long verification commands: background, don't truncate

- **Foreground terminal calls die at the ~180s wall even when you passed a larger timeout** — a full pytest/suite run longer than that is killed mid-run with no verdict. Any verification expected to exceed 180s goes `terminal(background=true)`, then `process_manage(action="wait", session_id=...)` for the result; a wait's own timeout clamps short but the process keeps running, so re-wait instead of re-running. Cheap sizing probe first: `pytest --co -q` collects in seconds and shows how big the run will be. Suite runtime >2 min on an otherwise healthy repo is normal, not a finding.
- **Run heavy single-package test verifications alone — one package per tool call, isolated with `timeout`.** A `-short -count=1` run of one heavy package (ledger-style state-machine suites) can take minutes BY ITSELF; chaining it behind other commands in one call hits the call timeout, kills the whole chain, and you lose the earlier commands' results along with the test run. Command body: `timeout 300 go test -short -count=1 ./<pkg>/` with a generous call timeout — or background it per the rule above. A `go test` that returns EMPTY output but exit 0 is still a PASS (go prints only the `ok` line; check the exit code, never the volume of output).

## Remote-host product repos: the lane's workdir is not the product

- **A monitoring/ops lane's workdir can hold NO product code — only docs, copies, and the board.** When `ls <workdir>` shows just `docs/`, `stack-copy/`, and `.coding-hermes/`, do not read that as a broken project: the real repo lives on a remote host. Resolve it from the project's own docs (the diagnostics/architecture note names the host and absolute path), then run every premise probe over `ssh <host> 'cd <path> && ...'`. Verify the path EXISTS on that host before diagnosing anything else — a Makefile/scripts premise checked against the stand-in copy silently verifies a different tree.
- **Run the premise's actual failing command on the remote host, not a grep of it.** For a 'documented command fails' row, ssh in and execute the command (with its env sourced the way a user would) and capture the real error line — the error names the exact missing piece (an unset var, an unsourced env file) which is the evidence line for the row; a grep that shows the var referenced proves only the row was plausible.
- **Health endpoints on the monitoring host are cheap liveness evidence for alert-derived rows.** `curl -s localhost:9090/api/v1/alerts` and `/api/v1/rules` over ssh (parse counts, not raw dumps) plus a `wc -l` of the spool file confirm the alert pipeline is live and which alerts fired/resolved — enough to confirm or refresh alert-row premises without regenerating anything.

## Infra and host premises: probe the surface the claim is about

- **Each status tool answers a different question — pick the one the premise names.** For a
  'host down / agent missing / installability unproven' premise, the host's network presence and
  the orchestrator's agent inventory are INDEPENDENT: run `tailscale status` (or the equivalent
  liveness surface) to decide reachability and the orchestrator's list to decide what is
  attached, and do not read one as evidence about the other. At-rest emptiness ('no agents on
  this box right now') is the normal state, never a down host.
- **De-risk `running`/blocked rows with a host-side probe before echoing them as live.** A
  premise held over from an earlier cycle is only as fresh as its evidence: check the host the
  precedent was about, and whether a DIFFERENT host ran the same leg successfully since — a
  passing leg on another host narrows the row to its own named acceptance (that host, that
  proof) instead of restating the whole claim, and that narrowing is the useful report.
