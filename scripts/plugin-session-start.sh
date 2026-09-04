#!/bin/bash
# plugin install delivers files, it can't set statusLine. this notices the gap
# and hands /creature the path it needs to close it.
set -uo pipefail

HOMEDIR="$HOME/.claude/terminalcreature"
ROOT="${CLAUDE_PLUGIN_ROOT:-}"

# the cache path moves on every plugin update, so re-record it each session
# rather than only when unwired
if [ -n "$ROOT" ]; then
  mkdir -p "$HOMEDIR" 2>/dev/null || exit 0
  printf '%s\n' "$ROOT" > "$HOMEDIR/plugin-root" 2>/dev/null || exit 0
fi

# wired means both halves: the library the commands import, and a statusLine
# actually pointing at the shim. either one missing and there's no creature.
check_wired() {
  [ -d "$HOMEDIR/lib/terminalcreature" ] || return 1
  [ -x "$HOMEDIR/statusline-terminalcreature.sh" ] || return 1
  # match on the shim's basename, not its full path: a hand-wired user may point
  # at it through ~, and a false "not wired" nags them every session
  python3 - "$HOME/.claude/settings.json" <<'PY' 2>/dev/null
import json, sys
try:
    with open(sys.argv[1]) as f:
        cmd = (json.load(f).get("statusLine") or {}).get("command", "")
except Exception:
    cmd = ""
raise SystemExit(0 if "statusline-terminalcreature.sh" in cmd else 1)
PY
}

if check_wired; then exit 0; fi

python3 - "$ROOT" <<'PY'
import json, sys
root = sys.argv[1] or "the terminalcreature plugin directory"
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": (
        "terminalcreature is installed as a plugin but its statusline is not wired up yet, so "
        "there is no creature on screen and its CLI is not on disk. If the user runs any "
        "/creature command or asks about it, offer to finish the setup by running:\n"
        "  %s/install.sh --no-commands\n"
        "It wraps their existing statusline rather than replacing it, and lays the first "
        "egg. Ask before running it." % root
    ),
}}))
PY
