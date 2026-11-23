# Releng tick operations

Recipes that apply to every releng delivery, kept out of SKILL.md so the always-on
rules stay readable. Each section is a rule plus the command that measures it.

## Tick start: skill_view dedup means read the file from disk

A tick brief that orders "load the X skill" can get a dedup response from
skill_view — "content unchanged since loaded earlier, refer to the earlier
result" — with NO content returned, because the gateway session previously
loaded that skill. On an unattended tick the earlier result is not in context
(compaction), so the pass starts blind. Read SKILL.md from disk instead — but
do NOT assume the flat layout `~/.hermes/skills/<name>/SKILL.md`: the library
nests many skills under category directories
(`~/.hermes/skills/<category>/<name>/SKILL.md`) and the layout is mixed per
skill, so a flat-path read misses a skill that exists and reads as "skill
missing". Resolve the real path in one bounded glob, then read:

    for d in ~/.hermes/skills/<name> ~/.hermes/skills/*/<name>; do
      [ -f "$d/SKILL.md" ] && echo "$d/SKILL.md"; done

The same dedup applies to linked references: `skill_view(name, file_path=…)`
can return the unchanged-status without content too — read the reference file
directly at the resolved skill_dir path.

## Carry-only fire: the surfaces, one probe each

A fire over an unchanged product tree re-derives only what can move. Take the first
probe first — it decides whether anything else is owed:

    git fetch origin --tags --quiet
    TIP=$(git rev-parse origin/<default>)
    git diff --name-only <certified-sha> "$TIP" -- . ':!releng' ':!.coding-hermes' ':!reports' | wc -l
    git rev-parse HEAD "$TIP"; git rev-list --left-right --count "$TIP"...HEAD; git status --porcelain

Zero paths means the verdict CARRIES: no census, no rebuild, no product gate rerun. Then
re-read only the movable surfaces, all read-only:

    gh run list --repo <org>/<repo> --limit 40 \
      --json databaseId,workflowName,headSha,status,conclusion \
      --jq ".[] | select(.headSha==\"$(git rev-parse HEAD)\") | [.databaseId,.workflowName,.status,.conclusion]|@tsv"
    gh run view <prior-run-id> --json workflowName,status,createdAt,updatedAt   # baseline = updatedAt - createdAt
    git ls-remote --tags origin                       # tag OBJECT and its ^{} peel, both
    gh api repos/<org>/<repo>/releases --jq length    # 0 = still a first publication
    grep -rl '<full-40-char-candidate-sha>' .gitreins/history/*/*/verdict.json | wc -l   # 0 = gate unmeasured
    ls docs/dogfood dogfood-evidence 2>/dev/null      # newest battery + whether it binds the candidate
    command -v <artifact>; systemctl list-units --all | grep -i <project>
    grep -nE '<major>\.[0-9]+\.[0-9]+' README.md go.mod | head; sed -n '3p;25p;28p' CHANGELOG.md

`gh run list` has no SHA filter — the `headSha` select needs the FULL 40-character SHA, and
`--limit` must reach past every run the lane pushed since the tip: a limit that stops short
returns an empty list that reads exactly like "no run registered for this tip".

Three classifications that decide the record:

- A leg `in_progress` for LESS time than the same workflow's own prior run is SLOW, not
  stuck. Quote the baseline duration beside the elapsed one; file no stuck-run row and mint
  no carrier for a leg that is merely mid-build.
- A `failure` on a bookkeeping carrier whose product tree is byte-identical to a candidate
  that passed the same job is a FLAKE INSTANCE. When a pending row already owns that test or
  assertion type, name it measured-and-carried in the record — no new row, no event, no
  carrier — because the product gate did not move.
- A version-surface disagreement (build metadata vs README/CHANGELOG banner) is a carried
  finding owned by its hygiene row. Never pre-bump it on an unauthorized cut: the version
  stamp and the dated changelog section ARE the release commit.

A carry fire's entire durable output is ONE memory key (`.../pass-NN-fire<letter>`) holding
the decision, both SHAs and every reading above. If no reading differs from the prior
fire's, say so and mint nothing; the duplicate-schedule count (N fires of one tick id over
an unmoved tree) belongs in the report as an owner line, never as a board row.

## Release-notes coverage is measured against the certified tip

A driver that extracts the release-notes section from the changelog publishes it
VERBATIM. The section is written at version-prep time, so it freezes while the
branch keeps moving, and no heading or date reveals the drift. Gate on coverage,
not existence:

    git rev-list --count <version-prep-commit>..<candidate>          # total landed after prep
    git log --no-merges --format='%s' <version-prep-commit>..<candidate> \
      | grep -cE '^(feat|fix|perf)(\([^)]*\))?!?:'                  # material ones

That grep counts a LOWER BOUND when it is run over a `%h %s` line: `^` anchors to the
hash, so a subject one field later never matches and the tally silently collapses while
the range looks measured. Classify the subject alone (`--format='%s'`), and assert the
per-class tally sums to `git rev-list --no-merges --count` with a non-conventional bucket
carrying the remainder. When a per-class histogram and a grep count disagree, the
CLASSIFIER is wrong — never cite either number until they reconcile, and never let the
smaller one stand as "the" material count.

A nonzero material count means the section COULD be stale even though it is dated
and its Range line looks authoritative — it does not prove it is. Counting material
commits after prep measures the EXPOSURE; only a per-CITATION check measures the
GAP — and the citation form has to be the one the changelog actually uses. Probe
commit SHAs against a section that cites finding ids and every material commit reads
MISSING: a 100% false-positive rate that looks like total notes failure and will file
a blocker on a section that is already correct. Read the section first and identify
the token class it cites (finding ids, PR numbers, SHAs), then count gaps in that
class. The reconcile work lands as ordinary `docs(release): reconcile …`
commits that add entries without moving the version-prep sha forward. Carrying the
count alone refiles the same blocker pass after pass while the section is already
correct:

    awk '/^## \[<version>\]/{f=1;next}/^## \[/{f=0}f' CHANGELOG.md > sec.txt
    for s in $(git log --no-merges --format='%h %s' <prep-sha>..<candidate> \
               | grep -E '^([0-9a-f]+) (feat|fix|perf)' | cut -d' ' -f1); do
      grep -q "$s" sec.txt || echo "MISSING $s"; done

When the section cites finding ids instead of SHAs, the gap instrument is the id token
extracted from each material subject, checked against the version section — and the
counts worth reporting are both the id-bearing subset and the gaps inside it:

    awk '/^## \[<version>\]/{f=1;next}/^## \[/{f=0}f' CHANGELOG.md > sec.txt
    git log --no-merges --format='%h %s' <prep-sha>..<candidate> \
      | grep -E '^[0-9a-f]+ (feat|fix|perf)' > mat.txt
    # for each subject, pull its id tokens, then require each in sec.txt
    grep -oE '([A-Z][A-Z0-9]*-)+[0-9]+' mat.txt | sort -u > ids.txt
    while read -r t; do grep -qF "$t" sec.txt || echo "GAP $t"; done < ids.txt

Report it as `N of M id-bearing material commits covered, K gaps`, and triage the gaps
by whether the BEHAVIOUR is described: a gap whose change adds a new hard prerequisite
(a tool the build now requires, a flag that now fails closed) is substantive and gets a
row; a gap that is only a missing attribution for behaviour the section already
describes is not worth a row. Check the prerequisite claim against the build file, not
against the commit message — the message says what the author believed, the Makefile
says what a consumer now has to install.

