#!/bin/bash
# terminalcreature installer. wraps an existing statusline, never replaces it.

# every line below this is bash, pipefail included, so bash gets confirmed first.
# windows has no bash of its own but two shells that are one, so name both.
if [ -z "${BASH_VERSION:-}" ]; then
  case "$(uname -s 2>/dev/null || echo unknown)" in
    MINGW*|MSYS*|CYGWIN*|Windows*)
      echo "this installer is bash, and this shell isn't. two routes work on windows: WSL, or Git Bash," >&2
      echo "which comes with git for windows. open either one and run ./install.sh again." >&2
      ;;
    *)
      echo "this installer is bash. run 'bash install.sh' rather than sh." >&2
      echo "on windows that means WSL or Git Bash; there's no powershell version." >&2
      ;;
  esac
  exit 1
fi
set -euo pipefail

usage() {
  cat <<'EOF'
terminalcreature installer

  ./install.sh                     install, wire claude's statusline, then every other agent found here
  ./install.sh --folder <path>     count a folder of markdown notes
  ./install.sh --vault <path>      use a structured vault layout
  ./install.sh --statusline <cmd>  wrap this command instead of settings.json's
  ./install.sh --inline            one-line segment instead of the boxed column
  ./install.sh --no-wire           install the library only, wire it yourself
  ./install.sh --no-commands       skip the slash commands, something else ships them
  ./install.sh --claude-only       wire claude and leave the other agents alone
  ./install.sh --host <name>       wire one host instead: cursor, copilot, qwen, droid, or a card host
  ./install.sh --uninstall         unwire every host, restore the old statuslines
EOF
}

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOMEDIR="$HOME/.claude/terminalcreature"
LIB="$HOMEDIR/lib"
CMDS="$HOME/.claude/commands"
SETTINGS="$HOME/.claude/settings.json"
SHIM="$HOMEDIR/statusline-terminalcreature.sh"
WRAPPED="$HOMEDIR/wrapped-command"
BEGIN="# >>> brainbuddy >>>"
END="# <<< brainbuddy <<<"
COMMAND_NAMES="creature creature-hide creature-show creature-new creature-hatch creature-update"
# what a brainbuddy 1.x install left behind, for the migration
OLD_HOMEDIR="$HOME/.claude/brainbuddy"
OLD_SHIM="$OLD_HOMEDIR/statusline-brainbuddy.sh"
OLD_COMMAND_NAMES="brainbuddy brainbuddy-hide brainbuddy-show brainbuddy-new brainbuddy-hatch"
VAULT=""
FOLDER=""
WIRE=1
INLINE=0
COMMANDS=1
MODE=install
STATUSLINE=""
# empty means claude here, then every other agent the adapters detect
HOST=""
CLAUDE_ONLY=0
# set when a host adapter reports a failure: the script carries on past it,
# since the hosts after it and the egg still want doing, and exits 1 at the end
HOSTFAIL=0

# shift 2 with nothing to shift trips set -e, so a missing value used to exit 1
# with no output at all
need_value() {
  if [ -z "${2:-}" ]; then echo "$1 needs a value"; usage; exit 1; fi
}

while [ $# -gt 0 ]; do
  case "$1" in
    --vault) need_value --vault "${2:-}"; VAULT="$2"; shift 2 ;;
    --folder) need_value --folder "${2:-}"; FOLDER="$2"; shift 2 ;;
    --statusline) need_value --statusline "${2:-}"; STATUSLINE="$2"; shift 2 ;;
    --host) need_value --host "${2:-}"; HOST="$2"; shift 2 ;;
    --claude-only) CLAUDE_ONLY=1; shift ;;
    --inline) INLINE=1; shift ;;
    --no-wire) WIRE=0; shift ;;
    --no-commands) COMMANDS=0; shift ;;
    --uninstall) MODE=uninstall; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1"; exit 1 ;;
  esac
done

command -v python3 >/dev/null 2>&1 || { echo "python3 not found. terminalcreature needs it."; exit 1; }

# --host all is the default spelled out, --host claude is --claude-only
case "$HOST" in
  all) HOST="" ;;
  claude) HOST=""; CLAUDE_ONLY=1 ;;
esac

