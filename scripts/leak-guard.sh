#!/bin/bash
# terminalcreature points at directories full of private notes, so no absolute home
# path or vault-shaped filename should ever reach the repo. Given filenames, it
# checks those; given none, it checks everything tracked. The hook passes the
# commits it's about to push, CI passes nothing and gets the whole tree.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

HITS=0
CHECKED=0
scan() {
  f="$1"
  [ -f "$f" ] || return 0
  # this file and the hook both carry the pattern, so they'd match themselves
  case "$f" in .githooks/*|scripts/leak-guard.sh) return 0 ;; esac
  CHECKED=$((CHECKED + 1))
  if grep -inE '/(Users|home)/[^/ "]+/|project_[a-z_]+\.md|reference_[a-z_]+\.md' "$f" >/dev/null 2>&1; then
    echo "leak-guard: $f contains a machine path or vault-shaped filename"
    HITS=1
  fi
}

if [ "$#" -gt 0 ]; then
  # quoted all the way down. a filename with a space used to split in two here,
  # and both halves failed the -f test, so the one file that mattered was the
  # one file never opened
  for f in "$@"; do scan "$f"; done
else
  while IFS= read -r -d '' f; do scan "$f"; done < <(git ls-files -z)
fi

[ "$HITS" = 0 ] || { echo "leak-guard: blocked. scrub these before pushing."; exit 1; }
echo "leak-guard: clean ($CHECKED files)"
