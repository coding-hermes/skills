# Readiness pass discipline

Depth for a recurring release-readiness sweep: a lane that re-fires several times inside one window, measures, and decides GO/NO-GO without developing. Load this when a readiness pass is not the first for its window, when a prior pass left a re-fire note, or when the same blocker refuses on consecutive passes.

## 1. Establish the fire ordinal from the ledger, before measuring

The pass ordinal is a ledger fact, not a board fact. Board rows are shared, lag, and are sometimes unwritable; the append-only event log who-ran-already is not.

- Query the pass-key family for the window — e.g. `/project/<p>/release/<window>/pass-NN` — and read the highest ordinal. This fire is the next one.
- Read every prior pass's artifact section **and any explicit re-fire note**. The note names the exact inventories the next pass owes, usually because the tip moved while the prior pass was writing. Discharge those first; re-running a prior pass's whole measurement set burns the budget and adds no evidence.
- When the ledger bridge is unavailable at the opening of the pass, derive the ordinal from the carrier's own record rather than guessing or skipping it: `git log --oneline --since=<window> | grep 'pass [0-9]'` and `ls releng-evidence-<window>/ | grep pass`. The lane writes its ordinal into commit subjects and artifact filenames (`... pass 2 of tick <id> — NO_CUT at <sha>`), which is enough to know you are pass N+1. Confirm from the ledger at the close; the opening derivation is cheap, the closing confirmation is the authoritative one.
- Fire count is not row count. Grepping the tick id over the board returns one line per row a single fire's carrier batch wrote, not one per fire: a fire that lands an artifact, a board row and an event can produce three or five hits for one run. Resolve the ordinal from the pass keys and treat a repeated tick id inside one carrier batch as one fire — a pass that reads its own row batch as a fire family over-counts passes and then re-measures what already landed.
- At the end, list the family again. Exactly N keys and no N+1 means no sibling fired concurrently. If a sibling did, reconcile against its evidence rather than filing a parallel verdict.

## 2. Recover the row inventory from the prior artifact, not the board

The prior artifact's "debt filed" / "rows filed" section enumerates the row ids, their owners, and what each covers. This is what prevents duplicate dispatch.

- Read it **before** filing anything. A finding that maps to an existing open row gets **no new row**. Name the owning row in the artifact instead, and escalate the *staleness* in prose: how many consecutive passes it has now blocked.
- A row that reproduces across consecutive passes with zero progress is a scheduling problem, not an evidence problem. Saying so in prose is the escalation; a second row per artifact is the duplicate-dispatch hazard.
- If the board read is **refused** (guard/consent, not an error), the safe direction is to file nothing. You cannot certify non-duplication, so do not write. Record the refusal, cite the newest verified census as *carried* (with its ordinal), and state plainly that this pass cannot certify the current row count.

## 3. Classify a tip advance: product change vs bookkeeping

A judged commit followed by a bookkeeping commit (board rows, ledger dirs, notes) leaves the cut SHA unjudged even though the product tree is byte-identical.

- Prove the classification, don't assume it:
  - `git diff --name-only <judged> <tip> -- . ':(exclude).coding-hermes' ':(exclude).gitreins' ':(exclude)docs/releases'` → `0` paths
  - `git show --stat <tip>` → only bookkeeping paths
- Then state the gap as **bookkeeping-only**, which is strictly narrower than "unjudged product", and say so explicitly so the next reader does not inherit the older, worse framing.
- It still does not close the gap. Report `0 of N verdicts name <tip>` and keep the verdict non-green: the binding rule is that a verdict must name the cut SHA. Classification changes severity, never the verdict.
- Symmetrically: a verdict naming an *ancestor* whose product diff to the candidate is empty is the useful-evidence case — read `verdict-artifact-reading` and the `releases` step-5 binding rules rather than re-deriving a label.

## 4. CI truth is per-SHA, never "latest run on main"

```bash
gh api "repos/<org>/<repo>/commits/<sha>/check-runs" \
  --jq '.check_runs[] | [.name, .status, .conclusion] | @tsv'
gh api "repos/<org>/<repo>/actions/runs?head_sha=<sha>" \
  --jq '.workflow_runs[] | [.id, .name, .event, .branch, .status, .conclusion, (.run_number|tostring)] | @tsv'
```

Cite run id, workflow, event, status/conclusion and run_number. Green runs at neighbouring SHAs are context, not proof of the candidate. Derive `<org>/<repo>` from `git remote -v`, never from the directory name.

