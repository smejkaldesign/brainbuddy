"""Command line. `render` is what the statusline calls; everything else is human-facing.

render must never crash a statusline. On any unexpected error it prints nothing
and exits 0, because a broken pet should not break the prompt.
"""

import json
import os
import sys

from . import __version__
from . import creature as creature_mod
from . import metric, render, sprites
from . import state as state_mod

USAGE = """brainbuddy - a terminal pet that evolves with your memory

  render              one-line statusline segment (what the statusline calls)
  compose "<text>"    your statusline text with the creature as a left column
  card                full creature card
  new [name]          lay a new egg (--replace or --add)
  hatch [--from-zero] open the egg; --from-zero starts at 0 instead of scoring
        [--name <n>]  what you've already written. --name names it as it opens
  names               two fresh name ideas, for naming an egg before it opens
  focus <name>        choose which creature banks new xp
  list                the roster
  rename <old> <new>
  retire <name>
  config              show settings
  config <key> <val>  set one (provider, vault_root, xp_max, density, columns, sprite_height, unicode, border, hidden)
  hide / show         drop the creature from the statusline, or bring it back
  simulate <xp>       preview any level without touching your real state
  refresh             recompute the xp cache (run in the background by render)
  sources             what it can count, and what to do if that's nothing
  doctor [--check]    check what brainbuddy can see; --check also asks pypi
  update              ask pypi whether there's a newer brainbuddy

update and doctor --check are the only commands that go online, and only when
you run them. Everything else, the statusline included, is offline.

provider is claude (stock Claude Code memory), vault (a structured vault) or
folder (any directory of markdown, set vault_root to point at it).
"""


def _load():
    return state_mod.load()


def _stdin_text():
    """Whatever the statusline piped us, or "" when a human is at the keyboard.

    isatty, or `brainbuddy compose "text"` typed by hand would sit there waiting
    for a statusline payload that is never coming.
    """
    try:
        if sys.stdin.isatty():
            return ""
        return sys.stdin.read()
    except Exception:
        return ""


def _session_id(raw):
    """Claude Code's statusline JSON carries the session id. Only that is read."""
    try:
        return json.loads(raw).get("session_id") or None
    except (ValueError, AttributeError):
        return None


def _bank(st, session_id):
    """Credit new xp, then work out what this session is responsible for."""
    xp, counts = render.current_xp(st, allow_blocking=False)
    dirty = False
    if xp and state_mod.sync(st, xp):
        dirty = True
    c = state_mod.focused(st)
    gain, is_new = state_mod.session_gain(st, session_id, c.get("xp_banked", 0) if c else 0)
    if dirty or is_new:
        state_mod.save(st)
    return xp, counts, gain


def cmd_render(args):
    try:
        session = _session_id(_stdin_text())
        st = _load()
        if st["settings"].get("hidden"):
            return 0
        xp, counts, gain = _bank(st, session)
        line = render.segment(st, xp, counts, gain=gain)
        if line:
            sys.stdout.write(line)
    except Exception:
        pass
    return 0


def cmd_compose(args):
    """Merge caller-supplied statusline text with the creature as a left column."""
    left = args[0] if args else ""
    try:
        raw = _stdin_text()
        # the statusline passes its text as an argument and its json on stdin.
        # piping the text instead still works, it just has no session to count.
        session = _session_id(raw) if args else None
        if not args:
            left = raw.rstrip("\n")
        st = _load()
        # hidden means the caller's bar passes through untouched, xp still banks on the next visible run
        if st["settings"].get("hidden"):
            sys.stdout.write(left)
            return 0
        xp, counts, gain = _bank(st, session)
        sys.stdout.write(render.compose(st, left, xp, counts, gain=gain))
    except Exception:
        sys.stdout.write(left)
    return 0


