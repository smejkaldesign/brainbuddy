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
LATEST_PATH = os.path.join(STATE_DIR, "latest-version")
UPDATE_TTL = 24 * 3600

# bumped when the file's shape changes. `migrate` is what actually reads it, and
# an upgrade that de-levels someone's buddy is the one failure with no undo
STATE_VERSION = 2

DEFAULT_SETTINGS = {
    "provider": "claude",       # "claude" | "vault"
    "vault_root": "",
    "weights": {},
    "xp_max": metric.XP_MAX_DEFAULT,
    "density": "compact",       # "compact" | "minimal" | "full" | "sprite"
    "columns": 0,               # right-align sprite mode to this width, 0 = flush left
    "sprite_height": 5,         # 5 rows, or 3 to keep the footer closer
    "unicode": True,
    "hidden": False,          # keep the creature out of the statusline without uninstalling
    "border": True,           # box the compose column. costs two rows of height
    "update_check": False,    # opt-in: refresh may ask pypi for the latest version once a day
    "update_check_asked": False,  # the one-time offer was shown; never show it again
}


# enough for the handful of sessions anyone has open at once. the oldest baseline
# drops out rather than the file growing for the life of the install
SESSION_KEEP = 8


def default_state():
    return {"version": STATE_VERSION, "high_water_xp": 0, "focused": None, "creatures": [],
            "sessions": {}, "settings": dict(DEFAULT_SETTINGS)}


def session_gain(state, session_id, banked):
    """XP the focused creature has put on since this session first drew itself.

    Returns (gain, is_new). Baselining on first sight is what makes it a session
    counter: without it every session would open claiming credit for the whole
    vault. Concurrent sessions each get their own mark, because there are
    usually several open and one shared mark would have them overwriting
    each other's starting point.
    """
    if not session_id:
        return 0, False
    sessions = state.setdefault("sessions", {})
    row = sessions.get(session_id)
    # a total below the mark means focus moved to a different creature, so
    # re-baseline instead of rendering a negative
    if row is None or row.get("at", 0) > banked:
        sessions[session_id] = {"at": banked, "ts": int(time.time())}
        if len(sessions) > SESSION_KEEP:
            stale = sorted(sessions, key=lambda k: sessions[k].get("ts", 0))[:len(sessions) - SESSION_KEEP]
            for key in stale:
                del sessions[key]
        return 0, True
    return banked - row["at"], False


def migrate(data):
    """Bring a state file of any older shape forward. Additive, never lossy.

    Upgrades are the one moment a buddy can silently disappear, so this only
    ever fills in what's missing. Nothing is dropped, including keys written by
    a version we don't know about. Species, rarity and shiny aren't stored at
    all, they come back off the seed, so there's nothing derived to rebuild.
    """
    state = default_state()
    state.update(data)
    settings = dict(DEFAULT_SETTINGS)
    settings.update(data.get("settings") or {})
    state["settings"] = settings

    creatures = [c for c in (state.get("creatures") or []) if isinstance(c, dict)]
    for i, c in enumerate(creatures):
        # every read path indexes these directly, so one written before the key
        # existed, or edited by hand, crashes the statusline instead of degrading.
        # setdefault isn't enough: a hand-edited "name": null has the key and
        # still crashes every command that lowercases it
        if c.get("seed") is None:
            c["seed"] = c.get("id") or "creature-%d" % i
        if c.get("id") is None:
            c["id"] = c["seed"]
        if c.get("name") is None:
            c["name"] = creature_mod.suggest_name(c["seed"])
        c.setdefault("hatched_at", None)
        if c.get("xp_banked") is None:
            c["xp_banked"] = 0
        if c.get("last_stage_seen") is None:
            c["last_stage_seen"] = 0
    state["creatures"] = creatures

    if state.get("focused") not in {c["id"] for c in creatures}:
        # a focus pointing at nothing renders as "no buddy", which reads as a
        # wiped roster even though every creature is still sitting in the file
        alive = [c for c in creatures if not c.get("retired_at")]
        state["focused"] = alive[0]["id"] if alive else None

    seen = state.get("version")
    # a newer brainbuddy's stamp survives a downgrade rather than being relabelled
    state["version"] = seen if isinstance(seen, int) and seen > STATE_VERSION else STATE_VERSION
    return state


def load(path=STATE_PATH):
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return default_state()
    if not isinstance(data, dict):
        return default_state()
    return migrate(data)


