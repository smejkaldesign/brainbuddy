"""Rendering. The statusline segment is the hot path and must not glob.

R12: nothing here ever prints a matched path. Counts only. A path that can
reach stdout can reach a screenshot, and memory filenames leak plenty on their
own even though R2 means we never opened them.
"""

import contextlib
import os
import re
import sys
import unicodedata

from . import creature as creature_mod
from . import metric, sprites, state as state_mod

RARITY_COLOR = {
    "Common": "\033[37m",
    "Uncommon": "\033[33m",
    "Rare": "\033[36m",
    "Epic": "\033[35m",
    "Legendary": "\033[32m",
}
DIM = "\033[2m"
# session gain reads as a gain, so green. it is not a rarity, it just shares the code
GAIN = "\033[32m"
# bold yellow, its own constant on purpose: flat yellow is the Uncommon tint,
# and an Uncommon creature must not wear the chip's colour on its own face
UPDATE = "\033[1;33m"
BOLD = "\033[1m"
RESET = "\033[0m"
# 256-colour grey rather than \033[90m, which themes remap and some render near-white.
# The box is meant to sit behind the creature, so it has to stay darker than the art.
BORDER = "\033[38;5;240m"

BOX_UNICODE = ("┌", "─", "┐", "│", "└", "┘")
BOX_ASCII = ("+", "-", "+", "|", "+", "+")
BOX_PAD = 1

# marks the segment as terminalcreature's. it sits in the right-hand column, so the two
# cells an emoji takes can't push the boxed art out of alignment
EGG_ICON = "🥚"
EGG_ICON_ASCII = "o"


FORMATS = ("ansi", "tmux", "plain")

# keyed on the escape, so the constants above stay the one place a colour is chosen
TMUX_STYLE = {
    "\033[37m": "#[fg=white]",
    "\033[33m": "#[fg=yellow]",
    "\033[36m": "#[fg=cyan]",
    "\033[35m": "#[fg=magenta]",
    "\033[32m": "#[fg=green]",
    "\033[2m": "#[dim]",
    "\033[1;33m": "#[fg=yellow,bold]",
    "\033[1m": "#[bold]",
    "\033[38;5;240m": "#[fg=colour240]",
}
TMUX_RESET = "#[default]"


def color_ok():
    return os.environ.get("NO_COLOR") is None and os.environ.get("TERM") != "dumb"


class Style:
    """One paint per backend. ansi is the terminal's own escapes and honours
    NO_COLOR. tmux speaks #[fg=] because tmux strips raw escapes out of a
    status command's output and shows the bytes instead. plain is bare text,
    for prompts that escape whatever they are handed.
    """

    def __init__(self, fmt="ansi"):
        if fmt not in FORMATS:
            raise ValueError("format must be one of %s" % ", ".join(FORMATS))
        self.fmt = fmt

    def paint(self, text, code):
        if self.fmt == "plain":
            return text
        if self.fmt == "tmux":
            style = TMUX_STYLE.get(code, "")
            return "%s%s%s" % (style, text, TMUX_RESET) if style else text
        return "%s%s%s" % (code, text, RESET) if color_ok() else text


_active = Style("ansi")


def paint(text, code):
    return _active.paint(text, code)


@contextlib.contextmanager
def styled(fmt):
    """Every paint inside the block goes through this backend. None means ansi,
    so callers that never heard of formats keep the bytes they always got.
    """
    global _active
    prev = _active
    _active = Style(fmt or "ansi")
    try:
        yield
    finally:
        _active = prev


# a styling directive in either backend. zero columns wide on screen
_DIRECTIVE = re.compile(r"(\033\[[0-9;]*m|#\[[^\]]*\])|(.)", re.DOTALL)


def _cell_width(ch):
    if unicodedata.combining(ch):
        return 0
    # the egg icon and its kind take two cells; counting them as one would
    # let a capped line run a column past where the host cuts it
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def fit(text, width):
    """Cap every line at width visible columns. Directives cost nothing, wide
    glyphs cost two, and a cut lands after a whole word rather than inside one.
    Whatever styling was open at the cut is closed, so the host's own text
    after it doesn't inherit the creature's colour.
    """
    if not width or width < 1:
        return text
    return "\n".join(_fit_line(line, width) for line in text.split("\n"))


