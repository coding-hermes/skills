#!/usr/bin/env bash
# worktree.sh — coding-hermes multi-worktree helper (parallel/wave dispatch)
#
# One worktree per worker. Never two workers in one shared tree.
# Convention (see coding-hermes-foreman "Parallel Ticks — Git Worktrees"):
#   dir:    $WT_ROOT/<project>-<taskid>
#   branch: wt/<taskid>        (local-only until the foreman merges)
#   base:   origin/<main> (or origin/master), never a local branch
#
# Subcommands
#   new    <project> <taskid> [--base <ref>] [--slug <s>]   create worktree + branch
#   list   <project>                                        show worktrees for a project
#   flags  <project> <taskid>                               print boardctl --worktree/--branch flags
#   reap   <project> [--all]                                remove finished worktrees + prune
#   prune  <project>                                        git worktree prune + stale dir sweep
#   doctor                                                  leak report across all projects
#
# Board integration (boardctl >= 0e4cc91): rows carry worktree/branch/sessions.
#   boardctl -C <repo> update <id> $(worktree.sh flags <project> <taskid>) --session <sid>
set -uo pipefail

WT_ROOT="${WT_ROOT:-/home/kara/worktrees}"
PROJECTS_ROOT="${PROJECTS_ROOT:-/home/kara}"

die() { echo "worktree.sh: $*" >&2; exit 1; }
info() { echo "worktree.sh: $*"; }

# taskid -> filesystem-safe slug (branch names and dirs must survive / : @ etc.)
slug() { printf '%s' "$1" | tr '/: @{}' '-–' | tr -s '-' ; }

resolve_repo() {
  local project="$1" repo="$PROJECTS_ROOT/$1"
  [ -d "$repo/.git" ] || [ -f "$repo/.git" ] || die "no git repo at $repo"
  printf '%s' "$repo"
}

default_base() {
  local repo="$1" ref
  for ref in origin/main origin/master main master; do
    if git -C "$repo" rev-parse --verify --quiet "$ref" >/dev/null; then printf '%s' "$ref"; return; fi
  done
  die "no main/master ref found in $repo"
}

cmd_new() {
  local project="$1" taskid="$2"; shift 2
  local base="" s=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --base) base="$2"; shift 2;;
      --slug) s="$2"; shift 2;;
      *) die "unknown arg $1";;
    esac
  done
  [ -n "$s" ] || s="$(slug "$taskid")"
  local repo; repo="$(resolve_repo "$project")"
  [ -n "$base" ] || base="$(default_base "$repo")"
  local path="$WT_ROOT/$project-$s" branch="wt/$s"

  [ -e "$path" ] && die "path already exists: $path (reap it first)"
  if git -C "$repo" show-ref --verify --quiet "refs/heads/$branch"; then
    die "branch $branch already exists in $repo (reap it first, or reuse with --slug)"
  fi

  mkdir -p "$WT_ROOT"
  git -C "$repo" fetch --quiet origin 2>/dev/null || true
  git -C "$repo" worktree add "$path" -b "$branch" "$base" >/dev/null || die "worktree add failed"
  local sha; sha="$(git -C "$path" rev-parse --short HEAD)"
  info "created $path"
  echo "WORKTREE=$path"
  echo "BRANCH=$branch"
  echo "BASE=$base"
  echo "BASE_SHA=$sha   # record this: a base that moves orphans the branch (skill §2a)"
}

cmd_list() {
  local project="$1"; local repo; repo="$(resolve_repo "$project")"
  git -C "$repo" worktree list
}

cmd_flags() {
  local project="$1" taskid="$2"; local s; s="$(slug "$taskid")"
  printf -- '--worktree %s --branch wt/%s' "$WT_ROOT/$project-$s" "$s"
}

cmd_prune() {
  local project="$1"; local repo; repo="$(resolve_repo "$project")"
  git -C "$repo" worktree prune -v
  # sweep registered-but-deleted dirs (the leak class: /tmp verification worktrees)
  git -C "$repo" worktree list --porcelain | awk '/^worktree /{print $2}' | while read -r p; do
    case "$p" in "$repo") continue;; esac
    [ -d "$p" ] || { info "missing dir $p (pruned)"; }
  done
}

cmd_reap() {
  local project="$1" all="${2:-}"
  local repo; repo="$(resolve_repo "$project")"
  local target; target="$(git -C "$repo" symbolic-ref --quiet --short HEAD 2>/dev/null || echo master)"
  git -C "$repo" worktree list --porcelain | awk '/^worktree /{print $2}' | while read -r path; do
    case "$path" in
      "$repo"|"$WT_ROOT/$project-"*) : ;;
      *) continue;;
    esac
    [ "$path" = "$repo" ] && continue
    local br dirty
    br="$(git -C "$path" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    dirty="$(git -C "$path" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
    if [ "$dirty" != "0" ] && [ "$all" != "--all" ]; then
      info "SKIP $path ($br): $dirty uncommitted file(s) — worker output, never auto-discard"
      continue
    fi
    if git -C "$repo" merge-base --is-ancestor "$br" "$target" 2>/dev/null; then
      git -C "$repo" worktree remove --force "$path" >/dev/null 2>&1 && info "removed $path (merged $br)"
      if [ "$br" != "$target" ]; then git -C "$repo" branch -d "$br" >/dev/null 2>&1 && info "deleted merged branch $br"; fi
    else
      [ "$all" = "--all" ] || { info "KEEP $path ($br): unmerged — evidence"; continue; }
      git -C "$repo" worktree remove --force "$path" >/dev/null 2>&1 && info "REMOVED UNMERGED $path ($br still exists)"
    fi
  done
  git -C "$repo" worktree prune
}

cmd_doctor() {
  echo "WT_ROOT=$WT_ROOT"
  for repo in "$PROJECTS_ROOT"/*/; do
    [ -f "$repo/.git/HEAD" ] || continue
    local n dirs
    n="$(git -C "$repo" worktree list --porcelain 2>/dev/null | grep -c '^worktree ')"
    [ "${n:-0}" -le 1 ] && continue
    dirs="$(git -C "$repo" worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2}' | tail -n +2 | tr '\n' ' ')"
    echo "$(basename "$repo"): $((n-1)) worktree(s)"
    for d in $dirs; do
      [ -d "$d" ] || { echo "   LEAK (dir gone): $d"; continue; }
      echo "   $(git -C "$d" status --porcelain 2>/dev/null | wc -l | tr -d ' ') dirty · $(git -C "$d" rev-parse --abbrev-ref HEAD 2>/dev/null) · $d"
    done
  done
}

case "${1:-}" in
  new)   shift; [ $# -ge 2 ] || die "new <project> <taskid>"; cmd_new "$@";;
  list)  shift; [ $# -ge 1 ] || die "list <project>"; cmd_list "$@";;
  flags) shift; [ $# -ge 2 ] || die "flags <project> <taskid>"; cmd_flags "$@";;
  reap)  shift; [ $# -ge 1 ] || die "reap <project> [--all]"; cmd_reap "$@";;
  prune) shift; [ $# -ge 1 ] || die "prune <project>"; cmd_prune "$@";;
  doctor) cmd_doctor;;
  *) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 1;;
esac
