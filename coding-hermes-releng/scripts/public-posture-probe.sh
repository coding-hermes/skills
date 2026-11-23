#!/usr/bin/env bash
# public-posture-probe.sh <owner/repo> [checkout-dir]
#
# One re-executable public-posture battery for a published repo. Run it from a
# CLONE of the published ref (never the shared lane checkout, which may hold a
# sibling's unpublished residue), then paste its key=value lines plus the tip
# sha into the releng audit document.
#
# Read-only: gh api GETs and git plumbing reads. No writes, no mutation.
set -uo pipefail

REPO=${1:?usage: public-posture-probe.sh <owner/repo> [checkout-dir]}
DIR=${2:-.}
cd "$DIR" 2>/dev/null || { echo "FAIL checkout_missing=$DIR"; exit 2; }

sec() { printf '\n-- %s --\n' "$1"; }
out() { printf '%s\n' "$*"; }

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)
TMP=$(mktemp -t posture.XXXXXX.json 2>/dev/null || echo /tmp/posture.$$.json)

sec tip
out "tip=$(git rev-parse HEAD 2>/dev/null || echo UNKNOWN)"
out "tip_subject=$(git log -1 --format=%s 2>/dev/null | cut -c1-120)"
out "branch=$BRANCH"
out "dirty_paths=$(git status --porcelain=v1 --untracked-files=all 2>/dev/null | wc -l)"

sec repo_identity
if gh api "repos/$REPO" >"$TMP" 2>/dev/null; then
  jq -r '"visibility=\(.visibility) private=\(.private) license=\(.license.spdx_id // "NONE") default_branch=\(.default_branch)"' "$TMP"
  jq -r '"secret_scanning=\(.security_and_analysis.secret_scanning.status) push_protection=\(.security_and_analysis.secret_scanning_push_protection.status) non_provider_patterns=\(.security_and_analysis.secret_scanning_non_provider_patterns.status) validity_checks=\(.security_and_analysis.secret_scanning_validity_checks.status) dependabot_security_updates=\(.security_and_analysis.dependabot_security_updates.status)"' "$TMP"
else
  out "repo_identity=UNREADABLE (probe the slug and the token, do not infer from a failure)"
fi
rm -f "$TMP"

sec branch_protection
if gh api "repos/$REPO/branches/$BRANCH/protection" >/dev/null 2>&1; then
  out "branch_protection=PRESENT"
else
  out "branch_protection=ABSENT (HTTP 404: force-push and branch deletion are open; an OWNER decision, not foreman work)"
fi
out "repo_rulesets=$(gh api "repos/$REPO/rulesets" --jq 'length' 2>/dev/null || echo UNREADABLE)"

sec license
out "license_file=$(test -f LICENSE && head -1 LICENSE || echo MISSING)"

sec ci
out "workflows_dir=$(test -d .github/workflows && echo PRESENT || echo ABSENT)"
out "workflow_runs=$(gh run list --repo "$REPO" --limit 3 --json status,conclusion,displayTitle,headBranch 2>/dev/null | tr -d '\n' | cut -c1-300)"

sec published_refs
out "published_heads=$(git ls-remote --heads origin 2>/dev/null | wc -l)"
out "release_tags=$(git ls-remote --tags origin 2>/dev/null | wc -l)"
MASTER=$(git ls-remote --heads origin 2>/dev/null | grep 'refs/heads/master$' | cut -f1)
if [ -n "$MASTER" ]; then
  out "master_ref=$MASTER"
  if git cat-file -e "$MASTER" 2>/dev/null; then
    out "master_commits=$(git rev-list --count "$MASTER" 2>/dev/null)"
    if git merge-base --is-ancestor "$MASTER" HEAD 2>/dev/null; then
      out "master_ancestor_of_head=yes"
    else
      out "master_ancestor_of_head=no (unrelated lineage published beside the default branch)"
    fi
  else
    out "master_commits=UNMEASURED (sha not in this clone; fetch it before quoting a count)"
  fi
else
  out "master_ref=none"
fi

sec absolute_host_paths
out "files_with_abs_path=$(git grep -lIE '/home/[a-z][a-z0-9_-]*/' HEAD 2>/dev/null | wc -l)"
out "hits_abs_path=$(git grep -oIE '/home/[a-z][a-z0-9_-]*/' HEAD 2>/dev/null | wc -l)"
out "files_excl_verdict_bundles=$(git grep -lIE '/home/[a-z][a-z0-9_-]*/' HEAD -- . ':(exclude).gitreins' 2>/dev/null | wc -l)"

sec credential_shapes
out "credential_hits=$(git grep -oIE '(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xoxb-[A-Za-z0-9-]{10,}|BEGIN [A-Z ]*PRIVATE KEY)' HEAD 2>/dev/null | wc -l)"

sec note
out "A leg that reproduces an existing pending row is EVIDENCE for that row, not a reason to file a second one: grep the board for the finding first, then quote the delta against the row's filed figure."
