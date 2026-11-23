# Double fire and judge failover

A scheduler can deliver the SAME tick id more than once. Treat every delivery as its own pass over
one release decision — not as permission to redo writes, and not as proof the earlier pass finished.

## 1. Classify the fire before writing anything

Start with the one-command discriminator: `git show <remote>/<default-branch>:.coding-hermes/board/events.jsonl | grep -c '<tick-id>'`. A count of 1 proves an audit event for this exact tick id is already pushed, so a sibling pass for the same fire wrote before you did — go straight to the verification-only outcome and file nothing. A count of 0 means nothing board-level was filed and you classify the remaining surfaces below. Run this probe FIRST: it is one cheap read, and it is the difference between a clean verification pass and a duplicate event on a row a foreman will dispatch.

A count of 0 is not absence of the pass. Projects differ in what a lane may file: a lane whose
sweep record is a rolling row plus a dated report artifact can emit no per-tick audit event at all,
so `events.jsonl`, `git log --grep '<tick-id>'`, and a `releng/<tick-id>.md` check can ALL read
empty on a tick that fully completed. Treat the memory ledger as a co-equal discriminator rather
than the last resort: list the project namespace once and match `attributes.tick` (or the key's
`pass-<n>` discriminator) against your tick id — a hit on the same tick id means the prior pass
exists and this fire is verification-only, whatever the repo-side greps say. Reading three empty
repo probes as "nothing exists" and re-running the sweep is the duplicate pass this ordering
exists to prevent.

Read the repo state the previous firing would have produced, in this order:

1. The sweep artifact on the fetched default branch AND on disk — follow the project's own
   convention rather than a fixed path: it may be `releng/<tick-id>.md` or a dated report under
   `reports/verification/`, so glob the lane's report tree for the newest file and read its tick id
   before concluding that no artifact exists.
2. The board row for the release line (`tasks.jsonl`) — status, evidence fields, carrier SHA.
3. The event log (`events.jsonl`) for an audit row with your actor and this tick id.
4. The memory ledger key for this tick id.

Six outcomes, six actions:

- **Nothing exists** — a CANDIDATE first pass, not yet a fact: run the empty-ledger probes in §2b
  (evidence-dir artifacts and row `detail.evidence[].run_id` carrying this tick id) before doing the
  full sweep, because a lane that never mirrored its decision into memory leaves all four probes
  above empty on a tick that already ran twice.
- **Row exists, artifact does not** — a half-fire. The earlier firing landed a carrier commit and
  then died or ran out of context. Write the artifact, append one audit event, do NOT file a second
  `RELEASE-*` row (the existing row already owns the work), and say in the artifact that this pass
  supplied the missing record.
- **Artifact exists, board record does not** — the mirror half-fire: the earlier firing landed the
  artifact and its carrier but filed no row refresh and no audit event, so the rolling `RELEASE-*` row
  still carries a superseded premise. Refresh that row in place (title, reasoning, detail, `updated_at`)
  and append one audit event; do not mint a sibling `RELEASE-*` row merely because none was filed.
  Check first whether the row is pending and dispatchable — a stale premise on a dispatchable row is a
  live hazard for the next foreman, and that hazard is what justifies the extra carrier commit.
- **Artifact exists, latest work missing** — a later pass; append, never replace (see
  `releng-tick-operations.md`).
- **Record landed, delivery did not** — the artifact and carrier are on the default branch, the
  ledger key exists, and no message exists in the delivery thread. Re-measure at the live tip,
  then send once; the missing work is transport, not analysis. Do not re-run the sweep as if the
  numbers were unproven.