Zero MISSING discharges the coverage blocker and it must stop being copied forward;
name the reconcile commits you found so the next pass does not re-litigate it. What
usually remains is only the numeric Range preamble, which re-stales on every later
commit and therefore has to be refreshed AT the cut commit rather than in its own prep
pass — refreshing it early buys nothing and re-opens the same finding.

The prep row's acceptance must require the RECOUNT plus this citation check, not
"a section exists".

## Re-delivery probes: match the artifact NAME form, not the tick id

Artifacts are named from the tick, but repos shorten the id. A file called
`release-evidence-<YYYY-MM-DD>-<HHMM>.md` is derived from the tick's timestamp,
so grepping the full tick id returns nothing and the pass concludes it is first.
Before editing an existing artifact, read the complete remote-tree file and retain its
prior sections byte-for-byte; a re-delivery appends a new pass/correction section and
never replaces the historical report with a fresh one:

    git ls-tree -r --name-only origin/<default> | grep -i releng      # find the family
    git ls-tree -r --name-only origin/<default> | grep <date>-<HHMM>  # the stem
    git show origin/<default>:<artifact> | grep -n '^## Pass'         # how many passes landed

A third form prefixes the LANE name onto the full tick id — `releng/<project>-<tick-id>.md`, e.g. `releng/crier-releng-2026-11-09-17-55-22.md`. Probing `git show origin/<default>:releng/<tick-id>.md` then exits 128 while the artifact sits right there, which reads as "no prior pass delivered". Enumerate the family first; an exit-128 path guess is not evidence of absence:

    git ls-tree -r --name-only origin/<default> -- releng/

Tick notes have their own home WHEN a repo uses them: `.coding-hermes/tick-notes/`, a SIBLING
of `.coding-hermes/board/`, not inside it — probing `board/tick-notes/<note>.md` returns ENOENT
for a note that exists, and that reads exactly like "no prior pass delivered". Measure the
directory on the FETCHED tree rather than in the checkout:

    git ls-tree -r --name-only origin/<default> -- .coding-hermes/tick-notes/ | wc -l

Zero is a real and common answer: many repos have no tick-notes corpus at all, and their
durable artifact home is whichever directory they already populate — usually
`.coding-hermes/board/reports/` beside the sweep rows. Write the artifact where the board and
the next pass actually read it; do not mint a notes directory that no reader greps, because an
empty directory you created turns a delivered pass into a file nobody opens. Say in the report
that repo-local notes are absent and the record went to the ledger, so the next pass does not
spend a probe rediscovering it.

A `write_file` refusal ("Refusing to overwrite <path>") is therefore positive proof the
artifact is there and was never read — treat it as a presence signal, read the file, and
append with `patch`. Routing around the refusal (new filename, different directory) is how
a single line's decision ends up scattered across two artifacts.

After a final-tip re-anchor, update the existing artifact header and append the new pass before computing its digest; do not put the pre-edit digest into the final pass or row. Calculate the digest from the exact final bytes that will be staged, and write that value to the board row only after the artifact edit is complete.

Two signals that a sibling delivery already ran minutes ago: the newest commits on
the default branch are `docs(releng)`/`board(releng)` pairs, and their CI run ids
postdate your tick start. Read the artifact from the FETCHED blob and append a new
`## Pass N` section; never create a second file for the same tick.

When the lane fired MORE THAN ONCE for the same line, several tick-stemmed files exist
and none of them is named after your id. The file that owns the current pass is the one
whose `Certified candidate` / baseline header names the state you just measured — not the
one whose timestamp matches your tick, because a later tick's file routinely carries the
correction for an earlier tick's record. Append there and name the owning file in the
report; minting a third file for one line scatters a single decision across three
artifacts that later passes must reconcile by hand.

When the new pass certifies a DIFFERENT candidate, rewrite the artifact's header
certification line in the same edit — do not only append. Readers take
`Certified candidate: <sha>` first, and a file whose header still names the superseded
sha contradicts its own Pass N section. Keep the correction dated and named
("pass N — pass M certified `<old sha>`") so the trail reads append-shaped even though
the header line is replaced in place.

The row needs the same treatment, and a rebind that touches only the structured
`detail` is the defect: `detail.candidate` is where a machine reads the state, while
`title` and `reasoning` are what every human and dispatcher reads FIRST. A pass that
re-stamps the candidate into `detail` and leaves the title naming a superseded sha has
produced a row that contradicts itself, and the next pass faithfully re-derives the
wrong sha from the text. Move title, reasoning and any `blocked_reason` that names a
sha in the same write as `detail`, and keep the original reasoning body verbatim
beneath a labelled correction block rather than editing it — the old text is the only
record that the candidate field moved at all.

Header-in-place, body-append — never a whole-file replace, even after reading the file. `write_file` can discard every historical pass while the new header still looks correct. Use a targeted patch for the certification line and an append-only operation for the new section; never copy a shortened report over the tracked artifact. Then prove it:
`grep -c '^## Pass'` rises by exactly one and the earlier pass text still greps. Quote that number as "N `## Pass` headings", never "N passes": the heading is what was counted, and the semantic restatement is a claim nothing can re-grep — the artifact's prose need not use the word at all. An artifact
that lost its history is worse than one with a stale header, because the superseded SHAs it
used to name are the only trace that the candidate field moved at all.

For a DELTA-ONLY re-delivery write two short things and no new row: a `## Pass N`
section when the project's decision doc is the artifact, plus ONE
`boardctl event --type audit --task-id <existing sweep row> --detail @<json>`
when the branch moved under the earlier pass — new tip sha, new run id, the
re-measured numbers, and the release layers re-verified rather than copied. A second sweep row for the same tick id is the duplicate the board cannot absorb.
Pass `--no-tick-write` when appending that event: a board whose first line is a task
row (no `board.jsonl` header) fails the writer's tick-write step AFTER minting the
event, so the flag is what keeps the append clean. Prove it landed and quote the
minted id in the commit subject:

    boardctl event --type audit --task-id <existing row> --actor releng \
      --detail @<payload.json> --no-tick-write
    tail -2 <board>/events.jsonl | jq -c '{id,event_type,task_id,actor}'

Build that payload from values that are TRUE at write time. The event is minted before
the commit that carries it, so a `carrier` field can only hold `PENDING_PUSH` or an
invented sha, and the tracked JSONL cannot be corrected afterwards on an unattended tick
— an in-place rewrite of a staged board file is refused, and `patch` cannot reach a key
inside the event's JSON-encoded `detail` string anyway. Leave the carrier out of the
detail, land the event inside the carrier commit, and name the carrier in the commit body.
A placeholder in durable board state is a data defect the next pass has to interpret.

The stored `detail` field is a JSON-encoded STRING, not an object: `(.detail|keys)` returns nothing and a filter that assumes an object reports a landed event as malformed. Read fields back through `(.detail|fromjson)`, e.g. `jq -r '(.detail|fromjson).pass'` — but `fromjson` ABORTS the whole filter on legacy events whose `detail` is null or absent, so gate it rather than dropping events: `select(.detail|type=="string") | (.detail|fromjson).key`, or inline `(.detail|if type=="string" then fromjson else {} end)`.

Before hand-appending to a board that has no writer, assert the tail is the id you expect
instead of trusting a line count — a sibling append between your read and your write
silently reorders the log and your row lands out of sequence:

    test "$(jq -r .id <board>/events.jsonl | tail -1)" = "<expected-id>" \
      && cat <row.json> >> <board>/events.jsonl
    tail -1 <board>/events.jsonl | jq -r '.id, .event_type, .task_id'

