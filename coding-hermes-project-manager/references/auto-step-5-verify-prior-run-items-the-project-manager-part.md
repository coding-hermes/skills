# Step 5 — Verify Prior-Run Items (the "project manager" part)


The reconciler's TEXT line is the summary, not the proof: reconcile the target's ledger from
the JSON buckets for the specific project (`board_open_work_items`, `no_id_matches`,
`stale_terminal` entries carrying `project == TARGET`), and grep the raw ledger
(`python3 /tmp/<name>.py` over `~/.hermes/stand-in/ledger.json`, items filtered by
`project == TARGET`) for every `status != verified` item — the summary tables can omit or
generalize what a direct item scan shows (e.g. 45 verified + 1 stale out of 46 total), and the raw scan is what the cycle report's item count must match.

**A zero target ledger follow-up count does not end the board walk.** QA, dogfood, releng,
and earlier PM writes can leave actionable board rows that are not paired with a non-verified
ledger item. Census the current target board separately, then probe its small open set. When a
row's own premise is directly refuted by the current tree and the cited fix is present, close
that row in place with the exact command, commit, push, and post-write G8/validation evidence;
do not invent a ledger item merely to make the board and ledger counts agree. Conversely, a
pending "verified-good" record is a closure candidate only when its own durable evidence and
acceptance criteria are rechecked; do not leave a provably satisfied record open as bookkeeping,
and do not close a row that still names owner action or unperformed work.

For every ledger item from previous runs with `status != verified`:

1. **Board check** — did the foreman pick it up? (status row: `- [ ]` → `- [x]`, or `pending` → `in_progress`/`complete`). Update ledger:
    - If board status is `pending` and worker_status is `pending` → ledger status remains `added`.
    - If board status is `pending` and worker_status is `in_progress` or `complete` → update ledger status to `picked_up`.
    - If board status is `in_progress` → update ledger status to `picked_up` (if not already).
    - If board status is `complete` → update ledger status to `complete`.
    Always update `last_checked_at` and `verification_evidence` with the current check results.

1a. **Stale ledger reconciliation** — if a ledger item is marked `stale` but the board shows it's in a non-terminal state (`pending`, `in_progress`, etc.), update the ledger status to match the board status and continue verification as normal. A `stale` ledger status should only persist when the board confirms the item is truly inactive or resolved.

2. **Evidence check (the real verification)** — for `complete` items, RUN the
    pass criteria from Step 4: does the integration guide now exist? does the
    API doc render? does `go test -short` finish under 60s? does the endpoint
    return 200? **A fix is only `verified` when the command proves it.** No
    command = still unverified, mark `stale` if the board claims done but the
    evidence fails.
    **Note**: If there are no ledger items with `status != verified` to check,
    this is a valid outcome indicating all prior work has been verified. Still run the reconciler to get accurate fleet context, but report zero items to verify for this lane.
3. **Update the board if the foreman marked it done but verification FAILED**:
   reopen with a note (`❌ verification failed: <evidence>`) so it gets fixed
   properly — this is the difference between "tick theater" and real done.
4. **Escalate** items stuck > 48h in `added`/`picked_up`: consider bumping priority one level + add a `⏰ stale` note, and note it in your report to the user. **Note**: Priority bumping is not always appropriate - for some items (like fleet inventory holes), deliberately keeping the original priority may be correct when multiple related items exist and bumping wouldn't change which gets picked first.
5. **Stale-era items orphaned by a G8 dedupe:** when a re-minted row (fresh
   `GAP-###`) supersedes an old-prefix item, annotate the OLD ledger item as
   superseded (name the re-mint id in `verification_evidence`) and KEEP its
   status `stale` — never re-open it, never stamp it verified off the re-mint's
   existence. Escalate a `picked_up` item with weeks of no board movement to
   `stale` rather than letting it inflate the open count, and re-run the live
   verification command against the re-minted row each cycle so its premise is
   proven, not assumed.

