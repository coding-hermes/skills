#!/usr/bin/env bash
# verify_board_rows_remote.sh — re-prove filed board rows against their REMOTE blobs in one run.
#
# Spec file: one row per line, fields separated by '|':
#     <repo-abs-path>|<remote>|<branch>|<row-id>
# Lines starting with '#' and blank lines are ignored.
#
# Output (tab-separated): row, repo, remote/branch, HEAD, ahead, behind, row=<status>|commit|title
#   row=NOT_ON_REMOTE  -> the id is absent from the published blob (a claim with no landing)
#   MISSING_REPO       -> the path is not a checkout any more (lane/workdir drift)
#
# Why: a row's note and the working-tree copy are claims; the published blob is the state. Run this
# before concluding a P1 is "already covered" by a prior tick, and put the PUBLISHING remote in the
# spec (a repo may publish over `github` while `origin` is a mirror, or the reverse).
set -u
BOARD=".coding-hermes/board/tasks.jsonl"

git_board_row() {
  # $1=repo $2=remote $3=branch $4=row
  git -C "$1" show "$2/$3:$BOARD" 2>/dev/null \
    | jq -r --arg r "$4" 'select(.id==$r) | "\(.status)|\(.commit_hash // "none")|\(.title // "-")"' \
    | head -1
}

[ $# -eq 1 ] || { echo "usage: $0 <spec-file>" >&2; exit 2; }
[ -r "$1" ] || { echo "FAIL spec not readable: $1" >&2; exit 2; }

while IFS='|' read -r repo remote branch row; do
  case "$repo" in ''|'#'*) continue ;; esac
  repo=$(printf '%s' "$repo" | xargs)
  remote=$(printf '%s' "$remote" | xargs)
  branch=$(printf '%s' "$branch" | xargs)
  row=$(printf '%s' "$row" | xargs)

  if [ ! -d "$repo" ]; then
    printf '%s\t%s\t%s/%s\tMISSING_REPO\n' "$row" "$repo" "$remote" "$branch"
    continue
  fi
  git -C "$repo" fetch -q "$remote" 2>/dev/null
  head_sha=$(git -C "$repo" rev-parse --short HEAD 2>/dev/null || echo '?')
  ahead=$(git -C "$repo" rev-list --count "$remote/$branch..HEAD" 2>/dev/null || echo '?')
  behind=$(git -C "$repo" rev-list --count "HEAD..$remote/$branch" 2>/dev/null || echo '?')
  blob=$(git_board_row "$repo" "$remote" "$branch" "$row")
  printf '%s\t%s\t%s/%s\tHEAD=%s\tahead=%s\tbehind=%s\trow=%s\n' \
    "$row" "$repo" "$remote" "$branch" "$head_sha" "$ahead" "$behind" "${blob:-NOT_ON_REMOTE}"
done < "$1"
