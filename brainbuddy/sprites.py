"""ASCII art.

Stage templates carry the silhouette (the growth arc has to read at a glance),
species supply a motif character and an eye pair. That's 6 shapes x 8 species
of variety without 48 hand-drawn sprites to keep in sync.

All original. Nothing here derives from any other project's art.
"""

STAGE_TEMPLATES = [
    # 0 Egg
    [
        "    ___    ",
        "   /   \\   ",
        "  ( {m}{m}{m} )  ",
        "   \\___/   ",
        "           ",
    ],
    # 1 Hatchling
    [
        "    ___    ",
        "   ( {e} )   ",
        "   /{m}{m}{m}\\   ",
        "    ^ ^    ",
        "           ",
    ],
    # 2 Fledgling
    [
        "    ___    ",
        "   ( {e} )   ",
        "  <|{m}{m}{m}|>  ",
        "   /   \\   ",
        "   ^   ^   ",
    ],
    # 3 Adept
    [
        "    \\|/    ",
        "   ( {e} )   ",
        "  <|{m}{m}{m}|>  ",
        "   /|_|\\   ",
        "   ^   ^   ",
    ],
    # 4 Sage
    [
        "   .\\|/.   ",
        "  ( {e} )  ",
        " /|{m}{m}{m}|\\ ",
        "  |___|    ",
        "  /     \\  ",
    ],
    # 5 Ascendant
    [
        "  *.\\|/.*  ",
        " \\( {e} )/ ",
        " /|{m}{m}{m}|\\ ",
        "  =|___|=  ",
        "  ^     ^  ",
    ],
]

# motif char, eye pair (3 wide, for sprites), compact eyes (2 wide, for the statusline)
SPECIES_LOOK = {
    "Mote":    ("o", "o o", "oo"),
    "Wisp":    ("~", "- -", "--"),
    "Ember":   ("*", "^ ^", "^^"),
    "Pip":     (".", ". .", ".."),
    "Fen":     ("=", "o o", "°°"),
    "Bramble": ("#", "x x", "xx"),
    "Nim":     ("+", "' '", "''"),
    "Quill":   ("/", "> <", "><"),
}

# The statusline gets ~5 columns, so the creature has to be a face. A bare
# progress glyph there read as a spinner, not a pet.
FACE_WRAP_UNICODE = ["(·)", "(%s)", "<%s>", "«%s»", "{%s}", "*%s*"]
FACE_WRAP_ASCII = ["(.)", "(%s)", "<%s>", "[%s]", "{%s}", "*%s*"]

SPRITE_WIDTH = 13

GLYPHS_UNICODE = ["\u25cc", "\u25cb", "\u25d4", "\u25d1", "\u25d5", "\u25cf"]
GLYPHS_ASCII = [".", "o", "c", "C", "O", "@"]


def look(species):
    return SPECIES_LOOK.get(species, SPECIES_LOOK["Mote"])[:2]


def face(species, stage_index, unicode_ok=True):
    """Tiny creature for the statusline. Eyes come from the species, the
    bracket grows with the stage, and an egg has no eyes yet.
    """
    eyes = SPECIES_LOOK.get(species, SPECIES_LOOK["Mote"])[2]
    if not unicode_ok and any(ord(c) > 127 for c in eyes):
        eyes = "oo"
    table = FACE_WRAP_UNICODE if unicode_ok else FACE_WRAP_ASCII
    wrap = table[max(0, min(len(table) - 1, stage_index))]
    return wrap if "%s" not in wrap else wrap % eyes


def glyph(stage_index, unicode_ok=True):
    table = GLYPHS_UNICODE if unicode_ok else GLYPHS_ASCII
    return table[max(0, min(len(table) - 1, stage_index))]


def sprite(species, stage_index, shiny=False):
    """Return the 5 rows for a species at a stage, padded to equal width."""
    motif, eyes = look(species)
    if shiny:
        motif = motif.upper() if motif.isalpha() else "$"
    rows = STAGE_TEMPLATES[max(0, min(len(STAGE_TEMPLATES) - 1, stage_index))]
    out = [r.replace("{m}", motif).replace("{e}", eyes) for r in rows]
    # Pad to a fixed width across every stage and species, otherwise the card's
    # right-hand column shifts as the creature evolves.
    width = max(SPRITE_WIDTH, max(len(r) for r in out))
    return [r.center(width) if r.strip() else " " * width for r in out]


def stage_track(stage_index, unicode_ok=True):
    """Six-slot evolution track. Filled slots are stages reached."""
    filled = "\u25aa" if unicode_ok else "#"
    empty = "\u25ab" if unicode_ok else "-"
    return "".join(filled if i <= stage_index else empty for i in range(len(STAGE_TEMPLATES)))


def bar(fraction, width=10, unicode_ok=True):
    fraction = max(0.0, min(1.0, fraction))
    full = "\u2588" if unicode_ok else "="
    empty = "\u2591" if unicode_ok else "."
    n = int(round(fraction * width))
    return full * n + empty * (width - n)
