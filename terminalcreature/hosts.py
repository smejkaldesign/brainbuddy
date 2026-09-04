"""What each host pipes to a statusline command, and how to read it.

Every host that renders a statusline copies Claude Code's contract: session
JSON on stdin, stdout drawn in the chrome. The field names drift a little
per host, so this is one map from each host's shape to the four things the
creature cares about. Nothing here raises: a payload we don't recognise
renders without a session, it never breaks the prompt.
"""

import json
import os
import shlex
import shutil

HOSTS = ("claude", "cursor", "copilot", "qwen", "droid")

# dotted paths tried in order per field. a list at a path means its first item
FIELD_MAP = {
    "claude": {
        "session_id": ("session_id",),
        "model": ("model.display_name", "model.id"),
        "workspace": ("workspace.current_dir", "cwd"),
        "context_used_pct": ("context_window.used_percentage", "context_window.percentage",
                             "context_usage.used_percentage"),
    },
    # read off the cursor cli 2026.09 bundle: claude's shape plus render_width_chars
    # and autorun, with session_name, vim and worktree when they apply
    "cursor": {
        "session_id": ("session_id",),
        "model": ("model.display_name", "model.id"),
        "workspace": ("workspace.current_dir", "cwd"),
        "context_used_pct": ("context_window.used_percentage",),
        # the columns cursor gives the line; the only host that says
        "width": ("render_width_chars",),
    },
    # read off the copilot cli 1.0.82 bundle: claude's shape plus session_name,
    # username, remote, ai_used and allow_all_enabled
    "copilot": {
        "session_id": ("session_id",),
        "model": ("model.display_name", "model.id"),
        "workspace": ("workspace.current_dir", "cwd"),
        "context_used_pct": ("context_window.used_percentage", "context_window.percentage"),
    },
    "qwen": {
        "session_id": ("session_id",),
        "model": ("model.display_name",),
        "workspace": ("workspace.current_dir",),
        "context_used_pct": ("context_window.used_percentage",),
    },
    # docs only, never captured live. accepts the claude shape and a flat
    # camelCase one, since the settings file is camelCase throughout
    "droid": {
        "session_id": ("session_id", "sessionId", "session.id"),
        "model": ("model.display_name", "model", "modelId"),
        "workspace": ("workspace.current_dir", "cwd", "workingDirectory"),
        "context_used_pct": ("context_window.used_percentage", "contextWindow.usedPercentage",
                             "contextUsagePercent"),
    },
}

# keys only that host sends. checked in this order, so a host that copies
# claude's keys and adds its own is named before the claude fallback catches it.
# cursor and copilot both send transcript_path and output_style, so they go first
MARKERS = (
    ("cursor", ("render_width_chars", "autorun", "vim", "worktree")),
    ("copilot", ("username", "remote", "ai_used", "allow_all_enabled")),
    ("qwen", ("metrics",)),
    ("droid", ("sessionId", "workingDirectory", "modelId")),
    ("claude", ("transcript_path", "hook_event_name", "cost", "exceeds_200k_tokens", "output_style")),
)
# claude's keys with nothing else to go on. cursor and copilot both send these
CLAUDE_SHAPE = ("session_id", "model", "workspace", "context_window")

EMPTY = {"host": "unknown", "session_id": None, "model": None, "workspace": None, "context_used_pct": None,
         "width": None}


def _get(data, path):
    cur = data
    for key in path.split("."):
        if isinstance(cur, list):
            cur = cur[0] if cur else None
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    if isinstance(cur, list):
        cur = cur[0] if cur else None
    return cur


def _first(data, paths, kind):
    for path in paths:
        value = _get(data, path)
        if kind is str and isinstance(value, str) and value:
            return value
        if kind is float and isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def detect(data):
    """Which host's shape this is, or "unknown"."""
    if not isinstance(data, dict):
        return "unknown"
    for host, keys in MARKERS:
        if any(k in data for k in keys):
            return host
    if any(k in data for k in CLAUDE_SHAPE):
        return "claude"
    return "unknown"


