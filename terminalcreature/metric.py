"""Memory sizing. Counts files, never opens them.

R2: the only filesystem calls in here are glob and stat. No open(), no read().
If you're adding something that needs file contents, it doesn't belong in this
module and probably doesn't belong in terminalcreature at all.
"""

import glob
import math
import os

# calibrated so an established vault (~650 xp of durable notes) sits around 65,
# leaving real headroom without the early levels crawling. 5000 was slow enough
# that a new user saw almost nothing move, which is how a pet like this dies
XP_MAX_DEFAULT = 1500
LEVEL_MAX = 100
STAGE_SPAN = 20

# sprite 0 is the egg, which is now the unhatched state rather than a level
# band. so level stages start at sprite 1 and a level-0 buddy is a baby, not an egg
EGG_SPRITE = 0

LEVEL_STAGES = [
    (0, 19, "Hatchling"),
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

# the vault layout keys off directory names, so it counts zero on anyone else's notes
FOLDER_SOURCES = [
    {"key": "notes", "glob": "**/*.md", "weight": 2, "exclude": ["MEMORY.md", "index.md", "README.md"]},
]

# Every coding agent's memory on disk, one entry each. Roots stay ~-relative
# here and expand at measure time, so the table itself never holds a home path.
# Weights: durable memory and instruction files 3, rules 2, session logs 1.
# Session stores are counted as files (a .db is one file), never opened.
# An agent is "found" when any of its root directories exists.
AGENT_ROOTS = [
    {"key": "claude", "label": "Claude Code", "roots": [
        ("~/.claude/projects", [
            {"key": "memories", "glob": "*/memory/*.md", "weight": 3, "exclude": ["MEMORY.md", "index.md"]},
        ]),
    ]},
    {"key": "codex", "label": "Codex", "roots": [
        ("~/.codex", [
            {"key": "memories", "glob": "memories/**/*", "weight": 3, "exclude": []},
            {"key": "instructions", "glob": "AGENTS.md", "weight": 3, "exclude": []},
            {"key": "sessions", "glob": "sessions/**/*.jsonl", "weight": 1, "exclude": []},
        ]),
    ]},
    {"key": "gemini", "label": "Gemini CLI", "roots": [
        ("~/.gemini", [
            {"key": "instructions", "glob": "GEMINI.md", "weight": 3, "exclude": []},
            {"key": "sessions", "glob": "tmp/*/chats/**/*", "weight": 1, "exclude": []},
        ]),
    ]},
    {"key": "copilot", "label": "Copilot CLI", "roots": [
        ("~/.copilot", [
            {"key": "instructions", "glob": "copilot-instructions.md", "weight": 3, "exclude": []},
            {"key": "instructions", "glob": "instructions/*.md", "weight": 3, "exclude": []},
            {"key": "sessions", "glob": "session-state/*/events.jsonl", "weight": 1, "exclude": []},
        ]),
    ]},
    {"key": "cursor", "label": "Cursor", "roots": [
        ("~/.cursor", [
            {"key": "rules", "glob": "**/rules/*.mdc", "weight": 2, "exclude": []},
            {"key": "sessions", "glob": "chats/**/*", "weight": 1, "exclude": []},
        ]),
    ]},
    {"key": "qwen", "label": "Qwen Code", "roots": [
        ("~/.qwen", [
            {"key": "instructions", "glob": "QWEN.md", "weight": 3, "exclude": []},
            {"key": "sessions", "glob": "tmp/*/**/*", "weight": 1, "exclude": []},
        ]),
    ]},
    {"key": "droid", "label": "Droid", "roots": [
        ("~/.factory", [
            {"key": "sessions", "glob": "sessions/*.json", "weight": 1, "exclude": []},
            {"key": "specs", "glob": "specs/**/*.md", "weight": 2, "exclude": []},
        ]),
    ]},
    {"key": "opencode", "label": "opencode", "roots": [
        ("~/.local/share/opencode", [
            {"key": "sessions", "glob": "opencode.db", "weight": 1, "exclude": []},
        ]),
        ("~/.config/opencode", [
            {"key": "instructions", "glob": "AGENTS.md", "weight": 3, "exclude": []},
        ]),
    ]},
    {"key": "amp", "label": "Amp", "roots": [
        ("~/.local/share/amp", [
            {"key": "sessions", "glob": "threads/*.json", "weight": 1, "exclude": []},
        ]),
    ]},
    {"key": "goose", "label": "Goose", "roots": [
        ("~/.local/share/goose", [
            {"key": "sessions", "glob": "sessions/sessions.db", "weight": 1, "exclude": []},
        ]),
        ("~/.config/goose", [
            {"key": "instructions", "glob": ".goosehints", "weight": 3, "exclude": []},
        ]),
    ]},
    {"key": "continue", "label": "Continue", "roots": [
        ("~/.continue", [
            {"key": "sessions", "glob": "sessions/*.json", "weight": 1, "exclude": []},
        ]),
    ]},
    {"key": "kiro", "label": "Kiro", "roots": [
        ("~/.kiro", [
            {"key": "rules", "glob": "steering/*.md", "weight": 2, "exclude": []},
        ]),
    ]},
    {"key": "cline", "label": "Cline", "roots": [
        ("~/.cline", [
            {"key": "sessions", "glob": "data/sessions/**/*", "weight": 1, "exclude": []},
            {"key": "rules", "glob": "rules/*.md", "weight": 2, "exclude": []},
        ]),
    ]},
    {"key": "crush", "label": "Crush", "roots": [
        ("~/.config/crush", [
            {"key": "instructions", "glob": "CRUSH.md", "weight": 3, "exclude": []},
        ]),
    ]},
]

# auto picks agents when two or more agent roots exist, else claude, so a
# stock install measures exactly what it did before the table existed
PROVIDERS = ("claude", "vault", "folder", "agents", "auto")
AUTO_MIN_AGENTS = 2


def default_claude_root():
    return os.path.expanduser("~/.claude/projects")


def agent_keys():
    return [a["key"] for a in AGENT_ROOTS]


def found_agents():
    """Keys of the agents whose root directory exists. isdir only, no scan."""
    found = []
    for agent in AGENT_ROOTS:
        if any(os.path.isdir(os.path.expanduser(root)) for root, _ in agent["roots"]):
            found.append(agent["key"])
    return found


def measure_agents(weights=None):
    """Return (xp, {agent: {key: count}}, [found agent keys]).

    Only found agents get a counts row, so a missing one reads as absent
    rather than as an agent with nothing written. Weights override by source
    key across every agent, the same knob the other providers take.
    """
    weights = weights or {}
    counts = {}
    found = []
    xp = 0
    for agent in AGENT_ROOTS:
        present = False
        # every key seeded, so a root that isn't there reads as zero rather
        # than as a key that went missing
        row = dict((s["key"], 0) for _, sources in agent["roots"] for s in sources)
        for root, sources in agent["roots"]:
            root = os.path.expanduser(root)
            if not os.path.isdir(root):
                continue
            present = True
            for source in sources:
                n = count_source(root, source)
                # a key can appear twice under one agent, so add rather than set
                row[source["key"]] += n
                xp += n * weights.get(source["key"], source["weight"])
        if present:
            counts[agent["key"]] = row
            found.append(agent["key"])
    return xp, counts, found


def flatten_agent_counts(counts):
    """Per-agent counts folded by source key, the shape the cache and card take."""
    flat = {}
    for row in counts.values():
        for key, n in row.items():
            flat[key] = flat.get(key, 0) + n
    return flat


def count_source(root, source):
    """Count matching files. Resolves realpaths so a symlinked memory dir can't
    be counted twice when two globs reach the same file by different routes.
    """
    exclude = set(source.get("exclude", []))
    seen = set()
    pattern = os.path.join(root, source["glob"])
    # glob skips dotted dirs itself, so ** doesn't wander into .git
    for path in glob.iglob(pattern, recursive=True):
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

    Capped at LEVEL_MAX. 100 is fully grown, and the answer to "what now" is a
    new egg rather than a number that climbs forever with nothing attached.
    """
    if xp <= 0:
        return 0
    if xp_max <= 0:
        return 0
    return min(LEVEL_MAX, int(math.floor(100 * math.sqrt(xp / float(xp_max)))))


def xp_for_level(level, xp_max=XP_MAX_DEFAULT):
    """Inverse of level_for, for 'XP to next level' readouts."""
    if level <= 0:
        return 0
    return int(math.ceil(xp_max * (level / 100.0) ** 2))


def stage_for(level):
    """Return (sprite_index, stage_name) for a hatched creature.

    Offset by one because sprite 0 is the egg. Keeping the sprite numbering
    stable is what lets last_stage_seen survive this change unmigrated.
    """
    for i, (lo, hi, name) in enumerate(LEVEL_STAGES):
        if level >= lo and (hi is None or level <= hi):
            return i + 1, name
    return 1, LEVEL_STAGES[0][2]


def next_stage_level(level):
    """First level of the next evolution, or None at Ascendant."""
    band = stage_for(level)[0] - 1
    if band >= len(LEVEL_STAGES) - 1:
        return None
    return LEVEL_STAGES[band + 1][0]


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