# the other hosts are wired by the python adapters. this script stays the
# claude path. the source tree is on the path too, for an uninstall run after
# the library is already gone
hostbb() { PYTHONPATH="$LIB:$SRC" python3 -m terminalcreature.cli "$@"; }
# one named host takes every flag; the sweep over detected hosts takes --inline
# only, since --statusline names claude's command and would wrap it everywhere
HOSTARGS=(--host "$HOST")
SWEEPARGS=()
if [ "$INLINE" = 1 ]; then HOSTARGS+=(--inline); SWEEPARGS+=(--inline); fi
if [ -n "$STATUSLINE" ]; then HOSTARGS+=(--statusline "$STATUSLINE"); fi

# every host the adapters detect, claude reporting itself already wired.
# under bash 3.2 an empty array expands as unset, so the guard
sweep_hosts() {
  if [ "${#SWEEPARGS[@]}" -gt 0 ]; then hostbb install "${SWEEPARGS[@]}"; else hostbb install; fi
}

read_statusline() {
  python3 - "$SETTINGS" <<'PY'
import json, sys
try:
    with open(sys.argv[1]) as f:
        print((json.load(f).get("statusLine") or {}).get("command", ""))
except Exception:
    print("")
PY
}

write_statusline() {
  # $1 = command, or empty to drop the key entirely
  python3 - "$SETTINGS" "$1" <<'PY'
import json, os, shutil, sys
path, command = sys.argv[1], sys.argv[2]
data = {}
if os.path.exists(path):
    # raw bytes, before parsing. a backup of the parse result is worthless
    # exactly when you need it
    backup = path + ".pre-terminalcreature.bak"
    if not os.path.exists(backup):
        shutil.copyfile(path, backup)
    with open(path) as f:
        try:
            data = json.load(f)
        except ValueError:
            sys.stderr.write("settings.json isn't valid JSON, so nothing was changed. fix it and re-run.\n")
            raise SystemExit(1)
# mutate rather than replace, or siblings like padding get dropped
line = data.get("statusLine")
if not isinstance(line, dict):
    line = {}
if command:
    line.setdefault("type", "command")
    line["command"] = command
    data["statusLine"] = line
else:
    data.pop("statusLine", None)
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
}

target_path_of() {
  local cmd="$1" cand
  # the script can be the whole string, the first word or the last. ~ expands by
  # substitution, since `eval echo` would run substitutions from the user's config.
  for cand in "$cmd" "${cmd%% *}" "${cmd##* }"; do
    cand="${cand/#\~/$HOME}"
    if [ -n "$cand" ] && [ -f "$cand" ]; then echo "$cand"; return 0; fi
  done
  echo ""
}

# none | ours | modified. ours comes out or the creature renders twice; an edited
# one is their code.
classify_target() {
  local target="$1"
  if [ -z "$target" ] || [ ! -f "$target" ]; then echo none; return 0; fi
  python3 - "$target" "$BEGIN" "$END" <<'PY'
import sys
path, begin, end = sys.argv[1], sys.argv[2], sys.argv[3]
GENERATED = ['printf " "', '"$HOME/.claude/terminalcreature/statusline-terminalcreature.sh"']
GENERATED_OLD = ['printf " "', '"$HOME/.claude/brainbuddy/statusline-brainbuddy.sh"']
try:
    with open(path) as f:
        lines = [line.rstrip("\n") for line in f]
except OSError:
    print("none")
    raise SystemExit
inner, inside, fenced = [], False, False
for line in lines:
    s = line.strip()
    if s == begin:
        inside, fenced = True, True
        continue
    if s == end:
        inside = False
        continue
    if inside and s:
        inner.append(s)
if fenced:
    print("ours" if inner in (GENERATED, GENERATED_OLD) else "modified")
elif any("terminalcreature.cli" in line or "brainbuddy.cli" in line for line in lines):
    print("modified")
else:
    print("none")
PY
}

