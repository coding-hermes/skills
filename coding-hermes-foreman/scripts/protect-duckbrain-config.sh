#!/bin/bash
# Protect duckbrain.config.json fleet-level fields from foreman rotation.
# Place this in .git/hooks/pre-commit or reference from .gitreins/hooks.
# When defaultNamespace or authorEmail changes are staged, block the commit.

STAGED=$(git diff --cached --name-only | grep duckbrain.config.json)
if [ -z "$STAGED" ]; then
  exit 0  # config not in this commit
fi

ROTATED=$(git diff --cached duckbrain.config.json | grep -E '^[-+].*"(defaultNamespace|authorEmail)"' | grep -v hermes-memory | grep -v totalwindupflightsystems)
if [ -n "$ROTATED" ]; then
  echo "⛔ BLOCKED: duckbrain.config.json fleet-level fields changed."
  echo "   defaultNamespace is PINNED to hermes-memory."
  echo "   authorEmail is PINNED to totalwindupflightsystems@gmail.com."
  echo "   Revert these changes before committing."
  echo ""
  echo "   Changed lines:"
  echo "$ROTATED"
  exit 1
fi

exit 0
