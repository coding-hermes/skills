# Ledger Structure and Board Hygiene Patterns

Procedural details for working with the stand-in PM ledger and board files, discovered through operational cycles.

## Ledger Structure

The ledger at `~/.hermes/stand-in/ledger.json` is an **object** with two keys:
- `.items` — object keyed by item ID (not an array), each value has: `project`, `status`, `title`, `added_at`, `updated_at`
- `.last_updated` — timestamp

### Query Patterns

```bash
# Count items for a specific project
jq '.items | to_entries | map(select(.value.project=="bunker")) | length' ~/.hermes/stand-in/ledger.json

# Count open items (added/picked_up) for a project
jq '.items | to_entries | map(select(.value.project=="bunker" and (.value.status=="added" or .value.status=="picked_up"))) | length' ~/.hermes/stand-in/ledger.json

# List open items with details
jq '.items | to_entries | map(select(.value.project=="bunker" and (.value.status=="added" or .value.status=="picked_up"))) | map({id: .key, status: .value.status, title: .value.title[0:80]})' ~/.hermes/stand-in/ledger.json
```

**Common mistake**: The ledger is NOT an array. Using `.[]` to iterate will fail with "Cannot index object with number". Always use `.items | to_entries` to convert the object to an array of `{key, value}` pairs.

## Board Hygiene Issues

When auditing a board, look for these patterns:

### 1. Duplicate IDs
Multiple rows with the same ID (often from concurrent appends or failed merges).
- **Fix**: Keep the most recent, annotate others with `superseded_by`.

### 2. Status Vocabulary Drift
Rows using off-vocabulary status values:
- `done` → should be `complete`
- `partial`, `wip`, `in_progress` → should be `pending`
- **Fix**: Normalize to canonical set: `pending`, `complete`, `closed`, `archived`, `retired`

### 3. Priority Vocabulary Drift
Mix of numeric priorities (`0`, `1`, `2`, `3`) and string priorities (`P0`, `P1`, `P2`, `P3`).
- **Fix**: Normalize to string form (P0/P1/P2/P3).

### 4. Non-Canon Keys
Rows carrying extra keys not in the schema: `ts`, `worktree`, `branch`, `created`, `verified_in`, `priority_x`, `review_notes`.
- **Fix**: Remove or migrate to standard fields.

### 5. Unreaped Worktrees
Worktrees fully merged (0 commits ahead of main) but not deleted.
- **Fix**: Reap them.

### 6. Stale Rows
Rows with `updated_at` > 48h old, especially from audit/QA cycles that were never picked up.
- **Fix**: Escalate or close with reason.

### 7. Superseded Re-Sweep Series
Boards accumulate point-in-time re-sweep/report rows — release-readiness re-sweeps, review re-verifications, QA re-runs — where a NEWER sweep row restates the same verdict over a superset baseline (later HEAD, more commits, same conclusion).
- **Fix**: Close the older rows `complete` with a `superseded_by <latest-id>` note (plus a one-clause reason) and an events.jsonl status_change entry. Never delete them (they are provenance); never leave them pending (they inflate backlog and every next tick re-audits them). Keep the newest row open only if it still names unclosed findings; if its remaining scope lives in its own dedicated work rows, close the sweep row too. Re-verify the row's premise (e.g. `git log --grep` for a fix commit, then confirm containment in the default branch) before flipping any row this way.

### Detection Pattern

```bash
# Find stale rows (>48h old)
jq -r 'select(.status != "complete" and .status != "closed" and .status != "archived" and .status != "retired") | select(.updated_at != null) | "\(.id) | \(.updated_at) | \(.title[0:60])"' .coding-hermes/board/tasks.jsonl | awk -F'|' '{cmd="date -d \""$2"\" +%s 2>/dev/null"; cmd | getline ts; close(cmd); now=systime(); age=(now-ts)/3600; if(age>48) print $0" | AGE="int(age)"h"}' | head -15
```

## Release Blocker Detection

When a board carries a P0 release blocker row, verify the specific conditions:

### 1. CI State
```bash
gh run list --limit 5 --json status,conclusion,createdAt
```
- `queued` for >1h = CI is stuck, not just slow
- `in_progress` but no conclusion = still running
- `failure` conclusion = CI is red

### 2. Version Prep
```bash
grep -r "version.*0\." internal/version/ 2>/dev/null | head -5
```
Check if version files are updated to match the target release.

### 3. Open Defects
```bash
jq -r 'select(.status == "pending" and (.priority == "P0" or .priority == "P1")) | .id' .coding-hermes/board/tasks.jsonl | wc -l
```

A release is blocked when ANY of these are true:
- CI is queued/stuck (not actively passing)
- Version prep is absent (version files don't match the target release)
- Open P0/P1 defects remain (rows with `pending` status)

Report the specific blockers, not just "release blocked".