When the pass's only commit is board/docs, that commit still dispatches the repo's CI:
poll for its exact-SHA conclusion and quote the run id before calling the pass green.
A green run on the released tag says nothing about the evidence commit that records it. If that run is still `in_progress` when the bounded polls run out, the carrier verdict is PENDING with its run id and the report must say so — the repo's own gate fallback (`no completed run for <sha> — checking main tip`) is not evidence for your carrier, and the parent's green run stays the candidate's receipt. If a pre-commit guard fails because a detached worktree lacks dependencies or the guard cannot execute, first prove the staged path set contains only intended evidence/board bookkeeping, then use the repository-approved bookkeeping bypass only for that commit; record the guard as FAIL/UNVERIFIED and never let the bypass imply that the product gate passed. Compose the message file expecting to quote the guard: in a repo whose test leg runs on EVERY commit — any Python repo, where `tests (full)` is not path-filtered the way Go legs are (`skips: go_build/go_lint/go_tests=No Go files staged`) — a venv-less detached worktree fails the guard on evidence-only and board-only commits too. The failed attempt is not wasted: HEAD stays put, the staged set survives, so rewrite the message file with the guard's own failure text and re-commit with the bypass in one step rather than re-running `git add`, and assert HEAD moved afterwards. Re-run or cite substantive gates separately on the candidate. When appending a pass section to an artifact whose last line carries no trailing newline, `cat section >> file` lands as `-1/+N` in `--numstat` because the final old line is rewritten with one; prove append-only by re-hashing the first N pre-existing lines, never by requiring a zero-deletion diff.

Read board state from the fetched remote before deciding whether work remains:

    git show origin/<default>:<board> | jq 'select(.id == "<id>")'

A shared checkout can be behind while another lane owns its changes; do not fast-forward
it merely to inspect a row. Use a clean detached worktree at the fetched tip for writes,
and verify the committed result from the remote after pushing.

### The tip can move more than once, and the movement can be material

A busy lane can reject and rebuild one pass two or three times inside an hour. Before
re-running a 1500-commit census, classify the movement — it is often bookkeeping only:

    git diff --name-only <pass-N-sha>..<fetched-tip> | grep -v '^\.coding-hermes/' | wc -l

Zero means every changed path is board/evidence bookkeeping, the code tree is
byte-identical to the sha whose census already ran, and the census CARRIES. Record it as
a carried measurement naming both shas and the empty path set — not as silently restated
numbers, and not as a fresh census re-derived from a tree that cannot have changed. Two
row fields keep a reader from mistaking a descendant for an unmeasured candidate: hold
`detail.candidate` at the current tip while naming the product-certified SHA separately
(`certified_candidate`, or `candidate_certified_in_artifact`), and stamp
`carried_product_measurements_at` with that certified SHA. Without the pair, a
bookkeeping-only descendant reads as a new candidate nobody gated, and the next pass
either re-runs a census that cannot change or files a blocker against it. Any
NONZERO result is a material movement: re-derive the range and re-check the decision
before reusing a single class count.

A SHARED checkout's `origin/<default>` is mutated by every sibling process that fetches, so the
same `git diff <sha>..origin/<default>` can return different answers minutes apart with no push
anywhere in between. Capture the ref once — `TIP=$(git rev-parse origin/<default>)` right after
your own fetch — and compute every range, census and diff against that literal SHA; then
re-fetch and re-capture immediately before the final re-anchor and the decision. A symbolic ref
resolved twice in one pass is two different measurements wearing one name, and the artifact
that mixes them cites a tip it never measured.

A busy lane can reject and rebuild one pass two or three times inside an hour. Every
rebuild that moves a MATERIAL path is a fresh census, not a re-push: re-fetch, re-derive the
range, and re-read the NEWEST commit's subject before assuming the decision still holds. A pass
whose movement is confined to board/evidence bookkeeping CARRIES the census instead — name both
SHAs and the empty material path set, and still re-anchor every receipt that any commit
invalidates (hosted run at the new tip, tags, release objects, board row states). Preserve multi-line
commit bodies with NUL/record delimiters or a checked-in parser; line-oriented tab-field
awk over `%b` counts continuation lines as separate records and can produce a plausible
but false total. Reconcile the class sum to `git rev-list --count` and sample subjects
before reusing the result. A commit that lands
between your probe and your push does not merely invalidate the tip sha — if it is a
`feat`/`fix` it invalidates the DECISION, and a no-cut note published beside a freshly
landed feature is a wrong durable record that outlives the tick.

When the movement is material, the pass owes a NEW row (due, bump, blocker, executable
unblock) rather than another no-cut note, and the earlier note gets one line saying it
was true at the sha it named and was superseded minutes later. Commits you built and
then discarded unsent stay reachable only from their own worktree: name them in the row
or the commit body so the next pass is not hunting an unexplained sha.

Rebuild by replaying the writer in a NEW detached worktree at the fetched tip. Do not
reset the shared tree to get there — the reset is refused outright on unattended
surfaces, and the superseded tree is itself the evidence that the pass ran.

## Delivery target lives in the lane config, not in inference

The scheduler config block for the lane carries the destination literally:

    grep -n -A10 'name = "<project>-releng"' ~/.hermes/fleet.toml   # deliver = "telegram:<chat>:<topic>"

Read that field. Do not infer a thread from a neighbouring lane (a qa/pm lane for
the same project posts somewhere else), and state in the report that no outbound
message id is exposed when the surface offers no readback.

Deliver with the file form rather than inline text, and keep the body under the
platform's single-message ceiling (Telegram rejects over ~4096 characters, so an
evidence table plus decision has to fit or be split deliberately). Re-read the exact
report file immediately before sending; do not compose a second, shorter summary from
memory after the evidence work is complete, because that can silently omit the final
candidate, carrier, CI state, or UNVERIFIED leg:

    hermes send -t <deliver-target> -f <report>.txt --json | jq -r '.message_id // .id'

A bare `sent` in the tool output is a transport ack, not a receipt: quote the message
id, or record the delivery as unverified. Write the report file with a plain heading
you have re-read before sending — a typo'd lane name in the first line survives into
an outbound message nobody can edit.

## The repo target is the board symlink, not the path in the lane prompt

A lane prompt names a checkout path that may not exist on this host, and the stand-in
workdir is something else again. Resolve the repository from the lane's own wiring before
searching the filesystem:

    readlink -f <workdir>/.coding-hermes/board        # → <project checkout>/.coding-hermes/board
    PROJ=$(dirname "$(dirname "$(readlink -f <workdir>/.coding-hermes/board)")")
    git -C "$PROJ" remote -v                          # the org/repo every gh call must use
    gh api repos/<org>/<repo> --jq '.name,.default_branch'

The board link is authoritative because that is where this lane's rows have to land, and the
`git remote` of the checkout holding it is the only source for the org/repo argument. A
A `find ~ -maxdepth 3 -name '*<project>*'` sweep returns namespaces, sync workdirs and
non-checkouts — each hit costs a probe and none of them is the repo. A name-similar SIBLING
is the worse trap: a fleet commonly carries `<project>` and `<project>flow` (or
`<project>-rs`) as SEPARATE repositories with separate remotes, and a rename note about one
does not mean the lane's target moved. Confirm identity with `git -C <candidate> remote -v`
per hit — the org/repo SLUG decides which tree you measure, never the directory name or the
parent folder — and never carry a commit range, tag inventory or CI receipt across the two.
absent, state that in one line of the artifact, name the remote you actually measured, and
file on that repo's board: a sweep that silently measures a differently-named checkout leaves
the next pass re-resolving from zero.

## One canonical row per topic

Boards accumulate non-terminal readiness rows for the same topic — two sweeps of
different dates, neither closed. Pick the ONE whose `acceptance_criteria` already
carries the executable contract, refresh it in place (title, note, evidence,
corrected `reasoning`), and give a genuinely different work item its own row.
A third readiness row for a topic that already has two leaves the foreman
decomposing duplicates.

