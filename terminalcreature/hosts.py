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
    lines.append("prompt surfaces (tmux, starship, shells): see `terminalcreature snippet`")
    return lines