def _fit_line(line, width):
    kept, cols, cut = [], 0, False
    for m in _DIRECTIVE.finditer(line):
        directive, ch = m.group(1), m.group(2)
        if directive:
            kept.append((directive, True))
            continue
        w = _cell_width(ch)
        if cols + w > width:
            # a cut inside a word leaves a fragment, so back up to the last gap
            if not ch.isspace():
                gaps = [i for i, (t, d) in enumerate(kept) if not d and t.isspace()]
                if gaps:
                    kept = kept[:gaps[-1]]
            cut = True
            break
        kept.append((ch, False))
        cols += w
    while kept and not kept[-1][1] and kept[-1][0].isspace():
        kept.pop()
    out = "".join(t for t, _ in kept)
    if cut:
        opened = [t for t, d in kept if d]
        if opened and opened[-1] not in (RESET, TMUX_RESET):
            out += TMUX_RESET if opened[-1].startswith("#[") else RESET
    return out


def unicode_ok(settings):
    if not settings.get("unicode", True):
        return False
    enc = (sys.stdout.encoding or "").lower()
    return "utf" in enc


def spawn_refresh():
    """Claim the cache first so concurrent renders don't stampede, then refresh
    in the background. Same trick the Ona chip uses.
    """
    import subprocess  # 3.8ms to import, and the hot path never gets here

    try:
        os.makedirs(state_mod.STATE_DIR, exist_ok=True)
        # the claim has to be a cache read_cache accepts. an empty file reads as
        # no cache at all, so every render before the scan finished spawned
        # another scan
        if state_mod.read_cache() is None:
            state_mod.write_cache(0, {})
        os.utime(state_mod.CACHE_PATH, None)
        subprocess.Popen(
            [sys.executable, "-m", "terminalcreature.cli", "refresh"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        pass


def current_xp(st, allow_blocking=True):
    """Cached XP. Blocks only on a genuine cold start."""
    cached = state_mod.read_cache()
    if cached is not None:
        xp, counts, age = cached
        if age > state_mod.CACHE_TTL:
            spawn_refresh()
        return xp, counts
    if not allow_blocking:
        # Cold start on the hot path. Kick off a scan so the next render has
        # something, rather than showing an empty segment forever.
        spawn_refresh()
        return 0, {}
    xp, counts = state_mod.measure_now(st["settings"])
    state_mod.write_cache(xp, counts)
    return xp, counts


# one line, because the whole point is that it gets pasted somewhere
SETUP_PROMPT = (
    "Set up a persistent memory system for this project: one markdown file per "
    "durable fact in your memory directory, an index listing them, and write to "
    "it as we work."
)


def no_source_help(settings, status):
    """What the user has to go do to earn XP. Empty string when XP is flowing.

    One branch per cause, and each one only says what's true for that cause.
    Offering "set the provider" to someone whose provider is already right, or
    "ask Claude to start keeping memory" to someone who just typo'd a path,
    reads as boilerplate and buries the one action that would work.
    """
    state = status["state"]
    if state == "ok":
        return ""
    provider = settings.get("provider", "claude")

    if state == "layout_mismatch":
        return "\n".join([
            "Found %d markdown files under that root, but none in the places the %s layout looks." % (
                status.get("stray", 0), provider),
            "",
            "Count it as a plain folder of notes instead:",
            "  /creature config provider folder",
        ])

    if state == "empty" or provider != "claude":
        # their setup is fine, so don't hand them configuration to re-do
        if state == "empty":
            return "\n".join([
                "That folder's empty, so there's nothing on the menu. Write a note and your",
                "buddy eats on the next render.",
            ])
        return "\n".join([
            "That folder isn't there, so your buddy has nothing to feed on. Point it somewhere real:",
            "  /creature config vault_root ~/notes",
            "",
            "`/creature config` shows the path it's using now.",
        ])

    # provider is claude and the directory has never existed, so this is someone
    # who hasn't kept memory at all. the only branch that earns the long version.
    return "\n".join([
        "Buddies feed off memories, and there's nothing here to feed on yet. Your",
        "buddy grows as your second brain does, so it needs one to eat from.",
        "",
        "Ask Claude Code to start keeping one:",
        "",
        '  "' + SETUP_PROMPT + '"',
        "",
        "Already keep notes somewhere? Point it at them instead:",
        "  /creature config provider folder",
        "  /creature config vault_root ~/notes",
    ])


def update_chip(settings, uni, word=True, available=None):
    """The update chip, or "". A fact off the cache, never a fetch: it exists
    only for opted-in users whose cached latest is newer than this install.
    Always painted whole and always last on its line; the word is the first
    thing cut in tight densities, never the icon. Callers that need both
    variants pass `available` so the cache is read once, not per variant.
    """
    from . import release

    if available is None:
        available = release.update_available(settings)
    if not available:
        return ""
    icon = "⬆" if uni else "^"
    return paint(icon + " update" if word else icon, UPDATE)


def segment(st, xp=None, counts=None, gain=0, mood=None, fmt=None, width=None):
    """One line for the statusline. Empty string means render nothing.

    fmt picks the style backend, width caps the columns. Both default to what
    Claude Code has always been handed.
    """
    with styled(fmt):
        return fit(_segment(st, xp, counts, gain, mood), width)


def _segment(st, xp, counts, gain, mood):
    settings = st["settings"]
    uni = unicode_ok(settings)
    if xp is None:
        xp, counts = current_xp(st)

    c = state_mod.focused(st)
    if c is None:
        return paint("%s no buddy" % sprites.glyph(0, uni), DIM)

    full = creature_mod.hydrate(c)

    level = metric.level_for(c["xp_banked"], settings["xp_max"])
    if state_mod.is_hatched(c):
        idx, _ = metric.stage_for(level)
        label = "Lv%d" % level
        tint = RARITY_COLOR.get(full["rarity"], "")
        mark = full["rarity_mark"]
        shiny = "*" if full["shiny"] else ""
    else:
        # level, rarity colour, mark and shiny all come off the seed, so an egg
        # wearing any of them has told you what's inside before you opened it
        idx, label = metric.EGG_SPRITE, "egg /creature-hatch"
        tint, mark, shiny = DIM, "", ""
    f = sprites.face(full["species"], idx, uni, mood)
    # the name is chosen at the hatch, so before it there isn't one to show
    shown = full["name"] if state_mod.is_hatched(c) else "Unhatched"

    earned = (" " + paint("+%d XP" % gain, GAIN)) if gain > 0 else ""
    from . import release
    avail = release.update_available(settings)  # one cache read for both variants
    chip_icon = update_chip(settings, uni, word=False, available=avail)
    chip_icon = (" " + chip_icon) if chip_icon else ""
    chip_word = update_chip(settings, uni, word=True, available=avail)
    chip_word = (" " + chip_word) if chip_word else ""

    if settings.get("density") == "sprite":
        return sprite_block(full, "%s %s%s" % (shown, label, mark), idx, tint, settings,
                            chip=update_chip(settings, uni, word=False, available=avail), mood=mood)
    if settings.get("density") == "minimal":
        # one glyph is the whole point of minimal, so no counter and no chip
        return paint(sprites.glyph(idx, uni) + shiny, tint)
    if settings.get("density") == "full":
        # rstrip: Common's empty mark left a trailing space, invisible at line
        # end until the chip started rendering after it
        return "%s %s %s%s%s" % (paint(f + shiny, tint), paint(shown, BOLD), paint(("%s %s" % (label, mark)).rstrip(), DIM), earned, chip_word)
    # compact's ~10 columns are a contract, so the chip is icon-only here
    return "%s %s%s%s" % (paint(f + shiny + mark, tint), paint(label, DIM), earned, chip_icon)




def ruler(width=200):
    """Width ruler for the statusline. There's no terminal width on stdin and
    no tty, so the only way to learn it is to print a ruler and read where the
    terminal cuts it off.
    """
    out = []
    for i in range(1, width + 1):
        if i % 10 == 0:
            out.append(str((i // 10) % 10))
        elif i % 5 == 0:
            out.append("+")
        else:
            out.append("-")
    return "".join(out)


# the whole gap now that the art is trimmed, so it's the real number rather than
# sitting on top of the sprite's own padding. the box adds BOX_PAD inside the wall
GUTTER = 2


def _trim(art):
    """Drop blank edge rows and the shared left indent the templates carry."""
    art = list(art)
    while art and not art[-1].strip():
        art.pop()
    while art and not art[0].strip():
        art.pop(0)
    indent = min(len(r) - len(r.lstrip()) for r in art if r.strip())
    return [r[indent:].rstrip() for r in art]


def _column_width(full, short):
    """Widest trimmed form for this creature, across every stage."""
    return max(
        len(r)
        for i in range(len(sprites.STAGE_TEMPLATES))
        for r in _trim(sprites.sprite(full["species"], i, full["shiny"], short=short))
    )


def compose(st, left, xp=None, counts=None, gain=0, mood=None, fmt=None, width=None):
    """Merge a caller's statusline text with the creature as a left column.

    The creature's first row shares row one with the bar, so it reads as a
    column starting at the top rather than a block hanging underneath. Left
    rather than right because a fixed-width column needs no measurement: the
    host's box can be any width and the art still lands whole.
    """
    with styled(fmt):
        return fit(_compose(st, left, xp, counts, gain, mood), width)


def _compose(st, left, xp, counts, gain, mood):
    settings = st["settings"]
    if settings.get("density") == "ruler":
        return ruler()
    uni = unicode_ok(settings)
    if xp is None:
        xp, counts = current_xp(st, allow_blocking=False)
    c = state_mod.focused(st)
    if c is None:
        return left

    full = creature_mod.hydrate(c)
    level = metric.level_for(c["xp_banked"], settings["xp_max"])
    hatched = state_mod.is_hatched(c)
    idx, stage = metric.stage_for(level) if hatched else (metric.EGG_SPRITE, "egg")
    tint = RARITY_COLOR.get(full["rarity"], "") if hatched else DIM

    short = settings.get("sprite_height", 5) <= 3
    art = _trim(sprites.sprite(full["species"], idx, full["shiny"], short=short, mood=mood))

    banked = c["xp_banked"]
    lo = metric.xp_for_level(level, settings["xp_max"])
    hi = metric.xp_for_level(level + 1, settings["xp_max"])
    frac = (banked - lo) / float(hi - lo) if hi > lo else 0.0
    # the caption is a statusline row, not part of the sprite block, so it lines up
    # under the caller's own rows instead of hanging off the bottom of the art
    icon = EGG_ICON if uni else EGG_ICON_ASCII
    if hatched:
        # painted in pieces. wrapping the finished string in BOLD would end at
        # the gain's own reset and leave the bar unbolded. the gain reads as a
        # delta on the bar, so it sits to the bar's right, and the chip last
        caption = paint("%s %s · %s Lv%d" % (icon, full["name"], stage, level), BOLD)
        caption += " " + paint(sprites.bar(frac, 6, uni), BOLD)
        if gain > 0:
            caption += " " + paint("+%d XP" % gain, GAIN)
        chip = update_chip(settings, uni, word=True)
        if chip:
            caption += " " + chip
    else:
        # no name, no level, no progress bar: the name is chosen at the hatch
        # and everything else would spoil the reveal before you open it
        caption = paint("%s Unhatched · /creature-hatch" % icon, BOLD)

    # pin the column to the widest form this creature will ever reach, so the text
    # beside it doesn't jump two columns the day it evolves into an Ascendant
    block = _column_width(full, short)
    lead = " " * ((block - max(len(r) for r in art)) // 2)
    # shift the whole sprite as one unit. centring row by row would undo the
    # per-row padding the art relies on to line up
    art = [(lead + r).ljust(block) for r in art]

    # fixed-width column, so nothing here needs the terminal width
    left_lines = left.split("\n") if left else []
    left_lines.append(caption)

    if settings.get("border", True):
        tl, h, tr, v, bl, br = BOX_UNICODE if uni else BOX_ASCII
        # a column of breathing room, or a wide stage's arms touch the wall
        inner = block + 2 * BOX_PAD
        bar = paint(v, BORDER)
        pad = " " * BOX_PAD
        cells = [paint(tl + h * inner + tr, BORDER)]
        cells += [bar + paint(pad + r + pad, tint) + bar for r in art]
        cells.append(paint(bl + h * inner + br, BORDER))
        # the caller's first row belongs beside the head, not beside the box lid
        left_lines.insert(0, "")
        width = inner + 2
    else:
        cells = [paint(r, tint) for r in art]
        width = block

    rows = []
    for i in range(max(len(left_lines), len(cells))):
        l = left_lines[i] if i < len(left_lines) else ""
        # painted cells carry escape bytes, so pad from the known column width
        cell = cells[i] if i < len(cells) else " " * width
        rows.append((cell + " " * GUTTER + l).rstrip())
    return "\n".join(rows)


def sprite_block(full, label, stage_index, tint, settings, chip="", mood=None):
    """Full creature on its own rows, for multi-line statuslines.

    Right-aligns to settings["columns"] because a statusline script can't learn
    the real terminal width. There's no field for it on stdin and /dev/tty
    isn't attached, so the width has to be declared rather than measured.

    The chip arrives separately and painted: measuring it inside the label
    would count its escapes as columns, and folding it into the DIM span
    would leave it dimmed instead of independently painted.
    """
    art = sprites.sprite(full["species"], stage_index, full["shiny"], short=settings.get("sprite_height", 5) <= 3, mood=mood)
    while art and not art[-1].strip():
        art.pop()
    cols = settings.get("columns") or 0

    rows = []
    for row in art:
        pad = " " * max(0, cols - len(row))
        rows.append(pad + paint(row, tint))
    caption = paint(label, DIM)
    width = len(label)
    if chip:
        caption += " " + chip
        width += 2  # one icon and its space, whatever escapes wrap them
    pad = " " * max(0, cols - width)
    rows.append(pad + caption)
    return "\n" + "\n".join(rows)


def _zero_note(st, xp):
    """One line for the card when nothing is being counted. None when it is.

    Only runs on a zero, so the scan it costs never lands on a working setup.
    """
    if xp:
        return None
    if state_mod.source_status(st["settings"])["state"] == "ok":
        return None
    return paint("going hungry. /creature doctor says what it needs", DIM)


def egg_card(st, c):
    """An egg's card. Names nothing derived from the seed, or there's no reveal left.

    Species, rarity, shiny, stage and stats all come off the seed and are known
    the moment the egg exists. Printing any of them here spoils the hatch.
    """
    art = sprites.sprite("Mote", metric.EGG_SPRITE, False)
    out = [""] + ["  " + r for r in art]
    out += [
        "",
        "  %s" % paint("Unhatched", BOLD),
        "  " + paint("%d xp eaten and counting" % c.get("xp_banked", 0), DIM),
        "  " + paint("/creature-hatch to find out what it is", DIM),
    ]
    note = _zero_note(st, c.get("xp_banked", 0))
    if note:
        out += ["", "  " + note]
    out.append("")
    return "\n".join(out)


def card(st, xp=None, counts=None, hungry_note=True, art=True, fmt=None, width=None):
    """The /creature view. Multi-line, safe to be verbose, except about paths.

    hungry_note=False for callers that answer the zero themselves. The card's
    version points at doctor, which is the wrong thing to read directly above
    the same answer spelled out. art=False for callers that just drew the
    creature, like the hatch ceremony: it drops the sprite and the name header
    rather than repeating them.
    """
    with styled(fmt):
        return fit(_card(st, xp, counts, hungry_note, art), width)


def _card(st, xp, counts, hungry_note, art):
    settings = st["settings"]
    uni = unicode_ok(settings)
    if xp is None:
        xp, counts = current_xp(st)
    c = state_mod.focused(st)
    if c is None:
        # a retired buddy isn't "no buddy". this used to assert the roster was
        # empty and drop the one command that gets them back
        parked = [x["name"] for x in st.get("creatures", [])]
        if parked:
            return "Nothing focused. `/creature focus %s` brings it back, or /creature-new lays a fresh egg." % parked[0]
        return "No buddy yet. /creature-new lays an egg."
    if not state_mod.is_hatched(c):
        return egg_card(st, c)

    full = creature_mod.hydrate(c)
    banked = c["xp_banked"]
    p = metric.progress(banked, settings["xp_max"])
    stats = creature_mod.stats_from_counts(counts)

    tint = RARITY_COLOR.get(full["rarity"], "")

    header = "%s  %s" % (paint(full["name"], BOLD), paint("%s %s%s" % (full["species"], full["rarity"], " shiny" if full["shiny"] else ""), tint))

    span_lo = metric.xp_for_level(p["level"], settings["xp_max"])
    span_hi = p["next_level_xp"]
    frac = (banked - span_lo) / float(span_hi - span_lo) if span_hi > span_lo else 0.0

    info = [] if not art else [header, ""]
    info += [
        "Level %d   %s   %s" % (p["level"], p["stage"], sprites.stage_track(p["stage_index"], uni)),
        "%s  %d / %d xp" % (sprites.bar(frac, 10, uni), banked, span_hi),
    ]
    if p["next_stage_level"]:
        info.append(paint("Next form at level %d (%d xp)" % (p["next_stage_level"], p["next_stage_xp"]), DIM))
    else:
        info.append(paint("Fully evolved. Hatch a new egg to start another.", DIM))

    if any(stats.values()):
        # the folder provider feeds none of the five, and a row of zeros reads
        # as broken rather than early
        info.append("")
        info.append("  ".join("%s %d" % (k, v) for k, v in stats.items()))
    info.append(paint("counted: " + "  ".join("%s %d" % (k, v) for k, v in sorted(counts.items())), DIM))
    note = _zero_note(st, xp) if hungry_note else None
    if note:
        info += ["", note]

    if not art:
        return "\n".join("  " + r for r in info).rstrip()

    sprite_art = sprites.sprite(full["species"], p["stage_index"], full["shiny"])
    lines = []
    pad = max(len(r) for r in sprite_art)
    for i in range(max(len(sprite_art), len(info))):
        left = sprite_art[i] if i < len(sprite_art) else " " * pad
        right = info[i] if i < len(info) else ""
        lines.append("  %s   %s" % (paint(left, tint), right))
    return "\n".join(lines).rstrip()


def _article(word):
    # Uncommon and Epic were reading as "a Uncommon"
    return "an" if word[:1].lower() in "aeiou" else "a"


def hatch_ceremony(st, c):
    """The reveal. Shows whatever stage the egg banked its way to, not a baby."""
    full = creature_mod.hydrate(c)
    level = metric.level_for(c.get("xp_banked", 0), st["settings"]["xp_max"])
    idx, stage = metric.stage_for(level)
    tint = RARITY_COLOR.get(full["rarity"], "")
    art = sprites.sprite(full["species"], idx, full["shiny"])
    out = ["", "  " + paint("the egg cracks", DIM), ""]
    out += ["  " + paint(r, tint) for r in art]
    out += [
        "",
        "  %s, %s %s %s%s" % (paint(full["name"], BOLD), _article(full["rarity"]), full["rarity"], full["species"], " (shiny)" if full["shiny"] else ""),
        "  " + paint("Lv%d %s" % (level, stage), DIM),
        "",
    ]
    return "\n".join(out)


def empty_hatch_note(st, status):
    """The reveal with nothing counted. Says day one out loud instead of nothing.

    Hatching on a machine with no memory system is the one path where the
    ceremony lands on a Lv0 that means "there was nothing to eat". The creature
    is still whatever the seed made it, so the reveal is intact; what's missing
    is any sign that the number is the start of something rather than a dud.
    """
    out = [
        "  " + paint("nothing counted yet, so Lv0. that's the floor, not a dud roll.", DIM),
        "  " + paint("it levels off the markdown you keep, so give it something to eat.", DIM),
    ]
    help_text = no_source_help(st["settings"], status)
    if help_text:
        out += ["", help_text]
    return "\n".join(out)


def egg_notice(st, c):
    """What you see after `new`: an egg, no level, and how to open it.

    Same rule as egg_card. `new` is the main way people get an egg, so a rarity
    colour here spoils the reveal for most of them.
    """
    tint = DIM
    art = sprites.sprite("Mote", metric.EGG_SPRITE, False)
    out = [""] + ["  " + paint(r, tint) for r in art]
    out += [
        "",
        "  %s" % paint("An egg, unhatched", BOLD),
        "  " + paint("/creature-hatch to open it", DIM),
        "",
    ]
    return "\n".join(out)


def evolution_notice(event, st):
    uni = unicode_ok(st["settings"])
    return "  %s  %s evolved into %s at level %d" % (
        sprites.glyph(event["stage_index"], uni),
        event["creature"],
        event["stage"],
        event["level"],
    )