# bash -c not sh -c, since the wrapped string is whatever was in
# statusLine.command and may lean on bash, which isn't sh everywhere.
write_shim() {
  # one prologue for both modes, or a bug in it has two places to live
  cat > "$SHIM" <<'EOF'
#!/bin/bash
# generated by the terminalcreature installer. safe to delete, reinstalling restores it.
# already inside our own wrap, so the thing we'd run next is us. that forks forever.
if [ -n "${TERMINALCREATURE_WRAPPING:-}" ]; then exit 0; fi
export TERMINALCREATURE_WRAPPING=1
# the installer's library when it is here, else a pip or pipx entry point on PATH
if [ -d "$HOME/.claude/terminalcreature/lib" ]; then
  creature() { PYTHONPATH="$HOME/.claude/terminalcreature/lib" python3 -m terminalcreature.cli "$@"; }
else
  creature() { terminalcreature "$@"; }
fi
INPUT="$(cat)"
LEFT=""
if [ -s "$HOME/.claude/terminalcreature/wrapped-command" ]; then
  LEFT="$(printf '%s' "$INPUT" | bash -c "$(cat "$HOME/.claude/terminalcreature/wrapped-command")" 2>/dev/null)"
fi
EOF
  if [ "$INLINE" = 1 ]; then
    cat >> "$SHIM" <<'EOF'
printf '%s' "$LEFT"
if [ -n "$LEFT" ]; then printf ' '; fi
printf '%s' "$INPUT" | creature render 2>/dev/null || true
EOF
  else
    cat >> "$SHIM" <<'EOF'
printf '%s' "$INPUT" | creature compose "$LEFT" 2>/dev/null || printf '%s' "$LEFT"
EOF
  fi
  chmod +x "$SHIM"
}

strip_legacy_block() {
  local target="$1"
  python3 - "$target" "$BEGIN" "$END" <<'PY'
import sys
path, begin, end = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f:
    lines = f.readlines()
out, skip = [], False
for line in lines:
    if line.strip() == begin: skip = True; continue
    if line.strip() == end: skip = False; continue
    if not skip: out.append(line)
with open(path, "w") as f:
    f.writelines(out)
PY
  echo "  removed the old terminalcreature block from $(basename "$target")"
}

# a brainbuddy install comes over in place: same creature, same wrapped command,
# settings repointed, old command files gone. a stub stays at the old shim path
# because a project-level settings.json may still name it.
migrate_from_brainbuddy() {
  [ -d "$OLD_HOMEDIR" ] || return 0
  local moved=0 f c
  for f in state.json xp.cache latest-version wrapped-command; do
    if [ -f "$OLD_HOMEDIR/$f" ] && [ ! -e "$HOMEDIR/$f" ]; then mv "$OLD_HOMEDIR/$f" "$HOMEDIR/$f"; moved=1; fi
  done
  rm -rf "$OLD_HOMEDIR/lib" "$OLD_HOMEDIR/plugin-root"
  if [ "$COMMANDS" = 1 ]; then
    for c in $OLD_COMMAND_NAMES; do rm -f "$CMDS/$c.md"; done
  fi
  printf '%s\n' '#!/bin/bash' \
    '# brainbuddy is now terminalcreature. this stub hands off to the new shim.' \
    'exec "$HOME/.claude/terminalcreature/statusline-terminalcreature.sh" "$@"' > "$OLD_SHIM"
  chmod +x "$OLD_SHIM"
  case "$(read_statusline)" in
    "$OLD_SHIM"|"~/.claude/brainbuddy/statusline-brainbuddy.sh"|"\$HOME/.claude/brainbuddy/statusline-brainbuddy.sh")
      write_statusline "$SHIM"
      echo "  migrated -> your brainbuddy install, same creature, new name" ;;
    *)
      if [ "$moved" = 1 ]; then echo "  migrated -> your brainbuddy state, same creature, new name"; fi ;;
  esac
}

if [ "$MODE" = uninstall ] && [ -n "$HOST" ]; then
  hostbb uninstall "${HOSTARGS[@]}"
  # one host unwired, the library stays for the others
  exit 0
fi