When a row's acceptance invents an owner gate for a minor cut, the gate is
refuted, not honored: correct the `reasoning` with the correction block ABOVE the
original text (extract it verbatim, concatenate, run the skill's
`board-row-reasoning.py`), because readers take `reasoning` first and a note
appended beneath it corrects nothing.

## A row that cannot run its own acceptance command is blocked, not pending

An acceptance criterion that needs a capability this lane does not have — a local
toolchain home that is not mounted, a registry login, a deploy target — will never go
green here, and a `pending` row is an invitation for a foreman to dispatch a worker into
that same environment failure. Mark it explicitly and keep the row open:

    boardctl update <ID> --blocked-reason "Acceptance criterion requires '<cmd>' to exit 0 in this lane; <capability> is unavailable (<BLOCKER-ROW>), so it fails before <first real step>." \
      --note "Unblock path: <BLOCKER-ROW>. Hosted CI stands as build evidence but does not satisfy the literal criterion: run <id> green at <sha>."

Do not close the row to make the board look clean, and do not leave it dispatchable
after writing the reason — verify `status` and `blocked_reason` from the FETCHED remote
board, since the point of the flag is what the NEXT reader sees.

### An unexplained `blocked` is the opposite defect

A row reading `blocked` with a null or empty `blocked_reason` is not a decision, it is a
dropped row: the status removes it from the dispatch pool while nothing on the board says
who must unblock it or how, so a release can sit behind a row no lane is allowed to pick
up. Attribute the state from the event log before touching it:

    git show origin/<default>:.coding-hermes/board/events.jsonl \
      | jq -c 'select(.task_id=="<ID>") | {id,timestamp,actor,detail}'

An update whose detail is just `{"status":"blocked"}` is the whole finding. Then either
write the real reason with the recipe above, or — when the acceptance IS executable in
this repository — restore `pending`, retitle the row to the work that actually remains,
and rewrite `acceptance_criteria` to match. Report the restoration explicitly in the
record and the commit body: a silent status flip reads to the next pass as an owner gate
it must keep honoring.

## A re-fire after this tick's own cut is a post-release sweep, not a second cut

When a lane fires again with the same tick id whose earlier firing already cut and
published the release, that firing owns the POST-RELEASE sweep. Re-verify the Release
object (state, complete asset set, downloaded sidecars), classify the range from the NEW
tag to the current tip, and refresh the same canonical row in place. Say in the record
that the baseline is the just-cut tag, so a reader cannot mistake "no material commits
since the tag" for "ready to cut" — the two produce the same near-empty census and
opposite decisions.

Nothing about a green tag-SHA run licenses a second tag under the same id, and a second
readiness row for the same line is the duplicate the board cannot absorb. A defect found
while sweeping the shipped release is filed as its own row (or corrected forward on the
existing one); it does not become an excuse to re-cut.

A later pass on the same id RE-DERIVES the release layers instead of quoting the earlier
record, and the strongest single receipt is artifact digests: re-read the registry's own
index and compare every filename, size and sha256 against the cut-time table. Identical
digests prove no re-upload, no yank-and-replace and no silent rebuild between passes:

    curl -s https://pypi.org/pypi/<pkg>/<version>/json \
      | jq -r '.urls[]|"\(.filename) \(.size) \(.digests.sha256)"'
    git ls-remote <remote> refs/tags/<tag>          # annotated object + peeled commit, unchanged

That pair is what turns "published and untouched" from a restatement into a measurement.
Name the two open blockers and their live state in the same block, so the pass reports
what is still unfixed rather than only what re-checked clean.

## A checksum sidecar is evidence only when it verifies OFF the build host

`sha256sum <pkg>.tar.gz > <pkg>.tar.gz.sha256` records whatever path you passed to it.
If that path is absolute or names a staging directory, `sha256sum -c` on the build host
resolves the STORED path and never reads the downloaded tarball — a tautological green
that ships with the release. The digest can be perfectly correct while the sidecar is
unusable by every consumer, so "asset present, digest matches release notes" does not
discharge the checksum arm.

Required shape — one line, no slash in the filename field:

    a96838c4…(64 hex)··hilo-0.4.1-x86_64-linux.tar.gz      # two spaces, bare basename
    awk 'NF!=2 || $2 ~ /\// {print "BAD " $0}' <pkg>.tar.gz.sha256   # empty output = portable
    wc -c <pkg>.tar.gz.sha256                                       # compare to the previous release

Required receipt — three arms in a fresh directory that holds ONLY the published assets,
with the packaging/staging path absent:

    sha256sum -c <pkg>.tar.gz.sha256                     # as shipped; must print "OK". A path
                                                          # it can only read on the build host is a FAIL
    sed 's|[^ ]*/||' <pkg>.tar.gz.sha256 > base.sha256   # negative: rewritten field
    sed -i 's|  |  /nonexistent-build-host/|' base.sha256 && sha256sum -c base.sha256   # rc=1, "FAILED open or read"
    printf '%s  %s\n' "$(cut -d' ' -f1 <pkg>.tar.gz.sha256)" "<pkg>.tar.gz" > good.sha256
    sha256sum -c good.sha256                             # rc=0, "OK", same digest

A changed sidecar shape between consecutive releases is a packaging REGRESSION, not a
house style — diff the two sidecars' line count and byte size before attributing intent.

When all of this fails, the verdict is: everything else in the release is certified, the
sidecar alone is broken, and the fix is an ASSET re-upload (new `.sha256` naming the bare
filename). Never re-cut, never move or delete the tag, never rebuild the tarball to "fix"
a text file. File it as its own row with the clean-consumer arms as acceptance, including
the negative arm — an acceptance that only says "sha256sum -c exits 0" is satisfied by the
same tautology that shipped.

