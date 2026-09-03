"""Rendering. The statusline segment is the hot path and must not glob.

R12: nothing here ever prints a matched path. Counts only. A path that can
reach stdout can reach a screenshot, and memory filenames leak plenty on their
own even though R2 means we never opened them.
"""

import os
import sys

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
BOLD = "\033[1m"
RESET = "\033[0m"
# 256-colour grey rather than \033[90m, which themes remap and some render near-white.
# The box is meant to sit behind the creature, so it has to stay darker than the art.
BORDER = "\033[38;5;240m"

BOX_UNICODE = ("┌", "─", "┐", "│", "└", "┘")
BOX_ASCII = ("+", "-", "+", "|", "+", "+")
BOX_PAD = 1

# marks the segment as brainbuddy's. it sits in the right-hand column, so the two
# cells an emoji takes can't push the boxed art out of alignment
EGG_ICON = "🥚"
EGG_ICON_ASCII = "o"


def color_ok():
    return os.environ.get("NO_COLOR") is None and os.environ.get("TERM") != "dumb"


def paint(text, code):
    return "%s%s%s" % (code, text, RESET) if color_ok() else text


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
        open(state_mod.CACHE_PATH, "a").close()
        os.utime(state_mod.CACHE_PATH, None)
        subprocess.Popen(
            [sys.executable, "-m", "brainbuddy.cli", "refresh"],
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


def segment(st, xp=None, counts=None):
    """One line for the statusline. Empty string means render nothing."""
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
    else:
        # an unopened egg doesn't show its level. that reveal is the whole point of hatching
        idx, label = metric.EGG_SPRITE, "egg"
    f = sprites.face(full["species"], idx, uni)
    tint = RARITY_COLOR.get(full["rarity"], "")
    mark = full["rarity_mark"]
    shiny = "*" if full["shiny"] else ""

    if settings.get("density") == "sprite":
        return sprite_block(full, "%s %s%s" % (full["name"], label, mark), idx, tint, settings)
    if settings.get("density") == "minimal":
        return paint(sprites.glyph(idx, uni) + shiny, tint)
    if settings.get("density") == "full":
        return "%s %s %s" % (paint(f + shiny, tint), paint(full["name"], BOLD), paint("%s %s" % (label, mark), DIM))
    return "%s %s" % (paint(f + shiny + mark, tint), paint(label, DIM))




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


def compose(st, left, xp=None, counts=None):
    """Merge a caller's statusline text with the creature as a left column.

    The creature's first row shares row one with the bar, so it reads as a
    column starting at the top rather than a block hanging underneath. Left
    rather than right because a fixed-width column needs no measurement: the
    host's box can be any width and the art still lands whole.
    """
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
    tint = RARITY_COLOR.get(full["rarity"], "")

    short = settings.get("sprite_height", 5) <= 3
    art = _trim(sprites.sprite(full["species"], idx, full["shiny"], short=short))

    banked = c["xp_banked"]
    lo = metric.xp_for_level(level, settings["xp_max"])
    hi = metric.xp_for_level(level + 1, settings["xp_max"])
    frac = (banked - lo) / float(hi - lo) if hi > lo else 0.0
    # the caption is a statusline row, not part of the sprite block, so it lines up
    # under the caller's own rows instead of hanging off the bottom of the art
    icon = EGG_ICON if uni else EGG_ICON_ASCII
    if hatched:
        caption = "%s %s · %s Lv%d %s" % (icon, full["name"], stage, level, sprites.bar(frac, 6, uni))
    else:
        # no level and no progress bar, or the reveal is spoiled before you open it
        caption = "%s %s · egg · /brainbuddy-hatch" % (icon, full["name"])

    # pin the column to the widest form this creature will ever reach, so the text
    # beside it doesn't jump two columns the day it evolves into an Ascendant
    block = _column_width(full, short)
    lead = " " * ((block - max(len(r) for r in art)) // 2)
    # shift the whole sprite as one unit. centring row by row would undo the
    # per-row padding the art relies on to line up
    art = [(lead + r).ljust(block) for r in art]

    # fixed-width column, so nothing here needs the terminal width
    left_lines = left.split("\n") if left else []
    # BOLD, not DIM: this row reads as a peer of the repo name the host prints
    # above it, and the host uses \033[1m for that
    left_lines.append(paint(caption, BOLD))

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


def sprite_block(full, label, stage_index, tint, settings):
    """Full creature on its own rows, for multi-line statuslines.

    Right-aligns to settings["columns"] because a statusline script can't learn
    the real terminal width. There's no field for it on stdin and /dev/tty
    isn't attached, so the width has to be declared rather than measured.
    """
    art = sprites.sprite(full["species"], stage_index, full["shiny"], short=settings.get("sprite_height", 5) <= 3)
    while art and not art[-1].strip():
        art.pop()
    cols = settings.get("columns") or 0

    rows = []
    for row in art:
        pad = " " * max(0, cols - len(row))
        rows.append(pad + paint(row, tint))
    pad = " " * max(0, cols - len(label))
    rows.append(pad + paint(label, DIM))
    return "\n" + "\n".join(rows)


def egg_card(st, c):
    """An egg's card. Names nothing derived from the seed, or there's no reveal left.

    Species, rarity, shiny, stage and stats all come off the seed and are known
    the moment the egg exists. Printing any of them here spoils the hatch.
    """
    art = sprites.sprite("Mote", metric.EGG_SPRITE, False)
    out = [""] + ["  " + r for r in art]
    out += [
        "",
        "  %s  %s" % (paint(c["name"], BOLD), paint("unhatched", DIM)),
        "  " + paint("%d xp banked and counting" % c.get("xp_banked", 0), DIM),
        "  " + paint("/brainbuddy-hatch to find out what it is", DIM),
        "",
    ]
    return "\n".join(out)


def card(st, xp=None, counts=None):
    """The /brainbuddy view. Multi-line, safe to be verbose, except about paths."""
    settings = st["settings"]
    uni = unicode_ok(settings)
    if xp is None:
        xp, counts = current_xp(st)
    c = state_mod.focused(st)
    if c is None:
        return "No buddy yet. Lay an egg with: brainbuddy new"
    if not state_mod.is_hatched(c):
        return egg_card(st, c)

    full = creature_mod.hydrate(c)
    banked = c["xp_banked"]
    p = metric.progress(banked, settings["xp_max"])
    stats = creature_mod.stats_from_counts(counts)

    art = sprites.sprite(full["species"], p["stage_index"], full["shiny"])
    tint = RARITY_COLOR.get(full["rarity"], "")

    header = "%s  %s" % (paint(full["name"], BOLD), paint("%s %s%s" % (full["species"], full["rarity"], " shiny" if full["shiny"] else ""), tint))

    span_lo = metric.xp_for_level(p["level"], settings["xp_max"])
    span_hi = p["next_level_xp"]
    frac = (banked - span_lo) / float(span_hi - span_lo) if span_hi > span_lo else 0.0

    info = [
        header,
        "",
        "Level %d   %s   %s" % (p["level"], p["stage"], sprites.stage_track(p["stage_index"], uni)),
        "%s  %d / %d xp" % (sprites.bar(frac, 10, uni), banked, span_hi),
    ]
    if p["next_stage_level"]:
        info.append(paint("Next form at level %d (%d xp)" % (p["next_stage_level"], p["next_stage_xp"]), DIM))
    else:
        info.append(paint("Fully evolved. Hatch a new egg to start another.", DIM))

    info.append("")
    info.append("  ".join("%s %d" % (k, v) for k, v in stats.items()))
    info.append(paint("counted: " + "  ".join("%s %d" % (k, v) for k, v in sorted(counts.items())), DIM))

    lines = []
    pad = max(len(r) for r in art)
    for i in range(max(len(art), len(info))):
        left = art[i] if i < len(art) else " " * pad
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


def egg_notice(st, c):
    """What you see after `new`: an egg, no level, and how to open it."""
    full = creature_mod.hydrate(c)
    tint = RARITY_COLOR.get(full["rarity"], "")
    art = sprites.sprite(full["species"], metric.EGG_SPRITE, full["shiny"])
    out = [""] + ["  " + paint(r, tint) for r in art]
    out += [
        "",
        "  %s is an egg" % paint(full["name"], BOLD),
        "  " + paint("/brainbuddy-hatch to open it", DIM),
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