def parse_session(raw_text):
    """Normalise whatever a host piped in. Empty, not JSON, or a shape we don't
    know all come back as host "unknown" with every field None. width is the
    columns the host gives the line, when it says.
    """
    try:
        data = json.loads(raw_text)
    except (ValueError, TypeError):
        return dict(EMPTY)
    host = detect(data)
    if host == "unknown":
        return dict(EMPTY)
    fields = FIELD_MAP[host]
    out = {
        "host": host,
        "session_id": _first(data, fields["session_id"], str),
        "model": _first(data, fields["model"], str),
        "workspace": _first(data, fields["workspace"], str),
        "context_used_pct": _first(data, fields["context_used_pct"], float),
    }
    # width is columns, so a whole number or nothing; most hosts never send one
    width = _first(data, fields.get("width", ()), float)
    out["width"] = int(width) if width is not None and width >= 1 else None
    return out


def describe(session):
    """One line for doctor. Says the shape and what was in it, never the path:
    a workspace dir carries a username, and doctor output gets pasted into issues.
    """
    if session["host"] == "unknown":
        return "stdin: unknown schema, rendering without a session"
    parts = []
    parts.append("session id" if session["session_id"] else "no session id")
    if session["model"]:
        parts.append("model %s" % session["model"])
    if session["context_used_pct"] is not None:
        parts.append("context %d%%" % int(session["context_used_pct"]))
    if session["workspace"]:
        parts.append("workspace dir")
    return "stdin: %s schema (%s)" % (session["host"], ", ".join(parts))


# ---------------------------------------------------------------------------
# adapters: where each host keeps its settings, and how its statusline key looks

STATE_DIR = "~/.claude/terminalcreature"
BACKUP_SUFFIX = ".pre-terminalcreature.bak"

# settings: the file the key lives in. key: dotted path to the statusline value.
# typed: the value is {"type": "command", "command": ...} rather than {"command": ...}.
# extras: siblings the host wants set alongside the command, added only when absent.
# inline: default to the one-line segment. probe: files or binaries, any one of
# which proves the cli is here when the dir alone doesn't (the cursor ide shares
# ~/.cursor). shim and wrapped are filenames under the state dir.
REGISTRY = {
    "claude": {
        "label": "Claude Code", "dir": "~/.claude", "settings": "~/.claude/settings.json",
        "key": "statusLine", "typed": True, "extras": {}, "jsonc": False, "inline": False, "probe": (),
        "shim": "statusline-terminalcreature.sh", "wrapped": "wrapped-command",
    },
    # the cli-config schema in the 2026.09 bundle: statusLine {type, command,
    # padding?, updateIntervalMs?, timeoutMs?}. a custom statusline replaces the
    # native footer, so inline keeps the wrapped output on the line
    "cursor": {
        "label": "Cursor CLI", "dir": "~/.cursor", "settings": "~/.cursor/cli-config.json",
        "key": "statusLine", "typed": True, "extras": {}, "jsonc": False, "inline": True,
        "probe": ("~/.cursor/cli-config.json", "agent", "cursor-agent"),
        "shim": "statusline-terminalcreature-cursor.sh", "wrapped": "wrapped-command-cursor",
    },
    # jsonc: comments are allowed in the file, so reads strip them and the
    # backup keeps them
    "copilot": {
        "label": "GitHub Copilot CLI", "dir": "~/.copilot", "settings": "~/.copilot/settings.json",
        "key": "statusLine", "typed": True, "extras": {}, "jsonc": True, "inline": False, "probe": (),
        "shim": "statusline-terminalcreature-copilot.sh", "wrapped": "wrapped-command-copilot",
    },
    # two lines at most and a 5 s timeout, so inline. the hot path only reads the cache
    "qwen": {
        "label": "Qwen Code", "dir": "~/.qwen", "settings": "~/.qwen/settings.json",
        "key": "ui.statusLine", "typed": True, "extras": {"respectUserColors": True}, "jsonc": False,
        "inline": True, "probe": (),
        "shim": "statusline-terminalcreature-qwen.sh", "wrapped": "wrapped-command-qwen",
    },
    # {command, padding?, maxRows?}, no type field
    "droid": {
        "label": "Factory Droid", "dir": "~/.factory", "settings": "~/.factory/settings.json",
        "key": "statusLine", "typed": False, "extras": {}, "jsonc": False, "inline": False, "probe": (),
        "shim": "statusline-terminalcreature-droid.sh", "wrapped": "wrapped-command-droid",
    },
}