**Verification best practices** (always-on: run the pass-criteria command, record its output as evidence; per-premise-shape depth — runner green-zeros, multi-surface access premises, already-satisfied premises — lives in `references/verification-premises.md`, read it before verifying any non-trivial row):
- `.gitreins/history/<date>/<hash>/verdict.json` for the row id is strong evidence (read `task_id`, `passed`, `commit`, tier summaries) — but it is still a claim: re-run the verdict's own cited test command yourself before stamping verified, and confirm the fix commit hash is on master.
- **Compare the DEPLOYED build against the fix commit before trusting a live probe.** A Docker stack keeps serving a years-old image until someone redeploys: check the container's image build/created timestamp (`docker inspect <c> --format '{{.Created}}'` or `docker ps --format '{{.RunningFor}}'`) against the fix commit's date. A live probe that FAILS on a pre-fix image is a CORRECT fail — the row stays open — and the redeploy is the remaining work, not a regression: say 'fix merged, not yet deployed' on the row. Isolate WHICH component is stale by probing a path the fix touched against a sibling path known to work (e.g. direct-create vs the batch-ingest path sharing the same worker) — a split verdict pins the stale image instead of blaming the code. Two refinements: (a) when the service's source is BIND-MOUNTED into the container, grepping the container's files is NOT deploy evidence — the fix line appears in the bind-mounted file the moment it lands on the host while the running process still predates the commit; compare the CONTAINER's `docker inspect --format '{{.Created}}'` (not the image's) against the fix commit's committer date. (b) when the fix is event-driven (publishes to a queue/stream a worker consumes), verify the EVENT was published, not only that the row's end state changed: read the stream's newest entry id (e.g. redis `XLEN` + `XRANGE <stream> - + COUNT 1`) and confirm an entry newer than your probe exists — 'probe still stranded' with a silent stream means the running producer predates the fix. A consumer group's pending-entry count (`XINFO GROUPS` → pending) plus a log flood of permanent-class consumer errors is direct live evidence for a never-acked/no-DLQ row — attach it to that row as an evidence refresh instead of re-deriving the premise.
- **A fix commit may live in a repo other than the row's home project.** The row detail names the owning codebase (the file/function the fix touched) — resolve the owning repo from that and run `git log --all --grep "<fix subject>"` THERE before reading a containment failure as a red flag. To FIND the owning repo when the detail does not name it, sweep the sibling workdirs under the same umbrella: `for r in <umbrella>/*/; do git -C "$r" cat-file -t <sha> 2>/dev/null && echo $r; done` — a harness/QA fix often lands in the umbrella's infra repo, not the product repo. Before reading a containment failure as a red flag: the row's home repo never contained the commit, so a `merge-base --is-ancestor` against it fails spuriously and reads as 'fix not deployed' when the fix is fine. When the owning repo lives only on a REMOTE deployment host, resolve the node from `tailscale status` and run the hash check over ssh; if the hash is unresolvable even there, verify the fix by its FILE SIGNATURE on the live tree (grep the rewritten file for the construct the row describes) and cite that as deploy evidence — the commit itself may exist only on the host.
- **Verify a REMOTE deployed binary by version string → repo containment, not by service restart.** Read the running version/commit from the binary itself on the host (`<tool> version`), confirm the fix commit is an ancestor of that deployed commit in the owning repo, and cross-check the binary's mtime against the fix commit's date and the service restart time — a restarted service can still run a weeks-old binary, and `main` being newer than the deployment proves nothing in either direction.
- **Resolve a remote node's address from `tailscale status` by NODE NAME every cycle** — hardcoded node IPs go stale, and the probe then reports 'no route to host' against a host that is up and reachable at its current address. Read the node's own liveness column in the same pass: `offline, last seen <N>d ago` beside a failing ssh/port probe means the HOST is down, which is a different verdict from a stale row. Record such a row's premise as UNVERIFIABLE (never `failed` — nothing proved the defect is gone), keep the row `pending`, and report the fleet consequence separately: every row whose pass criteria name that host is blocked until it returns, and the live-server verification battery has no bearing host, which is an escalation even when it is nobody's row.
- **A 'release channel / installer serves stale binaries' premise must be re-probed against the LIVE channel, never trusted from the row's own figures.** Rows of this class quote a tag, an asset list and a commit lag; any release cut since then refutes the loudest clause while a smaller true lag survives. Probe `gh api repos/<org>/<repo>/releases/latest --jq '.tag_name, .published_at'`, `gh release view <tag> --json assets --jq '.assets[].name'` (asset completeness), `git merge-base --is-ancestor <named-fix-sha> <tag>` (does the published tag actually ship the named fix?) and `git rev-list --count <tag>..HEAD` (residual lag). A tag that now contains the fix plus a smaller residual count means NARROW the row to the residual lag with the fresh numbers as evidence — do not close it (the lag is real, the users still get a behind-HEAD build) and do not leave the refuted figure standing as the premise.
- **Point remote-host probes at the target host explicitly.** A local CLI whose config selects a default server silently reports THAT server's state (version, agents, uptime) when you meant another — read the command's server banner line before trusting the output, and when in doubt ssh the node and run the binary there.
- **A row's premise can be a produced ARTIFACT, not a repo state.** Audit-family rows cite violation counts from a gatherer's output (per-family JSON under `~/.hermes/audits/`). Verify by reading, not regenerating: check the artifact's `generated_at` against the row's `created_at` for freshness, then sum the `rule_counts` for the cited repo and compare to the row's total EXACTLY. Check `~/.hermes/audits/python-<family>-audit.json` for the FRESHEST `generated_at` before probing a row's cited report — a later gather may already exist, and verifying against the freshest artifact is what keeps the refresh from re-proving a superseded count. Full recipe including the row-minted-before-regen decision (count mismatch = evidence refresh on the row, not a false premise): `references/audit-row-verification.md`.
- **Old rows cite paths that have moved.** Grep the row's cited path inside the repo first; if absent, grep the fleet script dirs (`~/.hermes/scripts/`) for the filename — then refresh the row with the corrected path as an evidence note instead of closing it on the wrong premise or leaving the stale citation in place.
- **A multi-surface premise can be PARTIALLY satisfied — narrow it, don't close it and don't keep it whole.** When a row's premise enumerates surfaces ('no endpoint, no CLI command, no tool'), probe each surface and compare what you find against the row's `created_at` — an implementation that PREDATES the row makes that surface's half stale, while the unsatisfied surfaces keep the row open. Append an evidence note stating exactly which half is stale (name the found surface) and which half stands, rewording the premise to the narrower claim, and commit it like any board edit. Closing on the stale half loses live work; keeping the row whole sends the foreman to re-fix something that already exists.