- A release driver that shells `gh run list --commit <sha> --workflow <file> --status success` can refuse with "no successful run found for <sha>" while `check-runs` for that same SHA already reads all-green: the runs index lags check-run completion by seconds. Classify it as a transient index lag, never as red CI — poll `check-runs` to terminal, wait a few seconds, re-run the driver once. Do not bypass the gate to get past it and do not report the SHA as failing; the gate refuses in the safe direction and clears on its own.
- Every bookkeeping commit re-opens a CI-green-on-HEAD gate. Batch all remaining board/artifact writes into ONE commit, poll CI on that final SHA, and only then re-run the driver's dry-run. Stewarding a pass to a 4/4 preflight and then pushing another commit leaves the repo whose readiness nobody has measured — if a later write is unavoidable, the pass owes one more poll-and-dry-run cycle on the new tip before reporting.

## 5. A clean-tree preflight gate deadlocks against a co-harness that writes untracked artifacts

Symptom: the release driver refuses at its dirty-tree gate, pass after pass, on a tree nobody edited.

Mechanism: the gate tests `git status --porcelain --untracked-files=all` for emptiness, while a co-harness (gitreins, coverage, lint caches) deposits untracked runtime artifacts — history dirs, state and lock files — on every run. If those paths have no ignore rule (`git check-ignore -v <path>` → rc=1), the gate can never pass in any checkout where the harness has ever run.

- Reproducing the refusal across consecutive passes is the proof it is structural, not incidental dirt. Say "Nth consecutive reproduction", not "residue present".
- **Committing the artifacts is not a fix.** It clears one run and re-dirties on the next; that treadmill is itself the evidence that the gate and the harness disagree by design.
- The durable fix is an ignore rule for the harness's artifact paths, or excluding them in the gate. File it against the row that already owns the residue.
- Gates **after** a refusing gate stay `UNVERIFIED` (observed refusal), not passed. Either peel (move the residue aside, re-read, restore) or say so — do not narrate later gates as if they ran.
- **Ignore rules cannot fix TRACKED artifacts.** When `git ls-files <artifact dir>` is non-empty the harness outputs are in the index, so no `.gitignore` line will clean the gate; the fix is `git rm --cached` on each generated path (leaving the files on disk) plus ignore rules so they cannot return. Prove it, do not assert it: delete every artifact, run the harness's own regeneration command, and show `git status --porcelain --untracked-files=all` printing nothing afterward.
- Enumerate the whole generated set before dispatching the fix. Untracking only the file the refusal happened to name leaves the rest tracked and re-dirties the gate on the next harness run; read the artifact directory listing (`ls -a <artifact dir>`) and untrack everything regenerable in one commit. A follow-up dispatch for "the remaining ones" is the price of skipping the listing.
- Separate authored config from generated output by what the harness does with it, not by its directory. A manifest whose fields (interfaces, ports, mount points) are hand-written and never rewritten by re-initialization is config; untracking it ships checkouts without it. Keep it tracked even when a row's acceptance criterion literally demands `git ls-files <dir>` prints 0 — prove the criterion's INTENT (a regeneration never dirties the tree) and record the deviation in the row's note and the artifact. Closing on intent-plus-disclosure is honest; mutating shipped config to satisfy a count is not.

## 6. Version and notes hygiene that decides a first publication

- Count breaking markers in **both** legal positions before proposing semver: a subject `!` before the colon, and a `BREAKING CHANGE` trailer in the body. Prose that mentions "breaking" is not a marker.
- With no prior tag, feats present and no breaking marker, the first publication is the minor (`v0.x.0`). Do not escalate a major-bump confirmation unless a marker actually fired.
- Grep the changelog for terms naming the subsystems the candidate actually ships. Zero mentions means the record describes a smaller product, and notes curated from it will be wrong — that is a blocker row, not a wording nit.
- The notes artifact, the changelog and the authorization flag are **separate** gates. Absence of any one blocks regardless of version.
- Authorization is never inferred. Unset means NO-GO: propose the version, describe the cut, do not tag.
- An authorization row is one whose **title** names the target and the version. A raw `grep -c '<marker>'` over the board is not a count of authorizations: readiness rows quote the marker inside their own acceptance criteria (the criterion literally instructs `grep -ci 'RELEASE-cut' ... prints at least 1`), so the count includes the record that *forbids* the cut plus its audit events. Resolve every hit to row id, status and title before reporting, and state that the residual hits are quotation — otherwise a NO_CUT pass appears to have found its own permission.

