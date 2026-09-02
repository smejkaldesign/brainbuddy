"""Memory sizing. Counts files, never opens them.

R2: the only filesystem calls in here are glob and stat. No open(), no read().
If you're adding something that needs file contents, it doesn't belong in this
module and probably doesn't belong in brainbuddy at all.
"""

import glob
import math
import os

XP_MAX_DEFAULT = 5000
STAGE_SPAN = 20

STAGES = [
    (0, 0, "Egg"),
    (1, 19, "Hatchling"),
    (20, 39, "Fledgling"),
    (40, 59, "Adept"),
    (60, 79, "Sage"),
    (80, None, "Ascendant"),
]

# Vault layout. Durable facts outweigh session logs because they cost more to
# produce. Index files are generated, so they'd inflate the count for free.
VAULT_SOURCES = [
    {"key": "memories", "glob": "auto-memory/*.md", "weight": 3, "exclude": ["MEMORY.md", "index.md"]},
    {"key": "knowledge", "glob": "05-knowledge/*.md", "weight": 2, "exclude": ["index.md"]},
    {"key": "projects", "glob": "04-projects/*.md", "weight": 2, "exclude": ["index.md"]},
    {"key": "sessions", "glob": "memory/sessions/*.md", "weight": 1, "exclude": []},
    {"key": "decisions", "glob": "memory/decisions/*.md", "weight": 2, "exclude": []},
]

# Stock Claude Code layout, for anyone without a vault.
CLAUDE_SOURCES = [
    {"key": "memories", "glob": "*/memory/*.md", "weight": 3, "exclude": ["MEMORY.md", "index.md"]},
]


def default_claude_root():
    return os.path.expanduser("~/.claude/projects")


def count_source(root, source):
    """Count matching files. Resolves realpaths so a symlinked memory dir
    (eric-brain points ~/.claude/... back into the repo) can't be counted twice
    when two globs reach the same file by different routes.
    """
    exclude = set(source.get("exclude", []))
    seen = set()
    pattern = os.path.join(root, source["glob"])
    for path in glob.iglob(pattern):
        if os.path.basename(path) in exclude:
            continue
        try:
            key = os.path.realpath(path)
            st = os.stat(key)
        except OSError:
            continue
        if not os.path.isfile(key):
            continue
        seen.add((key, st.st_ino))
    return len(seen)


def measure(root, sources, weights=None):
    """Return (xp, {key: count}). weights overrides the source defaults."""
    weights = weights or {}
    counts = {}
    xp = 0
    for source in sources:
        n = count_source(root, source)
        counts[source["key"]] = n
        xp += n * weights.get(source["key"], source["weight"])
    return xp, counts


def level_for(xp, xp_max=XP_MAX_DEFAULT):
    """Square root curve: early memories move the needle, later ones don't.

    Uncapped on purpose. Level keeps climbing past 100; it's evolution that
    stops at Ascendant.
    """
    if xp <= 0:
        return 0
    if xp_max <= 0:
        return 0
    return int(math.floor(100 * math.sqrt(xp / float(xp_max))))


def xp_for_level(level, xp_max=XP_MAX_DEFAULT):
    """Inverse of level_for, for 'XP to next level' readouts."""
    if level <= 0:
        return 0
    return int(math.ceil(xp_max * (level / 100.0) ** 2))


def stage_for(level):
    """Return (stage_index, stage_name)."""
    for i, (lo, hi, name) in enumerate(STAGES):
        if level >= lo and (hi is None or level <= hi):
            return i, name
    return 0, STAGES[0][2]


def next_stage_level(level):
    """First level of the next evolution, or None at Ascendant."""
    idx, _ = stage_for(level)
    if idx >= len(STAGES) - 1:
        return None
    return STAGES[idx + 1][0]


def progress(xp, xp_max=XP_MAX_DEFAULT):
    """Everything the renderer and card need, in one pass."""
    level = level_for(xp, xp_max)
    idx, name = stage_for(level)
    nxt = next_stage_level(level)
    return {
        "xp": xp,
        "level": level,
        "stage_index": idx,
        "stage": name,
        "next_level_xp": xp_for_level(level + 1, xp_max),
        "next_stage_level": nxt,
        "next_stage_xp": xp_for_level(nxt, xp_max) if nxt else None,
    }
