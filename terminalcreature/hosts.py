"""What each host pipes to a statusline command, and how to read it.

Every host that renders a statusline copies Claude Code's contract: session
JSON on stdin, stdout drawn in the chrome. The field names drift a little
per host, so this is one map from each host's shape to the four things the
creature cares about. Nothing here raises: a payload we don't recognise
renders without a session, it never breaks the prompt.
"""

import json

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
    "cursor": {
        "session_id": ("session_id", "conversation_id"),
        "model": ("model.display_name", "model"),
        "workspace": ("workspace.current_dir", "cwd", "workspace_roots"),
        "context_used_pct": ("context_window.used_percentage", "context_usage.used_percentage",
                             "context_usage.percentage"),
    },
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
# claude's keys and adds its own is named before the claude fallback catches it
MARKERS = (
    ("cursor", ("cursor_version", "_agent_type", "workspace_roots", "conversation_id")),
    ("copilot", ("copilot_version", "session_name", "username", "remote")),
    ("qwen", ("metrics",)),
    ("droid", ("sessionId", "workingDirectory", "modelId")),
    ("claude", ("transcript_path", "hook_event_name", "cost", "exceeds_200k_tokens", "output_style")),
)
# claude's keys with nothing else to go on. cursor and copilot both send these
CLAUDE_SHAPE = ("session_id", "model", "workspace", "context_window")

EMPTY = {"host": "unknown", "session_id": None, "model": None, "workspace": None, "context_used_pct": None}


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
    know all come back as host "unknown" with every field None.
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
