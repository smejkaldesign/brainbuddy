#!/bin/bash
# brainbuddy points at directories full of private notes, so no absolute home
# path or vault-shaped filename should ever reach the repo. Given filenames, it
# checks those; given none, it checks everything tracked. The hook passes the
# commits it's about to push, CI passes nothing and gets the whole tree.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ "$#" -gt 0 ]; then FILES="$*"; else FILES=$(git ls-files); fi

HITS=0
CHECKED=0
for f in $FILES; do
  [ -f "$f" ] || continue
  # this file and the hook both carry the pattern, so they'd match themselves
  case "$f" in .githooks/*|scripts/leak-guard.sh) continue ;; esac
  CHECKED=$((CHECKED + 1))
  if grep -nE '/Users/[a-z]+/(dev|Documents)/|project_[a-z_]+\.md|reference_[a-z_]+\.md' "$f" >/dev/null 2>&1; then
    echo "leak-guard: $f contains a machine path or vault-shaped filename"
    HITS=1
  fi
done

[ "$HITS" = 0 ] || { echo "leak-guard: blocked. scrub these before pushing."; exit 1; }
echo "leak-guard: clean ($CHECKED files)"