This arm is re-measured on EVERY pass, including a pass whose own earlier note recorded it
PASS: the earlier pass most likely ran on the build host where the absolute path still
existed. When you correct such a note, say so in the appended section ("the shipped
sidecar embeds an absolute path; that arm was tautological") rather than leaving a stale
PASS in the durable artifact that later passes would copy forward.

## Deferred-tool argument preflight

Treat deferred-tool schemas as executable contracts, not hints. Before a DuckBrain or other deferred-tool call, construct and inspect the complete serialized arguments object, including every required field and the explicit namespace resolved from the project's established ledger family. For a read, never send `{}`, omit the query, or accept a successful response from the default namespace when a scoped namespace was required. For a write, never send a partial payload when the schema requires `key`, `domain`, `attributes`, and `embedding_text`. If the wrapper drops the populated arguments or returns a missing-argument/schema error, correct the serialized payload once and make one direct populated call; do not repeat the same empty or unscoped shape. If the corrected call cannot be dispatched or read back, report the memory leg UNVERIFIED while preserving the release evidence locally.

## Ledger key shape for releng lanes

Namespace `releases`, key family `/releases/<project>/<YYYY-MM-DD>-<topic>`,
domain `event`. Probe both homes before writing: the project's own namespace carries
`/project/<project>/...` sync, board and foreman keys and holds no releng decision
family, so finding keys there is not evidence you found the right home — a release
decision appended beside sync records is invisible to the next pass that greps its
own family. Attributes carry what a later pass must compare:
`candidate`, `carrier`, `baseline_tag`, `bump`, `decision`, `ci_run`,
`live_blocker`, the row ids, and `artifact_sha256`. One pass-scoped key per delivery keeps re-deliveries addressable while the family stays discoverable by
prefix. When an earlier pass on this project already established a releng family —
a commit trailer naming `memory=duckbrain:/project/<project>/releng/...`, or
existing keys under that prefix — CONTINUE that family instead of minting the
`/releases/...` home beside it: two homes for one lane's decisions is exactly the
invisibility the probe above exists to prevent, and pass-scoped keys under a
timestamped project prefix stay just as addressable. Name in the record which
family you continued, so the next pass greps the right prefix. Read the key back and compare the stored `attributes` after writing.

A project's OWN namespace can already carry the family — `/projects/<project>/releng/<tick-id>` beside its board and foreman keys. That is the continuation case, not a third home: add one pass-scoped key per tick under that prefix and name the continued family in the record. Minting a date-prefixed `/releases/<project>/<YYYY-MM-DD>-<topic>` home beside it is exactly the invisibility the probe above exists to prevent.

### Confirm the write from the partition file, and keep the suffix shape

Namespace listing gives you the ordinal and the host default in one call; read the key list at a
depth that shows the per-fire component (a `pass-NN` / `pass-NN-refire` child sits one level
below the tick directory):

    # MCP: list_namespaces → note `currentNamespace`; then list_keys(prefix="/", maxDepth=4, namespace=<project>)
    f=/home/kara/duckbrain/namespaces/<ns>/event/$(date -u +%Y-%m)/current.jsonl
    grep -c '<your-key-tail>' "$f"
    jq -c 'select(.key=="<full-key>")|{key,decision:.attributes.decision,cand:.attributes.candidate_sha[0:8],fire:.attributes.fire}' "$f"

Two rules ride on that read:

- Pass `namespace` EXPLICITLY even when the listing marks the project's namespace as the host
  default (`isDefault: true`, `currentNamespace`). The default is a connection property, not a
  fact about this project, and a host-default change silently repoints later fires that omitted it.
- Continue the family's existing suffix shape rather than the generic `-fire<letter>` example:
  a chain at `pass-01-refire` continues at `pass-01-refire-b`, never `pass-01-firec`, or one
  tick's fires stop being enumerable by a single prefix probe.

A store-partition grep is the durability receipt; the writer's 2xx only proves transport.

## A not-due verdict has to publish its path set

The post-cut sweep and the cut decide on the same number — commits or files that touch INSTALLED code — and that number only means something when the exclusion set travels with it. On one tag range, excluding `.coding-hermes/` alone leaves 21 commits while excluding `.coding-hermes/`, `.gitreins/`, `docs/`, `CHANGELOG.md` and `README.md` leaves 8. Both are true; quoting "8 commits since the tag" without the set lets the next pass re-derive 21 and call it movement, and quoting 21 without the set makes a bookkeeping-only range look like a backlog.

    git log --format='%H %s' <tag>..<tip> | sed 's/^[0-9a-f]* //' | cut -d: -f1 | sort | uniq -c | sort -rn
    git log --oneline <tag>..<tip> -- . ':!.coding-hermes' ':!.gitreins' ':!docs' ':!CHANGELOG.md' ':!README.md' | wc -l
    git diff --name-only <tag>..<tip> | grep -vE '^(\.coding-hermes/|\.gitreins/|docs/|CHANGELOG\.md|README\.md)' | wc -l

Reconcile the class sum against `git rev-list --count` and read the tally honestly: `cut -d: -f1` leaves a subject with no colon — a QA/PM tick title — as the WHOLE subject, which is a non-conventional row, not a new class. The verdict is NOT DUE only when the material classes are zero AND the path-filtered diff is empty; either nonzero means re-derive the decision instead of reusing a prior pass's no-cut note.

Deployed-binary staleness pairs with that as a one-line proof: `git merge-base --is-ancestor <installed-commit> <tag>` returning 0 says the release content is ABSENT from the running binary, whatever its `--version` banner claims. Cite the commit/file gap between that ancestor and the tag rather than release names ("two releases behind"), and leave the row open for the lane that owns installation.

## A board diff with rows you never wrote is a CONCURRENT WRITER, not normalization

After a create/update batch, the shape you expect from your own writes is
`+2N` appends (one per create) plus `+K/-K` on exactly the rows you updated. The
event log is a SEPARATE shape: each `create` mints one `task_created` event, but an
`update` may emit no event at all — a board whose `task_updated` stream stopped
long ago keeps accepting updates — so `+1/−0` on `events.jsonl` beside `+2/−1` on
`tasks.jsonl` is a correct one-update-plus-one-create delivery. Prove an update from
the ROW (status, evidence count, `detail.evidence[-1].tree_fp`), never from an event
that was never minted, and never hand-append an event to make the log look right. When
`git diff --text --numstat -- <board>` reports MORE changed rows than that, do not
assume the writer re-rendered siblings — attribute it:

    jq -r 'select(.updated_at >= "<your first write, ISO>") | "\(.id) \(.updated_at)"' <board>
jq -r 'select(.id=="<id>") | to_entries|sort_by(.key)[]|"\(.key)=\(.value|tojson)"' \
  <(git show origin/<default>:<board>) <board>     # key-by-key delta of one row

A row you never named whose `updated_at` is MINUTES AFTER your own writes is a
foreign writer on the same board (another lane's foreman, a qa/pm tick). Distrust
`/proc/*/cwd` attribution here: those shells are transient (the pid is gone by the
time you look) and the pid you do find is usually your own tool session.

Prove the writer is row-scoped instead of guessing:

    git worktree add --detach <probe-wt> <fetched-tip>
    boardctl update -C <probe-wt> <one-row> --note 'writer probe'
    git -C <probe-wt> diff --text --numstat -- <board>     # expect 1 1

A single-line delta proves your tooling did not touch the foreign rows, so the
foreign edits are someone else's in-flight work: own only your rows.

Do NOT land them together, and do NOT hand-splice. Building a commit by awk-
replacing the foreign lines with the origin blob still ships a hand-edited board
and leaves the canonical file diverged. Replay the WRITER instead, in a detached
worktree at the fetched tip — same updates, same creates, same flags — commit
there, and push with `git push <remote> HEAD:<branch>`. Name the excluded rows in
the commit body so the exclusion reads as a decision, not an accident. Expect the
canonical checkout to end up mid-rebase with `UU` on BOTH board files while the
sibling replays onto your carrier: leave it alone, and verify your rows from
`git show origin/<default>:<board>` rather than from the working tree.

## An ABANDONED rebase orphans the commit it was replaying

`UU` on both board files while a sibling is actively replaying means leave it alone.
The same shape later, with no process holding that tree, means the rebase DIED — and
the difference matters, because a rebase re-points `refs/heads/<default>` to `onto`
BEFORE it replays the todo:

    ls -d <repo>/.git/rebase-merge && cat <repo>/.git/rebase-merge/{head-name,onto,msgnum,end}
    git -C <repo> reflog --date=iso -6            # rebase (start)/(abort) entries timestamp the moves
    git -C <repo> rev-parse HEAD refs/heads/main origin/main   # branch == remote tip, HEAD detached
    git -C <repo> rev-list --count origin/<default>..<pre-rebase-sha>   # 1 = orphaned, no branch holds it
    git -C <repo> cat-file -e <pre-rebase-sha>; echo "still_here=$?"

The tree can still be clean by CONTENT (board equal to the remote blob, `jq -c .`
rc=0, empty `git-rebase-todo`), so content-cleanliness is not state-health: read the
state files, not the diff. Recovery is a FORWARD cherry-pick of that sha onto the
current tip with board conflicts resolved as a union, because each side owns rows the
other never saw — the orphan's rows are absent from the remote, and the newer passes
on the remote are absent from the orphan. Enumerate both directions before resolving
(`git diff --numstat origin/<default> <orphan> -- <board paths>`, then name the ids on
each side). Never `git rebase --abort` a died rebase "to get clean": abort restores
the pre-rebase branch, making the orphan the tip and re-conflicting on the next pull.
File one row naming the sha, the rows at risk, the forward-recovery command, and the
fact that the object is the only copy until gc prunes it — a verify-only lane does
not rebase a sibling's work.

Board-only commit hooks: in a worktree the hook may print
`Tier 1: DEGRADED PASS (skips: go_build/go_lint/go_tests=No Go files staged)`
instead of staying silent. Both shapes are non-evidence about the code tree; the
carrier's own hosted exact-SHA runs are the gate.

## Board rows whose evidence path is gitignored

`.gitignore` can declare an evidence directory untracked BY POLICY, and the repo's
comment then names where durable evidence actually lives. Check before trusting any
row's `detail.evidence`:

    git check-ignore -v <artifact>                        # rc=0 means the path is ignored
    git show origin/<default>:<artifact> | sha256sum      # fails: the receipt cannot run
    git ls-tree -r --name-only origin/<default> -- <dir>  # what IS tracked there

When the path is ignored, the protocol's "hash the artifact from the fetched
remote" receipt is UNRUNNABLE: record it UNVERIFIED with the host-local hash and
line count beside the row's `tree_fp`, never as a pass. Do not repair it by
`git add -f` through the rule; file ONE row for the destination decision, and
check that the directory the comment names actually exists — a comment pointing at
`history/` can describe a tree that is really `.gitreins/history/`, and creating the
literal path it names would mint a second, wrong home. Prefer inline `--reasoning`
for new rows while the destination is undecided: the board row itself is tracked,
so the decision survives without the artifact.

## A shipped release's census cannot be reproduced from its tag

Once the tag exists, `git rev-list --count <baseline>..<tag>` is LARGER than the cut
record's total, because the version-prep commits (`release: prepare …`, plus any
follow-up that fixed a prep-time red) landed between the census and the tag:

    git log --no-merges --format='%s' <baseline>..<tag> \
      | sed -E 's/^([a-z]+)(\(.*\))?!?:.*/\1/' | sort | uniq -c | sort -rn

The material classes come out identical and only the totals move. Reconcile
class-by-class and name the prep commits as the difference; never edit the cut
record's total to match the late measurement — the classes are the evidence, the
total is an artifact of when you counted.

## A tag object that differs locally is drift in the LOCAL tag, not a release defect

`git fetch --tags` can warn that a local tag "would clobber" the remote one while both point
at the same commit. Compare the object id and the PEELED commit separately before calling it
divergence: an annotated tag's object id is minted when the tag object is created, so a
locally re-created tag yields a different object for byte-identical content.

    git rev-parse <tag> <tag>^{commit}          # local tag object + the commit it points at
    git ls-remote <remote> 'refs/tags/<tag>*'   # remote tag object + remote peel
    git merge-base --is-ancestor <tag>^{commit} <candidate>; echo "contained=$?"

Identical peel means the release content is intact: report both object ids beside the shared
peeled commit and leave the tag untouched. Do not silence the warning by deleting and
re-pushing, or by force-moving, the tag — that rewrites what consumers already fetched, and it
is precisely the mutation a readiness sweep must not perform. Drift is a finding only when the
PEELED commits differ, and even then it goes on the board as a row, never into a `git tag -f`.

## A prior pass's evidence entry can be durable in the row and absent from the remote

A delivery can write `detail.evidence[]` into the working board and never commit it,
so the local row reads correct forever while `origin/<default>` — and every later
reader of it — never carries the entry. Detect it by reading the count from BOTH
trees, not from the row you were handed:

    git show HEAD:.coding-hermes/board/tasks.jsonl \
      | jq -r 'select(.id=="<ID>") | ((.detail.evidence)//[])|length'
    jq -r 'select(.id=="<ID>") | ((.detail.evidence)//[])|length' .coding-hermes/board/tasks.jsonl

## Edit one board row without churning the file

Running `jq -c` over a whole `tasks.jsonl` re-serialises every line in the writer's own
canonical style, so a one-row status change lands as hundreds of +/- lines. That diff is
unreviewable and, on a shared board, collides with every sibling writer. Edit the physical
line, not the file:

```bash
<SKILL_DIR>/scripts/board-row-set-json.py <board>/tasks.jsonl <ROW-ID> --json acceptance=acc.json --write
# <SKILL_DIR> is the skill's own directory (load-time `skill_dir`), NOT <repo>/scripts.
# Only when that packaged helper is itself unusable, splice the physical line:
# without the helper: copy untouched lines verbatim, replace only the target line
awk -v id='<ROW-ID>' 'index($0,"\"id\": \"" id "\""){print NEW; next}{print}' old > rebuilt
```

- `--json key=path` json.load()s the file and stores the STRUCTURE it finds, so a scalar
field needs a file whose entire content is that scalar (`"pending"`, not
`{"note":"pending"}`) — an object silently writes an object into a field the board and
the foreman read as a string. Prose goes through `--text`, because a literal newline
inside a quoted JSON string is invalid JSON and the payload is rejected before the
writer ever runs. Both are caught by the dry run the helper prints by default; read the
reported `chars` per field before adding `--write`.

A repo with no board writer and no helper still has to be edited by splicing lines, and
that path needs its own assertions because nothing else will catch them. Back the file up
beside the pass, count the rows whose id matches and ABORT unless it is exactly one (last
line wins only when you have proven the id is duplicated on purpose), re-dump the other
lines as the bytes you read — `ensure_ascii=False` with default separators keeps existing
UTF-8 prose (em dashes, accents) identical instead of escaping it into a whole-file churn —
and after writing assert that the set of changed line indexes equals exactly the target
index, that every line still parses as JSON, and that the total line count is unchanged.

Prove the shape with numbers, not by eyeballing:

```bash
git diff --text --numstat -- <board>/tasks.jsonl              # +1/-1 per edited row, +N appends
git diff --text -U0 -- <board>/tasks.jsonl | grep -c '^-'    # only the rows you touched
```

A normalised value diff (`jq -cS . | sort` both sides) proves no DATA was lost; it does
not prove the file was not churned. Line count and +/- are the receipts for that, and the
reviewer reads the second one.

## Event ids are a MIXED-TYPE namespace

Legacy events can carry string ids (a tick-derived slug) beside the numeric counter, so
`jq -s 'map(.id//0)|max'` aborts: `string (...) and number (1) cannot be added`. Take the
numeric maximum and continue from it:

```bash
jq -s 'map(.id) | map(select(type=="number")) | max' <board>/events.jsonl
```

Hand-appending events is legitimate only on a board with no writer (`boardctl event`); each
appended object must carry `task_id`, `event_type`, `actor`, and the tick id so the next
pass can attribute it, and the tail must be re-read to show the ids landed in order.

When a commit or push of your own board writes is blocked (consent gate, concurrent
writer, refused command), the delivery is NOT durable and must say so in the report: name
the exact row ids that exist only in the carrier worktree, and copy the rows plus the tick
note to a path outside the pruned scratch tree (`/var/tmp/<lane>-<project>-<date>/`) so a
foreman can commit them without re-deriving your measurements. Do not retry or rephrase a
blocked command, and do not report the rows as filed — they are pending until they appear
in `git show origin/<default>:<board>`.

A higher working-copy count is that gap, and closing it is the no-delta pass's real
work — a re-delivery that re-verifies everything and leaves the entry unpushed has
recorded nothing durable. Repair by re-minting the same entry through the writer on a
fresh detached worktree at the fetched tip (`boardctl update <ID> --evidence-run-id
<run> --evidence-fingerprint <sha> --evidence-artifact <path>`, plus a note saying the
pass repaired durability rather than added evidence), because the writer mints its row
and event on that base. Never copy the single physical JSONL line across trees: a
hand-spliced row skips the writer's event and its schema handling. Land it as a
board-only carrier, read the row back from `origin/<default>` after the push, and query
that carrier's own exact-SHA run before calling the record durable.

## Version hygiene is measured against the PROPOSED version, not the current tag

Running the repo's pin check with the version that is already pinned is a tautology: the
tree was written for that tag, so it PASSES no matter how far the branch has moved, and
the PASS says nothing about readiness for the next cut. Worse, it is positive evidence
the carrier is UNPREPARED — every surface still names the shipped version. Run the check
with the version you intend to tag, and expect it to FAIL until the prep row lands:

    bash scripts/check-release-pin.sh v<proposed>        # pre-prep: must name each stale site
    bash scripts/check-openapi-version.sh v<proposed>    # info.version + copy parity
    git grep -nE '0\.[0-9]+\.[0-9]+' -- README.md CHANGELOG.md cmd/server/openapi.yaml docs/openapi.yaml

Quote the pre-prep FAIL (with its site list) as the reason the cut is blocked, never the
current-tag PASS as "version hygiene verified". The same holds for gates whose verdict is
carried by SHA identity: a carried gate is a carried MEASUREMENT (name both SHAs and the
empty material path set) — it is not a fresh pass, and a version check cannot be carried
at all, because its answer depends on the version argument rather than on the tree.

## A release layer needs a receipt that its workflow TRIGGERS on that ref

Before planning a cut, confirm the CI workflow fires on the ref the release creates:

    grep -n -A8 '^on:' .github/workflows/ci.yml    # needs tags: ['v*.*.*'] (or dispatch + run id)

A workflow with only `push`/`pull_request` gives a pushed tag no run at all, so the tag
commit ships with zero CI evidence and cannot be certified after the fact without a
dispatch. That is a prep row (add the trigger, or document the dispatch command and quote
its run id), not a reason to tag anyway and hope.

## Deployed surfaces are three receipts, not one

A released version is stale or current independently on each surface, and quoting one
for another is how a stale deployment reads as shipped:

    curl -s http://127.0.0.1:<port>/version                       # what the RUNNING service serves
    go version -m <repo>/bin/<artifact> | head -5                 # source commit baked into the BUILT artifact
    command -v <artifact> && <artifact> -version                  # what a bare invocation on PATH resolves to

A `--version` banner reporting `dev` or a `git describe` suffix is not the build's source
commit — `go version -m` is, and `git merge-base --is-ancestor <that commit> <tag>`
decides whether the release content is present at all. Report the three surfaces as three
lines with their own versions; do not collapse them into "deployed: vX".

A long-lived process with no version surface is a fourth receipt, and a cheap one:

    ps -o pid=,lstart= -p <pid>            # when the RUNNING process started
    stat -c '%y %n' <source-file>          # when the code on disk was last written
    grep -c '<feature-log-key>' <log>      # does the running process emit the new behaviour at all

A process start time OLDER than its source's mtime is running code that no longer exists on
disk, whatever the file claims, and a zero log count for the feature corroborates it. Cite the
three together as one stale-deployment receipt; quoting the mtime alone says the tree is new,
which is the opposite claim.

## A refused worktree: build the carrier with a throwaway index

`git worktree add` is not always available — an unattended surface can refuse it outright,
and consent for it is not yours to assume. Do not abandon the delivery, and do not reset or
check out the shared tree. A carrier can be built purely from the fetched tree with an index
file that is not the repository's:

```bash
S=<scratch>/<lane>
git read-tree <fetched-tip>                                      # base
BLOB=$(git hash-object -w $S/<edited-file>)                      # stage the bytes, not the path
git update-index --add --cacheinfo 100644,$BLOB,<repo/relative/path>
TREE=$(git write-tree)
COMMIT=$(git commit-tree $TREE -p <fetched-tip> -F $S/msg.txt)
git diff --name-status <fetched-tip> $COMMIT                      # PARITY GATE, before pushing
git push origin $COMMIT:refs/heads/<branch>
```

- The parity diff is the gate, not a formality: it must list exactly the paths you meant.
  A stale `read-tree`, a wrong path string or an un-staged deletion ships a commit that
  adds or drops files while the message describes one edit.
- Base each carrier on the THEN-current remote tip and chain the SHAs: fetch, build, push
  and verify the evidence commit before basing the board carrier on it. A second carrier
  built on the pre-push base is a force-push waiting to happen.
- Pass `GIT_INDEX_FILE` per command, or `unset` it before you go back to ordinary git. An
  exported index left in a persistent shell makes every later `git status`/`git add`/`git diff`
  answer about a detached index that has nothing to do with the checkout.
- State in the commit body that the working tree was never checked out and which tip the
  tree was built from, so the next reader does not mistake a behind checkout for a lost write.
- Verify from the REMOTE tree afterwards (`git show origin/<branch>:<path>`), because nothing
  on local disk reflects a commit that was never checked out.

## Quote only output you actually saw

`git log -1 <A> <B>` prints ONE commit — the newest of the revision set — and exits 0,
so a two-sha comparison returns a complete-looking single record and the missing subject
is never noticed. Give each revision its own `git log -1`, or count what you asked for:
`git log --no-walk --format='%H %s' <A> <B> | wc -l` must equal the number of revisions.

Chaining probes into one shell call collapses their output to a line count on some
surfaces, and a number you cannot see is a number you cannot cite. A compound probe is also a
single CONSENT gate: one execution-shaped element inside it — an inline interpreter call, a
venv build, a package install — can refuse the whole call and take every read-only leg with
it, leaving a leg you never got to blame for being unverified. Read version and metadata
from FILES instead (`*.dist-info/METADATA`, the source `__version__` line, `uv tool list`,
`git show <ref>:<path>`), and keep interpreter invocation out of probes that only need to
look. Run each command whose
exact value belongs in the report as its own call, and re-run single-line probes one at a
time rather than reconstructing the value from the earlier combined run. When a probe
fails on a guessed identifier — a short sha, an absent column, a path form — read the
real identifier first (`gh api ...` with the full sha, `pragma_table_info('<table>')`
before projecting columns, `git ls-tree` before path guessing) and retry once.

A verification SET chained with `&&` is one gate, not many: a `jq` filter that dies on a
guessed field name (`.payload.decision` on an event whose payload actually lives in the
JSON-string `detail`) exits nonzero and every leg after it NEVER RUNS, while the report goes
on to claim the measurements the pass did not take. Give each leg its own line
(`<leg>; echo "rc=$?"`) or its own call, and treat a nonzero rc as UNVERIFIED for every leg
behind it — the tags/release/artifact counts are exactly the legs a dead chain silently skips.

### Capture-then-read when even a single call comes back as a line count

On a long session, per-call results themselves get reduced to `N lines output`, and
splitting into more calls does not help — the reduction is on the result, not the command.
Stop re-running: write the whole census into one labeled file and read that file back.

    OUT=~/.hermes/cache/scratch/<project>-pass<N>.txt
    { echo "TIP_FULL=$(git rev-parse origin/$DEF)"
      git log -1 --format='TIP_TS=%ci TIP_SUBJ=%s' origin/$DEF
      echo "MATERIAL=$(git diff --name-only <tag>..origin/$DEF -- . ':(exclude).coding-hermes/**' \
                       ':(exclude).gitreins/**' | wc -l)"
      echo "ART_SHA=$(git show origin/$DEF:<artifact> | sha256sum)"
      echo "ART_BYTES=$(git cat-file -s $(git rev-parse origin/$DEF:<artifact>))"
    } > "$OUT"

Label every value `KEY=value` as it is written. An unlabeled number cannot be attributed
a call later, and re-deriving it costs the same probes again. Then `read_file` the path —
that result is not collapsed, so the numbers you cite come from bytes you actually saw.
Keep one file per pass so a later pass can show what it re-measured versus carried. Scope each file by EVIDENCE QUESTION, not by pass alone: one file per question (identity and tip, material-path census, CI receipts, gate rows, deploy surfaces), each a few dozen to a couple hundred lines. A single dump that grows into the tens of thousands of lines is not a capture, it is a context bomb — reading it back costs several 100KB `read_file` chunks, and on a long session that volume prunes the skill and probe results already loaded out of the window, so the pass pays for the same `skill_view` calls twice and loses the procedures it was following. If a capture read exceeds roughly 40KB, stop reading and re-split the remaining probes into separate files rather than paging through it.

### A dead runner pool makes the TAG path dead too, so the gate is unsatisfiable

A pipeline on the tip that is `pending` with `started_at` null, every job `created` and
unassigned, and project runners `online=false` / `status=stale` / `contacted_at` null is
CI ABSENT — never red, and never green. The decision consequence is stronger than
"cannot verify": a tag pushes new pipelines onto the SAME dead pool, so cutting produces a
second never-started pipeline and no tag-triggered Release object at all. Report it as
"gate unsatisfiable until the runner is back", refuse the cut on that ground (it is not a
doctrine violation to be overridden, it is a no-op that leaves a false-released tag), and
attribute the unblock to the CI/runner row instead of re-filing it. A candidate's own run
reading `canceled` beside a later push is a SUPERSEDE, not a verdict — quote the
candidate run and the carrier run separately by exact SHA, and say so, or the next pass
re-litigates a failure that never happened.

### Zero workflows is ABSENT, not red — and a re-fire cannot move it

A repository that has never been released has no gate to stand on:

    gh api repos/<org>/<repo>/actions/workflows --jq .total_count   # 0 = no workflow file at all
    gh api repos/<org>/<repo>/actions/runs --jq .total_count        # 0 = never ran
    git ls-remote --tags origin | wc -l                             # 0 = no baseline to diff against
    gh release list --repo <org>/<repo>                             # empty = first publication undecided

Report it as ABSENT with all four counts and never as "CI not green": a reader who hears RED
waits for a rerun that no push will produce, while the actual unblock is a workflow file that
does not exist. Because no measurement the lane can take will change the verdict, the decision
is unmovable by a re-fire — file the missing-gate, missing-tooling and first-channel rows ONCE,
and let later passes on the same id carry them, record the re-fire against the same canonical
rows, and put the pass's own verdict in the ledger. A third readiness row for the same blocker
is the duplicate the board cannot absorb.

The same holds for a leg the harness REFUSES to execute: a probe stopped by a consent gate
before it runs is not a measurement, so the same leg coming back UNMEASURED on two
consecutive fires is a structural limit of this LANE, not a per-pass gap to re-report. File
ONE row whose acceptance is executable where the operation is permitted — and give it a
negative arm (`the same procedure pinned to a nonexistent tag/artifact must fail nonzero`),
because an acceptance that says only "the probe exited 0" is satisfied by exactly the
tautology that produced the gap. Later passes carry that row: name it, count the consecutive
refusals, and do not re-attempt the refused probe each fire, since re-attempting cannot
change a gate that never ran.

## A row parked in a non-dispatchable status is invisible work

Status counts are not the health metric; WHICH statuses hold rows is. A row whose acceptance
is substantively met but which sits in a review-style state no lane consumes is invisible: the
foreman does not dispatch it, the releng lane may not close another lane's row, so it stays
open forever. Read the whole distribution every pass, not just `pending`:

    jq -r 'select(.status!=null)|.status' <board>/tasks.jsonl | sort | uniq -c | sort -rn
    git show origin/<default>:<board> | jq -r 'select(.status=="<non-terminal-status>")|.id'

A recommendation written inside the audit artifact never executes. Several consecutive passes
can each record "close this row" while nothing changes, because a report is not a work item.
Do not close the row yourself: file ONE pending closure row whose acceptance is executable in
this repository, state the residual precisely (what evidence is missing, not "finish the
work"), and make the acceptance two-path when the literal receipt is unattainable — the exact
evidence, OR a recorded decision naming the authority that accepts a substitute and the
substitute it accepts. The second path is cheap ON PURPOSE: an acceptance that only the
impossible evidence can satisfy re-creates the same parked row under a new id.

The closure row must not re-open work that is already done. When the acceptance was met by a
document that exists (a changelog section, a notes file), grep the tokens that document
actually cites before filing any rewrite, and ban the rewrite in the row text so no worker
re-authors a correct document and re-stales the thing you were trying to close.

## A pass over an unchanged code tree owes no new decision

Each pass commits its own bookkeeping, and that commit becomes the tip the next pass re-anchors
to. Nothing in that movement makes new facts measurable, so a lane can fire many times over a
byte-identical product tree while every pass faithfully reports "carried" and the board grows a
row plus a carrier commit each time. Measure the interval, not the tip:

    git log --format='%h %ci %s' --grep='releng' -12      # how often, and how far apart
    git diff --name-only <certified-tree>..<tip> \
      | grep -vE '^(\.coding-hermes/|\.gitreins/)' | wc -l   # must be 0 to carry

Zero material paths plus no owner decision on record IS the finding for that pass: state it
plainly, name the interval and the number of passes, and recommend gating the lane on a
material commit or an owner ruling rather than publishing another decision-shaped record. A
repeated identical NO-CUT note is churn with a commit attached, not diligence.

The artifact shape follows the same rule. One dated
`docs/release-evidence-<YYYY-MM-DD>-<HHMM>.md` per tick-fire grows a series of near-identical
files that every later pass must diff against its neighbours, and each new path is another
thing the product-path filters have to exclude — the exclusion pattern is a symptom of the
churn, not a feature of it. Append a `## Pass N` section to the artifact that already owns the
current candidate; mint a NEW file only when the candidate moves materially or the decision
flips, and when you do, name in its header the artifact it supersedes so the series stays a
chain instead of a pile.

## A dominated non-conventional bucket makes the bump rest on a few subjects

In a repo whose commits carry board or tick titles, non-conventional subjects can outnumber
conventional ones several times over while the bump is still decided by a handful of
`feat`/`fix` rows. Publish those subjects, not just the counts:

    git log --no-merges --format='%h %s' <baseline>..<candidate> \
      | grep -E '^[0-9a-f]+ (feat|fix)!?:'

Nobody can audit "feat=4", and a changelog banner whose feature total disagrees with the
recomputed feats is a finding worth a row — the banner ships verbatim into the published
notes, so it outlives the tick that could have caught it.

## A census can be plausible and entirely wrong

`git log --format='%s%x00'` emits a newline AFTER each NUL. Records past the first therefore
arrive newline-prefixed, every `^`-anchored type regex falls through to `non-conventional`, and
the classifier prints a tidy, believable result — `feat 0 / fix 0 / non-conventional 810 of 811`
— that would turn a minor bump into a patch bump with no error anywhere. Two cheap guards:
strip each split record (`s.strip()`), and assert `sum(classes) == git rev-list --no-merges
--count` before reading any feat/fix total. Same class of trap in a shell one-liner: grep for
`^[0-9a-f]+ (feat|fix)!?:` after `--format='%h %s'`, never against `%H`-only output, and
cross-check the feature count against `git log --grep='^feat' --oneline | wc -l` by a second
route before a bump decision leans on it.