if [ "$MODE" = uninstall ]; then
  PREVIOUS=""
  if [ -s "$WRAPPED" ]; then PREVIOUS="$(cat "$WRAPPED")"; fi
  CURRENT="$(read_statusline)"
  # a hand-wired settings.json can name the shim through ~, and an exact string
  # compare would then delete the shim while leaving statusLine pointing at it
  case "$CURRENT" in
    "$SHIM"|"~/.claude/terminalcreature/statusline-terminalcreature.sh"|"\$HOME/.claude/terminalcreature/statusline-terminalcreature.sh") CURRENT="$SHIM" ;;
    "$OLD_SHIM"|"~/.claude/brainbuddy/statusline-brainbuddy.sh"|"\$HOME/.claude/brainbuddy/statusline-brainbuddy.sh") CURRENT="$SHIM" ;;
  esac
  if [ "$CURRENT" = "$SHIM" ]; then
    write_statusline "$PREVIOUS"
    if [ -n "$PREVIOUS" ]; then
      echo "restored your previous statusline"
    else
      echo "removed the statusline entry we added"
    fi
  fi
  # our own shim always contains a terminalcreature call, so classifying it would
  # accuse the user of editing a file we generated. look at what it wrapped.
  if [ "$CURRENT" = "$SHIM" ]; then LEGACY="$(target_path_of "$PREVIOUS")"; else LEGACY="$(target_path_of "$CURRENT")"; fi
  case "$(classify_target "$LEGACY")" in
    ours) strip_legacy_block "$LEGACY" ;;
    modified) echo "left $(basename "$LEGACY") alone, you've edited the terminalcreature block in it" ;;
  esac
  rm -rf "$LIB" "$SHIM" "$WRAPPED" "$HOMEDIR/plugin-root" "$OLD_SHIM"
  # under --no-commands they're the plugin's copies, not ours to delete
  if [ "$COMMANDS" = 1 ]; then
    for cmd in $COMMAND_NAMES; do rm -f "$CMDS/$cmd.md"; done
  fi
  # claude is already back, so the adapters see only the other wired hosts.
  # their "nothing wired" line is noise under the summary, everything else is not
  if [ "$CLAUDE_ONLY" = 0 ]; then
    OTHERS="$(hostbb uninstall)" || HOSTFAIL=1
    case "$OTHERS" in "no host is wired"*) ;; *) echo "$OTHERS" ;; esac
  fi
  echo "uninstalled. state kept at ~/.claude/terminalcreature/state.json (delete it yourself for a clean slate)"
  exit "$HOSTFAIL"
fi

echo "installing terminalcreature"
mkdir -p "$LIB" "$CMDS" "$HOMEDIR"
migrate_from_brainbuddy
rm -rf "$LIB/terminalcreature"
cp -R "$SRC/terminalcreature" "$LIB/terminalcreature"
# don't ship the dev machine's bytecode
find "$LIB/terminalcreature" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
if [ "$COMMANDS" = 1 ]; then
  for cmd in $COMMAND_NAMES; do
    if [ -f "$SRC/commands/$cmd.md" ]; then cp "$SRC/commands/$cmd.md" "$CMDS/$cmd.md"; fi
  done
fi
# ~ rather than the expanded path, so a screenshot of this carries no username
echo "  library  -> ${LIB/#$HOME/~}"
if [ "$COMMANDS" = 1 ]; then
  echo "  commands -> ${CMDS/#$HOME/~}  (/creature, -new, -hatch, -hide, -show, -update)"
else
  echo "  commands -> left alone, the plugin already provides them"
fi

# always, even under --no-wire: self-wirers point their own script at it
write_shim

bb() { PYTHONPATH="$LIB" python3 -m terminalcreature.cli "$@"; }

if [ -n "$FOLDER" ]; then
  bb config provider folder >/dev/null
  bb config vault_root "$FOLDER" >/dev/null
  # a typo'd path otherwise reads as a working setup here and only surfaces
  # further down, after we've promised the egg will have earned a level
  if [ -d "${FOLDER/#\~/$HOME}" ]; then TYPO=""; else TYPO="  (not there yet)"; fi
  echo "  provider -> folder of notes at $FOLDER$TYPO"
elif [ -n "$VAULT" ]; then
  bb config provider vault >/dev/null
  bb config vault_root "$VAULT" >/dev/null
  if [ -d "${VAULT/#\~/$HOME}" ]; then TYPO=""; else TYPO="  (not there yet)"; fi
  echo "  provider -> vault at $VAULT$TYPO"
else
  # report what's actually configured. this used to claim stock memory on every
  # run without --vault, including reinstalls over a vault setup it left alone
  CURRENT_PROVIDER=$(bb config 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('provider','claude'), d.get('vault_root') or '')" 2>/dev/null || echo "claude ")
  case "$CURRENT_PROVIDER" in
    "vault "*) echo "  provider -> vault at ${CURRENT_PROVIDER#vault }  (unchanged)" ;;
    "folder "*) echo "  provider -> folder of notes at ${CURRENT_PROVIDER#folder }  (unchanged)" ;;
    "agents "*) echo "  provider -> every coding agent's memory on this machine  (unchanged)" ;;
    "claude "*) echo "  provider -> stock Claude Code memory (~/.claude/projects/*/memory)  (unchanged)" ;;
    *) echo "  provider -> auto (every coding agent's memory when two or more are installed, else stock Claude Code memory)" ;;
  esac