def save(state, path=STATE_PATH, own_settings=False):
    """Persist state. Only `config` owns settings.

    Background refreshes hold a whole-state copy for as long as the vault scan
    takes, so writing it back wholesale reverts any setting changed meanwhile.
    That silently undid config edits. Everyone except config re-reads settings
    off disk at write time.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not isinstance(state.get("version"), int):
        state = dict(state, version=STATE_VERSION)
    if not own_settings:
        try:
            with open(path, "r") as f:
                on_disk = json.load(f).get("settings")
            if on_disk:
                state = dict(state)
                state["settings"] = on_disk
        except (OSError, ValueError):
            pass
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def sources_for(settings):
    provider = settings.get("provider")
    root = os.path.expanduser(settings.get("vault_root") or "")
    if provider == "vault" and root:
        return root, metric.VAULT_SOURCES
    if provider == "folder" and root:
        return root, metric.FOLDER_SOURCES
    return metric.default_claude_root(), metric.CLAUDE_SOURCES


def source_status(settings):
    """Whether there's a memory system to count at all. Counts, never a path.

    Three zeroes look identical in the statusline and mean different things: a
    root that isn't there, a real root that's empty, and a root full of files
    the provider's layout doesn't match. Only the middle one means "keep
    writing", so they can't share one message.
    """
    root, sources = sources_for(settings)
    if not os.path.isdir(root):
        return {"state": "missing_root", "xp": 0, "counts": {}}
    xp, counts = metric.measure(root, sources, settings.get("weights"))
    if xp:
        return {"state": "ok", "xp": xp, "counts": counts}
    # only vault keys off directory names, so it's the only one that can score
    # zero on a root that's full of notes. that's a mismatch, not an empty vault.
    if sources is metric.VAULT_SOURCES:
        _, stray = metric.measure(root, metric.FOLDER_SOURCES)
        found = sum(stray.values())
        if found:
            return {"state": "layout_mismatch", "xp": 0, "counts": counts, "stray": found}
    return {"state": "empty", "xp": 0, "counts": counts}


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


def set_setting(key, value, path=STATE_PATH):
    """Set one setting against the file as it is NOW, not as it was loaded.

    Callers holding a state snapshot across anything slow (a card's cold-start
    scan, say) must not write their stale settings back wholesale; that is the
    same revert `save`'s own_settings rule exists to stop.
    """
    st = load(path)
    st["settings"][key] = value
    save(st, path=path, own_settings=True)


def read_latest(path=None):
    """Returns (version_or_empty, age_seconds) or None. Never raises.

    An empty version is a stamped failed attempt: the TTL still counts from
    it, so an offline machine retries tomorrow rather than on every refresh.
    path resolves at call time so tests can point LATEST_PATH elsewhere.
    """
    path = path or LATEST_PATH
    try:
        st = os.stat(path)
        with open(path, "r") as f:
            data = json.load(f)
        return str(data.get("version") or ""), time.time() - st.st_mtime
    except (OSError, ValueError):
        return None


def write_latest(version, path=None):
    path = path or LATEST_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w") as f:
        json.dump({"version": version or ""}, f)
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
    # an egg still banks xp, it just doesn't announce evolutions nobody can see.
    # the hatch ceremony is the reveal, so don't burn the beat before it
    if not is_hatched(c):
        return None
    if idx > c.get("last_stage_seen", 0):
        c["last_stage_seen"] = idx
        return {"creature": c["name"], "stage_index": idx, "stage": name, "level": level}
    return None


def create(state, name=None, focus=True):
    """Add a creature as an unhatched egg. New creatures start at zero banked XP.

    hatched_at stays None until `reveal`, which is what makes the egg a state
    rather than a level band.
    """
    c = creature_mod.new_creature(name=name)
    state.setdefault("creatures", []).append(c)
    if focus or state.get("focused") is None:
        state["focused"] = c["id"]
    return c


def is_hatched(c):
    return bool(c and c.get("hatched_at"))


def reveal(state):
    """Hatch the focused egg. Returns the creature, or None if there's nothing to open."""
    c = focused(state)
    if c is None or is_hatched(c):
        return None
    c["hatched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # the reveal shows whatever stage the egg banked its way to, so record it
    # here or the next sync fires an evolution notice for a stage just displayed
    level = metric.level_for(c.get("xp_banked", 0), state["settings"]["xp_max"])
    c["last_stage_seen"] = metric.stage_for(level)[0]
    return c


def active(state):
    return [c for c in state.get("creatures", []) if not c.get("retired_at")]


def retire(state, ident):
    """Retire by id or name. Keeps the record and its banked XP; focus can undo it."""
    c = find(state, ident)
    if c is None:
        return None
    c["retired_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if state.get("focused") == c["id"]:
        rest = active(state)
        state["focused"] = rest[0]["id"] if rest else None
    return c


def find(state, ident):
    for c in state.get("creatures", []):
        if c["id"] == ident or c["name"].lower() == str(ident).lower():
            return c
    return None


def focus(state, ident):
    """Focus by id or name (case-insensitive). Un-retires. Returns the creature or None."""
    c = find(state, ident)
    if c is None:
        return None
    c.pop("retired_at", None)
    state["focused"] = c["id"]
    return c