## 7. Ledger write and readback

- Write the pass event through the DuckBrain MCP `remember` bridge: `key` (the pass key), `domain: event`, `namespace`, `attributes` (decision, tip, carrier commit, ci run, verdicts-naming-tip, candidate version, any unverified leg), and an `embedding_text` that is a self-contained summary — it is what future recall surfaces.
- A 401 from the HTTP surface is a credential-source problem, not permission to skip the record. The MCP path carries its own credentials and is the working route.
- The `memories` view has no `content` column. Selecting it fails with `Binder Error ... Candidate bindings: "action", "timestamp", "domain"`; read `embedding_text` (plus `json_extract_string(attributes,'$.<field>')`) instead, and pass `content` as a STRING on write. The write's return also gives you `id`, `timestamp` and the resolved `partition` — quote those, then re-query the key to prove it landed.
- Nest each pass under the tick's own key (`<tick-key>/pass-N`) when the window has one tick per fire. What matters is that the whole family shares a prefix so a single `LIKE '<prefix>%'` lists every ordinal — that one query is both the opening ordinal and the closing sibling check.
- Read back from disk, do not trust the write return alone:

```bash
F=~/duckbrain/namespaces/<ns>/event/<YYYY-MM>/current.jsonl
grep -c '<pass-key>' "$F"
jq -r 'select(.key=="<pass-key>") | [.id,.timestamp,.domain,.author,(.attributes.decision)] | @tsv' "$F"
jq -r 'select(.key|test("/release/<window>/pass-")) | [.timestamp,.key] | @tsv' "$F" | sort
```

The last query doubles as the sibling-collision check of step 1.
- Never print the key. Mask env in diagnostics: `env | grep -i duckbrain | sed 's/=.*/=<set>/'`.

## 8. Artifact append and path-scoped carrier commit

- Append a delta section to the rolling readiness artifact; never rewrite prior passes. Build the section in a scratch file, then `cat scratch >> artifact` — a shell heredoc is the fragile path.
- When the shell write path is itself gated (heredocs and inline interpreters refused), the `patch` tool anchored on the artifact's final unique paragraph is the equivalent append: anchor on a full sentence from the tail, keep the new section self-contained so it does not inherit the anchor's wording, and re-read the tail to confirm the join.
- Commit the artifact alone: `git add -- <artifact> && git commit -F <msg-file>`, and confirm `git diff --cached --name-only` was the single file. Path-scoped staging stops a concurrent writer's dirt riding along.
- Push and prove parity: `git rev-list --left-right --count origin/main...HEAD` → `0 0`, and `git log -1 --format='%H %s' origin/main` is your commit.

## 9. Report shape

Order: **decision first** (GO/NO-GO, carried or changed), then the evidence table with a receipt column, then what the pass closed, then what is still blocked and which row owns it, then what was deliberately not mutated.

- Every table row needs a receipt the reader can re-run: a command result, a run id, a file path, a verdict id.
- State measurement holes plainly (refused read, unverified census, gates after a refusal) and label prior-pass values as carried with their ordinal. A hole named is evidence; a hole omitted is a false claim later.
- Say what you did **not** do at the end: no tag, no code edit, residue left as found, board not written and why. Leaving the blocker reproduced rather than cleaning it keeps the next pass honest.
- When the board is withheld because other lanes are writing, quantify the writers instead of asserting activity: `git diff -U0 <board>/tasks.jsonl | grep '^+' | grep -o '"id": *"[^"]*"' | sort -u`. Name the foreign row ids in the artifact. A later pass that sees the writer count rise (one lane, then two) has a strictly stronger reason to withhold than the pass before it — say so, so withholding does not read as inertia.

## 10. A re-fire after prior passes committed is a steward pass, not a second sweep

Trigger: the tick id you were handed already appears in the carrier's log (`... pass N of tick <id>`) or an evidence artifact for it already exists. Recognition costs one command; a full re-sweep costs the budget and risks contradicting a fresh artifact with a drifted one.