- **Judge staleness against the row's CURRENT scope fields, not its prose history.** Rows are refreshed in place: `reasoning` (or `detail`) often still carries the ORIGINAL owner directive while `description`, `acceptance_criteria`, `worker_summary`, `commit_hash`, and `created_by` carry the narrowed premise and already-landed work. Before appending any narrowing or evidence-refresh note, read the FULL row object (jq the whole row — never `.detail // .reasoning` alone): a probe result that already matches `description`/`acceptance_criteria` CONFIRMS the row is live as scoped, and is not a newly discovered stale half. Re-noting what the row's own description already claims wastes a board write and can double-narrow a row another lane already narrowed.
- **Let the row's own code define the probe.** When a row's premise is an
  integration against an API, read the cited script's env/URL construction
  first (`BASE = os.environ.get(...)`, table/path f-strings, KEY_FILE default)
  — the code gives the exact endpoint, namespace/table path, and token file to
  probe with, so you never guess a contract or probe with the wrong credential.
- **Discover the live API's request contract from `/openapi.json` before probing it.** Read the endpoint's requestBody schema (properties + required) and the login/token field names from the spec first — guessing body shapes burns a probe round per missing field, auth 401/422s look like verification failures, and the token field name varies (`accessToken`, not always `access_token`). Run the whole auth→create→re-fetch probe as ONE `/tmp` python script (urllib), not a chain of curl pipes.
- **Verify a degrade-path fix by REBUILDING the degraded shape, not by running the check on the healthy tree.** A guard/hardening fix that adds a tolerance (shallow copy, single-root-commit `git archive | git init` copy, grafted history) exercises a different code branch than a full clone — a green run on the healthy repo proves nothing about the branch the fix touched. Reproduce the exact degraded shape (`git archive HEAD | tar -x -C /tmp/copy && git init && git add -A && git commit` for the single-commit case), re-run the check there, and assert the degraded verdict (exit 0 / UNVERIFIED) — plus the healthy-tree run still green.
- For files: verify content, not just presence
- **CLI-flag fixes are the cheapest LIVE verification there is: run the row's own
  tool with the fix's exact flag/output shape and read the result — no worktree,
  no tests, one command.** Merge containment (`git merge-base --is-ancestor`) proves
  the commit landed, but only running the changed behavior proves it works.
