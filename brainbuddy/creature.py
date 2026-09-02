"""Creature generation.

Split follows the same idea as any anti-tamper cosmetic system: fields that
could be cheated are DERIVED from the seed on every load and overwrite whatever
is on disk. Only the things a user is allowed to own get persisted.

  derived  -> species, rarity, shiny, accent   (recomputed, never trusted)
  persisted-> id, seed, name, hatched_at, xp_banked

Stats are neither. They're read off the live memory counts, so they can't be
rolled or faked either, and they move as the vault moves.
"""

SALT = "brainbuddy/v1"

_MASK = (1 << 64) - 1
_PI64 = 0x243F6A8885A308D3  # nothing-up-my-sleeve seed constant


def _mix(x):
    """splitmix64. Deterministic and well distributed, which is all we need.

    Deliberately not hashlib: importing it cost 2.5ms on the statusline hot
    path, and nothing here is a security boundary. Rolling a cosmetic rarity
    doesn't need a cryptographic hash.
    """
    x = (x + 0x9E3779B97F4A7C15) & _MASK
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & _MASK
    return (x ^ (x >> 31)) & _MASK


def _hash(text):
    h = _PI64
    for b in text.encode("utf-8"):
        h = _mix(h ^ b)
    return h

SPECIES = ["Mote", "Wisp", "Ember", "Pip", "Fen", "Bramble", "Nim", "Quill"]

# (name, weight, mark). Mark carries rarity without relying on colour, so the
# tier still reads on a mono terminal or to a colour-blind user.
RARITIES = [
    ("Common", 60, ""),
    ("Uncommon", 25, "+"),
    ("Rare", 10, "*"),
    ("Epic", 4, "**"),
    ("Legendary", 1, "***"),
]

SHINY_CHANCE = 0.01

_ONSETS = ["ba", "ke", "mo", "ru", "ti", "vo", "za", "lu", "ne", "sy", "dra", "fi"]
_CODAS = ["nk", "lo", "ra", "mi", "th", "sk", "el", "ux", "in", "or"]


def _stream(seed, tag):
    """Deterministic float in [0,1) for a given seed and purpose.

    Separate tags keep the rolls independent, so shiny doesn't correlate with
    rarity just because they came off the same hash.
    """
    return _hash("%s:%s:%s" % (SALT, seed, tag)) / float(1 << 64)


def roll_rarity(seed):
    r = _stream(seed, "rarity") * sum(w for _, w, _ in RARITIES)
    acc = 0.0
    for name, weight, mark in RARITIES:
        acc += weight
        if r < acc:
            return name, mark
    return RARITIES[0][0], RARITIES[0][2]


def derive(seed):
    """The bones. Pure function of the seed, so editing state.json can't
    promote a Common into a shiny Legendary.
    """
    species = SPECIES[int(_stream(seed, "species") * len(SPECIES)) % len(SPECIES)]
    rarity, mark = roll_rarity(seed)
    return {
        "species": species,
        "rarity": rarity,
        "rarity_mark": mark,
        "shiny": _stream(seed, "shiny") < SHINY_CHANCE,
    }


def suggest_name(seed):
    """Fallback name for CLI hatching. The /brainbuddy command names it with
    Claude instead, which is better, but the CLI can't reach a model.
    """
    o = _ONSETS[int(_stream(seed, "n1") * len(_ONSETS)) % len(_ONSETS)]
    c = _CODAS[int(_stream(seed, "n2") * len(_CODAS)) % len(_CODAS)]
    return (o + c).capitalize()


def new_creature(name=None, seed=None, hatched_at=None):
    import uuid  # only needed when hatching, not on the statusline hot path

    seed = seed or uuid.uuid4().hex
    return {
        "id": uuid.uuid4().hex,
        "seed": seed,
        "name": name or suggest_name(seed),
        "hatched_at": hatched_at,
        "xp_banked": 0,
        "last_stage_seen": 0,
    }


def hydrate(creature):
    """Persisted fields plus freshly derived bones. Derived wins."""
    out = dict(creature)
    out.update(derive(creature["seed"]))
    return out


def stats_from_counts(counts):
    """Five stats, all computable from file counts alone (R2).

    Ferment is sessions against durable memories: high means you're generating
    faster than you're distilling. It replaced a planned "Chaos" stat that
    needed to parse unchecked boxes out of tasks.md, which R2 rules out.
    """
    memories = counts.get("memories", 0)
    knowledge = counts.get("knowledge", 0)
    projects = counts.get("projects", 0)
    sessions = counts.get("sessions", 0)

    def scale(n, full):
        return max(0, min(100, int(round(100.0 * n / full)))) if full else 0

    ferment = int(round(100.0 * sessions / memories)) if memories else 0
    return {
        "Recall": scale(memories, 150),
        "Depth": scale(knowledge, 80),
        "Drive": scale(projects, 40),
        "Streak": scale(sessions, 60),
        "Ferment": max(0, min(100, ferment)),
    }
