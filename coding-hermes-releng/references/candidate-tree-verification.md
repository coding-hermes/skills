# Verifying the candidate TREE, not the checkout

Recipes for producing exact-SHA release evidence when the product checkout is dirty, the
gate tooling is missing, or no verdict names the candidate. Add these to the pass artifact
verbatim so the next pass can tell inspection-verified from machine-verified.

## 0. Resolve the two checkouts before measuring anything

A releng lane usually has a **board/carrier repo** (small, may have no remote at all) and a
separate **product checkout** (has `origin`). The lane's nominal workdir is often the carrier.

```bash
for d in <lane-workdir> <product-checkout>; do
  echo "== $d"; git -C "$d" rev-parse --show-toplevel
  git -C "$d" remote -v
  git -C "$d" log -1 --format='%H %ci %s'
done
```

Rules:
- Identify the product checkout by **remote presence**, not by directory name.
- `fatal: 'origin' does not appear to be a git repository` from the lane repo is a topology
  fact, NOT a missing release channel. Never record "no remote" until both trees are checked.
- Name both paths in the artifact (`board root:` / `product checkout:`). Passes that omit
  this get re-derived from scratch by the next pass.
- The board lives with the carrier; `gh`/`git fetch`/tag reads must run in the product checkout.

## 1. Export the candidate tree (never scan the working checkout)

Dirty residue (`coverage.json`, `scripts/raw/`, stale `.env.example`) contaminates every scan
and inflates the ``working_tree_dirty_path_count`` a judge records. Export the exact SHA:

```bash
D=$(mktemp -d "$SCRATCH/cand.XXXXXX")
git -C <product> archive <candidate-sha> | tar -x -C "$D"
echo "TREE=$D files=$(find "$D" -type f | wc -l)"
```

All subsequent probes run against `$D`. State in the artifact that scratch work was an
archive export, so "product checkout untouched" is a receipt rather than a claim.

## 2. Secrets scan at the candidate

```bash
gitleaks dir "$D" --no-banner --redact -f json -r "$D/../gl.json" >/dev/null 2>&1; echo rc=$?
jq -r 'if length==0 then "FINDINGS=0" else (length|tostring) end' "$D/../gl.json"
jq -r '.[]|[(.RuleID//"?"),(.File//"?"),(.StartLine|tostring)]|@tsv' "$D/../gl.json" | head -20
```

`FINDINGS=0` converts "secrets scan unverified" into a measured reading. Pair it with the
gate's own stage output so you can distinguish the two failure classes:

| Gate stage output | Class | What to report |
|---|---|---|
| `gitleaks: clean` + builtin `SENSITIVE PATH (credential-store path class)` | path-class | No secret is leaking. Blocker is a filename rule; remedies are gitignore / secret manager / explicit override **with a recorded reason**. File it as small-scope, not an incident. |
| gitleaks findings on a real file | content-class | Actual leak. Never allowlist; the remediation is removing the credential and rotating. |
| `Cap exceeded: Iteration cap (N) reached` in tier 2 | budget-class | The criteria were never graded. A config bump of `evaluator.max_iterations` targets this; the tier-1 result is unaffected. |

## 3. Prometheus config validation without installing promtool

A local `prom/prometheus` image gives you `promtool` with no host install:

```bash
docker run --rm -v "$D/stack/prometheus":/cfg:ro --entrypoint promtool \
  prom/prometheus:v3.15.0 check config /cfg/prometheus.yml
```

Expect `SUCCESS: ... is valid prometheus config file syntax`. A `file_sd` WARNING about a
path that does not exist inside the container is a mount-time artifact, not a defect — say so
instead of reporting it as a finding. `docker images | grep prometheus` first; the image is
usually already present from the stack the repo deploys.

## 4. YAML parse across the whole tree

Stage a script file; do not pipe a heredoc to `python3` (unattended consent gates block that
pattern). Write `yamlparse.py` that walks `root` and `yaml.safe_load`s every `.yml`/`.yaml`,
prints `parsed=N failed=M`, then:

```bash
python3 /path/to/yamlparse.py "$D"
```

This is the cheap way to prove a config-only commit is syntactically sound when `make lint`
would need terraform init or network.

## 5. Bounding an UNBOUND candidate (no verdict names it)

`grep -rl <candidate-sha> .gitreins/history | wc -l` == 0 means every existing gate result is
stale. Instead of reporting a bare "unbound", measure the distance to the nearest judged SHA:

```bash
LAST=<judged-sha>
git merge-base --is-ancestor "$LAST" <candidate> && echo ANCESTOR=YES || echo ANCESTOR=NO
git log --format='%s' --no-merges "$LAST"..<candidate>      # the delta commits
git diff --stat "$LAST" <candidate>                          # the delta files
git diff --stat "$LAST" <candidate> | tail -1                # "1 file changed, +38"
```

Then state the carry-over explicitly:
- Ancestor YES + delta touches only guard/config/docs → the product tree that already passed
  lint/tests is **byte-identical** to the candidate's; those stage results carry over.
- Delta touches executable code → nothing carries over; the candidate needs its own verdict.
- A config bump aimed at a previous cap death is a **plausible, untested** fix. Write
  "plausible but untested — no verdict has been produced under the new config", never "fixed".

Also read the stage detail, not just `passed`:

```bash
jq -r '.summary' .gitreins/history/<date>/<run>/verdict.json
jq -r '.stages.tier1.steps[]|{id,passed,output}' .gitreins/history/<date>/<run>/verdict.json
```

`passed=false` alone cannot tell a secrets failure from a judge cap; the per-step output can.
Note `items[].passed: null` with "Not examined — evaluation ended before this criterion was
reached" means the criterion was never graded — that is not a criterion failure.

## 6. Release-surface census (one pass, all of it)

```bash
git -C <product> ls-tree -r --name-only <candidate> | grep -i -E 'release|goreleaser|RELEASING'
git -C <product> show <candidate>:Makefile | grep -n -E '^[a-zA-Z0-9_.-]+:' | grep -i -E 'release|tag|publish'
git -C <product> show <candidate>:CHANGELOG.md | grep -n -E '^## ' | head -5
git -C <product> ls-tree -r --name-only <candidate> | grep -c '^\.github/'
gh release list --repo <org/repo>
gh run list   --repo <org/repo> --limit 20
```

Record "absent" as an explicit negative (`(none above = absent)`, `0`) — an empty grep is
evidence only if the artifact says the command ran.

## 7. Commit only the artifact

Stage the artifact path explicitly; never `git add -A` or `git add .` in a lane repo where
another lane writes the board.

```bash
git add releng-evidence-<date>/<file>.md
git diff --cached --name-only            # must be the artifact and nothing else
git commit -F <msg-file>                 # msg file carries the Co-authored-by trailer
git status --porcelain | grep board      # board must STILL be dirty afterwards
```

If the board is clean after your commit, you swept a sibling lane's rows into a releng
commit — revert the board file out of the commit before pushing.