- **Everything exists** — verification-only pass. Re-derive the facts from live git/CI, confirm or
  contradict the recorded decision, and report; add no new durable rows. The minimum re-derivation
  set: live tip vs the candidate named in the record, the range census from the last real tag
  (commit count, type histogram, breaking count, product-path count), exact-SHA CI on the live tip
  with its ABSENT_BY_PATH_FILTER classification, tag immobility (`git ls-remote --tags` peel equals
  the recorded commit), repo-owned gate reruns, and the still-open blocker rows. A contradiction
  found here is reported, not silently rewritten.

  An acceptance arm whose probe is refused by the unattended gate or sandbox stays UNVERIFIED for
  this pass: report it as blocked with the criterion named, leave the row pending, and never infer it
  from a sibling's note or from the surrounding host looking repaired. Verifying one arm of a
  multi-arm blocker row does not license closing it — the remaining arms are the reason it is open.

  Count the carrier commits the branch already holds for this tick id before writing anything. Once a
  second pass has re-certified the artifact, this fire produces NO commit: the report is the delivery
  and the only durable artifact is one ledger key under the fire discriminator (`pass-<n>`). A further
  carrier commit exists only to give its own tip a CI receipt, which by construction does not exist at
  write time, so each extra pass lengthens the line the next pass must classify. Missing memory keys
  are not a defect worth a commit either — write the key, say the previous pass never mirrored it,
  and leave the artifact alone.

A record that names a `carrier` while its `carrier_ci_run` belongs to a different commit is a
labelling defect, not a false release: the carrier field was set to the evidence commit, or the row
was never re-bound after a sibling's bookkeeping commit. Report it plainly and leave it alone. Repair
it only inside a pass that must re-bind anyway; a commit whose sole purpose is to correct the pair
generates a new tip whose own CI does not exist at write time, so the repair reproduces the defect
one commit later.

Probe the binding instead of eyeballing it — three independent pairs, each of which can disagree on
its own:

```bash
jq -c 'select(.id=="<row-id>")|{status,candidate,d: (.detail|{artifact_sha256,carrier,carrier_ci_run,carrier_ci_status})}' <board>/tasks.jsonl
sha256sum releng/*.md | grep '<row artifact_sha256>' || echo "BINDING ARTIFACT NOT PRESENT"   # (a)
gh run view <carrier_ci_run> --json headSha,status,conclusion \
  --jq '"\(.headSha[0:8]) \(.status)/\(.conclusion)"'                                        # (b)+(c)
```

(a) the digest must match an artifact that exists NOW, (b) `carrier` must equal the run's `headSha`,
(c) `carrier_ci_status` must equal that run's live conclusion. Any disagreement makes the row's
receipt STALE even when its `candidate` is still the right tree — the candidate field is often the
only input that is current. Report the three readings verbatim and mark the row's durability
UNVERIFIED-BY-DESIGN for this pass; re-binding it from a verification-only fire is what starts the
re-anchor loop, and a stale receipt on a correct candidate misleads nobody who reads the digests. Four re-anchor commits in one day across the same line is the tell that the loop
has started — stop re-binding and hand the mismatch to the foreman.

## 1a. A recorded `failed` is not a census of what landed

The scheduler records the fate of the RUN, not of the work. A fire can be stamped `failed` at the
moment its gateway call timed out while the writer that did the measurement committed a carrier
minutes later — so the ledger and the board look empty for that tick while the default branch
already carries its output.

Before treating a re-fire as a redo, attribute the stamp against the branch:

```bash
git log --oneline --since="<recorded failure timestamp>" --until="<now>" <default-branch>
```