# one prologue for every host, or a bug in it has five places to live. same
# text as install.sh writes for claude, with the wrapped file swapped per host
SHIM_PROLOGUE = """#!/bin/bash
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
if [ -s "$HOME/.claude/terminalcreature/%(wrapped)s" ]; then
  LEFT="$(printf '%%s' "$INPUT" | bash -c "$(cat "$HOME/.claude/terminalcreature/%(wrapped)s")" 2>/dev/null)"
fi
"""
SHIM_INLINE = """printf '%s' "$LEFT"
if [ -n "$LEFT" ]; then printf ' '; fi
printf '%s' "$INPUT" | creature render 2>/dev/null || true
"""
SHIM_COMPOSE = """printf '%s' "$INPUT" | creature compose "$LEFT" 2>/dev/null || printf '%s' "$LEFT"
"""


def settings_path(host):
    return os.path.expanduser(REGISTRY[host]["settings"])


def shim_path(host):
    return os.path.join(os.path.expanduser(STATE_DIR), REGISTRY[host]["shim"])


def wrapped_path(host):
    return os.path.join(os.path.expanduser(STATE_DIR), REGISTRY[host]["wrapped"])


def installed(host):
    """The host's settings dir is here, and for hosts whose dir is shared with
    something else, one of the probes hit too.
    """
    spec = REGISTRY[host]
    if not os.path.isdir(os.path.expanduser(spec["dir"])):
        return False
    if not spec["probe"]:
        return True
    for p in spec["probe"]:
        if "/" in p:
            if os.path.exists(os.path.expanduser(p)):
                return True
        elif shutil.which(p):
            return True
    return False


def shim_text(host, inline):
    spec = REGISTRY[host]
    return SHIM_PROLOGUE % {"wrapped": spec["wrapped"]} + (SHIM_INLINE if inline else SHIM_COMPOSE)


def shim_command(host):
    """The shim path as the hosts run it, through a shell: quoted only when a
    space or the like in home would otherwise split it.
    """
    return shlex.quote(shim_path(host))


def is_ours(command, host):
    """Whether a settings command names our shim, however ~ was spelled."""
    rel = STATE_DIR + "/" + REGISTRY[host]["shim"]
    return command in (shim_path(host), shim_command(host), rel, "$HOME" + rel[1:])


def _strip_jsonc(text):
    """Comments out, strings untouched. Trailing commas go too, since files that
    allow one usually allow the other. Both are decided outside strings only,
    so a value like "a,}" keeps its comma.
    """
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        elif c == "," and text[_skip_blank(text, i + 1):_skip_blank(text, i + 1) + 1] in ("}", "]"):
            # trailing: only whitespace or comments sit between it and the closer
            i += 1
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _skip_blank(text, i):
    n = len(text)
    while i < n:
        if text[i].isspace():
            i += 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            break
    return i


def _parse(host, raw):
    # utf-8-sig: an editor that writes a byte order mark is not a broken file
    text = raw.decode("utf-8-sig")
    if REGISTRY[host]["jsonc"]:
        text = _strip_jsonc(text)
    data = json.loads(text) if text.strip() else {}
    if not isinstance(data, dict):
        raise ValueError("not an object")
    return data


def read_settings(host):
    """(data, raw bytes or None, problem or None). raw is what's on disk before
    any parsing, because that is what the backup has to be.
    """
    path = settings_path(host)
    if not os.path.exists(path):
        return {}, None, None
    try:
        with open(path, "rb") as f:
            raw = f.read()
        return _parse(host, raw), raw, None
    except (OSError, ValueError) as e:
        return {}, None, "%s isn't valid JSON (%s), so nothing was changed. fix it and re-run." % (
            REGISTRY[host]["settings"], e.__class__.__name__)


