"""Command line. `render` is what the statusline calls; everything else is human-facing.

render must never crash a statusline. On any unexpected error it prints nothing
and exits 0, because a broken pet should not break the prompt.
"""

import json
import os
import sys

from . import creature as creature_mod
from . import metric, render, sprites
from . import state as state_mod

USAGE = """brainbuddy - a terminal pet that evolves with your memory

  render              one-line statusline segment (what the statusline calls)
  compose "<text>"    your statusline text with the creature as a left column
  card                full creature card
  new [name]          lay a new egg (--replace or --add)
  hatch               open the egg, revealing whatever level it reached
  focus <name>        choose which creature banks new xp
  list                the roster
  rename <old> <new>
  retire <name>
  config              show settings
  config <key> <val>  set one (provider, vault_root, xp_max, density, columns, sprite_height, unicode, border, hidden)
  hide / show         drop the creature from the statusline, or bring it back
  simulate <xp>       preview any level without touching your real state
  refresh             recompute the xp cache (run in the background by render)
  doctor              check what brainbuddy can see
"""


def _load():
    return state_mod.load()


def cmd_render(args):
    try:
        st = _load()
        if st["settings"].get("hidden"):
            return 0
        xp, counts = render.current_xp(st, allow_blocking=False)
        if xp:
            event = state_mod.sync(st, xp)
            if event:
                state_mod.save(st)
        line = render.segment(st, xp, counts)
        if line:
            sys.stdout.write(line)
    except Exception:
        pass
    return 0


def cmd_compose(args):
    """Merge caller-supplied statusline text with the creature as a left column."""
    try:
        left = args[0] if args else sys.stdin.read().rstrip("\n")
        st = _load()
        # hidden means the caller's bar passes through untouched, xp still banks on the next visible run
        if st["settings"].get("hidden"):
            sys.stdout.write(left)
            return 0
        xp, counts = render.current_xp(st, allow_blocking=False)
        if xp:
            event = state_mod.sync(st, xp)
            if event:
                state_mod.save(st)
        sys.stdout.write(render.compose(st, left, xp, counts))
    except Exception:
        sys.stdout.write(args[0] if args else "")
    return 0


def cmd_refresh(args):
    st = _load()
    xp, counts = state_mod.measure_now(st["settings"])
    state_mod.write_cache(xp, counts)
    event = state_mod.sync(st, xp)
    state_mod.save(st)
    if event:
        print(render.evolution_notice(event, st))
    return 0


def cmd_card(args):
    st = _load()
    xp, _ = render.current_xp(st)
    state_mod.sync(st, xp)
    state_mod.save(st)
    print(render.card(st))
    return 0


def cmd_new(args):
    """Lay a new egg. --replace retires the current buddy, --add keeps it."""
    st = _load()
    name = next((a for a in args if not a.startswith("-")), None)
    cur = state_mod.focused(st)
    first = not st.get("creatures")

    if cur is None:
        mode = "add"
    elif "--replace" in args:
        mode = "replace"
    elif "--add" in args:
        mode = "add"
    else:
        print("%s is your current buddy. Pick one:" % cur["name"])
        print("  brainbuddy new --replace   retire %s and start a new egg" % cur["name"])
        print("  brainbuddy new --add       keep %s in the roster, start a new egg" % cur["name"])
        return 1

    if mode == "add" and cur is not None and "--yes" not in args:
        # no level threshold any more. the tradeoff is the same at 12 as at 99,
        # so state it and let them decide instead of gating on a number
        lvl = metric.level_for(cur["xp_banked"], st["settings"]["xp_max"])
        print("%s is level %d. A new egg starts at 0 and takes focus, so %s holds its level and stops gaining." % (cur["name"], lvl, cur["name"]))
        print("Run: brainbuddy new --add --yes")
        return 1

    if mode == "replace":
        lvl = metric.level_for(cur["xp_banked"], st["settings"]["xp_max"])
        state_mod.retire(st, cur["id"])
        print("retired %s at Lv%d, %d xp kept. `brainbuddy focus %s` brings it back." % (
            cur["name"], lvl, cur.get("xp_banked", 0), cur["name"]))

    c = state_mod.create(st, name=name)
    if first:
        # the first egg inherits the memory that already exists, so it opens at
        # your real level. later ones start at zero, that's per-creature banking
        xp, counts = state_mod.measure_now(st["settings"])
        state_mod.write_cache(xp, counts)
        state_mod.sync(st, xp)
    state_mod.save(st)
    print(render.egg_notice(st, c))
    return 0