def cmd_refresh(args):
    # measure before taking the snapshot that gets written back. the scan takes
    # as long as the vault is big, and a roster held across it would revert any
    # egg laid or hatched meanwhile
    xp, counts = state_mod.measure_now(state_mod.load()["settings"])
    state_mod.write_cache(xp, counts)
    st = _load()
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
    """Open the egg. Reveals whatever level it banked its way to.

    `--from-zero` opens it at level 0 instead, baselining whatever is already
    written so only notes from here on count.
    """
    st = _load()
    c = state_mod.focused(st)
    if c is None:
        print("no egg to open. /brainbuddy-new lays one.")
        return 1
    if state_mod.is_hatched(c):
        lvl = metric.level_for(c["xp_banked"], st["settings"]["xp_max"])
        print("%s is already out, Lv%d. /brainbuddy shows it." % (c["name"], lvl))
        return 1

    if "--name" in args:
        i = args.index("--name")
        chosen = args[i + 1].strip() if i + 1 < len(args) and not args[i + 1].startswith("-") else ""
        if not chosen:
            print("--name takes the name. try: hatch --name Zephyr")
            return 1
        c["name"] = chosen[:24]

    # measure instead of reading the cache: the guided flow can set the provider
    # seconds earlier, and a cached count would score the source it replaced
    xp, counts = state_mod.measure_now(st["settings"])
    state_mod.write_cache(xp, counts)

    from_zero = "--from-zero" in args
    if from_zero:
        # park the high-water mark at everything already written, so none of it
        # gets credited and the next note is the first thing that counts
        st["high_water_xp"] = xp
        c["xp_banked"] = 0
    else:
        state_mod.sync(st, xp)
    state_mod.reveal(st)
    state_mod.save(st)
    # a zero here means there was nothing to count, not that the egg was empty.
    # --from-zero lands on Lv0 too, but that one was chosen and says so itself
    empty = not from_zero and not xp
    print(render.hatch_ceremony(st, c))
    # art=False: the ceremony just showed the sprite and the name. showing the
    # identical creature again ten lines later dilutes the one reveal it gets
    print(render.card(st, xp=0 if from_zero else xp, counts=counts, hungry_note=not empty, art=False))
    if from_zero:
        # the stats still read the live vault, so say why the level doesn't
        print("\n  %d xp of existing notes baselined. new ones count from here." % xp)
    elif empty:
        print("\n" + render.empty_hatch_note(st, state_mod.source_status(st["settings"])))
    return 0


def cmd_names(args):
    """Two fresh name ideas. Random on purpose: the egg's own seed already has a
    fallback name, and drawing from it here would make every suggestion the same."""
    import uuid

    for _ in range(2):
        print(creature_mod.suggest_name(uuid.uuid4().hex))
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
        try:
            value = int(raw)
        except ValueError:
            print("xp_max takes a number, not %r. try: config xp_max 1500" % raw)
            return 1
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
    elif key == "provider":
        if raw not in metric.PROVIDERS:
            print("provider must be one of: %s" % ", ".join(metric.PROVIDERS))
            return 1
        value = raw
    elif key == "vault_root":
        # a relative path would resolve against whatever directory the statusline
        # happens to run in, so it reads as a missing root from anywhere else
        value = raw if raw.startswith("~") else os.path.abspath(os.path.expanduser(raw))
        if not os.path.isdir(os.path.expanduser(value)):
            print("warning: that folder isn't there yet, so nothing will be counted")
    elif key == "weights":
        # a bare string here used to reach metric.measure and crash every read
        print("weights isn't settable from the CLI, edit state.json")
        return 1
    elif key == "sprite_height":
        try:
            value = 3 if int(raw) <= 3 else 5
        except ValueError:
            print("sprite_height takes a number, not %r. it's 3 or 5" % raw)
            return 1
    elif key == "columns":
        try:
            value = int(raw)
        except ValueError:
            print("columns takes a number, not %r. try: config columns 40" % raw)
            return 1
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
    try:
        xp = int(args[0])
    except ValueError:
        print("simulate takes an xp number, not %r. try: simulate 300" % args[0])
        return 1
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


PROVIDER_LABEL = {
    "claude": "stock Claude Code memory",
    "vault": "vault layout",
    "folder": "folder of notes",
}

SHIM = "~/.claude/brainbuddy/statusline-brainbuddy.sh"
USER_SETTINGS = os.path.expanduser("~/.claude/settings.json")


def _statusline_command(path):
    """statusLine.command out of a settings file, or "". Reads, never writes."""
    try:
        with open(path, "r") as f:
            return (json.load(f).get("statusLine") or {}).get("command") or ""
    except (OSError, ValueError, AttributeError):
        return ""


def _project_settings():
    """The .claude/settings.json this directory would actually use, or None.

    The working directory first, then the repo root, because a statusline set at
    the root applies to every directory under it and doctor is usually run from
    somewhere deeper.
    """
    # realpath both sides: /tmp and /home are symlinks on plenty of machines, so
    # comparing what getcwd returns against what ~ expands to misses otherwise
    here = os.path.realpath(os.getcwd())
    home = os.path.realpath(os.path.expanduser("~"))
    candidates, d = [here], here
    while d != home:
        if os.path.isdir(os.path.join(d, ".git")):
            candidates.append(d)
            break
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    for c in candidates:
        path = os.path.join(c, ".claude", "settings.json")
        # a repo checked out at $HOME would otherwise report the user's own file
        # as a project overriding itself
        if os.path.isfile(path) and os.path.realpath(path) != os.path.realpath(USER_SETTINGS):
            return path
    return None