fi

HOSTWIRED=0
if [ "$WIRE" = 1 ] && [ -n "$HOST" ]; then
  hostbb install "${HOSTARGS[@]}" || HOSTFAIL=1
  HOSTWIRED=1
  WIRE=0
fi

if [ "$WIRE" = 1 ]; then
  if [ -n "$STATUSLINE" ]; then
    EXISTING="$STATUSLINE"
  else
    EXISTING="$(read_statusline)"
  fi

  # re-installing over ourselves, so keep what we wrapped last time
  if [ "$EXISTING" = "$SHIM" ]; then
    EXISTING=""
    if [ -s "$WRAPPED" ]; then EXISTING="$(cat "$WRAPPED")"; fi
  fi

  HANDWIRED=""
  TARGET="$(target_path_of "$EXISTING")"
  case "$(classify_target "$TARGET")" in
    ours) strip_legacy_block "$TARGET" ;;
    modified) HANDWIRED="$TARGET" ;;
  esac
fi

if [ "$WIRE" = 1 ] && [ -n "${HANDWIRED:-}" ]; then
  echo "  ! $(basename "$HANDWIRED") calls terminalcreature itself, so wrapping it would draw two creatures"
  echo "    leaving your wiring and settings.json alone, library updated in place."
  echo "    to hand the wiring over, drop the terminalcreature lines from that script and re-run"
  WIRE=0
fi

if [ "$WIRE" = 1 ]; then
  if [ -n "$EXISTING" ]; then
    printf '%s' "$EXISTING" > "$WRAPPED"
    if [ "$INLINE" = 1 ]; then
      WIRED="  statusline -> wrapping your existing one, creature as a segment after it"
    else
      WIRED="  statusline -> wrapping your existing one, creature on the left"
    fi
  else
    : > "$WRAPPED"
    WIRED="  statusline -> set in settings.json"
  fi

  # after the write, not before, so a refusal doesn't get announced as a success
  write_statusline "$SHIM"
  echo "$WIRED"
  # then every other agent on the machine, so nobody picks hosts. claude is
  # wired above and the adapters say so
  if [ "$CLAUDE_ONLY" = 0 ]; then
    echo "  hosts    -> every agent found here (--claude-only skips this)"
    sweep_hosts || HOSTFAIL=1
    HOSTWIRED=1
  fi
fi

echo
# `sources` exits nonzero when there's nothing to count
SOURCE_HELP=""
if bb sources >/dev/null 2>&1; then HAS_SOURCE=1; else HAS_SOURCE=0; SOURCE_HELP="$(bb sources 2>/dev/null || true)"; fi

# lay the first egg so the zero state is an egg rather than nothing at all.
# `new` exits 1 when a buddy exists, which is the re-install path: leave it be
if ! bb new >/dev/null 2>&1; then bb list; echo; fi

# homework first, egg last: the door closes on the one action left to take,
# not on a config recipe
if [ -n "$SOURCE_HELP" ]; then echo "$SOURCE_HELP"; echo; fi

# prompt off the roster, not off whether we just laid it, or a reinstall never
# re-offers the one action the user still has to take
if bb list 2>/dev/null | grep -q '^\*.*unhatched'; then
  if [ "$WIRE" = 1 ] || [ "$HOSTWIRED" = 1 ] || [ -n "${HANDWIRED:-}" ]; then
    echo "there's an egg in your statusline, and it's hungry. open it:"
  else
    # --no-wire promised "wire it yourself"; this is the how
    echo "there's an egg waiting, and it's hungry. it shows up once statusLine.command"
    echo "points at ~/.claude/terminalcreature/statusline-terminalcreature.sh. open it either way:"
  fi
  echo "  /creature-hatch"
  if [ "$HAS_SOURCE" = 1 ]; then
    echo "it hatches at whatever level your memories have already fed it."
  else
    echo "it'll open at level 0 for now, and grow once there are memories to feed on."
  fi
fi

# the host that failed said why above; the exit code says so too
if [ "$HOSTFAIL" = 1 ]; then
  echo
  echo "one host above wasn't wired. fix its file and run 'terminalcreature install' again"
  exit 1
fi
