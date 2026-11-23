#!/usr/bin/env bash
# Prove product-tree identity across a commit SERIES by one digest, not pairwise tree equality.
#
#   scripts/product-digest.sh <git-dir> <ref> [<ref> ...]
#
# Prints, per ref: file count + sha256 over the filtered `git ls-tree -r` listing
# (mode, blob sha and path all participate, so equal digests == byte-identical product trees).
# Root trees differ whenever bookkeeping paths differ, so `rev-parse <sha>^{tree}` equality
# cannot answer "is the product the same across these five commits" — this can.
#
# EXCLUDES: space-separated path prefixes, default '.coding-hermes/ .gitreins/'.
set -euo pipefail

DIR=${1:?usage: product-digest.sh <git-dir> <ref> [<ref>...]}
shift
[ $# -ge 1 ] || { echo "usage: product-digest.sh <git-dir> <ref> [<ref>...]" >&2; exit 2; }

EXCLUDES=${EXCLUDES-.coding-hermes/ .gitreins/}

git -C "$DIR" rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git dir: $DIR" >&2; exit 2; }

for REF in "$@"; do
  SHA=$(git -C "$DIR" rev-parse --verify "$REF^{commit}" 2>/dev/null) || {
    echo "BAD_REF $REF" >&2; exit 3; }

  # Filter in awk on field 2 (the PATH). Field 1 is mode, field 2 is type, so split on tab and
  # take the LAST field: a grep anchored on '^(dir)/' matches the mode column instead and silently
  # drops nothing, digesting the whole tree and faking a multi-way mismatch.
  FILTERED=$(git -C "$DIR" ls-tree -r --full-tree "$SHA" \
    | awk -F'\t' -v ex="$EXCLUDES" '
        BEGIN { n = split(ex, a, " "); for (i = 1; i <= n; i++) if (a[i] != "") p[i] = a[i] }
        {
          path = $2
          for (i in p) if (index(path, p[i]) == 1) next
          print $1 "\t" $2 "\t" $3
        }')

  # Fail LOUD when the filter removed everything: a no-op filter is how a "product digest"
  # silently becomes a whole-tree digest and reports divergence that does not exist.
  COUNT=$(printf '%s\n' "$FILTERED" | grep -c . || true)
  if [ "$COUNT" -eq 0 ]; then
    echo "FILTER_NOOP $REF ($SHA): no paths survived EXCLUDES='$EXCLUDES'" >&2
    exit 4
  fi

  TOTAL=$(git -C "$DIR" ls-tree -r --full-tree "$SHA" | wc -l | tr -d ' ')
  DIGEST=$(printf '%s\n' "$FILTERED" | LC_ALL=C sort | sha256sum | cut -d' ' -f1)

  printf '%s\tsha=%s\tproduct_files=%s\tbookkeeping_files=%s\tdigest=%s\n' \
    "$REF" "$SHA" "$COUNT" "$((TOTAL - COUNT))" "$DIGEST"
  LAST_DIGEST=$DIGEST
  LAST_COUNT=$COUNT
  [ -n "${FIRST_DIGEST:-}" ] || FIRST_DIGEST=$DIGEST
  [ -n "${FIRST_COUNT:-}" ] || FIRST_COUNT=$COUNT
  if [ -n "${PREV_DIGEST:-}" ] && [ "$DIGEST" != "$PREV_DIGEST" ]; then
    echo "DIVERGES from previous ref: $REF" >&2
  fi
  PREV_DIGEST=$DIGEST
  unset PREV_DIGEST_
  true
  PREV_DIGEST=$DIGEST
done

echo "IDENTITY=$([ "$FIRST_DIGEST" = "$LAST_DIGEST" ] && [ "$FIRST_COUNT" = "$LAST_COUNT" ] && echo MATCH || echo MISMATCH)"