def cmd_hatch(args):
    """Open the egg. Reveals whatever level it banked its way to."""
    st = _load()
    c = state_mod.focused(st)
    if c is None:
        print("no egg to open. `brainbuddy new` lays one.")
        return 1
    if state_mod.is_hatched(c):
        lvl = metric.level_for(c["xp_banked"], st["settings"]["xp_max"])
        print("%s is already out, Lv%d. `brainbuddy card` shows it." % (c["name"], lvl))
        return 1
    xp, counts = render.current_xp(st)
    if xp:
        state_mod.sync(st, xp)
    state_mod.reveal(st)
    state_mod.save(st)
    print(render.hatch_ceremony(st, c))
    print(render.card(st, xp=xp, counts=counts))
    return 0


def cmd_focus(args):
    if not args:
        print("which one? brainbuddy focus <name>")
        return 1
    st = _load()
    c = state_mod.focus(st, args[0])
    if c is None:
        print("no creature called %s" % args[0])
        return 1
    state_mod.save(st)
    print("focused %s. it banks new xp from here." % c["name"])
    return 0


def cmd_list(args):
    st = _load()
    if not st.get("creatures"):
        print("no creatures yet. brainbuddy new")
        return 0
    uni = render.unicode_ok(st["settings"])
    for c in st["creatures"]:
        full = creature_mod.hydrate(c)
        lvl = metric.level_for(c["xp_banked"], st["settings"]["xp_max"])
        if state_mod.is_hatched(c):
            idx, stage = metric.stage_for(lvl)
            level_col = "Lv%-4d" % lvl
            # rarity and shiny come off the seed, so an egg must not print them
            desc = full["rarity"] + (" shiny" if full["shiny"] else "")
        else:
            idx, stage, level_col = metric.EGG_SPRITE, "unhatched", "egg   "
            desc = ""
        flag = "*" if c["id"] == st.get("focused") else " "
        note = "retired" if c.get("retired_at") else ""
        print(("%s %s %-10s %s %-10s %s %s" % (
            flag, sprites.glyph(idx, uni), c["name"], level_col, stage, desc, note)).rstrip())
    print("\n* = focused (the one gaining xp)")
    return 0


def cmd_rename(args):
    if len(args) < 2:
        print("brainbuddy rename <old> <new>")
        return 1
    st = _load()
    for c in st.get("creatures", []):
        if c["name"].lower() == args[0].lower():
            c["name"] = args[1]
            state_mod.save(st)
            print("renamed to %s" % args[1])
            return 0
    print("no creature called %s" % args[0])
    return 1


def cmd_retire(args):
    if not args:
        print("brainbuddy retire <name>")
        return 1
    st = _load()
    c = state_mod.retire(st, args[0])
    if c is None:
        print("no creature called %s" % args[0])
        return 1
    state_mod.save(st)
    # retiring keeps the record. it used to delete, which threw away banked xp
    # with no confirmation and no way back
    print("retired %s, %d xp kept. `brainbuddy focus %s` brings it back." % (
        c["name"], c.get("xp_banked", 0), c["name"]))
    return 0