def _project_override():
    """Named when a project's own statusline is what runs here. None otherwise.

    The installer only ever touches ~/.claude/settings.json. A project that sets
    statusLine wins inside that project, so the install is correct, the creature
    is nowhere, and nothing on either side says why.
    """
    if "statusline-brainbuddy.sh" not in _statusline_command(USER_SETTINGS):
        return None
    path = _project_settings()
    if path is None:
        return None
    command = _statusline_command(path)
    if not command or "statusline-brainbuddy.sh" in command:
        return None
    home = os.path.realpath(os.path.expanduser("~"))
    shown = "~" + path[len(home):] if path.startswith(home) else path
    return "\n".join([
        "this project sets its own statusline in %s, so that one runs here and your buddy doesn't." % shown,
        "the installer only wires ~/.claude/settings.json, and a project's own file wins inside the project.",
        "",
        "wrap theirs, then point the project at the shim:",
        '  ./install.sh --statusline "%s"' % command,
        '  then in that file: "statusLine": { "type": "command", "command": "%s" }' % SHIM,
    ])


def cmd_doctor(args):
    """Report what we can see. Counts only, never a path (R12)."""
    st = _load()
    settings = st["settings"]
    status = state_mod.source_status(settings)
    xp, counts = status["xp"], status["counts"]
    print("brainbuddy %s" % __version__)
    print("provider: %s (%s)" % (settings["provider"], PROVIDER_LABEL.get(settings["provider"], "unknown")))
    # the root the user typed, home-relative. R12 covers the memory files we match,
    # and "why is it zero" can't be answered without this
    root = state_mod.sources_for(settings)[0]
    home = os.path.expanduser("~")
    if root.startswith(home):
        root = "~" + root[len(home):]
    print("root: %s (%s)" % (root, "missing" if status["state"] == "missing_root" else "found"))
    for k in sorted(counts):
        print("  %-10s %d" % (k, counts[k]))
    p = metric.progress(xp, settings["xp_max"])
    # the buddy's banked line below is the real level; this one is what the
    # source would feed a fresh egg, and on a broken root they diverge
    print("source xp %d -> level %d (what a new egg would bank)" % (xp, p["level"]))
    # the two diverge whenever a creature was hatched --from-zero, so one line
    # claiming to be both would be wrong for anyone who chose that
    c = state_mod.focused(st)
    if c is not None:
        banked = c.get("xp_banked", 0)
        bp = metric.progress(banked, settings["xp_max"])
        stage = bp["stage"] if state_mod.is_hatched(c) else "egg"
        print("%s banked %d -> level %d (%s)" % (c["name"], banked, bp["level"], stage))
    override = _project_override()
    if override:
        print("\n" + override)
    help_text = render.no_source_help(settings, status)
    if help_text:
        print("\n" + help_text)
    if "--check" in args:
        print("\n" + _version_check())
    return 0


def _version_check():
    # imported here, not at the top: this is the one path allowed a socket, and
    # keeping the import inside it is what proves the rest never gets one
    from . import release

    return release.check()


def cmd_update(args):
    """Ask pypi whether there's a newer brainbuddy. One request, then done."""
    print(_version_check())
    return 0


def cmd_sources(args):
    """What it can count, and what to do when that's nothing.

    The installer calls this so a fresh install on a machine with no memory
    system says so on the spot, instead of leaving a level-0 egg and no reason.
    """
    st = _load()
    status = state_mod.source_status(st["settings"])
    help_text = render.no_source_help(st["settings"], status)
    if help_text:
        print(help_text)
        # nonzero so the installer can branch on the exit code. it used to match
        # on the first word of the success line, which reworded copy would break
        return 1
    print("counting %d xp of memory. /brainbuddy shows your buddy." % status["xp"])
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
    "new": cmd_new, "hatch": cmd_hatch, "names": cmd_names, "focus": cmd_focus, "list": cmd_list,
    "rename": cmd_rename, "retire": cmd_retire, "config": cmd_config,
    "simulate": cmd_simulate, "doctor": cmd_doctor, "sources": cmd_sources,
    "hide": cmd_hide, "show": cmd_show, "update": cmd_update,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    fn = COMMANDS.get(argv[0])
    if fn is None:
        # the full usage after a typo is a wall. one guess or one pointer
        import difflib
        close = difflib.get_close_matches(argv[0], COMMANDS, n=1)
        hint = "did you mean %s?" % close[0] if close else "brainbuddy -h lists what there is"
        print("unknown command %s. %s" % (argv[0], hint))
        return 1
    return fn(argv[1:])


if __name__ == "__main__":
    sys.exit(main())