def get_command(data, host):
    """The command the host's key names right now, or ""."""
    cur = data
    for k in REGISTRY[host]["key"].split("."):
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(k)
    if isinstance(cur, str):
        return cur
    if isinstance(cur, dict) and isinstance(cur.get("command"), str):
        return cur["command"]
    return ""


def set_command(data, host, command):
    """Point the key at command, or drop the key when command is empty. Mutates
    in place so siblings like padding and refreshInterval survive.
    """
    spec = REGISTRY[host]
    parts = spec["key"].split(".")
    cur = data
    for k in parts[:-1]:
        if not isinstance(cur.get(k), dict):
            if not command:
                return
            cur[k] = {}
        cur = cur[k]
    leaf = parts[-1]
    if not command:
        cur.pop(leaf, None)
        return
    node = cur.get(leaf)
    if not isinstance(node, dict):
        node = {}
    if spec["typed"]:
        node.setdefault("type", "command")
    for k, v in spec["extras"].items():
        node.setdefault(k, v)
    node["command"] = command
    cur[leaf] = node


def _atomic_write(path, data_bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp-terminalcreature"
    with open(tmp, "wb") as f:
        f.write(data_bytes)
    try:
        # a private settings file (0600) stays private after the swap
        os.chmod(tmp, os.stat(path).st_mode & 0o777)
    except OSError:
        pass
    os.replace(tmp, path)


def write_settings(host, data, raw, backup=True):
    path = settings_path(host)
    if backup and raw is not None and not os.path.exists(path + BACKUP_SUFFIX):
        with open(path + BACKUP_SUFFIX, "wb") as f:
            f.write(raw)
    _atomic_write(path, (json.dumps(data, indent=2) + "\n").encode("utf-8"))


def _read_wrapped(host):
    try:
        with open(wrapped_path(host), "r") as f:
            return f.read()
    except OSError:
        return ""


def write_shim(host, inline):
    path = shim_path(host)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(shim_text(host, inline))
    os.chmod(path, 0o755)


def wire(host, inline=None, statusline=None):
    """Point the host at our shim, wrapping whatever it ran before. (ok, message).
    inline None takes the host's default; True or False overrides it.
    """
    spec = REGISTRY[host]
    data, raw, problem = read_settings(host)
    if problem:
        return False, problem
    existing = statusline if statusline is not None else get_command(data, host)
    already = is_ours(existing, host)
    if already:
        # re-installing over ourselves, so keep what we wrapped last time
        existing = _read_wrapped(host)
    if inline is None:
        inline = spec["inline"]
    write_shim(host, inline)
    if already and statusline is None:
        return True, "already wired, shim refreshed"
    with open(wrapped_path(host), "w") as f:
        f.write(existing)
    set_command(data, host, shim_command(host))
    write_settings(host, data, raw)
    how = "segment after it" if inline else "creature on the left"
    if existing:
        what = "wrapping your existing command, %s" % how
    else:
        what = "set in %s" % spec["settings"]
    if spec["jsonc"] and raw is not None and b"/" in raw:
        what += " (written as plain JSON, the backup keeps your comments)"
    return True, what


def _same_but_for_us(host, data, backup_raw):
    """Whether the settings file has only changed at our key since the backup."""
    try:
        before = _parse(host, backup_raw)
    except ValueError:
        return False
    a, b = json.loads(json.dumps(data)), json.loads(json.dumps(before))
    set_command(a, host, "")
    set_command(b, host, "")
    return a == b


def unwire(host):
    """Put the host back. The backup comes back byte for byte when nothing else
    changed since, so a jsonc file keeps its comments; otherwise only our key
    is undone and the rest of the file is left as it is now. (ok, message).
    """
    spec = REGISTRY[host]
    data, raw, problem = read_settings(host)
    if problem:
        return False, problem
    previous = _read_wrapped(host)
    message = "wasn't wired"
    if is_ours(get_command(data, host), host):
        backup = settings_path(host) + BACKUP_SUFFIX
        backup_raw = None
        if os.path.exists(backup):
            with open(backup, "rb") as f:
                backup_raw = f.read()
        if backup_raw is not None and _same_but_for_us(host, data, backup_raw):
            _atomic_write(settings_path(host), backup_raw)
            message = "restored %s from the backup" % spec["settings"]
        else:
            set_command(data, host, previous)
            write_settings(host, data, raw, backup=False)
            message = "restored your previous command" if previous else "removed the key we added"
    for p in (shim_path(host), wrapped_path(host)):
        try:
            os.remove(p)
        except OSError:
            pass
    return True, message


def status(host):
    """not installed | native, wired | native, not wired"""
    if not installed(host):
        return "not installed"
    data, _, problem = read_settings(host)
    wired = not problem and is_ours(get_command(data, host), host)
    return "native, wired" if wired else "native, not wired"


def doctor_lines():
    lines = ["hosts:"]
    for host in HOSTS:
        lines.append("  %-8s %-19s %s" % (host, REGISTRY[host]["label"], status(host)))
    lines += hook_doctor_lines()
    try:
        from . import plugins
        lines += plugins.doctor_lines()
    except ImportError:
        pass
    lines.append("prompt surfaces (tmux, starship, shells): see `terminalcreature snippet`")
    return lines


# ---------------------------------------------------------------------------
# hook hosts: no statusline command, but a turn-end hook whose JSON reply the
# host shows to the user. the card is one line in that reply.

HOOK_HOSTS = ("codex", "gemini", "vibe", "auggie")

# config: the file the hook entry lives in. format: json files hold a claude-shaped
# {hooks: {event: [{hooks: [{type, command}]}]}} tree; toml gets a marked block
# appended, never parsed. event: the turn-end event. field: the reply key the
# host shows. silent: what a turn with no card prints, per the host's contract.
# jsonc: comments allowed in the file. name: whether the handler carries a name.
# shell: the host hands the command to a shell, so a path with a space needs
# quoting; off, it execs the file itself and quotes would be part of the name.
# matcher: what the group carries when the host documents one, else None.
HOOK_REGISTRY = {
    # docs, 2026-09: ~/.codex/hooks.json, Stop replies JSON, systemMessage is
    # shown as a warning line, exit 0 with no output is success. hooks run only
    # once approved with /hooks inside codex. matcher isn't used for Stop
    "codex": {
        "label": "Codex CLI", "dir": "~/.codex", "config": "~/.codex/hooks.json", "format": "json",
        "jsonc": False, "name": False, "event": "Stop", "field": "systemMessage", "silent": "",
        "shim": "hookcard-codex.sh", "note": "approve it once with /hooks inside codex",
        "shell": True, "matcher": None,
    },
    # docs, 2026-09: hooks live under "hooks" in settings.json, AfterAgent fires once
    # per turn, systemMessage prints to the terminal. stdout is parsed as JSON and
    # an empty reply isn't documented, so a quiet turn prints {}. every documented
    # group carries a matcher and "*" is the documented match-all
    "gemini": {
        "label": "Gemini CLI", "dir": "~/.gemini", "config": "~/.gemini/settings.json", "format": "json",
        "jsonc": True, "name": True, "event": "AfterAgent", "field": "systemMessage", "silent": "{}",
        "shim": "hookcard-gemini.sh", "note": "",
        "shell": True, "matcher": "*",
    },
    # docs, 2026-09: [[hooks]] tables in ~/.vibe/hooks.toml, type post_agent fires
    # after every turn, system_message is UI-only, exit 0 with empty stdout passes
    "vibe": {
        "label": "Mistral Vibe", "dir": "~/.vibe", "config": "~/.vibe/hooks.toml", "format": "toml",
        "jsonc": False, "name": True, "event": "post_agent", "field": "system_message", "silent": "",
        "shim": "hookcard-vibe.sh", "note": "",
        "shell": True, "matcher": None,
    },
    # docs, 2026-09: same tree as codex under "hooks" in ~/.augment/settings.json,
    # Stop takes no matcher, systemMessage goes to the user, the script must be an
    # executable .sh with a shebang and is executed directly, not through a shell.
    # stdin carries conversation_id, not session_id
    "auggie": {
        "label": "Augment auggie", "dir": "~/.augment", "config": "~/.augment/settings.json", "format": "json",
        "jsonc": False, "name": False, "event": "Stop", "field": "systemMessage", "silent": "",
        "shim": "hookcard-auggie.sh", "note": "",
        "shell": False, "matcher": None,
    },
}

HOOK_MARK = "terminalcreature"
TOML_OPEN = "# >>> terminalcreature >>>"
TOML_CLOSE = "# <<< terminalcreature <<<"

# the statusline prologue's re-entry guard, then the card. stdin is left for the
# cli to read. no lib dir means a pip install, which put the command on PATH
HOOK_SHIM = """#!/bin/bash
# generated by the terminalcreature installer. safe to delete, reinstalling restores it.
if [ -n "${TERMINALCREATURE_WRAPPING:-}" ]; then exit 0; fi
export TERMINALCREATURE_WRAPPING=1
if [ -d "$HOME/.claude/terminalcreature/lib" ]; then
  PYTHONPATH="$HOME/.claude/terminalcreature/lib" python3 -m terminalcreature.cli hookcard --host %(host)s 2>/dev/null || true
else
  terminalcreature hookcard --host %(host)s 2>/dev/null || true
fi
"""


def hook_config_path(host):
    return os.path.expanduser(HOOK_REGISTRY[host]["config"])


def hook_shim_path(host):
    return os.path.join(os.path.expanduser(STATE_DIR), HOOK_REGISTRY[host]["shim"])


def hook_installed(host):
    return os.path.isdir(os.path.expanduser(HOOK_REGISTRY[host]["dir"]))


def hook_session_id(raw, host):
    """The session id out of a hook payload. Hosts name it differently and one
    only sets it in the environment, so this tries each. None when nothing fits.
    """
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        data = {}
    if isinstance(data, dict):
        for key in ("session_id", "conversation_id"):
            if isinstance(data.get(key), str) and data[key]:
                return data[key]
    for var in ("GEMINI_SESSION_ID", "AUGMENT_CONVERSATION_ID"):
        if os.environ.get(var):
            return os.environ[var]
    return None


def hook_envelope(host, line):
    """What hookcard prints. line None means a quiet turn. Hook hosts get the
    JSON their docs describe; anything else (the plugin hosts) gets bare text.
    """
    spec = HOOK_REGISTRY.get(host)
    if spec is None:
        return line or ""
    if line is None:
        return spec["silent"]
    return json.dumps({spec["field"]: line})


def hook_command(host):
    """The shim path as the host's config carries it: quoted for a host that
    runs it through a shell, bare for one that execs the file.
    """
    path = hook_shim_path(host)
    return shlex.quote(path) if HOOK_REGISTRY[host]["shell"] else path


def _hook_handler(host):
    handler = {"type": "command", "command": hook_command(host)}
    if HOOK_REGISTRY[host]["name"]:
        handler["name"] = HOOK_MARK
    return handler


def _is_our_handler(handler):
    # both words, so a hook of the user's own that merely mentions the
    # creature isn't taken for ours and dropped on uninstall
    command = str(handler.get("command", "")) if isinstance(handler, dict) else ""
    return HOOK_MARK in command and "hookcard" in command


def _event_groups(data, host, create=False):
    """The list under hooks.<event>, or None when the tree isn't there. With
    create, a missing level is made; one that's there in the wrong shape is
    refused (ValueError) rather than overwritten, since it's the user's.
    """
    event = HOOK_REGISTRY[host]["event"]
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        if not create:
            return None
        if hooks is not None:
            raise ValueError('a "hooks" that isn\'t an object')
        hooks = data["hooks"] = {}
    groups = hooks.get(event)
    if not isinstance(groups, list):
        if not create:
            return None
        if groups is not None:
            raise ValueError('a "hooks.%s" that isn\'t a list' % event)
        groups = hooks[event] = []
    return groups


def _has_our_hook(data, host):
    groups = _event_groups(data, host) or []
    for group in groups:
        if isinstance(group, dict) and any(_is_our_handler(h) for h in group.get("hooks") or []):
            return True
    return False


def _add_our_hook(data, host):
    if _has_our_hook(data, host):
        return False
    group = {"hooks": [_hook_handler(host)]}
    if HOOK_REGISTRY[host]["matcher"] is not None:
        group = {"matcher": HOOK_REGISTRY[host]["matcher"], "hooks": group["hooks"]}
    _event_groups(data, host, create=True).append(group)
    return True


def _drop_our_hook(data, host):
    """Take our handler out and nothing else. A group we emptied goes, an event
    list we emptied goes, and a bare hooks object we emptied goes, so a file
    that only ever held our entry is back to what it was.
    """
    groups = _event_groups(data, host)
    if groups is None:
        return False
    kept = []
    for group in groups:
        if not isinstance(group, dict):
            kept.append(group)
            continue
        handlers = group.get("hooks")
        if isinstance(handlers, list) and any(_is_our_handler(h) for h in handlers):
            handlers = [h for h in handlers if not _is_our_handler(h)]
            if not handlers:
                continue
            group = dict(group, hooks=handlers)
        kept.append(group)
    if len(kept) == len(groups) and all(a is b for a, b in zip(kept, groups)):
        return False
    event = HOOK_REGISTRY[host]["event"]
    if kept:
        data["hooks"][event] = kept
    else:
        del data["hooks"][event]
        if not data["hooks"]:
            del data["hooks"]
    return True


def _read_hook_config(host):
    """(data or text, raw bytes or None, problem or None)."""
    spec = HOOK_REGISTRY[host]
    path = hook_config_path(host)
    if not os.path.exists(path):
        return ({} if spec["format"] == "json" else ""), None, None
    try:
        with open(path, "rb") as f:
            raw = f.read()
        if spec["format"] == "toml":
            return raw.decode("utf-8-sig"), raw, None
        text = raw.decode("utf-8-sig")
        if spec["jsonc"]:
            text = _strip_jsonc(text)
        data = json.loads(text) if text.strip() else {}
        if not isinstance(data, dict):
            raise ValueError("not an object")
        return data, raw, None
    except (OSError, ValueError) as e:
        return None, None, "%s couldn't be read (%s), so nothing was changed. fix it and re-run." % (
            spec["config"], e.__class__.__name__)


def _toml_block(host):
    # json.dumps makes a valid toml basic string out of any path
    return "\n".join([
        TOML_OPEN,
        "[[hooks]]",
        'name = "%s"' % HOOK_MARK,
        'type = "%s"' % HOOK_REGISTRY[host]["event"],
        "command = %s" % json.dumps(hook_command(host)),
        "timeout = 10.0",
        'description = "creature card after each turn"',
        TOML_CLOSE,
    ]) + "\n"


def _strip_toml_block(text):
    start = text.find(TOML_OPEN)
    if start < 0:
        return text, False
    end = text.find(TOML_CLOSE, start)
    if end < 0:
        return text, False
    end += len(TOML_CLOSE)
    if text[end:end + 1] == "\n":
        end += 1
    return text[:start] + text[end:], True


def _write_hook_config(host, content, raw, backup=True):
    path = hook_config_path(host)
    if backup and raw is not None and not os.path.exists(path + BACKUP_SUFFIX):
        with open(path + BACKUP_SUFFIX, "wb") as f:
            f.write(raw)
    if isinstance(content, str):
        _atomic_write(path, content.encode("utf-8"))
    else:
        _atomic_write(path, (json.dumps(content, indent=2) + "\n").encode("utf-8"))


def _write_hook_shim(host):
    path = hook_shim_path(host)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(HOOK_SHIM % {"host": host})
    os.chmod(path, 0o755)


def wire_hook(host):
    """Add our turn-end hook to the host's config, next to whatever hooks are
    already there. (ok, message).
    """
    spec = HOOK_REGISTRY[host]
    content, raw, problem = _read_hook_config(host)
    if problem:
        return False, problem
    if spec["format"] == "toml":
        if TOML_OPEN in content:
            if not _strip_toml_block(content)[1]:
                return False, "%s has our begin marker with no end marker, so nothing was changed. fix it and re-run." % (
                    spec["config"])
            _write_hook_shim(host)
            return True, "already wired, shim refreshed"
        _write_hook_shim(host)
        joint = "" if not content or content.endswith("\n") else "\n"
        _write_hook_config(host, content + joint + _toml_block(host), raw)
    else:
        try:
            added = _add_our_hook(content, host)
        except ValueError as e:
            return False, "%s has %s, so nothing was changed. fix it and re-run." % (spec["config"], e)
        _write_hook_shim(host)
        if not added:
            return True, "already wired, shim refreshed"
        _write_hook_config(host, content, raw)
    what = "%s hook set in %s" % (spec["event"], spec["config"])
    if spec["note"]:
        what += " (%s)" % spec["note"]
    if spec["jsonc"] and raw is not None and b"/" in raw:
        what += " (written as plain JSON, the backup keeps your comments)"
    return True, what


def _hook_same_but_for_us(host, content, backup_raw):
    """Whether the config has only changed by our entry since the backup."""
    if isinstance(content, str):
        return _strip_toml_block(content)[0] == _strip_toml_block(backup_raw.decode("utf-8-sig"))[0]
    try:
        before = json.loads(_strip_jsonc(backup_raw.decode("utf-8-sig")))
    except ValueError:
        return False
    if not isinstance(before, dict):
        return False
    a, b = json.loads(json.dumps(content)), json.loads(json.dumps(before))
    _drop_our_hook(a, host)
    _drop_our_hook(b, host)
    return a == b


def unwire_hook(host):
    """Take our entry out. The backup comes back byte for byte when nothing else
    changed since; otherwise only our entry goes. A file we created and emptied
    is removed. (ok, message).
    """
    spec = HOOK_REGISTRY[host]
    content, raw, problem = _read_hook_config(host)
    if problem:
        return False, problem
    path = hook_config_path(host)
    message = "wasn't wired"
    if spec["format"] == "toml":
        content, had = _strip_toml_block(content)
    else:
        had = _drop_our_hook(content, host)
    if had:
        backup = path + BACKUP_SUFFIX
        backup_raw = None
        if os.path.exists(backup):
            with open(backup, "rb") as f:
                backup_raw = f.read()
        if backup_raw is not None and _hook_same_but_for_us(host, content, backup_raw):
            _atomic_write(path, backup_raw)
            message = "restored %s from the backup" % spec["config"]
        elif backup_raw is None and not (content.strip() if isinstance(content, str) else content):
            os.remove(path)
            message = "removed %s, which held only our hook" % spec["config"]
        else:
            _write_hook_config(host, content, raw, backup=False)
            message = "removed our hook from %s" % spec["config"]
    try:
        os.remove(hook_shim_path(host))
    except OSError:
        pass
    return True, message


def hook_wired(host):
    content, _, problem = _read_hook_config(host)
    if problem:
        return False
    if HOOK_REGISTRY[host]["format"] == "toml":
        return _strip_toml_block(content)[1]
    return _has_our_hook(content, host)


def hook_status(host):
    """not installed | card, wired | card, not wired"""
    if not hook_installed(host):
        return "not installed"
    return "card, wired" if hook_wired(host) else "card, not wired"


def hook_doctor_lines():
    return ["  %-8s %-19s %s" % (host, HOOK_REGISTRY[host]["label"], hook_status(host)) for host in HOOK_HOSTS]