- Re-measure only the **decisive** facts — the ones whose change would flip the verdict: candidate SHA and parity (`git fetch origin --tags`; `git rev-list --left-right --count origin/main...HEAD`), tag/release inventory (`git tag`, `gh release list`), CI presence at the candidate, whether any verdict names the candidate, and every gate row's current status.
- Carrying is legal only when the tree is provably untouched: state the identity check (candidate SHA unchanged and equal to the remote tip) in the same breath as the carried values.
- The artifact MUST carry a **"what was deliberately not re-measured"** section naming each carried leg and why. A steward artifact that silently omits the census reads as a full sweep and will be cited as one by the next pass.
- Report the delta since the prior pass, separated by owner: rows another lane wrote during the tick are delta, not findings. Finding nothing new is a valid result — write "delta: board-only, none release-relevant" instead of manufacturing work.
- Do not re-file. Every open blocker should already own a row; the pass's useful output is verifying those rows still carry executable acceptance criteria (an AC-less row can never be dispatched) and that the blocker map is unchanged.
- Leave the standing NO_CUT record intact. Consecutive passes agreeing on the same candidate is stronger evidence than a fourth attempt to find a reason to cut.
- **When the re-measurement proves the verdict CANNOT change, the pass owes no artifact at all.** The trigger for appending a delta section is a fact worth re-reading from the repo. If the product diff since the certified candidate is docs-only, the tag/release inventory is still empty, the candidate is still the remote tip (parity `0 0`), the tip's CI is green and authorization is still absent, then the ledger pass-key IS the record: no artifact, no carrier commit, no board row, no version-surface edit. Put in the ledger content the identity check that licenses the carry, every leg deliberately not re-measured with its ordinal, and an explicit `reason_no_artifact` — otherwise the missing artifact reads to the next reader as a missed deliverable rather than a decision.
- A prior pass's artifact for the same tick is a different case from no artifact at all. When a lineage file already holds passes 1..N-1, append this fire as one dated delta section (its own readings, the identity check licensing the carry, the not-re-measured list) and keep that as the tick's durable record: minting a second artifact is the duplication error, but skipping the record because "nothing changed" strands the tick when scratch is pruned.
- Prove tag/remote agreement without fetching, in one call: `git ls-remote origin 'refs/tags/<tag>*'` returns both the annotated object and its peeled `^{}` ref — compare against `git rev-parse <tag>` and `git rev-parse '<tag>^{commit}'`. Two object ids matching locally and remotely is the receipt; an inventory listing (`git tag`, `gh release list`) alone does not prove the tag was never moved.
- To prove a published release body equals the repo's notes file, hash both sides with matching newline handling: `gh api repos/<org>/<repo>/releases/tags/<tag> | jq -r '.body' | sha256sum` against `sha256sum <(git show '<tag>:<notes path>')`, and repeat for the HEAD copy. Use `jq -j` when the notes file carries no trailing newline — one newline of drift makes a byte-identical note hash differently and reports a false mismatch.
- Discharge the prior pass's in-flight leg instead of inheriting it. A CI leg the last pass reported as running is the one decisive fact that can change with zero product movement: poll it to a terminal conclusion (`gh api .../commits/<sha>/check-runs`, loop on `[.check_runs[]|select(.status!="completed")]|length` until 0, bounded) and record final counts plus the workflow run id. A closed tip-CI receipt is the legitimate new evidence of a zero-mutation steward pass — reporting "still in progress" when it finishes inside your own pass throws away the only thing you measured.

## 11. Run the carrier in a real environment

A carrier commit is only as good as the guard verdict that admitted it, and the guard needs an interpreter.

- Measure in place when you can. A lane checkout that is clean and zero commits ahead may be fast-forwarded to the fetched tip (`git merge --ff-only origin/main`) so the pass measures the real tip where an environment already exists, instead of a throwaway detached worktree whose guard cannot import the package. Disclose the pointer move in the artifact: it creates no commit, no push and no tree change.
- Classify the guard verdict; do not read its exit code as a bare pass. `rc=0` with `Tier 1: DEGRADED PASS (skips: lint=no staged files)` is the correct outcome for a carrier that stages no source files — report the skip as a skip and never as lint coverage.
- The skip reason is the guard's own accounting, not a fact about what you staged: a carrier that staged a docs/artifact path can still be told `lint=no staged files`. Quote the message verbatim, disclose that lint did not cover the staged path, and do not upgrade the line to a clean pass because secrets and tests did run.
- Escalation after repeated refusal is a row edit, not another attempt. Once the same leg refuses on several consecutive fires, name that count in the artifact and make the owning row's acceptance require a host that permits unattended installs; rephrasing or splitting the command to slip past the gate is the same forbidden reach-around.
- A harness-refused command is `UNVERIFIED` — not a failure of the artifact, and not a licence to reach the same result another way. Carry the leg with the row that already owns it, say how many consecutive passes it has now refused, and do not re-attempt inside the same fire; a later fire may run the identical command once.