A commit in that window whose message names this lane is the dead fire's actual product. Then state
which leg is missing — measurement or delivery — and do only that leg: a partially delivered tick
re-measures at the live tip (the tip moved past the dead fire's tree) and sends once, rather than
publishing a second sweep of identical numbers. Never report the tick as successful because its
carrier exists, and never report it as a total miss because the scheduler said failed.

## 2. One durable record per tick id

- One artifact at `releng/<tick-id>.md`, edited in place across passes with a pass/correction note.
- One audit event for the tick; allocate its id by checking the value, not max+1 (a foreman row can
  have taken the max seconds ago).
- One rolling release row for the line. A re-fire that adds coverage refreshes that row's note; it
  does not mint a sibling row.
- One ledger key per fire, named `<project>/releng/<tick-id>-<discriminator>` where the discriminator
  escalates (`-doublefire`, `-triplefire`, …; `pass-<n>` where the lane numbers passes) — never
  overwrite the record of a fire that already exists. Carry `prior_fires` in `attributes` as an array
  of the earlier keys and set `fire: "second|third|…"`, so the whole chain is readable from the newest
  record alone without walking the namespace.
- The board writers store text values verbatim, so stage every field in its own file with no trailing
  newline: a lone trailing `\n` lands inside `title` and `updated_at` and is invisible until someone
  greps the row. Compute the artifact's `sha256` AFTER the final artifact edit — the row and the ledger
  must cite the digest the commit actually contains, not the pre-edit one.

## 2a. Identify the fire number in ONE read, before any measurement

The project ledger is the fastest fire counter and is co-equal evidence with the board probes in
section 1. Read it through the STORAGE path: `list_keys` with the tick prefix at `maxDepth: 4` (2-3
stops at the tick directory and hides the per-fire keys), then one SQL projection over the memories
view. Do this BEFORE the first mutation of the pass — before the first artifact append, row note or
carrier — because that is the only point where knowing the ordinal can still change what you write.

```sql
SELECT key, timestamp, json_extract_string(attributes,'$.fire') AS fire,
       json_extract_string(attributes,'$.decision') AS decision
FROM memories WHERE key LIKE '/releng/ticks/<project>/<tick-id>%' ORDER BY timestamp
```

The memories view has no `content` column (its columns are `id, key, domain, timestamp, author,
action, embedding_text, attributes`) and `DESCRIBE` is rejected as non-SELECT, so a `SELECT content`
probe fails on the column list rather than on the read path; take the decision from `attributes` and
`embedding_text`. Never open with `recall`/`search`: the semantic leg is the one that hangs, and a
300 s timeout there costs the whole budget while proving nothing — `list_keys` plus this query answer
the ordinal in seconds over the same data.

COUNT ORDINALS FROM KEYS, NOT FROM SQL ROWS. `list_keys` returns one entry per key, but the memories
view returns one ROW per append, so a fire whose record was rewritten under the same key (a
canonicalizing second write of the same fire) shows twice while still being ONE fire — a family of
seven keys can return eight rows, and counting rows invents a pass that never ran. Count the deduped
key set for the ordinal and treat a duplicate row as evidence that the earlier text of that fire was
superseded. Project `key, embedding_text` rather than `SELECT *` so the whole chain stays readable in
one response, and read the HIGHEST-suffix record's `embedding_text` in full: it carries the carried
verdict, the certified candidate SHA, the CI run ids, the blocker set and the previous fire's
measured readings, which is what lets this fire re-derive only the surfaces that can move instead of
re-measuring the product.

Two or more keys naming the SAME tick id means this delivery is a repeat fire: the decision, the
certified candidate and the blocker set are already recorded, so the pass is a re-derivation of the
surfaces that can have moved (tip, product-path diff, exact-tip CI, tags/releases, deploy surface)
and NOT a re-measurement of the product. Read the newest record first — it carries `prior_fires` and
the carried verdict — and contradict it explicitly if a fresh reading disagrees rather than writing a
fresh independent narrative beside it. Count the discriminator keys, not the suffix letter: a family
showing `pass-27`, `pass-27-fireb`, `pass-27-firec`, `pass-27-fired` is four fires deep in under an
hour, so the fifth fire carries the verdict and mints nothing. If you only discover that AFTER
pushing an artifact section and a row note, do not revert (a revert pair is more churn on a shared
default branch); publish one correction that states the true ordinal, the earlier fires that minted
nothing, and that this fire's carriers were a deviation from carry-only, so the next fire inherits the
pattern instead of repeating it.

## 2b. An empty ledger is not a first fire

Lanes mirror their decision into memory inconsistently: a fire can land its artifact and its board
row and write no ledger key at all, so a prefix recall returns zero for a tick id that has already
been dispatched twice. Reading that zero as "nothing exists" and then measuring is how a lane
re-derives a decision three times and reports the third as news.

Probe the two surfaces the fire cannot avoid leaving before concluding anything:

```bash
# (a) artifacts: the board evidence dir, globbed on the tick id
ls -lat .coding-hermes/board/evidence | grep '<tick-id>'
# (b) rows: the run id stamped into detail.evidence[] by the row writer
jq -r 'select(.detail.evidence!=null)|.id as $i|.detail.evidence[]|[$i,.run_id,.ts]|@tsv' \
  .coding-hermes/board/tasks.jsonl | grep '<tick-id>'
```

- Two artifacts for one tick id with differencing suffixes (`<tick>.md`, `<tick>-fire-b.md`) mean
  two completed fires; the newest also tells you which fire YOU are (`-fire-c` next).
- The row's `detail.evidence[].run_id` plus its `ts` is the fire's own timestamp — read it before
  writing a new row, because `boardctl create` refuses a re-detected finding and the refusal is not
  a licence to retitle it into a new one.
- When the artifacts and rows exist but no ledger key does, the missing record is the deliverable:
  write it under the explicit fire suffix, state in the body that the earlier fires never mirrored
  their decision, and do NOT write retroactive keys for them — the chain reads correctly as "fires
  A and B unrecorded here, fire C measured and recorded".
- Re-measure the surfaces that can have moved even when the verdict is carried: tip, product-path
  diff, exact-tip CI (classify a `[ci skip]` push as absent-by-design rather than green), tags and
  Release objects, and the deployed-binary reading. A carried verdict with fresh readings is the
  output; a carried verdict quoting last fire's numbers is not.

## 2c. Prove "nothing shipped" by tree fingerprint, not by a diff list

A product-path diff list answers "which files differ"; the release question is "can any input to the
decision have moved". Fingerprint the tree with the bookkeeping paths excluded and compare the two
SHAs — one line per SHA, and it survives console truncation that eats a long `--name-status` list:

```bash
for c in <prior-candidate> <live-tip>; do
  git ls-tree -r $c | grep -v -P '\t(\.coding-hermes/|\.gitreins/|docs/release-evidence-)' \
    | sha256sum | cut -c1-16
done
```

Identical digests mean every non-bookkeeping byte is the same, so the semver census, notes coverage
and version-surface answers are unchanged by construction — the pass is bookkeeping-only and the
verdict is CARRIED, with the digest quoted as the receipt. Different digests mean the product moved
and the pass is a fresh decision regardless of what the prior record says. Quote the digest pair,
not the prose conclusion: a later reader can re-run the two commands, and cannot re-run your summary.

Re-derive the tip with git every fire even when the previous pass named it. A carried SHA is a claim,
and the tip usually advances by bookkeeping commits between fires — the fingerprint is what turns
"the tip moved" into "the product did not".

## 2d. Correcting a number YOU published

A wrong measurement already in a pushed carrier is corrected forward, never rewritten: the earlier
carrier and ledger key stay byte-identical so the correction is auditable against what was published.
One firing produces one correction carrier carrying all three parts:

1. A named correction section in the artifact that states the retracted value beside the measured one
   and the command that produced it (shell arithmetic on `stat`/`systemctl` outputs, not mental math).
2. A rolling-row refresh that overwrites the stale field and adds a sibling `*_correction` field
   naming what it superseded — a reader who only inspects the live field must still learn it changed.
3. A NEW ledger key with `correction_of: <prior key>`, `prior_carrier: <prior carrier sha>` and
   `wrong_value_retracted` carrying the retired text verbatim. Never edit the prior key: its value is
the evidence that the number was published.

State the verdict consequence explicitly. If the correction widens a window (staleness, ungated range,
unmeasured days) without flipping the decision, say "verdict unchanged, window N wider than reported"
— that sentence is what stops the next pass from treating the repair as a re-decision.

A correction that also disproves a stored acceptance note is a reason to REOPEN the row that owns it,
not just to fix your own field: see `release-readiness-evaluation.md` for the check-time rule.

## 3. Never let a re-fire repeat a side effect

Re-fires are the main way a lane publishes twice, pushes twice, or double-counts a census. Before
any write, ask which populating call already happened. If the earlier pass published, you verify; if
it tagged, you never tag again; if it wrote the board row, you edit that row. `NEVER force-move an
existing tag` applies hardest here: a second pass that re-reads the tag as "missing" is usually
resolving an unfetched ref, not a deleted tag — fetch tags before concluding.

## 4. Judge failover

When a judge run times out, is cap-killed, or returns no verdict, the work is not failed — the
verdict is ABSENT. Poll the run's own status surface once, then read the verdict artifact
(`.gitreins/history/<date>/<id>/verdict.json`) rather than re-running the judge into the same cap.
Never re-run two judge runs concurrently in one checkout: shared coverage/report directories make a
spurious tier-1 failure that looks like a real regression. Absent verdict at delivery time is
reported as UNVERIFIED with the run id; it is not a green, and it is not a reason to withhold a
record that is otherwise complete.