def cmd_config(args):
    st = _load()
    if not args:
        # home-relative, so a screenshot of this doesn't carry a username
        shown = dict(st["settings"])
        home = os.path.expanduser("~")
        if shown.get("vault_root", "").startswith(home):
            shown["vault_root"] = "~" + shown["vault_root"][len(home):]
        print(json.dumps(shown, indent=2, sort_keys=True))
        return 0
    if len(args) < 2:
        print("brainbuddy config <key> <value>")
        return 1
    key, raw = args[0], args[1]
    if key not in state_mod.DEFAULT_SETTINGS:
        print("unknown setting %s. known: %s" % (key, ", ".join(sorted(state_mod.DEFAULT_SETTINGS))))
        return 1
    if key == "xp_max":
        value = int(raw)
        if value < 1:
            print("xp_max must be positive")
            return 1
    elif key in ("unicode", "hidden", "border"):
        value = raw.lower() in ("1", "true", "yes", "on")
    elif key == "density":
        if raw not in ("compact", "minimal", "full", "sprite", "ruler"):
            print("density must be compact, minimal, full, sprite or ruler")
            return 1
        value = raw
    elif key == "sprite_height":
        value = 3 if int(raw) <= 3 else 5
    elif key == "columns":
        value = int(raw)
        if value < 0:
            print("columns can't be negative")
            return 1
    else:
        value = raw
    st["settings"][key] = value
    state_mod.save(st, own_settings=True)
    print("%s = %s" % (key, value))
    return 0


def cmd_simulate(args):
    """Preview any level without a real vault or touching real state."""
    if not args:
        print("brainbuddy simulate <xp>")
        return 1
    xp = int(args[0])
    st = state_mod.default_state()
    c = state_mod.create(st, name=(args[1] if len(args) > 1 else None))
    state_mod.reveal(st)
    c["xp_banked"] = xp
    p = metric.progress(xp, st["settings"]["xp_max"])
    c["last_stage_seen"] = p["stage_index"]
    # Synthetic counts back-derived from the simulated xp. Reading the real
    # cache here would make a preview quietly report the live vault.
    counts = {"memories": xp // 6, "knowledge": xp // 12, "projects": xp // 30, "sessions": xp // 15, "decisions": xp // 300}
    print(render.card(st, xp=xp, counts=counts))
    print("\nstatusline: [%s]" % render.segment(st, xp, counts))
    return 0


def cmd_doctor(args):
    """Report what we can see. Counts only, never a path (R12)."""
    st = _load()
    xp, counts = state_mod.measure_now(st["settings"])
    print("provider: %s" % st["settings"]["provider"])
    print("configured root: %s" % ("set" if (st["settings"]["provider"] != "vault" or st["settings"]["vault_root"]) else "MISSING"))
    for k in sorted(counts):
        print("  %-10s %d" % (k, counts[k]))
    p = metric.progress(xp, st["settings"]["xp_max"])
    print("xp %d -> level %d (%s)" % (xp, p["level"], p["stage"]))
    if xp == 0:
        print("\nnothing found. check: brainbuddy config provider / vault_root")
    return 0


def _set_hidden(hidden):
    st = _load()
    st["settings"]["hidden"] = hidden
    state_mod.save(st, own_settings=True)
    name = None
    c = state_mod.focused(st)
    if c is not None:
        name = c["name"]
    who = name or "the creature"
    print("%s is %s the statusline" % (who, "hidden from" if hidden else "back in"))
    return 0


def cmd_hide(args):
    return _set_hidden(True)


def cmd_show(args):
    return _set_hidden(False)


COMMANDS = {
    "render": cmd_render, "compose": cmd_compose, "refresh": cmd_refresh, "card": cmd_card,
    "new": cmd_new, "hatch": cmd_hatch, "focus": cmd_focus, "list": cmd_list,
    "rename": cmd_rename, "retire": cmd_retire, "config": cmd_config,
    "simulate": cmd_simulate, "doctor": cmd_doctor,
    "hide": cmd_hide, "show": cmd_show,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    fn = COMMANDS.get(argv[0])
    if fn is None:
        print("unknown command %s\n" % argv[0])
        print(USAGE)
        return 1
    return fn(argv[1:])


if __name__ == "__main__":
    sys.exit(main())
