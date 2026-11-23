#!/usr/bin/env bash
# verify-go-release-assets.sh — verify a published Go release from its OWN bytes.
#
# Downloads the Release's assets, checks SHA256SUMS, then reads buildinfo from
# every binary with `go version -m`. It never executes an asset (an unattended
# surface can refuse a command that runs a downloaded binary, taking the
# harmless reads down with it), so this is the safe first leg after a cut.
#
# Usage:
#   verify-go-release-assets.sh <org/repo> <tag> [--expected <sha>] [--dir <path>]
#
# <tag> may be passed with or without the leading v. --expected is the tag's
# commit (short or full); every asset must report that vcs.revision prefix.
# --dir defaults to a fresh path named from the tag, so nothing needs cleaning
# up beforehand (a pre-clean `rm -rf` in the same command gets the whole line
# refused on a consent-gated surface).
#
# Exit codes: 0 all assets verified | 1 a check failed | 2 setup/download problem.
set -u

repo=""; tag=""; expected=""; dir=""
while [ $# -gt 0 ]; do
  case "$1" in
    --expected) expected="${2:-}"; shift 2 ;;
    --dir) dir="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) if [ -z "$repo" ]; then repo="$1"; elif [ -z "$tag" ]; then tag="$1"; else echo "unexpected arg: $1" >&2; exit 2; fi; shift ;;
  esac
done

if [ -z "$repo" ] || [ -z "$tag" ]; then
  echo "usage: $(basename "$0") <org/repo> <tag> [--expected <sha>] [--dir <path>]" >&2
  exit 2
fi

ver="${tag#v}"
dir="${dir:-${TMPDIR:-/tmp}/releng-assets-${tag}-$$}"

mkdir -p "$dir" || exit 2
echo "repo=$repo tag=$tag version=$ver dir=$dir"

gh release download "$tag" --repo "$repo" --dir "$dir" --clobber || { echo "DOWNLOAD FAILED" >&2; exit 2; }

count=$(find "$dir" -maxdepth 1 -type f | wc -l | tr -d ' ')
echo "assets: $count"

if [ -f "$dir/SHA256SUMS" ]; then
  ( cd "$dir" && sha256sum -c SHA256SUMS ) || { echo "CHECKSUM MISMATCH" >&2; exit 1; }
else
  echo "WARN: no SHA256SUMS asset published" >&2
fi

ok=0; bad=0
for f in "$dir"/*; do
  [ -f "$f" ] || continue
  base=$(basename "$f")
  case "$base" in SHA256SUMS|*.txt|*.json|*.md) continue ;; esac

  info=$(go version -m "$f" 2>/dev/null | tr '\n' ';')
  if [ -z "$info" ]; then
    echo "FAIL $base: no Go buildinfo (not a Go binary, or download truncated)"; bad=$((bad+1)); continue
  fi

  modver=$(printf '%s' "$info" | tr ';' '\n' | awk '$1=="mod"{print $3}' | head -1)
  rev=$(printf '%s' "$info" | tr ';' '\n' | sed -n 's/.*vcs\.revision=\([0-9a-f]\{7,\}\).*/\1/p' | head -1)

  reason=""
  case "$info" in *vcs.modified=false*) ;; *) reason="vcs.modified is not false" ;; esac
  if [ -z "$reason" ] && [ "$modver" != "v$ver" ] && [ "$modver" != "$ver" ]; then
    reason="mod version '$modver' != '$tag'"
  fi
  if [ -z "$reason" ] && [ -n "$expected" ]; then
    case "$rev" in "$expected"*) ;; *) reason="vcs.revision '${rev:-none}' does not match expected '$expected'" ;; esac
  fi

  if [ -z "$reason" ]; then
    ok=$((ok+1)); echo "OK   $base  mod=$modver rev=${rev:0:8}"
  else
    bad=$((bad+1)); echo "FAIL $base: $reason  (mod=${modver:-?} rev=${rev:-?})"
  fi
done

echo "buildinfo: ok=$ok bad=$bad"
[ "$bad" -eq 0 ] || exit 1
exit 0