- For services: check actual endpoints, not just process status. Read the running version from the service's OWN status payload (`/api/v1/status` → a `version` field) — a dedicated `/version` endpoint often does not exist and its 404 reads as a probe failure rather than a wrong endpoint.
- - **Verify the repo artifact, not the host install.** When a fix ships systemd
  timer/service templates, Makefile targets, or deploy scripts, presence on the
  merged tree + containment is the row's verification; whether the operator has
  INSTALLED the unit on the host (`systemctl list-timers`) is an operator
  decision, not a row defect — name it as a note ('template shipped, host
  install pending') instead of failing the row, and only treat it as live-work
  evidence when the row's own pass criteria say 'timer installed and firing'.
- For rows whose fix is a scheduled task (cron/timer/service), verify the SCHEDULER not the script: `systemctl --user list-timers` (or `crontab -l`) for last-fire/next-fire times plus `journalctl --user -u <unit> --since ...` for exit status and output. A script that reads correctly proves nothing about whether it runs; a timer firing on schedule with clean exits proves the fix live.
- For security: test both positive and negative cases
- For honest null results, document the evidence that shows no issue exists (e.g., productive ticks, passing tests) rather than searching for a non-existent problem.
- **Classify verification timeouts as unverified, not as passes or product failures.** Record the exact command, timeout boundary, and whether any partial output exists; keep the row open until a bounded targeted probe or a completed rerun proves the acceptance criterion. A successful CI run on a different commit or a neighboring test file does not convert a timed-out local probe into verification.
- **Attribute a bare suite `FAIL` before judging a row.** When the tail shows every printed package `ok` but the run ends `FAIL`, the failing package hides in the elided middle — re-run suspects individually, untouched-by-the-fix ones first. `panic: test timed out after 10m0s` with zero `--- FAIL` lines is the per-package default time budget under sibling load, not rot: report package, panic line, and whether the fix touched it.
- **A row's premise can be about the BOARD's own structure, not the repo.** A row claiming 'X and Y are duplicate ids', 'id N is missing', or 'row M cites a moved path' is verified by reading the CURRENT board (G8 raw audit, a direct row read), never against the repo. When the structure was already repaired by an earlier fold/collapse, close the row `complete` with the fold commit hash as evidence — do NOT re-fold, re-file, or leave it pending as fake work.

Update ledger fields for every checked item; mark board-complete rows `verified`
only after the exact probe passes and a ledger read-back confirms the status and
evidence persisted. A board close or foreman note alone is not verification.

### CI-health check (every tick)

Run `gh run list --repo <org>/<repo> --limit 3 --json status,conclusion,displayTitle,headBranch,createdAt` — derive org/repo ONLY from `git remote get-url origin` (strip host prefix and .git): a go.mod module path or CI config can name a different org than origin, and a wrong org 404s like 'no CI surface'. Empty `git remote -v` = no CI surface, skip + note. Empty `[]` = no workflows — not CI rot; note it, file nothing when an open row already tracks the missing surface. A `conclusion=failure` run: first bind the failure to its exact `headSha` and workflow, then classify BLOCKED vs REAL by counting steps (`gh api repos/<org>/<repo>/actions/runs/<runId>/jobs --jq '.jobs[].steps | length'`) — 0 steps = pre-runner billing/org block, NOT a code failure. A failed implementation run followed by a successful board-only run is not one undifferentiated CI verdict: report the implementation SHA/conclusion separately from the current branch SHA/conclusion, and do not call the current head red unless a run for that head fails. Check open rows for one already covering the failure BEFORE filing `INT-CI-<n>`: an existing open row gets the new run id as an evidence refresh, never a sibling row. All green → one line. **This check is a health signal, not a gate:** when `gh` is missing, unauthenticated or billing-blocked (`steps: 0`), the local gates in "Local CI is the gate" decide and the cycle continues — a hosted-CI outage never justifies an idle cycle, a deferred row, or a fleet-wide claim.

