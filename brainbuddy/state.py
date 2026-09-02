"""State: roster, per-creature XP banking, settings, and the XP cache.

The banking rule is the whole design. XP is measured globally off the memory
system, but it's credited to ONE creature: the focused one. Without that, a
second egg hatched at level 100 would spawn at level 100, because the memory
that earned the first hundred levels is still sitting there.
"""

import json
import os
import time

from . import creature as creature_mod
from . import metric

STATE_DIR = os.path.expanduser("~/.claude/brainbuddy")
STATE_PATH = os.path.join(STATE_DIR, "state.json")
CACHE_PATH = os.path.join(STATE_DIR, "xp.cache")
CACHE_TTL = 60

DEFAULT_SETTINGS = {
    "provider": "claude",       # "claude" | "vault"
    "vault_root": "",
    "weights": {},
    "xp_max": metric.XP_MAX_DEFAULT,
    "density": "compact",       # "compact" | "minimal" | "full" | "sprite"
    "columns": 0,               # right-align sprite mode to this width, 0 = flush left
    "sprite_height": 5,         # 5 rows, or 3 to keep the footer closer
    "unicode": True,
}


def default_state():
    return {"version": 1, "high_water_xp": 0, "focused": None, "creatures": [], "settings": dict(DEFAULT_SETTINGS)}


def load(path=STATE_PATH):
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return default_state()
    base = default_state()
    base.update(data)
    settings = dict(DEFAULT_SETTINGS)
    settings.update(data.get("settings") or {})
    base["settings"] = settings
    return base


def save(state, path=STATE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def sources_for(settings):
    if settings.get("provider") == "vault" and settings.get("vault_root"):
        return os.path.expanduser(settings["vault_root"]), metric.VAULT_SOURCES
    return metric.default_claude_root(), metric.CLAUDE_SOURCES


def measure_now(settings):
    root, sources = sources_for(settings)
    return metric.measure(root, sources, settings.get("weights"))


def read_cache(path=CACHE_PATH):
    """Returns (xp, counts, age_seconds) or None. Never raises."""
    try:
        st = os.stat(path)
        with open(path, "r") as f:
            data = json.load(f)
        return data["xp"], data.get("counts", {}), time.time() - st.st_mtime
    except (OSError, ValueError, KeyError):
        return None


def write_cache(xp, counts, path=CACHE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w") as f:
        json.dump({"xp": xp, "counts": counts}, f)
    os.replace(tmp, path)


def focused(state):
    fid = state.get("focused")
    for c in state.get("creatures", []):
        if c["id"] == fid:
            return c
    return None


def sync(state, current_xp):
    """Credit new XP to the focused creature. Returns an evolution event or None.

    High water only ever rises, so deleting memories can't de-level anyone.
    Good hygiene shouldn't be punished.
    """
    c = focused(state)
    if c is None:
        # nobody to credit, so leave the mark alone. move it here and a render
        # before the first hatch burns the xp, hatching you at level 0.
        return None

    high = state.get("high_water_xp", 0)
    delta = current_xp - high
    if delta > 0:
        state["high_water_xp"] = current_xp
        c["xp_banked"] = c.get("xp_banked", 0) + delta

    level = metric.level_for(c["xp_banked"], state["settings"]["xp_max"])
    idx, name = metric.stage_for(level)
    if idx > c.get("last_stage_seen", 0):
        c["last_stage_seen"] = idx
        return {"creature": c["name"], "stage_index": idx, "stage": name, "level": level}
    return None


def hatch(state, name=None, focus=True):
    """New creatures always start at zero banked XP."""
    c = creature_mod.new_creature(name=name, hatched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    state.setdefault("creatures", []).append(c)
    if focus or state.get("focused") is None:
        state["focused"] = c["id"]
    return c


def focus(state, ident):
    """Focus by id or name (case-insensitive). Returns the creature or None."""
    for c in state.get("creatures", []):
        if c["id"] == ident or c["name"].lower() == str(ident).lower():
            state["focused"] = c["id"]
            return c
    return None
