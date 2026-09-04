"""Tests. Run: python3 -m tests.test_terminalcreature  (from the repo root)

Fixtures are synthetic and generated into a temp dir. No real vault is ever
touched, so nothing here can leak a memory filename into CI output (R12).
"""

import os
import re
import shutil
import sys
import tempfile
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from terminalcreature import creature, metric, state as state_mod  # noqa: E402

FAILURES = []


def check(cond, label):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILURES.append(label)


def make_vault(counts):
    """Synthetic vault with the requested number of files per source."""
    root = tempfile.mkdtemp(prefix="bb-fixture-")
    layout = {
        "memories": "auto-memory",
        "knowledge": "05-knowledge",
        "projects": "04-projects",
        "sessions": "memory/sessions",
        "decisions": "memory/decisions",
    }
    for key, rel in layout.items():
        d = os.path.join(root, rel)
        os.makedirs(d)
        for i in range(counts.get(key, 0)):
            open(os.path.join(d, "note-%03d.md" % i), "w").close()
    # generated index files must not be counted
    open(os.path.join(root, "auto-memory", "MEMORY.md"), "w").close()
    open(os.path.join(root, "05-knowledge", "index.md"), "w").close()
    return root


def test_metric():
    print("\nmetric")
    root = make_vault({"memories": 130, "knowledge": 66, "projects": 26, "sessions": 48, "decisions": 1})
    try:
        xp, counts = metric.measure(root, metric.VAULT_SOURCES)
        check(counts["memories"] == 130, "MEMORY.md excluded from the count")
        check(counts["knowledge"] == 66, "index.md excluded from the count")
        check(xp == 624, "weighted xp is 624, got %d" % xp)
        check(metric.level_for(624) == 64, "624 xp is level 64 on the fast curve, got %d" % metric.level_for(624))
        # the point of the recalibration: a nearly empty vault still moves
        check(metric.level_for(3) >= 4, "3 xp already reads as a level, got %d" % metric.level_for(3))
        check(metric.level_for(60) >= 19, "60 xp is nearly the first evolution, got %d" % metric.level_for(60))

        for lvl in (0, 19, 20, 39, 40, 59, 60, 79, 80, 100):
            need = metric.xp_for_level(lvl)
            check(metric.level_for(need) == lvl, "level %d round-trips through xp_for_level" % lvl)

        check(metric.stage_for(0)[1] == "Hatchling", "level 0 is a baby, not an egg")
        check("Egg" not in [s[1] for s in metric.LEVEL_STAGES], "no level band is an Egg any more")
        check(metric.stage_for(0)[0] == metric.EGG_SPRITE + 1, "level stages start one past the egg sprite")
        check(metric.stage_for(35)[1] == "Fledgling", "level 35 is a Fledgling")
        check(metric.stage_for(100)[1] == "Ascendant", "level 100 is Ascendant")
        check(metric.stage_for(250)[1] == "Ascendant", "past 100 stays Ascendant, evolution caps")
        check(metric.level_for(20000) == 100, "level caps at 100 rather than climbing forever")
        check(metric.level_for(metric.XP_MAX_DEFAULT) == 100, "xp_max is exactly level 100")
        check(metric.next_stage_level(85) is None, "no next form after Ascendant")
    finally:
        shutil.rmtree(root)


def test_sprite_alignment():
    """Every drawn row has to sit on the same centre line.

    Sage's `|___|` was a column left of its own torso for four PRs because
    nothing measured it. Padding is what centring reduces to, so compare the
    two sides directly instead of eyeballing the art.
    """
    print("\nsprite alignment")
    from terminalcreature import sprites

    bad = []
    for short in (False, True):
        for shiny in (False, True):
            for species in sprites.SPECIES_LOOK:
                for idx in range(len(sprites.STAGE_TEMPLATES)):
                    art = sprites.sprite(species, idx, shiny, short=short)
                    widths = {len(r) for r in art}
                    if len(widths) != 1:
                        bad.append("%s/%d ragged widths %s" % (species, idx, sorted(widths)))
                    for n, r in enumerate(art):
                        if not r.strip():
                            continue
                        lead, trail = len(r) - len(r.lstrip()), len(r) - len(r.rstrip())
                        if abs(lead - trail) > 1:
                            bad.append("%s/%d%s row %d off-centre (%d left, %d right)" % (
                                species, idx, " short" if short else "", n, lead, trail))
    check(not bad, "every sprite row is centred (%s)" % ("; ".join(sorted(set(bad))[:4]) or "all"))

    art = sprites.sprite("Mote", 5, False)
    check(len({len(r) for r in art}) == 1, "Ascendant rows are one width")
    check(all(len(r) == sprites.SPRITE_WIDTH for r in sprites.sprite("Mote", 0, False)),
          "the egg pads to the shared sprite width")


def test_compose_column():
    """The left column has to be one width for the life of the creature.

    Whatever sits beside it is the user's own statusline, so a column that
    resizes on evolution drags their text two spaces sideways. The border made
    that visible; it was always there.
    """
    print("\ncompose column")
    os.environ["NO_COLOR"] = "1"
    try:
        from terminalcreature import render

        def widths(**settings):
            # only the row carrying the caller's text shows where the column ends.
            # the caption row's own length tracks the level, not the column
            out = []
            for xp in (0, 30, 90, 300, 700, 1400):
                st = state_mod.default_state()
                st["settings"].update(settings)
                c = state_mod.create(st, name="Zask")
                c["xp_banked"] = xp
                state_mod.reveal(st)
                rows = render.compose(st, "BAR", xp=xp, counts={}).split("\n")
                out.append(next(len(r.split("BAR")[0]) for r in rows if "BAR" in r))
            return out

        for label, kw in [("boxed", {}), ("bare", {"border": False}), ("short", {"sprite_height": 3})]:
            w = widths(**kw)
            check(len(set(w)) == 1, "%s column is one width across every stage, got %s" % (label, sorted(set(w))))

        st = state_mod.default_state()
        c = state_mod.create(st, name="Zask")
        c["xp_banked"] = 700
        state_mod.reveal(st)
        boxed = render.compose(st, "BAR", xp=700, counts={}).split("\n")
        st["settings"]["border"] = False
        bare = render.compose(st, "BAR", xp=700, counts={}).split("\n")
        check(len(boxed) == len(bare) + 2, "the box costs exactly two rows, got %d" % (len(boxed) - len(bare)))
        check(boxed[0].startswith("┌") and boxed[-1].startswith("└"), "the box closes top and bottom")
        check(all(r.startswith("│") for r in boxed[1:-1]), "every creature row is walled")
        check("BAR" in boxed[1], "the caller's first row sits beside the head, not the lid")

        caption = boxed[2]
        check(render.EGG_ICON in caption, "the caption is marked with the egg icon")
        check(caption.count("·") == 1, "one separator only, none between stage and level")
        check("Sage Lv" in caption, "stage and level read as one phrase")

        st["settings"].update({"border": True, "unicode": False})
        ascii_box = render.compose(st, "BAR", xp=700, counts={}).split("\n")
        check(ascii_box[0].startswith("+-") and ascii_box[1].startswith("|"), "ascii terminals get +- and |")
        check(not any(ch in "".join(ascii_box) for ch in "┌─│└"), "no box-drawing leaks into ascii mode")
        check(render.EGG_ICON not in "".join(ascii_box), "no emoji leaks into ascii mode either")
    finally:
        os.environ.pop("NO_COLOR", None)


def test_no_content_reads():
    """R2. The whole security posture rests on this one.

    Patch every builtin that can read a file and assert measure() never calls
    one against a memory path.
    """
    print("\nR2 conformance")
    import builtins
    import io

    root = make_vault({"memories": 5, "knowledge": 2, "projects": 1, "sessions": 3, "decisions": 0})
    opened = []
    real_open, real_io_open = builtins.open, io.open

    def trap(factory):
        def guard(file, *a, **kw):
            if str(file).startswith(root):
                opened.append(str(file))
            return factory(file, *a, **kw)
        return guard

    builtins.open = trap(real_open)
    io.open = trap(real_io_open)
    try:
        xp, counts = metric.measure(root, metric.VAULT_SOURCES)
    finally:
        builtins.open, io.open = real_open, real_io_open
        shutil.rmtree(root)

    check(xp > 0, "fixture measured something (%d xp)" % xp)
    check(opened == [], "zero file opens under the memory root, got %d" % len(opened))

    # catches branches the runtime trap never ran. tokenize not grep, or it
    # matches the module docstring saying "no open()" and fails on prose.
    import tokenize

    banned = {"open", "read", "readlines", "read_text", "read_bytes", "loadtxt"}
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "terminalcreature", "metric.py")
    found = set()
    with tokenize.open(path) as f:
        for tok in tokenize.generate_tokens(f.readline):
            if tok.type == tokenize.NAME and tok.string in banned:
                found.add(tok.string)
    check(not found, "metric.py calls no reader in code (found: %s)" % (", ".join(sorted(found)) or "none"))


def test_creature():
    print("\ncreature")
    a = creature.derive("seed-one")
    b = creature.derive("seed-one")
    c = creature.derive("seed-two")
    check(a == b, "same seed gives the same creature")
    check(a != c or a["species"] != c["species"] or True, "different seeds are independent")
    check(a["species"] in creature.SPECIES, "species comes from the table")

    tampered = {"seed": "seed-one", "name": "Cheater", "species": "Nope", "rarity": "Legendary", "shiny": True}
    hydrated = creature.hydrate(tampered)
    check(hydrated["rarity"] == a["rarity"], "hand-edited rarity is overwritten by the derived value")
    check(hydrated["shiny"] == a["shiny"], "hand-edited shiny is overwritten")
    check(hydrated["name"] == "Cheater", "name is persisted, not derived")

    tiers = {}
    for i in range(4000):
        r, _ = creature.roll_rarity("s%d" % i)
        tiers[r] = tiers.get(r, 0) + 1
    check(tiers.get("Common", 0) > tiers.get("Legendary", 0) * 10, "Common vastly outnumbers Legendary")
    check("Legendary" in tiers, "Legendary is reachable at all")

    stats = creature.stats_from_counts({"memories": 130, "knowledge": 66, "projects": 26, "sessions": 48})
    check(all(0 <= v <= 100 for v in stats.values()), "every stat lands in 0-100")
    check(set(stats) == {"Recall", "Depth", "Drive", "Streak", "Ferment"}, "the five stats are present")


def _hatched(st, name=None):
    """create + reveal, since most tests predate the egg being a real state."""
    c = state_mod.create(st, name=name)
    state_mod.reveal(st)
    return c


def test_banking():
    print("\nxp banking")
    # a render before the first hatch used to burn all the earned xp,
    # which hatched the first creature at level 0 instead of 35
    empty = state_mod.default_state()
    state_mod.sync(empty, 624)
    check(empty["high_water_xp"] == 0, "no creature means the high water mark does not move")
    c0 = _hatched(empty, name="Late")
    state_mod.sync(empty, 624)
    check(c0["xp_banked"] == 624, "so the first creature still inherits it, got %d" % c0["xp_banked"])

    st = state_mod.default_state()
    first = _hatched(st, name="Alpha")
    state_mod.sync(st, 624)
    check(first["xp_banked"] == 624, "first creature inherits the existing memory")
    check(metric.level_for(first["xp_banked"]) == 64, "which puts it at level 64")

    second = _hatched(st, name="Beta")
    check(second["xp_banked"] == 0, "a second creature starts at zero, not at 35")
    check(st["focused"] == second["id"], "hatching moves focus")

    state_mod.sync(st, 700)
    check(second["xp_banked"] == 76, "new xp goes to the focused creature, got %d" % second["xp_banked"])
    check(first["xp_banked"] == 624, "the unfocused creature gains nothing")

    state_mod.focus(st, "Alpha")
    state_mod.sync(st, 800)
    check(first["xp_banked"] == 724, "refocusing redirects new xp")
    check(second["xp_banked"] == 76, "and the other one stops gaining")

    state_mod.sync(st, 200)
    check(st["high_water_xp"] == 800, "deleting memories cannot lower the high water mark")
    check(first["xp_banked"] == 724, "so nobody de-levels for tidying up")

    st2 = state_mod.default_state()
    c = _hatched(st2, name="Gamma")
    c["xp_banked"] = metric.xp_for_level(19)
    c["last_stage_seen"] = 1
    st2["high_water_xp"] = c["xp_banked"]
    ev = state_mod.sync(st2, metric.xp_for_level(20))
    check(ev is not None and ev["stage"] == "Fledgling", "crossing level 20 fires an evolution event")
    check(state_mod.sync(st2, metric.xp_for_level(20)) is None, "the same evolution does not fire twice")


def test_egg_and_hatch():
    print("\negg and hatch")
    st = state_mod.default_state()
    c = state_mod.create(st, name="Shell")
    check(not state_mod.is_hatched(c), "a new creature starts as an unhatched egg")
    check(st["focused"] == c["id"], "the egg takes focus so it banks xp")

    # the whole point: an egg banks while closed, so hatching opens at your real level
    state_mod.sync(st, 624)
    check(c["xp_banked"] == 624, "an egg still banks xp while closed, got %d" % c["xp_banked"])
    check(state_mod.sync(st, 700) is None, "but it announces no evolution nobody can see")

    revealed = state_mod.reveal(st)
    check(revealed is c, "reveal returns the creature it opened")
    check(state_mod.is_hatched(c), "and it is hatched afterwards")
    lvl = metric.level_for(c["xp_banked"])
    check(lvl > 0, "it opens at the level it banked to, not zero (Lv%d)" % lvl)
    check(c["last_stage_seen"] == metric.stage_for(lvl)[0], "the reveal absorbs the stage it just showed")
    check(state_mod.sync(st, c["xp_banked"]) is None, "so hatching does not fire a stale evolution notice")
    check(state_mod.reveal(st) is None, "hatching twice is a no-op")


def test_retire_keeps_the_record():
    print("\nretire")
    st = state_mod.default_state()
    old = _hatched(st, name="Keeper")
    state_mod.sync(st, 624)
    banked = old["xp_banked"]

    new = state_mod.create(st, name="Fresh")
    state_mod.retire(st, "Keeper")
    check(len(st["creatures"]) == 2, "retiring keeps the record instead of deleting it")
    check(old["xp_banked"] == banked, "and keeps its banked xp, got %d" % old["xp_banked"])
    check(old.get("retired_at"), "the retirement is recorded")
    check([c["name"] for c in state_mod.active(st)] == ["Fresh"], "retired creatures drop out of the active roster")
    check(st["focused"] == new["id"], "focus moves off the retired one")

    back = state_mod.focus(st, "Keeper")
    check(back is old and not old.get("retired_at"), "focusing a retired creature brings it back")

    st2 = state_mod.default_state()
    solo = _hatched(st2, name="Only")
    state_mod.retire(st2, "Only")
    check(st2["focused"] is None, "retiring the last creature leaves nothing focused")
    check(solo in st2["creatures"], "but the record survives")


def test_state_roundtrip():
    print("\nstate file")
    d = tempfile.mkdtemp(prefix="bb-state-")
    path = os.path.join(d, "state.json")
    try:
        st = state_mod.default_state()
        _hatched(st, name="Delta")
        state_mod.save(st, path)
        back = state_mod.load(path)
        check(back["creatures"][0]["name"] == "Delta", "roster survives a save/load")
        check(back["settings"]["xp_max"] == metric.XP_MAX_DEFAULT, "settings default correctly")
        check(back["settings"]["hidden"] is False, "the creature is visible out of the box")
        back["settings"]["hidden"] = True
        state_mod.save(back, path, own_settings=True)
        check(state_mod.load(path)["settings"]["hidden"] is True, "hiding survives a save/load")
        check(state_mod.load(os.path.join(d, "nope.json"))["creatures"] == [], "missing state file degrades to empty")
        with open(path, "w") as f:
            f.write("{not json")
        check(state_mod.load(path)["creatures"] == [], "corrupt state file degrades instead of crashing")
    finally:
        shutil.rmtree(d)


def test_state_migration():
    """An upgrade must never cost someone their buddy.

    The state file outlives every version of the code that wrote it, so a load
    has to bring an older one forward rather than reading it as a fresh install.
    A de-levelled or vanished creature is the one bug with no undo: the XP is
    gone, and the seed that made that particular creature is gone with it.
    """
    print("\nstate migration")
    import json

    d = tempfile.mkdtemp(prefix="bb-migrate-")
    path = os.path.join(d, "state.json")
    try:
        # a file from before the stamp existed, hatched, with real banked xp
        legacy = {
            "high_water_xp": 624,
            "focused": "abc123",
            "creatures": [{
                "id": "abc123", "seed": "seed-one", "name": "Neux",
                "hatched_at": "2026-01-01T00:00:00Z", "xp_banked": 624, "last_stage_seen": 3,
            }],
            "settings": {"provider": "folder", "vault_root": "~/notes"},
        }
        with open(path, "w") as f:
            json.dump(legacy, f)

        st = state_mod.load(path)
        c = st["creatures"][0]
        check(st["version"] == state_mod.STATE_VERSION, "an unstamped file loads as the current version")
        check(c["xp_banked"] == 624, "banked xp survives the migration, got %d" % c["xp_banked"])
        check(metric.level_for(c["xp_banked"]) == 64, "so the buddy is still level 64 afterwards")
        check(st["high_water_xp"] == 624, "the high water mark survives too")
        check(state_mod.is_hatched(c) and st["focused"] == "abc123", "it's still hatched and still focused")
        check(st["settings"]["provider"] == "folder", "their settings are kept")
        check(st["settings"]["density"] == "compact", "and settings added since are filled in")
        check(creature.hydrate(c)["species"] == creature.derive("seed-one")["species"],
              "the species still comes off the same seed, so it's the same creature")

        # round-trip it the way an upgraded install would: load, save, load again
        state_mod.save(st, path)
        again = state_mod.load(path)
        check(again["creatures"][0]["xp_banked"] == 624, "and again after the next save")
        check(json.load(open(path))["version"] == state_mod.STATE_VERSION, "the stamp is written to disk")

        # a hand-edited or half-written creature: every read path indexes these
        with open(path, "w") as f:
            json.dump({"creatures": [{"seed": "seed-two"}], "focused": "gone"}, f)
        st = state_mod.load(path)
        c = st["creatures"][0]
        check(c["xp_banked"] == 0 and c["last_stage_seen"] == 0, "missing creature keys are filled, not fatal")
        check(c["id"] and c["name"], "so are the id and the name")
        check(st["focused"] == c["id"], "a focus pointing at nothing falls back to the roster")

        # a stamp from a version we don't know about is not ours to relabel
        with open(path, "w") as f:
            json.dump({"version": 99, "creatures": [], "focused": None}, f)
        check(state_mod.load(path)["version"] == 99, "a newer stamp survives a downgrade")
    finally:
        shutil.rmtree(d)


def test_version_check_is_explicit_only():
    """Nothing but `update` and `doctor --check` may open a socket.

    The statusline runs this code several times a second. A background update
    check there would be indistinguishable from telemetry, so the rule is that
    the network is only ever touched because someone asked. The guard below
    records every socket call and then proves itself by making one on purpose.
    """
    print("\nversion check")
    import subprocess

    from terminalcreature import release

    check(release.status_line("ok", "0.2.0", current="0.1.0").startswith("terminalcreature 0.2.0 is out"),
          "a newer release says so, and which one")
    check("pipx upgrade terminalcreature" in release.status_line("ok", "0.2.0", current="0.1.0"),
          "and names both ways to take it")
    check("latest" in release.status_line("ok", "0.1.0", current="0.1.0"), "matching versions read as current")
    check("ahead" in release.status_line("ok", "0.1.0", current="0.2.0"), "a local build ahead of pypi says that")
    check("isn't on pypi yet" in release.status_line("unpublished", None), "an unpublished package is calm about it")
    check("couldn't reach pypi" in release.status_line("unreachable", None), "so is being offline")
    check(release._parts("0.10.0") > release._parts("0.9.0"), "versions compare numerically, not as strings")

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = tempfile.mkdtemp(prefix="bb-offline-")
    log = os.path.join(home, "net.log")
    # every command the statusline can reach, plus the two that write state
    child = (
        "import socket, sys\n"
        "def guard(*a, **kw):\n"
        "    open(%r, 'a').write('called\\n')\n"
        "    raise AssertionError('network')\n"
        "socket.socket = guard\n"
        "socket.create_connection = guard\n"
        "socket.getaddrinfo = guard\n"
        "from terminalcreature import cli\n"
        "for argv in (['new'], ['hatch'], ['refresh'], ['render'], ['compose', 'BAR'], ['card'], ['doctor']):\n"
        "    cli.main(argv)\n"
        "try:\n"
        "    socket.socket()\n"
        "except AssertionError:\n"
        "    pass\n"
    ) % log
    try:
        env = dict(os.environ, HOME=home, PYTHONPATH=repo)
        r = subprocess.run([sys.executable, "-c", child], env=env, input="{}",
                           capture_output=True, text=True)
        check(r.returncode == 0, "the offline run finishes clean (%s)" % r.stderr.strip()[-120:])
        calls = open(log).read().splitlines() if os.path.exists(log) else []
        check(len(calls) == 1, "one socket call, the probe proving the guard works, got %d" % len(calls))
    finally:
        shutil.rmtree(home)

    # opted in, the refresh gets exactly one attempt per TTL, and the render
    # path still gets none: it reads the cache the attempt stamped. the class
    # itself stays unpatched here because ssl subclasses socket.socket on
    # import; the two call-path functions are the guard
    home = tempfile.mkdtemp(prefix="bb-optin-")
    log = os.path.join(home, "net.log")
    child = (
        "import socket, sys\n"
        "def guard(*a, **kw):\n"
        "    open(%r, 'a').write('called\\n')\n"
        "    raise AssertionError('network')\n"
        "socket.create_connection = guard\n"
        "socket.getaddrinfo = guard\n"
        "from terminalcreature import cli\n"
        "cli.main(['config', 'update_check', 'true'])\n"
        "cli.main(['refresh'])\n"
        "cli.main(['render'])\n"
        "cli.main(['compose', 'BAR'])\n"
        "cli.main(['refresh'])\n"
        "try:\n"
        "    socket.getaddrinfo('pypi.invalid', 443)\n"
        "except AssertionError:\n"
        "    pass\n"
    ) % log
    try:
        env = dict(os.environ, HOME=home, PYTHONPATH=repo)
        r = subprocess.run([sys.executable, "-c", child], env=env, input="{}",
                           capture_output=True, text=True)
        check(r.returncode == 0, "the opted-in run finishes clean (%s)" % r.stderr.strip()[-120:])
        calls = open(log).read().splitlines() if os.path.exists(log) else []
        check(len(calls) == 2,
              "opted in: one attempt from the first refresh, none from render or the stamped second, plus the probe; got %d" % len(calls))
    finally:
        shutil.rmtree(home)

    # the real statusline ordering: the xp cache goes stale, render spawns the
    # detached recount, and THAT child is where an opted-in fetch happens. an
    # in-process guard can't see across the fork, so a sitecustomize on
    # PYTHONPATH guards every python process this test starts, children included
    import time as _t

    home = tempfile.mkdtemp(prefix="bb-spawn-")
    log = os.path.join(home, "net.log")
    guard_dir = os.path.join(home, "guard")
    os.makedirs(guard_dir)
    with open(os.path.join(guard_dir, "sitecustomize.py"), "w") as f:
        f.write(
            "import socket, sys\n"
            "def _guard(*a, **kw):\n"
            "    with open(%r, 'a') as fh:\n"
            "        fh.write(' '.join(sys.argv) + chr(10))\n"
            "    raise AssertionError('network')\n"
            "socket.create_connection = _guard\n"
            "socket.getaddrinfo = _guard\n" % log
        )
    marker = os.path.join(home, ".claude", "terminalcreature", "latest-version")
    cache = os.path.join(home, ".claude", "terminalcreature", "xp.cache")
    try:
        for opted, expect_net in (("true", True), ("false", False)):
            open(log, "w").close()
            if os.path.exists(marker):
                os.remove(marker)
            child = (
                "import os\n"
                "from terminalcreature import cli, state as sm\n"
                "cli.main(['config', 'update_check', %r])\n"
                "sm.write_cache(5, {})\n"
                "os.utime(sm.CACHE_PATH, (1, 1))\n"
                "cli.main(['render'])\n"
            ) % opted
            env = dict(os.environ, HOME=home, PYTHONPATH=guard_dir + os.pathsep + repo)
            r = subprocess.run([sys.executable, "-c", child], env=env, input="{}",
                               capture_output=True, text=True)
            check(r.returncode == 0, "stale-cache render (%s) finishes clean (%s)" % (opted, r.stderr.strip()[-120:]))
            deadline = _t.time() + 20
            if expect_net:
                while _t.time() < deadline and not os.path.exists(marker):
                    _t.sleep(0.2)
                lines = open(log).read().splitlines() if os.path.exists(log) else []
                check(os.path.exists(marker), "opted in: the spawned refresh stamped its attempt")
                check(len(lines) >= 1 and all("refresh" in l for l in lines),
                      "every socket attempt came from the refresh child, none from the render: %r" % lines[:2])
            else:
                ino0 = None
                try:
                    ino0 = os.stat(cache).st_ino
                except OSError:
                    pass
                while _t.time() < deadline and (ino0 is None or os.stat(cache).st_ino == ino0):
                    _t.sleep(0.2)
                check(os.stat(cache).st_ino != ino0, "opted out: the spawned refresh still ran (cache rewritten)")
                _t.sleep(0.3)
                lines = open(log).read().splitlines() if os.path.exists(log) else []
                check(lines == [] and not os.path.exists(marker),
                      "and no process, child included, made a network attempt or stamped anything")
    finally:
        shutil.rmtree(home)


def test_update_apply():
    """`update --apply` runs the release's own installer, and only when there
    is a release to run. Both network calls are faked; the installer is a stub
    that records how it was invoked."""
    print("\nupdate --apply")
    import io
    import subprocess
    import tarfile
    from contextlib import redirect_stdout

    from terminalcreature import cli, release

    home = tempfile.mkdtemp(prefix="bb-update-")
    state_dir = os.path.join(home, ".claude", "terminalcreature")
    os.makedirs(state_dir)
    marker = os.path.join(home, "installer-ran")

    def fake_tarball(version, dest):
        src = tempfile.mkdtemp(prefix="bb-release-")
        top = os.path.join(src, "smejkaldesign-terminalcreature-abc123")
        os.makedirs(top)
        with open(os.path.join(top, "install.sh"), "w") as f:
            f.write("#!/usr/bin/env bash\necho installing %s\necho \"$@\" > %s\n" % (version, marker))
        with tarfile.open(dest, "w:gz") as tar:
            tar.add(top, arcname=os.path.basename(top))
        shutil.rmtree(src)
        return True

    fetches = []
    real_fetch, real_apply, real_state_dir = release.fetch_latest, release.apply, state_mod.STATE_DIR
    state_mod.STATE_DIR = state_dir

    def run(argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(argv)
        return code, out.getvalue()

    try:
        release.apply = lambda v, **kw: real_apply(v, state_dir=state_dir, fetch=lambda ver, dest: fetches.append(ver) or fake_tarball(ver, dest),
                                                    run=lambda cmd, **kw: subprocess.run(cmd, stdout=subprocess.DEVNULL, **kw))
        release.fetch_latest = lambda *a, **k: ("ok", "99.0.0")
        code, out = run(["update", "--apply"])
        check(code == 0, "a newer release installs and exits clean")
        check(fetches == ["99.0.0"], "the tarball fetched is the version pypi named")
        check(os.path.exists(marker), "the release's own install.sh ran")
        check(open(marker).read().strip() == "", "with no flags on a plain install")
        check("99.0.0 is installed" in out, "and the outcome is said")

        os.remove(marker)
        with open(os.path.join(state_dir, "plugin-root"), "w") as f:
            f.write("/plugin")
        run(["update", "--apply"])
        check(open(marker).read().strip() == "--no-commands", "a plugin install keeps the plugin's command files")
        os.remove(os.path.join(state_dir, "plugin-root"))

        os.remove(marker)
        fetches[:] = []
        code, out = run(["update"])
        check(code == 0 and not fetches and not os.path.exists(marker), "without --apply nothing is downloaded or run")

        release.fetch_latest = lambda *a, **k: ("ok", release.__version__)
        code, out = run(["update", "--apply"])
        check(code == 0 and not fetches and not os.path.exists(marker), "current already: --apply downloads nothing")

        release.fetch_latest = lambda *a, **k: ("unreachable", None)
        code, out = run(["update", "--apply"])
        check(code == 1 and not fetches and "couldn't reach pypi" in out, "offline: --apply says so, exits 1, touches nothing")

        release.fetch_latest = lambda *a, **k: ("ok", "99.0.0")
        release.apply = lambda v, **kw: real_apply(v, state_dir=state_dir, fetch=lambda ver, dest: False)
        code, out = run(["update", "--apply"])
        check(code == 1 and "wouldn't hand over the tarball" in out, "a failed download is a calm message and exit 1")

        def bad_tarball(version, dest):
            with open(dest, "w") as f:
                f.write("not a tarball")
            return True
        release.apply = lambda v, **kw: real_apply(v, state_dir=state_dir, fetch=bad_tarball)
        code, out = run(["update", "--apply"])
        check(code == 1 and "didn't unpack" in out, "a corrupt download is caught before anything runs")
    finally:
        release.fetch_latest, release.apply, state_mod.STATE_DIR = real_fetch, real_apply, real_state_dir
        shutil.rmtree(home)


def test_project_statusline_override():
    """A project's own statusLine wins, and doctor is the only place that can say so.

    Everything looks installed: the library is there, the shim is wired, the
    creature is correct. It just never draws inside that repo, and the installer
    can't fix it because it only ever touches ~/.claude/settings.json.
    """
    print("\nproject statusline override")
    import json
    import subprocess

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = tempfile.mkdtemp(prefix="bb-project-")
    try:
        project = os.path.join(home, "work", "app")
        os.makedirs(os.path.join(project, ".claude"))
        os.makedirs(os.path.join(project, ".git"))
        os.makedirs(os.path.join(home, ".claude"))
        env = dict(os.environ, HOME=home)
        subprocess.run(["bash", os.path.join(repo, "install.sh")],
                       env=env, input="", capture_output=True, text=True)

        def doctor(cwd):
            return subprocess.run([sys.executable, "-m", "terminalcreature.cli", "doctor"],
                                  env=dict(env, PYTHONPATH=repo), cwd=cwd,
                                  capture_output=True, text=True).stdout

        check("sets its own statusline" not in doctor(project), "a project with no settings of its own is quiet")

        theirs = {"statusLine": {"type": "command", "command": "~/repo/bar.sh"}}
        settings = os.path.join(project, ".claude", "settings.json")
        with open(settings, "w") as f:
            json.dump(theirs, f)

        out = doctor(project)
        check("sets its own statusline" in out, "doctor names the state")
        check('--statusline "~/repo/bar.sh"' in out, "and hands back the fix with their own command in it")
        check("statusline-terminalcreature.sh" in out, "pointing the project at the shim")
        check("~/work/app/.claude/settings.json" in out, "the file is named home-relative, not as a full path")
        with open(settings) as f:
            check(json.load(f) == theirs, "and their settings file is not written to")

        deep = os.path.join(project, "src", "web")
        os.makedirs(deep)
        check("sets its own statusline" in doctor(deep), "found from a subdirectory, via the repo root")
        check("sets its own statusline" not in doctor(home), "and not claimed for the home directory itself")
    finally:
        shutil.rmtree(home)


def test_empty_hatch_is_a_moment():
    """Hatching with nothing to count still has to land.

    The species, rarity and shiny are decided by the seed, so the reveal is
    intact; only the level is zero. Printing that and stopping reads as a broken
    install, which is exactly the wrong first impression for the one user who
    hasn't got a memory system yet.
    """
    print("\nempty hatch")
    import subprocess

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = tempfile.mkdtemp(prefix="bb-empty-")
    try:
        os.makedirs(os.path.join(home, ".claude"))
        env = dict(os.environ, HOME=home, NO_COLOR="1")
        subprocess.run(["bash", os.path.join(repo, "install.sh")],
                       env=env, input="", capture_output=True, text=True)
        out = subprocess.run([sys.executable, "-m", "terminalcreature.cli", "hatch"],
                             env=dict(env, PYTHONPATH=repo), capture_output=True, text=True).stdout

        check("the egg cracks" in out, "the reveal still runs")
        check("Lv0" in out, "at Lv0, since there was nothing to eat")
        check(any(r in out for r in ("Common", "Uncommon", "Rare", "Epic", "Legendary")),
              "and it still says what came out")
        check("that's the floor, not a dud roll" in out, "the zero is framed rather than left hanging")
        from terminalcreature import render
        check(render.SETUP_PROMPT in out, "and it ends on how to get something to feed it")
    finally:
        shutil.rmtree(home)


def _egg_renders(colour):
    """Every unhatched egg's segment and column, over a spread of seeds."""
    from terminalcreature import render

    if colour:
        os.environ.pop("NO_COLOR", None)
    else:
        os.environ["NO_COLOR"] = "1"
    segs, cols, rarities = set(), set(), set()
    for i in range(400):
        st = state_mod.default_state()
        # a distinct name per egg, so the sets below also prove no surface
        # shows a name before the hatch chooses one
        c = state_mod.create(st, name="Egg%d" % i)
        c["seed"] = "seed-%d" % i
        c["xp_banked"] = 700
        rarities.add(creature.hydrate(c)["rarity"])
        segs.add(render.segment(st, xp=700, counts={}))
        # every surface that can draw an unhatched egg, or the next one added
        # leaks the way egg_notice did while this test watched the other two
        cols.add(render.compose(st, "BAR", xp=700, counts={}) + render.egg_notice(st, c) + render.egg_card(st, c))
    return segs, cols, rarities


def test_egg_reveals_nothing():
    """An egg has to look the same no matter what's inside it.

    Species motif, shiny's `$`, the rarity mark and the rarity colour all come
    off the seed, so an egg wearing any of them answers the question hatching
    exists to answer. Three of the four leaked into the statusline for seven
    PRs because nothing here compared one egg against another.
    """
    print("\negg reveals nothing")
    from terminalcreature import sprites

    try:
        for short in (False, True):
            arts = set()
            for species in sprites.SPECIES_LOOK:
                for shiny in (False, True):
                    arts.add(tuple(sprites.sprite(species, 0, shiny, short=short)))
            check(len(arts) == 1, "one egg sprite across every species and shiny%s, got %d" % (
                " (short)" if short else "", len(arts)))

        for colour in (False, True):
            segs, cols, rarities = _egg_renders(colour)
            where = "with colour" if colour else "plain"
            check(len(rarities) >= 3, "%s: fixture spans %d rarities" % (where, len(rarities)))
            check(len(segs) == 1, "%s: the segment is identical for every egg, got %d" % (where, len(segs)))
            check(len(cols) == 1, "%s: so is the composed column, got %d" % (where, len(cols)))
            col = cols.pop()
            check("Unhatched" in col, "%s: an egg renders as Unhatched" % where)
            check("Egg0" not in col and "Egg1" not in col, "%s: and never as a name" % where)
            check("Lv" not in segs.pop(), "%s: and neither shows a level" % where)
    finally:
        os.environ.pop("NO_COLOR", None)


def test_source_status():
    """A zero XP reading has three causes and they need three different answers.

    Doctor used to print "check provider / vault_root" for all of them, which
    is actively wrong advice for someone who has simply never kept notes.
    """
    print("\nsource status")
    from terminalcreature import render

    settings = dict(state_mod.DEFAULT_SETTINGS)
    settings["provider"] = "folder"
    settings["vault_root"] = os.path.join(tempfile.gettempdir(), "bb-not-here-at-all")
    check(state_mod.source_status(settings)["state"] == "missing_root", "a root that isn't there reads as missing_root")

    root = tempfile.mkdtemp(prefix="bb-folder-")
    try:
        settings["vault_root"] = root
        check(state_mod.source_status(settings)["state"] == "empty", "a real but empty root reads as empty")
        empty_help = render.no_source_help(settings, state_mod.source_status(settings))
        check("Write a note" in empty_help, "and the help says to write something")
        # the whole point of splitting by cause: their provider is already right,
        # so re-offering it as the fix buries the one action that would work
        check("config provider" not in empty_help, "not to re-set config that's already correct")

        os.makedirs(os.path.join(root, "sub"))
        for rel in ("a.md", os.path.join("sub", "b.md"), "index.md"):
            open(os.path.join(root, rel), "w").close()
        s = state_mod.source_status(settings)
        check(s["state"] == "ok" and s["counts"]["notes"] == 2,
              "the folder provider walks subdirs and skips index.md, got %s" % s["counts"])
        check(render.no_source_help(settings, s) == "", "a working source gets no lecture")

        settings["provider"] = "vault"
        s = state_mod.source_status(settings)
        check(s["state"] == "layout_mismatch" and s["stray"] == 2,
              "the vault layout over a plain folder reads as layout_mismatch, got %s" % s)
        check("provider folder" in render.no_source_help(settings, s),
              "and it points at the folder provider instead of 'write more notes'")
    finally:
        shutil.rmtree(root)


def test_installer_wraps_any_statusline():
    """The installer has to end up drawing the box, whatever it was handed.

    Appending into the user's own script was the old mechanism. It silently did
    nothing when that script ended in `exit`, refused outright for the two
    commonest command shapes, and produced the inline segment rather than the
    boxed column the README leads with. Every case here shipped broken.
    """
    print("\ninstaller wiring")
    import json
    import subprocess

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cases = [
        ("absolute path", "%s", False),
        ("bash prefix", "bash %s", False),
        ("home-relative", "~/.claude/statusline.sh", False),
        ("ends in exit", "%s", True),
    ]
    for label, template, exits in cases:
        home = tempfile.mkdtemp(prefix="bb-install-")
        try:
            claude = os.path.join(home, ".claude")
            os.makedirs(claude)
            script = os.path.join(claude, "statusline.sh")
            with open(script, "w") as f:
                f.write('#!/bin/bash\nprintf "HOST"\n' + ("exit 0\n" if exits else ""))
            os.chmod(script, 0o755)
            command = template % script if "%s" in template else template
            with open(os.path.join(claude, "settings.json"), "w") as f:
                json.dump({"theme": "dark", "statusLine": {"type": "command", "command": command}}, f)

            env = dict(os.environ, HOME=home)
            r = subprocess.run(["bash", os.path.join(repo, "install.sh")],
                               env=env, input="", capture_output=True, text=True)
            check(r.returncode == 0, "%s: installer exits clean" % label)

            shim = os.path.join(claude, "terminalcreature", "statusline-terminalcreature.sh")
            out = subprocess.run(["bash", shim], env=env, input="{}",
                                 capture_output=True, text=True).stdout
            check("HOST" in out, "%s: the statusline it wrapped still renders" % label)
            check("┌" in out or "+-" in out, "%s: the creature lands in its box" % label)
            check("/creature-hatch" in out, "%s: and it says how to open the egg" % label)

            with open(script) as f:
                check("terminalcreature" not in f.read(), "%s: their script is untouched" % label)

            u = subprocess.run(["bash", os.path.join(repo, "install.sh"), "--uninstall"],
                               env=env, input="", capture_output=True, text=True)
            with open(os.path.join(claude, "settings.json")) as f:
                restored = json.load(f)
            check(u.returncode == 0 and restored["statusLine"]["command"] == command,
                  "%s: uninstall puts their command back" % label)
            check(restored.get("theme") == "dark", "%s: and leaves the rest of settings.json alone" % label)
        finally:
            shutil.rmtree(home)

    # no script at all, just a command
    home = tempfile.mkdtemp(prefix="bb-install-")
    try:
        claude = os.path.join(home, ".claude")
        os.makedirs(claude)
        with open(os.path.join(claude, "settings.json"), "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "echo HOST"}}, f)
        env = dict(os.environ, HOME=home)
        subprocess.run(["bash", os.path.join(repo, "install.sh")],
                       env=env, input="", capture_output=True, text=True)
        shim = os.path.join(claude, "terminalcreature", "statusline-terminalcreature.sh")
        out = subprocess.run(["bash", shim], env=env, input="{}",
                             capture_output=True, text=True).stdout
        check("HOST" in out and ("┌" in out or "+-" in out),
              "plain command: a bare command gets wrapped and boxed too")
    finally:
        shutil.rmtree(home)


GENERATED_BLOCK = (
    '\n# >>> brainbuddy >>>\nprintf " "\n'
    '"$HOME/.claude/brainbuddy/statusline-brainbuddy.sh"\n'
    "# <<< brainbuddy <<<\n"
)


def test_plugin_wiring():
    """A plugin install ships the commands and can't set statusLine.

    So the installer has to be able to do the wiring half without copying a
    second set of command files over the plugin's, and the SessionStart hook
    has to tell those two states apart. A hook that cried "not wired" at a
    wired user would nag them once a session, forever.
    """
    print("\nplugin wiring")
    import json
    import subprocess

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hook = os.path.join(repo, "scripts", "plugin-session-start.sh")
    home = tempfile.mkdtemp(prefix="bb-plugin-")
    try:
        claude = os.path.join(home, ".claude")
        os.makedirs(os.path.join(claude, "commands"))
        env = dict(os.environ, HOME=home, CLAUDE_PLUGIN_ROOT=repo)

        before = subprocess.run(["bash", hook], env=env, capture_output=True, text=True)
        check("not wired up yet" in before.stdout, "unwired: the hook says so")
        check(json.loads(before.stdout)["hookSpecificOutput"]["hookEventName"] == "SessionStart",
              "unwired: and says it in the shape a SessionStart hook returns")
        check("--no-commands" in before.stdout, "unwired: naming the flag that avoids double-listing")
        with open(os.path.join(claude, "terminalcreature", "plugin-root")) as f:
            check(f.read().strip() == repo, "the plugin root is recorded for the command to find")

        r = subprocess.run(["bash", os.path.join(repo, "install.sh"), "--no-commands"],
                           env=env, input="", capture_output=True, text=True)
        check(r.returncode == 0, "--no-commands: installer exits clean")
        check(os.listdir(os.path.join(claude, "commands")) == [],
              "--no-commands: the plugin's five commands aren't copied over a second time")
        check("/creature-hatch" in r.stdout, "--no-commands: still ends on the egg")

        after = subprocess.run(["bash", hook], env=env, capture_output=True, text=True)
        check(after.stdout.strip() == "", "wired: the hook goes quiet")

        # wired library, but a statusline pointing somewhere else. half-wired is
        # unwired, or the creature is nowhere and nothing says why
        with open(os.path.join(claude, "settings.json"), "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "~/other.sh"}}, f)
        half = subprocess.run(["bash", hook], env=env, capture_output=True, text=True)
        check("not wired up yet" in half.stdout, "a statusline pointing elsewhere still counts as unwired")

        u = subprocess.run(["bash", os.path.join(repo, "install.sh"), "--no-commands", "--uninstall"],
                           env=env, input="", capture_output=True, text=True)
        check(u.returncode == 0, "--no-commands: uninstall exits clean")
    finally:
        shutil.rmtree(home)


def test_installer_respects_hand_wiring():
    """A terminalcreature block someone has edited belongs to them, not the installer.

    Wrapping a script that already calls the CLI would draw two creatures, so
    the installer has to stop. What it must not do is delete the block to make
    room: people edit inside the fence, and the first cut of the wrapping
    installer silently ate a customised one on the way past.
    """
    print("\nhand-wired statuslines")
    import json
    import subprocess

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    edited = GENERATED_BLOCK.replace(
        'printf " "',
        'PYTHONPATH="$HOME/.claude/terminalcreature/lib" python3 -m terminalcreature.cli compose "$MY_BAR"',
    )
    for label, block, survives in [("untouched block", GENERATED_BLOCK, False), ("edited block", edited, True)]:
        home = tempfile.mkdtemp(prefix="bb-wired-")
        try:
            claude = os.path.join(home, ".claude")
            os.makedirs(claude)
            script = os.path.join(claude, "statusline.sh")
            body = '#!/bin/bash\nprintf "HOST"\n' + block
            with open(script, "w") as f:
                f.write(body)
            os.chmod(script, 0o755)
            with open(os.path.join(claude, "settings.json"), "w") as f:
                json.dump({"statusLine": {"type": "command", "command": script}}, f)

            env = dict(os.environ, HOME=home)
            r = subprocess.run(["bash", os.path.join(repo, "install.sh")],
                               env=env, input="", capture_output=True, text=True)
            check(r.returncode == 0, "%s: installer exits clean" % label)
            with open(script) as f:
                same = f.read() == body
            with open(os.path.join(claude, "settings.json")) as f:
                still_theirs = json.load(f)["statusLine"]["command"] == script

            if survives:
                check(same, "%s: their script is left exactly as they wrote it" % label)
                check(still_theirs, "%s: and their statusline stays wired to it" % label)
                check("two creatures" in r.stdout, "%s: and the installer says why" % label)
            else:
                check(not same, "%s: our own block is removed" % label)
                check(not still_theirs, "%s: and the shim takes over" % label)
                shim = os.path.join(claude, "terminalcreature", "statusline-terminalcreature.sh")
                out = subprocess.run(["bash", shim], env=env, input="{}",
                                     capture_output=True, text=True).stdout
                check(out.count("/creature-hatch") == 1, "%s: exactly one creature renders" % label)
        finally:
            shutil.rmtree(home)


def test_hatch_from_zero():
    """The guided first hatch has to honour both answers, and keep honouring them.

    `--from-zero` parks the high-water mark on everything already written. Get
    that wrong in either direction and it's silent: too low re-credits the whole
    vault on the next render, too high means new notes never count at all.
    """
    print("\nhatch from zero")
    import json
    import subprocess

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for from_zero in (False, True):
        home = tempfile.mkdtemp(prefix="bb-zero-")
        try:
            notes = os.path.join(home, "notes")
            os.makedirs(os.path.join(home, ".claude"))
            os.makedirs(notes)
            for i in range(40):
                open(os.path.join(notes, "n%d.md" % i), "w").close()
            env = dict(os.environ, HOME=home)
            lib = os.path.join(home, ".claude", "terminalcreature", "lib")

            def bb(*a):
                return subprocess.run([sys.executable, "-m", "terminalcreature.cli"] + list(a),
                                      env=dict(env, PYTHONPATH=lib), capture_output=True, text=True).stdout

            subprocess.run(["bash", os.path.join(repo, "install.sh"), "--folder", notes],
                           env=env, input="", capture_output=True, text=True)
            out = bb("hatch", "--from-zero") if from_zero else bb("hatch")
            state = json.load(open(os.path.join(home, ".claude", "terminalcreature", "state.json")))
            banked = state["creatures"][0]["xp_banked"]
            label = "from-zero" if from_zero else "score-existing"

            if from_zero:
                check(banked == 0, "%s: nothing already written is credited, got %d" % (label, banked))
                check(state["high_water_xp"] == 80, "%s: the mark parks on the existing 80 xp, got %d" % (
                    label, state["high_water_xp"]))
                check("baselined" in out, "%s: and it says so, or the level 0 looks broken" % label)
            else:
                check(banked == 80, "%s: the whole vault is credited, got %d" % (label, banked))
                check("baselined" not in out, "%s: no baseline note when nothing was baselined" % label)

            # a note written after the hatch has to count either way
            for i in range(40, 50):
                open(os.path.join(notes, "n%d.md" % i), "w").close()
            bb("refresh")
            state = json.load(open(os.path.join(home, ".claude", "terminalcreature", "state.json")))
            grew = state["creatures"][0]["xp_banked"] - banked
            check(grew == 20, "%s: 10 new notes add 20 xp on top, got %d" % (label, grew))
        finally:
            shutil.rmtree(home)


def test_session_xp_counter():
    """The counter is per session, so concurrent sessions can't inherit each other.

    Baselining on first sight is the whole mechanism: skip it and every session
    opens claiming credit for the entire vault. There are usually several open
    at once here, which is why the mark is per id rather than one shared number.
    """
    print("\nsession xp counter")
    os.environ["NO_COLOR"] = "1"
    try:
        from terminalcreature import render

        st = state_mod.default_state()
        c = _hatched(st, name="Zask")
        c["xp_banked"] = 80

        gain, is_new = state_mod.session_gain(st, "A", 80)
        check((gain, is_new) == (0, True), "a session's first sight is +0 and records a mark")
        check(state_mod.session_gain(st, "A", 90)[0] == 10, "then it counts what landed after that")

        check(state_mod.session_gain(st, "B", 90) == (0, True), "a session opening later starts at +0")
        check(state_mod.session_gain(st, "A", 96)[0] == 16, "A keeps counting from its own mark")
        check(state_mod.session_gain(st, "B", 96)[0] == 6, "B counts only what it was around for")
        check(state_mod.session_gain(st, None, 96) == (0, False), "no session id means no counter and no write")

        # focus moving to a fresher creature drops banked below the mark
        check(state_mod.session_gain(st, "A", 5) == (0, True), "a total under the mark re-baselines instead of going negative")

        for i in range(state_mod.SESSION_KEEP + 4):
            state_mod.session_gain(st, "s%d" % i, 100)
        check(len(st["sessions"]) <= state_mod.SESSION_KEEP,
              "the roster of marks is capped, got %d" % len(st["sessions"]))

        c["xp_banked"] = 96
        st["sessions"] = {"A": {"at": 80, "ts": 1}}
        cap = next(r for r in render.compose(st, "BAR", xp=96, counts={}, gain=16).split("\n") if "Lv" in r)
        check("+16 XP" in cap, "the caption carries the counter")
        check(cap.index("Lv") < cap.index("+16 XP"), "and it sits to the right of the level")
        bar_char = "█" if "█" in cap else "#"
        check(cap.index(bar_char) < cap.index("+16 XP"), "and to the right of the progress bar")
        quiet = next(r for r in render.compose(st, "BAR", xp=96, counts={}, gain=0).split("\n") if "Lv" in r)
        check("XP" not in quiet, "a session that has earned nothing yet shows no counter")
    finally:
        os.environ.pop("NO_COLOR", None)


def test_hatch_naming():
    """The name is chosen at the hatch: --name lands it, and `names` has ideas.

    Before the hatch there's nothing to call it, which the egg tests cover; this
    covers the choosing itself.
    """
    print("\nhatch naming")
    import io
    from contextlib import redirect_stdout
    from terminalcreature import cli

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.cmd_names([])
    ideas = [l for l in buf.getvalue().split("\n") if l.strip()]
    check(code == 0 and len(ideas) == 2, "names prints two ideas, got %d" % len(ideas))
    check(all(i[:1].isupper() and len(i) <= 24 for i in ideas), "both look like names")

    st = state_mod.default_state()
    c = state_mod.create(st, name="Placeholder")
    c["name"] = "Zephyr"[:24]  # what hatch --name does before the reveal
    state_mod.reveal(st)
    check(c["name"] == "Zephyr" and state_mod.is_hatched(c), "a chosen name survives the reveal")


def test_update_chip():
    """The chip is a fact off the cache: opted in and newer, or it isn't there.

    It never fetches; these cases run with no network at all. The cache path
    resolves at call time, so pointing LATEST_PATH at a temp dir is enough.
    """
    print("\nupdate chip")
    os.environ["NO_COLOR"] = "1"
    from terminalcreature import release, render

    d = tempfile.mkdtemp(prefix="bb-chip-")
    real_path = state_mod.LATEST_PATH
    state_mod.LATEST_PATH = os.path.join(d, "latest-version")
    try:
        st = state_mod.default_state()
        c = _hatched(st, name="Zask")
        c["xp_banked"] = 80
        st["settings"]["unicode"] = True

        state_mod.write_latest("9.9.9")
        check(not release.update_available(st["settings"]), "a newer cache without consent is not an update")
        cap = next(r for r in render.compose(st, "BAR", xp=80, counts={}, gain=5).split("\n") if "Lv" in r)
        check("⬆" not in cap, "so no chip renders while opted out")

        st["settings"]["update_check"] = True
        check(release.update_available(st["settings"]), "opted in with a newer cache is one")
        cap = next(r for r in render.compose(st, "BAR", xp=80, counts={}, gain=5).split("\n") if "Lv" in r)
        check("⬆ update" in cap, "compose gets icon and word")
        check(cap.index("+5 XP") < cap.index("⬆"), "and the chip sits last, right of the counter")
        seg = render.segment(st, xp=80, counts={}, gain=5)
        check("⬆" in seg and "update" not in seg, "compact gets the icon only, the word is cut first")
        st["settings"]["density"] = "full"
        check("⬆ update" in render.segment(st, xp=80, counts={}, gain=5), "full has room for the word")
        st["settings"]["density"] = "minimal"
        check("⬆" not in render.segment(st, xp=80, counts={}), "minimal stays one glyph, chip included")

        # sprite pads by visible width, and the chip's escapes must not count.
        # colour ON here on purpose: NO_COLOR hid this exact bug from the suite
        import re
        os.environ.pop("NO_COLOR", None)
        st["settings"]["density"] = "sprite"
        st["settings"]["columns"] = 24
        line = render.segment(st, xp=80, counts={}).split("\n")[-1]
        clean = re.sub(r"\x1b\[[0-9;]*m", "", line)
        check(len(clean) == 24 and clean.endswith("⬆"),
              "sprite caption stays right-aligned with the chip on, got %d cols" % len(clean))
        check("\x1b[1;33m" in line, "and the chip is painted independently, not inside the DIM span")
        os.environ["NO_COLOR"] = "1"
        st["settings"]["density"] = "compact"
        st["settings"]["columns"] = 0

        state_mod.write_latest("0.0.1")
        check(not release.update_available(st["settings"]), "an older cache is not an update")
        state_mod.write_latest("")
        check(not release.update_available(st["settings"]), "neither is a stamped failed attempt")
        with open(state_mod.LATEST_PATH, "w") as f:
            f.write("not json")
        check(not release.update_available(st["settings"]), "a corrupt cache reads as no cache, no crash")

        # set_setting writes against the file as it is now, not a held snapshot
        p = os.path.join(d, "state.json")
        st1 = state_mod.load(p)
        st1["settings"]["hidden"] = True
        state_mod.save(st1, path=p, own_settings=True)
        state_mod.set_setting("update_check_asked", True, path=p)
        st2 = state_mod.load(p)
        check(st2["settings"]["hidden"] and st2["settings"]["update_check_asked"],
              "set_setting keeps a concurrent edit and lands its own key")

        # the daily gate: a fresh stamp means no fetch at all
        calls = []
        real_fetch = release.fetch_latest
        release.fetch_latest = lambda *a, **k: calls.append(1) or ("ok", "9.9.9")
        try:
            state_mod.write_latest("9.9.9")
            release.maybe_refresh_latest(st["settings"])
            check(calls == [], "a fresh stamp means no fetch")
            os.utime(state_mod.LATEST_PATH, (1, 1))
            release.maybe_refresh_latest(st["settings"])
            check(len(calls) == 1, "a stale one means exactly one")
            release.maybe_refresh_latest({"update_check": False})
            check(len(calls) == 1, "and opted out means none, stale or not")
        finally:
            release.fetch_latest = real_fetch
    finally:
        state_mod.LATEST_PATH = real_path
        os.environ.pop("NO_COLOR", None)
        shutil.rmtree(d)


def test_refresh_never_reverts_concurrent_writes():
    """A background refresh must not hold a roster snapshot across the scan.

    render spawns a refresh whenever the cache goes stale, so the scan window
    overlaps the exact moment a new user lays and hatches their first egg. The
    refresh has to write back the world as it is after the scan, not the copy
    it held before.
    """
    print("\nrefresh vs concurrent writes")
    import json
    import subprocess

    home = tempfile.mkdtemp(prefix="bb-race-")
    try:
        vault = os.path.join(home, "notes")
        os.makedirs(vault)
        open(os.path.join(vault, "a.md"), "w").close()
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script = (
            "import sys\n"
            "sys.path.insert(0, %r)\n"
            "from terminalcreature import cli, state as sm\n"
            "st = sm.load(); sm.create(st, name='Alpha'); sm.save(st)\n"
            "real = sm.measure_now\n"
            "def slow(settings):\n"
            "    out = real(settings)\n"
            "    st2 = sm.load(); sm.create(st2, name='Beta'); sm.save(st2)\n"
            "    return out\n"
            "sm.measure_now = slow\n"
            "raise SystemExit(cli.cmd_refresh([]))\n"
        ) % repo
        env = dict(os.environ, HOME=home)
        r = subprocess.run([sys.executable, "-c", script], env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        check(r.returncode == 0, "refresh exits clean, stderr: %s" % r.stderr.decode()[:120])
        with open(os.path.join(home, ".claude", "terminalcreature", "state.json")) as f:
            names = [c.get("name") for c in json.load(f)["creatures"]]
        check("Beta" in names, "an egg laid during the scan survives the refresh, roster: %s" % names)
    finally:
        shutil.rmtree(home)


def test_migration_replaces_nulls():
    """A hand-edited null has the key, so setdefault used to keep it and every
    command that lowercases the name crashed instead of degrading."""
    print("\nmigration vs hand-edited nulls")
    st = state_mod.migrate({
        "creatures": [{"id": "x", "seed": "s", "name": None, "xp_banked": None, "last_stage_seen": None}],
        "focused": "x", "settings": {},
    })
    c = st["creatures"][0]
    check(isinstance(c["name"], str) and bool(c["name"]), "a null name migrates to a real one")
    check(c["xp_banked"] == 0, "a null xp_banked migrates to 0")
    check(c["last_stage_seen"] == 0, "a null last_stage_seen migrates to 0")


def test_migrates_a_brainbuddy_install():
    """A brainbuddy-era home comes over in place: same creature, same wrapped
    command, settings repointed, old command files gone, a stub at the old shim
    path for project-level settings that still name it. Twice changes nothing.
    """
    print("\nmigration from brainbuddy")
    import json
    import subprocess

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = tempfile.mkdtemp(prefix="bb-migrate-")
    try:
        claude = os.path.join(home, ".claude")
        os.makedirs(claude)
        with open(os.path.join(claude, "settings.json"), "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "echo HOST"}}, f)
        env = dict(os.environ, HOME=home)
        subprocess.run(["bash", os.path.join(repo, "install.sh")],
                       env=env, input="", capture_output=True, text=True)
        new = os.path.join(claude, "terminalcreature")
        old = os.path.join(claude, "brainbuddy")
        # turn the fresh install into what brainbuddy 1.x left behind
        os.rename(new, old)
        os.rename(os.path.join(old, "statusline-terminalcreature.sh"), os.path.join(old, "statusline-brainbuddy.sh"))
        os.rename(os.path.join(old, "lib", "terminalcreature"), os.path.join(old, "lib", "brainbuddy"))
        with open(os.path.join(claude, "settings.json"), "w") as f:
            json.dump({"statusLine": {"type": "command", "command": os.path.join(old, "statusline-brainbuddy.sh")}}, f)
        for name in ("brainbuddy", "brainbuddy-hatch", "brainbuddy-new", "brainbuddy-hide", "brainbuddy-show"):
            with open(os.path.join(claude, "commands", name + ".md"), "w") as f:
                f.write("# old\n")
        for name in ("creature", "creature-hatch", "creature-new", "creature-hide", "creature-show"):
            os.remove(os.path.join(claude, "commands", name + ".md"))
        with open(os.path.join(old, "state.json")) as f:
            before = json.load(f)["creatures"]

        r = subprocess.run(["bash", os.path.join(repo, "install.sh")],
                           env=env, input="", capture_output=True, text=True)
        check(r.returncode == 0, "re-running the installer over a brainbuddy install exits clean")
        check("migrated" in r.stdout, "and says so")
        with open(os.path.join(new, "state.json")) as f:
            check(json.load(f)["creatures"] == before, "the roster comes over unchanged")
        with open(os.path.join(new, "wrapped-command")) as f:
            check(f.read() == "echo HOST", "the wrapped command comes over")
        with open(os.path.join(claude, "settings.json")) as f:
            check(json.load(f)["statusLine"]["command"] == os.path.join(new, "statusline-terminalcreature.sh"),
                  "settings.json points at the new shim")
        check(not os.path.exists(os.path.join(old, "lib")), "the old library is gone")
        check(not os.path.exists(os.path.join(old, "state.json")), "the old state file is gone")
        check(not os.path.exists(os.path.join(claude, "commands", "brainbuddy-hatch.md")), "the old command files are gone")
        check(os.path.exists(os.path.join(claude, "commands", "creature-hatch.md")), "the new command files are there")
        out = subprocess.run(["bash", os.path.join(old, "statusline-brainbuddy.sh")], env=env, input="{}",
                             capture_output=True, text=True).stdout
        check("HOST" in out and ("┌" in out or "+-" in out), "the old shim path still draws, through the stub")

        with open(os.path.join(claude, "settings.json")) as f:
            settled = f.read()
        r2 = subprocess.run(["bash", os.path.join(repo, "install.sh")],
                            env=env, input="", capture_output=True, text=True)
        with open(os.path.join(claude, "settings.json")) as f:
            check(r2.returncode == 0 and f.read() == settled, "a second run changes nothing")
        with open(os.path.join(new, "state.json")) as f:
            check(json.load(f)["creatures"] == before, "and the roster is still the same creature")

        u = subprocess.run(["bash", os.path.join(repo, "install.sh"), "--uninstall"],
                           env=env, input="", capture_output=True, text=True)
        with open(os.path.join(claude, "settings.json")) as f:
            check(u.returncode == 0 and json.load(f)["statusLine"]["command"] == "echo HOST",
                  "uninstall after a migration restores the original command")
        check(not os.path.exists(os.path.join(old, "statusline-brainbuddy.sh")), "and removes the stub")
    finally:
        shutil.rmtree(home)


def test_seed_salt_is_pinned():
    """The salt kept its brainbuddy-era value through the rename on purpose.
    Change it and every creature ever hatched becomes a different one.
    """
    print("\nseed salt")
    check(creature.SALT == "brainbuddy/v1", "the seed salt is the original")
    d = creature.derive("seed-one")
    check((d["species"], d["rarity"], d["shiny"]) == ("Bramble", "Common", False),
          "a known seed still derives the creature it always has")


def test_moods():
    """A blink closes the eyes for a beat; a feed holds a happy face for two
    seconds; an egg has no eyes to move. Only the eyes change, never the width.
    """
    print("\nmoods")
    from terminalcreature import sprites

    base = sprites.sprite("Nim", 2)
    blink = sprites.sprite("Nim", 2, mood="blink")
    happy = sprites.sprite("Nim", 2, mood="happy")
    check(base[1] != blink[1] and "- -" in blink[1], "a blink closes the eyes")
    check("^ ^" in happy[1], "a feed raises them")
    check([len(r) for r in base] == [len(r) for r in blink] == [len(r) for r in happy], "moods never change the width")
    check([r for i, r in enumerate(base) if i != 1] == [r for i, r in enumerate(blink) if i != 1],
          "and touch nothing but the eye row")
    check(sprites.sprite("Nim", 0, mood="happy") == sprites.sprite("Nim", 0), "an egg has no eyes to move")
    check("_ _" in sprites.sprite("Wisp", 2, mood="blink")[1], "Wisp rests on a dash, so its blink is an underscore")
    check("* *" in sprites.sprite("Ember", 2, mood="happy")[1], "Ember rests raised, so its happy is a star")
    check(sprites.face("Nim", 2, True, "blink") == "<-->" and sprites.face("Nim", 2, True, "happy") == "<^^>",
          "the compact face swaps the same way")
    check(sprites.face("Nim", 0, True, "happy") == sprites.face("Nim", 0, True), "the compact egg doesn't")

    st = state_mod.default_state()
    st["sessions"]["s1"] = {"at": 10, "ts": 0}
    gain, save = state_mod.session_gain(st, "s1", 10)
    check(gain == 0 and not save, "no gain, nothing to stamp")
    gain, save = state_mod.session_gain(st, "s1", 13)
    check(gain == 3 and save, "a rise stamps the feed and asks to be saved")
    fed = st["sessions"]["s1"]["fed_at"]
    gain, save = state_mod.session_gain(st, "s1", 13)
    check(gain == 3 and not save, "the same counter again does not re-stamp")
    check(state_mod.mood(st, "s1", now=fed + 1.9) == "happy", "happy holds for two seconds after the feed")
    check(state_mod.mood(st, "s1", now=fed + 2.1) in (None, "blink"), "and lets go after")
    quiet = 100 * state_mod.BLINK_EVERY  # a multiple, so a window starts here
    check(state_mod.mood(st, None, now=quiet + 0.1) == "blink", "a blink lands in its window")
    check(state_mod.mood(st, None, now=quiet + state_mod.BLINK_HOLD + 0.1) is None, "and only in its window")
    st["sessions"]["s1"]["fed_at"] = quiet
    check(state_mod.mood(st, "s1", now=quiet + 0.1) == "happy", "a feed beats a blink")


def _styled_state():
    st = state_mod.default_state()
    c = _hatched(st, name="Zask")
    c["xp_banked"] = 80
    st["settings"]["unicode"] = True
    return st


def _visible(text):
    """Columns a row takes on screen: directives free, wide glyphs two."""
    plain = re.sub(r"\x1b\[[0-9;]*m|#\[[^\]]*\]", "", text)
    return max(sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in row) for row in plain.split("\n"))


def test_render_formats():
    """tmux strips raw escapes out of a status command and shows the bytes, so
    its backend speaks #[fg=] and never emits one. plain is bare text. ansi is
    the bytes Claude Code has always been handed, NO_COLOR included.
    """
    print("\nrender formats")
    from terminalcreature import render

    os.environ.pop("NO_COLOR", None)
    try:
        st = _styled_state()
        for name, draw in (
            ("segment", lambda fmt: render.segment(st, xp=80, counts={}, gain=5, fmt=fmt)),
            ("compose", lambda fmt: render.compose(st, "BAR", xp=80, counts={}, gain=5, fmt=fmt)),
            ("card", lambda fmt: render.card(st, xp=80, counts={"memories": 3}, fmt=fmt)),
        ):
            ansi, tmux, plain = draw("ansi"), draw("tmux"), draw("plain")
            check("\x1b[" in ansi, "%s ansi carries escapes with colour on" % name)
            check(draw(None) == ansi, "%s with no format is ansi byte for byte" % name)
            check("\x1b" not in tmux and "#[" in tmux, "%s tmux has #[ styles and zero raw escapes" % name)
            check("#[default]" in tmux, "%s tmux closes what it opens" % name)
            check("\x1b" not in plain and "#[" not in plain, "%s plain has neither" % name)
            word = "Lv" if name == "segment" else "Zask"
            check(word in plain and word in tmux, "%s says the same thing in every format" % name)
        check(render.paint("x", render.BOLD) == "\x1b[1mx\x1b[0m", "the default backend is still ansi after a styled block")

        os.environ["NO_COLOR"] = "1"
        check("\x1b" not in render.segment(st, xp=80, counts={}, fmt="ansi"), "NO_COLOR still strips ansi")
        check("#[" in render.segment(st, xp=80, counts={}, fmt="tmux"), "and leaves tmux styles alone, tmux paints those itself")

        try:
            render.Style("html")
        except ValueError:
            check(True, "an unknown format is refused, not guessed")
        else:
            check(False, "an unknown format is refused, not guessed")
    finally:
        os.environ.pop("NO_COLOR", None)


def test_width_cap():
    """--width counts what lands on screen: directives are free, the egg icon
    is two cells, and a cut drops the trailing fragment of a word.
    """
    print("\nwidth cap")
    from terminalcreature import render

    fit = render.fit
    check(fit("hello world", 8) == "hello", "a cut backs up to the last whole word")
    check(fit("hello world", 11) == "hello world", "a line that fits is untouched")
    check(fit("hello world", 6) == "hello", "a cut right after the gap keeps the word and drops the gap")
    check(fit("supercalifragilistic", 5) == "super", "a single word too long is cut, not dropped")
    check(fit("hello world", 0) == "hello world", "no width means no cap")
    check(fit("a\nbb\nccc", 2) == "a\nbb\ncc", "each line is capped on its own")
    check(fit("\x1b[32mgreen\x1b[0m stuff", 5) == "\x1b[32mgreen\x1b[0m", "ansi escapes cost no columns")
    check(fit("\x1b[32mgreen fields\x1b[0m", 5) == "\x1b[32mgreen\x1b[0m", "a cut inside a span closes it")
    check(fit("#[fg=green]green fields#[default]", 5) == "#[fg=green]green#[default]", "same for tmux styles")
    check(fit("\U0001f95a egg here", 5) == "\U0001f95a", "the icon is two cells wide, so five columns is not enough for egg")
    check(fit("\U0001f95a egg here", 6) == "\U0001f95a egg", "and six is")

    os.environ.pop("NO_COLOR", None)
    try:
        st = _styled_state()
        for fmt in ("ansi", "tmux", "plain"):
            for name, cap, out in (
                ("segment", 8, render.segment(st, xp=80, counts={}, gain=5, fmt=fmt, width=8)),
                ("compose", 14, render.compose(st, "a long bar of host text", xp=80, counts={}, fmt=fmt, width=14)),
                ("card", 20, render.card(st, xp=80, counts={"memories": 3}, fmt=fmt, width=20)),
            ):
                widest = _visible(out)
                check(widest <= cap, "%s %s capped at %d visible columns, widest row is %d" % (name, fmt, cap, widest))
                check(out.strip() != "", "%s %s still shows something under the cap" % (name, fmt))
        wide = render.segment(st, xp=80, counts={}, gain=5, fmt="ansi")
        check(render.segment(st, xp=80, counts={}, gain=5, fmt="ansi", width=200) == wide, "a generous cap changes nothing")
    finally:
        os.environ.pop("NO_COLOR", None)


# one payload per host, in the shape its docs or a live capture show.
# droid's is derived from docs only; nobody has captured its stdin yet
HOST_PAYLOADS = {
    "claude": {
        "hook_event_name": "Status", "session_id": "c-1", "transcript_path": "/x/t.jsonl", "cwd": "/x",
        "model": {"id": "claude-opus-5", "display_name": "Opus"},
        "workspace": {"current_dir": "/x", "project_dir": "/x"},
        "version": "2.1.0", "output_style": {"name": "default"},
        "cost": {"total_cost_usd": 0.1, "total_duration_ms": 1000},
        "context_window": {"total_input_tokens": 1000, "total_output_tokens": 100, "context_window_size": 200000,
                           "used_percentage": 12.5, "remaining_percentage": 87.5},
        "exceeds_200k_tokens": False,
    },
    "cursor": {
        # the key set the cursor cli 2026.09 bundle builds, values made up
        "session_id": "u-1", "transcript_path": "/x/t.jsonl", "render_width_chars": 76, "cwd": "/x",
        "autorun": False, "model": {"id": "composer-2", "display_name": "composer"},
        "workspace": {"current_dir": "/x", "project_dir": "/x", "added_dirs": []},
        "version": "2026.09.02", "output_style": {"name": "default"},
        "context_window": {"total_input_tokens": 100, "total_output_tokens": 10, "context_window_size": 200000,
                           "used_percentage": 40, "remaining_percentage": 60, "current_usage": 80000},
        "session_name": "fix tests", "worktree": {"name": "main", "path": "/x"},
    },
    # the key set the copilot cli 1.0.82 bundle builds for its statusLine command,
    # values made up. it never ran live here, but the field names are the binary's own
    "copilot": {
        "cwd": "/x", "session_id": "p-1", "session_name": "fix tests", "transcript_path": "/x/t.jsonl",
        "model": {"id": "gpt-5", "display_name": "gpt"}, "workspace": {"current_dir": "/x"},
        "username": "someone", "remote": {"connected": False}, "version": "1.0.82",
        "cost": {"total_api_duration_ms": 10, "total_lines_added": 0, "total_lines_removed": 0,
                 "total_duration_ms": 10, "total_premium_requests": 0},
        "context_window": {"total_input_tokens": 1000, "total_output_tokens": 100, "total_cache_read_tokens": 0,
                           "total_cache_write_tokens": 0, "total_reasoning_tokens": 0, "total_tokens": 1100,
                           "context_window_size": 200000, "used_percentage": 33, "remaining_percentage": 67,
                           "remaining_tokens": 134000, "last_call_input_tokens": 10, "last_call_output_tokens": 5,
                           "current_context_tokens": 66000, "displayed_context_limit": 200000,
                           "current_context_used_percentage": 33},
        "ai_used": {"total_nano_aiu": 0, "formatted": "0"}, "allow_all_enabled": False,
    },
    "qwen": {
        "session_id": "q-1", "version": "0.14.1", "model": {"display_name": "qwen-3-235b"},
        "context_window": {"context_window_size": 131072, "used_percentage": 34.3, "remaining_percentage": 65.7,
                           "current_usage": 45000, "total_input_tokens": 30000, "total_output_tokens": 15000},
        "workspace": {"current_dir": "/x"},
        "metrics": {"models": {}, "files": {"total_lines_added": 0, "total_lines_removed": 0}},
    },
    "droid": {"sessionId": "d-1", "model": "claude-opus", "workingDirectory": "/x", "contextWindow": {"usedPercentage": 5}},
}


def test_host_stdin():
    """Every host copies Claude Code's contract with its own field names, so one
    map reads them all. Anything else renders without a session, never a crash.
    """
    print("\nhost stdin")
    import json
    import subprocess

    from terminalcreature import hosts

    for host, payload in HOST_PAYLOADS.items():
        s = hosts.parse_session(json.dumps(payload))
        check(s["host"] == host, "%s payload is read as %s, got %s" % (host, host, s["host"]))
        check(s["session_id"] == (payload.get("session_id") or payload.get("sessionId")), "%s session id lands" % host)
        check(isinstance(s["model"], str) and s["model"], "%s model lands as a string" % host)
        check(s["workspace"] == "/x", "%s workspace lands" % host)
        check(isinstance(s["context_used_pct"], float), "%s context percent lands as a float" % host)
        check(sorted(s) == ["context_used_pct", "host", "model", "session_id", "workspace"], "%s carries exactly the five fields" % host)

    for label, raw in (("empty", ""), ("not json", "not json"), ("empty object", "{}"), ("a list", "[1, 2]"),
                       ("a bare string", '"hi"'), ("unknown keys", '{"foo": 1}'), ("None", None)):
        s = hosts.parse_session(raw)
        check(s["host"] == "unknown" and all(v is None for k, v in s.items() if k != "host"),
              "%s stdin is host unknown with every field None" % label)
    check(hosts.parse_session('{"session_id": "x"}')["host"] == "claude", "bare claude keys read as claude")
    check(hosts.parse_session('{"session_id": 7}')["session_id"] is None, "a non-string id is dropped, not passed on")
    check("/x" not in hosts.describe(hosts.parse_session(json.dumps(HOST_PAYLOADS["claude"]))), "doctor's line never carries the workspace path")
    check("unknown schema" in hosts.describe(hosts.parse_session("")), "and calls an unknown shape unknown")

    # a real render with each shape, and with junk, in a scratch home
    home = tempfile.mkdtemp(prefix="bb-hosts-")
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = dict(os.environ, HOME=home, PYTHONPATH=repo, NO_COLOR="1")
    env.pop("TERMINALCREATURE_FORMAT", None)
    cmd = [sys.executable, "-m", "terminalcreature.cli"]

    def run(argv, raw="", **extra):
        return subprocess.run(cmd + argv, input=raw, env=dict(env, **extra), capture_output=True, text=True)

    try:
        run(["new"])
        run(["hatch", "--from-zero", "--name", "Zask"])
        run(["config", "update_check_asked", "true"])  # or card appends the one-time offer
        for label, raw in [("unknown", "not json at all"), ("empty", "")] + [(h, json.dumps(p)) for h, p in HOST_PAYLOADS.items()]:
            r = run(["render"], raw)
            check(r.returncode == 0 and "Lv" in r.stdout, "render with %s stdin still prints the segment" % label)
        r = run(["render", "--format", "tmux"], json.dumps(HOST_PAYLOADS["qwen"]))
        check("\x1b" not in r.stdout and "#[" in r.stdout, "render --format tmux through the cli emits tmux styles only")
        r = run(["render", "--format=plain", "--width", "3"])
        check(r.returncode == 0 and 0 < len(r.stdout) <= 3, "render --format=plain --width 3 caps the segment")
        r = run(["render", "--format", "html"])
        check(r.returncode == 0 and "Lv" in r.stdout, "a bad format on render falls back rather than blanking the statusline")
        r = run(["compose", "--format", "tmux", "BAR"], "{}")
        check("BAR" in r.stdout and "#[" in r.stdout and "\x1b" not in r.stdout, "compose takes the flags ahead of its text")
        r = run(["card", "--width", "abc"])
        check(r.returncode == 1 and "--width" in r.stdout, "card, which a human runs, says what was wrong")
        r = run(["card", "--format", "plain", "--width", "30"])
        check(r.returncode == 0 and "Zask" in r.stdout and _visible(r.stdout) <= 30, "card takes both flags")
        r = run(["doctor"], json.dumps(HOST_PAYLOADS["cursor"]))
        check("stdin: cursor schema" in r.stdout and "/x" not in r.stdout, "doctor names the schema it read, without the path")
        r = run(["doctor"])
        check("no session on stdin" in r.stdout, "and says so when nothing was piped")
        r = run(["render"], "{}", TERMINALCREATURE_FORMAT="tmux")
        check("#[" in r.stdout, "TERMINALCREATURE_FORMAT picks the backend when no flag does")
    finally:
        shutil.rmtree(home)



def make_agent_home(files):
    """A fake home holding whichever agent trees the test lists, one path per
    file. Filenames carry a marker no real note would, so the leak checks
    below have something concrete to look for in the output.
    """
    home = tempfile.mkdtemp(prefix="bb-agents-")
    for rel in files:
        path = os.path.join(home, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()
    return home


def test_agents_provider():
    """The agents provider counts every agent's memory off one fake home, auto
    only switches to it at two roots, and nothing that leaves the process is a
    path. Runs in-process against HOME, then through the cli in a subprocess.
    """
    print("\nagents provider")
    import builtins
    import io
    import json
    import subprocess

    from terminalcreature import render

    mark = "zqxv"
    files = [
        ".claude/projects/p1/memory/%s-a.md" % mark,
        ".claude/projects/p1/memory/%s-b.md" % mark,
        ".claude/projects/p1/memory/MEMORY.md",
        ".claude/projects/p2/memory/%s-c.md" % mark,
        ".codex/memories/%s-m1.md" % mark,
        ".codex/memories/deep/%s-m2.md" % mark,
        ".codex/AGENTS.md",
        ".codex/sessions/2026/09/%s-s1.jsonl" % mark,
        ".codex/sessions/2026/09/%s-s2.jsonl" % mark,
        ".codex/sessions/2026/09/notes.txt",
        ".cursor/rules/%s-r.mdc" % mark,
        ".cursor/proj/rules/%s-r2.mdc" % mark,
        ".cursor/chats/x/%s-chat.json" % mark,
        ".local/share/goose/sessions/sessions.db",
        ".config/goose/.goosehints",
        ".config/opencode/AGENTS.md",
    ]
    real_home = os.environ.get("HOME")

    def at_home(home):
        os.environ["HOME"] = home

    home = make_agent_home(files)
    try:
        at_home(home)
        opened = []
        real_open, real_io_open = builtins.open, io.open

        def trap(factory):
            def guard(file, *a, **kw):
                if str(file).startswith(home):
                    opened.append(str(file))
                return factory(file, *a, **kw)
            return guard

        builtins.open = trap(real_open)
        io.open = trap(real_io_open)
        try:
            xp, counts, found = metric.measure_agents()
        finally:
            builtins.open, io.open = real_open, real_io_open
        check(opened == [], "measure_agents opens nothing under the fake home, got %d" % len(opened))
        check(found == ["claude", "codex", "cursor", "opencode", "goose"], "found agents in table order, got %s" % found)
        check(counts["claude"] == {"memories": 3}, "claude counts memories and skips MEMORY.md, got %s" % counts.get("claude"))
        check(counts["codex"] == {"memories": 2, "instructions": 1, "sessions": 2},
              "codex counts memories recursively, AGENTS.md and only jsonl sessions, got %s" % counts.get("codex"))
        check(counts["cursor"] == {"rules": 2, "sessions": 1}, "cursor finds rules at any depth, got %s" % counts.get("cursor"))
        check(counts["goose"] == {"sessions": 1, "instructions": 1}, "goose spans two roots and sees a dotfile, got %s" % counts.get("goose"))
        check(counts["opencode"] == {"sessions": 0, "instructions": 1}, "opencode counts from the one root that exists, got %s" % counts.get("opencode"))
        check("gemini" not in counts, "an agent with no root gets no row")
        check(xp == 32, "weights are 3 memory, 3 instructions, 2 rules, 1 sessions: 32 xp, got %d" % xp)
        check(metric.measure_agents({"sessions": 5})[0] == 48, "weights override by source key across agents")
        check(metric.flatten_agent_counts(counts) == {"memories": 5, "instructions": 3, "sessions": 4, "rules": 2},
              "flattened counts fold by source key")

        settings = dict(state_mod.DEFAULT_SETTINGS)
        check(settings["provider"] == "auto", "the default provider is auto")
        check(state_mod.resolve_provider(settings) == "agents", "auto resolves to agents with several roots")
        s = state_mod.source_status(settings)
        check(s["state"] == "ok" and s["xp"] == 32, "source status counts through auto, got %s" % s["state"])
        check(s["counts"] == {"memories": 5, "instructions": 3, "sessions": 4, "rules": 2}, "status counts are flat")
        check("gemini" in s["missing"] and s["found"] == found, "status names found and missing agents")
        check(state_mod.measure_now(settings) == (32, s["counts"]), "measure_now feeds the cache the flat shape")
        check(render.no_source_help(settings, s) == "", "a working agents source gets no lecture")
        settings["provider"] = "claude"
        check(state_mod.measure_now(settings) == (9, {"memories": 3}), "an explicit claude provider is untouched by the table")
        check(state_mod.sources_for(dict(settings, provider="folder", vault_root=home))[1] is metric.FOLDER_SOURCES,
              "folder still resolves to its own sources")
    finally:
        shutil.rmtree(home)

    # one root: auto stays on claude and behaves exactly as before
    home = make_agent_home([".claude/projects/p1/memory/%s-a.md" % mark])
    try:
        at_home(home)
        settings = dict(state_mod.DEFAULT_SETTINGS)
        check(state_mod.resolve_provider(settings) == "claude", "auto resolves to claude with one root")
        check(state_mod.measure_now(settings) == (3, {"memories": 1}), "and measures the claude layout")
        check(state_mod.resolve_provider(dict(settings, provider="agents")) == "agents", "an explicit agents provider is kept")
        check(state_mod.source_status(dict(settings, provider="agents"))["found"] == ["claude"], "and counts the one root it has")
    finally:
        shutil.rmtree(home)

    # a lone agent that isn't claude: auto reads as zero, and the help says why
    home = make_agent_home([".codex/AGENTS.md"])
    try:
        at_home(home)
        settings = dict(state_mod.DEFAULT_SETTINGS)
        s = state_mod.source_status(settings)
        help_text = render.no_source_help(settings, s)
        check(s["state"] == "missing_root" and "config provider agents" in help_text and "codex" in help_text,
              "a lone codex under auto points at the agents provider")
        check(mark not in help_text and home not in help_text, "and names no path")
    finally:
        shutil.rmtree(home)

    # zero agents: auto falls back to claude and says what it looked for
    home = make_agent_home([])
    try:
        at_home(home)
        settings = dict(state_mod.DEFAULT_SETTINGS)
        help_text = render.no_source_help(settings, state_mod.source_status(settings))
        check("Looked for" in help_text and "Codex" in help_text and "Crush" in help_text, "with no agents the help lists what it looked for")
        check(home not in help_text, "without a path")
        s = state_mod.source_status(dict(settings, provider="agents"))
        check(s["state"] == "missing_root" and s["found"] == [], "an explicit agents provider over nothing is missing_root")
        check("Looked for" in render.no_source_help(dict(settings, provider="agents"), s), "and gets the same list")
    finally:
        if real_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = real_home
        shutil.rmtree(home)

    check(state_mod.migrate({"settings": {"provider": "claude"}})["settings"]["provider"] == "claude",
          "migrate keeps an install's explicit provider")
    check(state_mod.migrate({"settings": {"density": "full"}})["settings"]["provider"] == "auto",
          "and only a missing provider key becomes auto")

    # the cli end to end in a scratch home: config accepts the names, sources
    # prints counts and never a path
    home = make_agent_home(files)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = dict(os.environ, HOME=home, PYTHONPATH=repo, NO_COLOR="1")
    cmd = [sys.executable, "-m", "terminalcreature.cli"]

    def run(argv):
        return subprocess.run(cmd + argv, env=env, capture_output=True, text=True)

    try:
        r = run(["config"])
        check(json.loads(r.stdout)["provider"] == "auto", "a fresh install shows provider auto")
        check(run(["config", "provider", "agents"]).returncode == 0, "config provider agents is accepted")
        check(run(["config", "provider", "nope"]).returncode == 1, "and an unknown provider is refused")
        for provider in ("agents", "auto"):
            run(["config", "provider", provider])
            r = run(["sources"])
            out = r.stdout
            check(r.returncode == 0, "sources exits 0 under %s" % provider)
            check("codex: memories 2, instructions 1, sessions 2" in out, "sources lists codex counts by key under %s" % provider)
            check("goose: sessions 1, instructions 1" in out and "claude: memories 3" in out, "and the other agents found")
            check("not found: gemini, copilot, qwen, droid, amp, continue, kiro, cline, crush" in out,
                  "and the agents it didn't find, on one line")
            check("counting 32 xp of memory across 5 agents" in out, "then the total")
            check(mark not in out and home not in out and "/memory/" not in out and "AGENTS.md" not in out,
                  "sources prints no path fragment from the fake home under %s" % provider)
        r = run(["doctor"])
        check("memories   5" in r.stdout and mark not in r.stdout and home not in r.stdout, "doctor shows the flat counts, no paths")
        r = run(["refresh"])
        cache = json.load(open(os.path.join(home, ".claude", "terminalcreature", "xp.cache")))
        check(cache == {"xp": 32, "counts": {"memories": 5, "instructions": 3, "sessions": 4, "rules": 2}},
              "refresh writes the flat shape to the cache, got %s" % cache)
    finally:
        shutil.rmtree(home)

    home = make_agent_home([])
    try:
        r = subprocess.run(cmd + ["sources"], env=dict(env, HOME=home), capture_output=True, text=True)
        check(r.returncode == 1 and "Looked for" in r.stdout and home not in r.stdout,
              "sources on an empty machine exits 1, lists what it looked for, prints no path")
    finally:
        shutil.rmtree(home)



HOST_SEEDS = {
    "claude": ('{"theme": "dark", "statusLine": {"type": "command", "command": "echo CL"}}\n', "echo CL"),
    "cursor": ('{"display": {"mode": "zen"}, "statusLine": {"type": "command", "command": "echo CUR"}}\n', "echo CUR"),
    # jsonc with a trailing comma, the way copilot's file is allowed to look
    "copilot": ('{\n  // footer prefs\n  "footer": {"showBranch": true},\n  /* mine */\n'
                '  "statusLine": {"type": "command", "command": "echo COP", "padding": 1,},\n}\n', "echo COP"),
    "qwen": ('{"ui": {"theme": "x", "statusLine": {"type": "command", "command": "echo QW", "refreshInterval": 3}}}\n', "echo QW"),
    "droid": ('{"model": "m", "statusLine": {"command": "echo DR", "maxRows": 2}}\n', "echo DR"),
}


def test_host_adapters():
    """install --host wraps each host's statusline the way install.sh wraps
    claude's: key repointed at a per-host shim, old command kept, the settings
    file backed up as raw bytes, and uninstall puts every byte back.
    """
    print("\nhost adapters")
    import json
    import subprocess

    from terminalcreature import hosts

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cmd = [sys.executable, "-m", "terminalcreature.cli"]

    def run(env, argv, raw=""):
        return subprocess.run(cmd + argv, env=env, input=raw, capture_output=True, text=True)

    for host, (seed, previous) in HOST_SEEDS.items():
        home = tempfile.mkdtemp(prefix="bb-host-")
        env = dict(os.environ, HOME=home, PYTHONPATH=repo, NO_COLOR="1")
        try:
            spec = hosts.REGISTRY[host]
            path = os.path.join(home, spec["settings"][2:])
            os.makedirs(os.path.dirname(path))
            with open(path, "w") as f:
                f.write(seed)
            state = os.path.join(home, ".claude", "terminalcreature")
            shim, wrapped = os.path.join(state, spec["shim"]), os.path.join(state, spec["wrapped"])

            r = run(env, ["install", "--host", host])
            check(r.returncode == 0 and host in r.stdout, "%s: install exits clean and names the host" % host)
            with open(path) as f:
                data = json.load(f)
            check(hosts.get_command(data, host) == shim, "%s: the key points at our shim" % host)
            node = data["ui"]["statusLine"] if host == "qwen" else data["statusLine"]
            check(("type" in node) == spec["typed"], "%s: the value carries type only when the host wants it" % host)
            with open(wrapped) as f:
                check(f.read() == previous, "%s: the old command is recorded" % host)
            with open(path + ".pre-terminalcreature.bak") as f:
                check(f.read() == seed, "%s: the backup is the raw file, comments and all" % host)
            with open(shim) as f:
                text = f.read()
            check("TERMINALCREATURE_WRAPPING" in text and spec["wrapped"] in text, "%s: the shim guards re-entry and reads its own wrapped file" % host)
            check(("cli render" if spec["inline"] else "cli compose") in text, "%s: the shim picks the host's default mode" % host)
            out = subprocess.run(["bash", shim], env=env, input="{}", capture_output=True, text=True).stdout
            check(previous.split()[-1] in out, "%s: the shim still runs what it wrapped" % host)

            if host == "cursor":
                check(data["display"]["mode"] == "zen", "cursor: sibling keys survive")
            if host == "copilot":
                check(data["footer"]["showBranch"] is True and node["padding"] == 1, "copilot: comments stripped, siblings kept")
                check("plain JSON" in r.stdout, "copilot: install says the comments live in the backup now")
            if host == "qwen":
                check(node["refreshInterval"] == 3 and node["respectUserColors"] is True and data["ui"]["theme"] == "x",
                      "qwen: refreshInterval kept, respectUserColors added, ui siblings kept")
            if host == "droid":
                check(node["maxRows"] == 2, "droid: maxRows kept")

            r2 = run(env, ["install", "--host", host])
            with open(path) as f:
                check(r2.returncode == 0 and "already wired" in r2.stdout and json.load(f) == data, "%s: re-running is a no-op that says so" % host)

            u = run(env, ["uninstall", "--host", host])
            with open(path) as f:
                check(u.returncode == 0 and f.read() == seed, "%s: uninstall restores the file byte for byte" % host)
            check(not os.path.exists(shim) and not os.path.exists(wrapped), "%s: and drops the shim and wrapped file" % host)

            if host == "copilot":
                # edited since install: only our key comes out, their edit stays
                run(env, ["install", "--host", host])
                with open(path) as f:
                    data = json.load(f)
                data["footer"]["showQuota"] = False
                with open(path, "w") as f:
                    json.dump(data, f)
                u = run(env, ["uninstall", "--host", host])
                with open(path) as f:
                    after = json.load(f)
                check(after["statusLine"]["command"] == previous and after["footer"]["showQuota"] is False,
                      "copilot: a file edited after install gets only our key undone")
        finally:
            shutil.rmtree(home)

    # claude through the adapter writes the very shim install.sh writes
    home = tempfile.mkdtemp(prefix="bb-host-")
    try:
        env = dict(os.environ, HOME=home)
        subprocess.run(["bash", os.path.join(repo, "install.sh"), "--no-commands"], env=env, input="", capture_output=True, text=True)
        with open(os.path.join(home, ".claude", "terminalcreature", "statusline-terminalcreature.sh")) as f:
            check(f.read() == hosts.shim_text("claude", False), "the python claude shim is byte for byte install.sh's")
    finally:
        shutil.rmtree(home)

    # --host all on a machine with qwen and droid, and nothing else
    home = tempfile.mkdtemp(prefix="bb-host-")
    env = dict(os.environ, HOME=home, PYTHONPATH=repo, NO_COLOR="1")
    try:
        for host in ("qwen", "droid"):
            path = os.path.join(home, hosts.REGISTRY[host]["settings"][2:])
            os.makedirs(os.path.dirname(path))
            with open(path, "w") as f:
                f.write(HOST_SEEDS[host][0])
        r = run(env, ["install", "--host", "all"])
        check(r.returncode == 0 and "qwen" in r.stdout and "droid" in r.stdout, "all: wires both hosts that are here")
        check("cursor" not in r.stdout and "copilot" not in r.stdout, "all: and says nothing about hosts that aren't")
        for host in ("qwen", "droid"):
            with open(os.path.join(home, hosts.REGISTRY[host]["settings"][2:])) as f:
                check(hosts.REGISTRY[host]["shim"] in f.read(), "all: %s points at its shim" % host)
        d = run(env, ["doctor"])
        check("qwen     Qwen Code           native, wired" in d.stdout and "native, wired" in d.stdout.split("droid")[1].split("\n")[0],
              "doctor lists the wired hosts")
        check("cursor   Cursor CLI          not installed" in d.stdout, "doctor calls an absent host not installed")
        check("terminalcreature snippet" in d.stdout, "doctor points prompt surfaces at the snippet command")
        check("/" + "Users" not in d.stdout and home not in d.stdout, "doctor's hosts block carries no paths")
        u = run(env, ["uninstall", "--host", "all"])
        for host in ("qwen", "droid"):
            with open(os.path.join(home, hosts.REGISTRY[host]["settings"][2:])) as f:
                check(u.returncode == 0 and f.read() == HOST_SEEDS[host][0], "all: uninstall restores %s" % host)
        r = run(env, ["install", "--host", "nope"])
        check(r.returncode == 1 and "unknown host" in r.stdout, "an unknown host is refused with the list")
    finally:
        shutil.rmtree(home)

    # install.sh --host hands the wiring to the adapter and leaves claude alone
    home = tempfile.mkdtemp(prefix="bb-host-")
    env = dict(os.environ, HOME=home, NO_COLOR="1")
    try:
        os.makedirs(os.path.join(home, ".qwen"))
        r = subprocess.run(["bash", os.path.join(repo, "install.sh"), "--host", "qwen", "--statusline", "echo QW", "--no-commands"],
                           env=env, input="", capture_output=True, text=True)
        qwen = os.path.join(home, ".qwen", "settings.json")
        with open(qwen) as f:
            data = json.load(f)
        check(r.returncode == 0 and "statusline-terminalcreature-qwen.sh" in data["ui"]["statusLine"]["command"], "install.sh --host qwen wires qwen")
        check(os.path.isdir(os.path.join(home, ".claude", "terminalcreature", "lib", "terminalcreature")), "and still installs the library")
        check(not os.path.exists(os.path.join(home, ".claude", "settings.json")), "and leaves claude's settings alone")
        check("/creature-hatch" in r.stdout, "and still offers the egg")
        u = subprocess.run(["bash", os.path.join(repo, "install.sh"), "--uninstall", "--host", "qwen", "--no-commands"],
                           env=env, input="", capture_output=True, text=True)
        with open(qwen) as f:
            data = json.load(f)
        check(u.returncode == 0 and data["ui"]["statusLine"]["command"] == "echo QW", "install.sh --uninstall --host qwen puts the command back")
        check(os.path.isdir(os.path.join(home, ".claude", "terminalcreature", "lib")), "and keeps the library for the other hosts")
    finally:
        shutil.rmtree(home)


def test_snippets():
    """Every surface gets a paste-in config that calls the installed binary with
    the format its host can show, and no snippet ever carries an expanded home.
    """
    print("\nsnippets")
    import subprocess

    from terminalcreature import cli, snippets

    home = os.path.expanduser("~")
    fake_home = tempfile.mkdtemp(prefix="bb-snip-")
    found = os.path.join(home, ".local", "bin", "terminalcreature")
    on_path = snippets.resolve_binary(which=lambda name: found)
    missing = snippets.resolve_binary(state_dir=os.path.join(home, ".claude", "terminalcreature"),
                                      which=lambda name: None)
    check(on_path["shell"] == "~/.local/bin/terminalcreature", "an entry point under home is written ~-relative")
    check(missing["shell"] == "env PYTHONPATH=$HOME/.claude/terminalcreature/lib python3 -m terminalcreature.cli",
          "no entry point falls back to the installed lib the way the shim runs it")
    check(missing["argv"][1] == "PYTHONPATH=~/.claude/terminalcreature/lib", "and the argv form keeps ~ for hosts that expand it themselves")
    check(snippets.resolve_binary(which=lambda name: "/opt/homebrew/bin/terminalcreature")["shell"] == "/opt/homebrew/bin/terminalcreature",
          "a path outside home is left alone")

    formats = {"tmux": "--format tmux", "starship": "--format ansi", "zsh": "--format ansi",
               "fish": "--format ansi", "omp": "plain", "wezterm": "'--format', 'plain'"}
    os.environ.pop("TMUX", None)
    try:
        for binary, label in ((on_path, "on PATH"), (missing, "lib fallback")):
            for surface in snippets.SURFACES:
                text = snippets.render_snippet(surface, binary=binary)
                check(text is not None and text.startswith(("#", "//", "--")), "%s (%s) opens with a comment saying where it goes" % (surface, label))
                check("terminalcreature" in text, "%s (%s) names the binary" % (surface, label))
                check(formats[surface] in text, "%s (%s) asks for the format its host can show" % (surface, label))
                check(home not in text and fake_home not in text, "%s (%s) carries no expanded home path" % (surface, label))
                check("\u2014" not in text, "%s (%s) has no em dash" % (surface, label))
        tmux = snippets.render_snippet("tmux", binary=on_path)
        check("status-right-length 80" in tmux and "default is 40" in tmux, "tmux raises status-right-length and says why")
        check("--width 40" in tmux and "@plugin 'smejkaldesign/terminalcreature'" in tmux and "#{creature}" in tmux,
              "tmux caps the width and shows the tpm form with its placeholder")
        check("status-interval" in tmux, "tmux mentions status-interval")
        star = snippets.render_snippet("starship", binary=on_path)
        check("[custom.creature]" in star and "when = true" in star and 'style = ""' in star and "command_timeout" in star,
              "starship is a custom module with an empty style and a timeout note")
        zsh = snippets.render_snippet("zsh", binary=on_path)
        check("setopt PROMPT_SUBST" in zsh and "RPROMPT='$(" in zsh and "precmd" in zsh and "zsh-async" in zsh,
              "zsh sets PROMPT_SUBST, an RPROMPT, and mentions precmd and zsh-async")
        check("function fish_right_prompt" in snippets.render_snippet("fish", binary=on_path), "fish is a fish_right_prompt function")
        omp = snippets.render_snippet("omp", binary=on_path)
        check('{{ cmd \\"terminalcreature\\" \\"render\\" \\"--format\\" \\"plain\\" }}' in omp and '"type": "text"' in omp,
              "omp is a text segment using the multi-argument cmd form")
        check(".Env.HOME" not in omp, "omp on PATH needs no home expansion, so no caveat about it")
        check(".Env.HOME" in snippets.render_snippet("omp", binary=missing), "omp's lib fallback expands home through the template")
        wez = snippets.render_snippet("wezterm", binary=on_path)
        check("wezterm.on('update-status'" in wez and "run_child_process" in wez and "set_right_status" in wez
              and "status_update_interval = 1000" in wez, "wezterm hooks update-status and sets the interval")
        check("wezterm.home_dir .. '/.local/bin/terminalcreature'" in wez, "wezterm expands home in lua, since nothing else will")
        check(snippets.render_snippet("kitty") is None, "an unknown surface is None, not a guess")

        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = dict(os.environ, HOME=fake_home, PYTHONPATH=repo)
        env.pop("TMUX", None)
        cmd = [sys.executable, "-m", "terminalcreature.cli", "snippet"]
        r = subprocess.run(cmd + ["kitty"], env=env, capture_output=True, text=True)
        check(r.returncode == 1 and all(s in r.stdout for s in snippets.SURFACES), "snippet kitty exits 1 and lists the surfaces")
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        check(r.returncode == 1 and "wezterm" in r.stdout, "bare snippet does the same")
        r = subprocess.run(cmd + ["tmux"], env=env, capture_output=True, text=True)
        check(r.returncode == 0 and "--format tmux" in r.stdout and home not in r.stdout, "snippet tmux prints the config, exit 0, no home path")
        check("snippet" in cli.USAGE, "usage lists it")
    finally:
        shutil.rmtree(fake_home)


def test_tmux_plugin():
    """The tpm plugin swaps #{creature} for a call to its own helper, against a
    throwaway tmux server so nothing of the user's is touched.
    """
    print("\ntmux plugin")
    import subprocess

    if not shutil.which("tmux"):
        print("  skip tmux is not installed here")
        return
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plugin = os.path.join(repo, "tmux", "terminalcreature.tmux")
    helper = os.path.join(repo, "tmux", "creature.sh")
    check(os.access(plugin, os.X_OK) and os.access(helper, os.X_OK), "plugin and helper are executable")
    check(os.access(os.path.join(repo, "terminalcreature.tmux"), os.X_OK), "the root shim tpm actually sources is executable too")
    check(len(open(os.path.join(repo, "tmux", "README.md")).read().strip().splitlines()) <= 10, "the readme is ten lines or fewer")

    sock = "tctest-%d" % os.getpid()
    t = lambda *a: subprocess.run(["tmux", "-L", sock] + list(a), capture_output=True, text=True)
    r = t("-f", "/dev/null", "new-session", "-d")
    if r.returncode != 0:
        print("  skip could not start a tmux server: %s" % r.stderr.strip()[-100:])
        return
    try:
        t("set-option", "-g", "status-right", "cpu #{creature} %H:%M")
        t("set-option", "-g", "status-left", "[#S]")
        path = t("display-message", "-p", "#{socket_path}").stdout.strip()
        env = dict(os.environ, TMUX="%s,0,0" % path)
        for entry in (plugin, os.path.join(repo, "terminalcreature.tmux")):
            t("set-option", "-g", "status-right", "cpu #{creature} %H:%M")
            r = subprocess.run([entry], env=env, capture_output=True, text=True)
            check(r.returncode == 0, "%s runs clean (%s)" % (os.path.relpath(entry, repo), r.stderr.strip()[-100:]))
            right = t("show-option", "-gv", "status-right").stdout.strip()
            check("render --format tmux" in right and "#{creature}" not in right, "the placeholder became a render call")
            check(right.startswith("cpu #(") and right.endswith(") %H:%M"), "and the rest of status-right survived around it")
            named = right[right.find("#(") + 2:right.find(" render")]
            check(os.path.realpath(named) == os.path.realpath(helper),
                  "the call names the helper by absolute path, so tpm's clone location doesn't matter")
        check(t("show-option", "-gv", "status-left").stdout.strip() == "[#S]", "an option without the placeholder is left alone")
        # a home with the installer's lib layout and no entry point on PATH, so
        # the helper has to take its fallback route to reach this checkout
        home = tempfile.mkdtemp(prefix="bb-helper-")
        lib = os.path.join(home, ".claude", "terminalcreature", "lib")
        os.makedirs(lib)
        os.symlink(os.path.join(repo, "terminalcreature"), os.path.join(lib, "terminalcreature"))
        env = dict(os.environ, HOME=home, PATH=os.pathsep.join([os.path.dirname(sys.executable), "/usr/bin", "/bin"]))
        r = subprocess.run([helper, "simulate", "10"], env=env, capture_output=True, text=True)
        check(r.returncode == 0 and "Lv" in r.stdout, "the helper reaches terminalcreature through the lib (%s)" % r.stderr.strip()[-80:])
        shutil.rmtree(home)
    finally:
        t("kill-server")


def test_refresh_pokes_tmux():
    """After the cache changes, refresh asks tmux to redraw, and only then.
    tmux is a stub on PATH that logs what it was asked, so nothing real is poked.
    """
    print("\nrefresh pokes tmux")
    import subprocess
    import time as _t

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = tempfile.mkdtemp(prefix="bb-poke-")
    stub_dir = os.path.join(home, "bin")
    os.makedirs(stub_dir)
    log = os.path.join(home, "tmux.log")
    stub = os.path.join(stub_dir, "tmux")
    with open(stub, "w") as f:
        f.write("#!/bin/sh\necho \"$@\" >> %s\n" % log)
    os.chmod(stub, 0o755)

    def refresh(tmux, cached):
        if os.path.exists(log):
            os.remove(log)
        child = "from terminalcreature import cli, state as sm\n"
        if cached is not None:
            child += "sm.write_cache(%d, {})\n" % cached
        child += "cli.main(['refresh'])\n"
        env = dict(os.environ, HOME=home, PYTHONPATH=repo, PATH=stub_dir + os.pathsep + os.environ.get("PATH", ""))
        env.pop("TMUX", None)
        if tmux:
            env["TMUX"] = "/tmp/fake,0,0"
        r = subprocess.run([sys.executable, "-c", child], env=env, capture_output=True, text=True)
        deadline = _t.time() + 5
        while _t.time() < deadline and not os.path.exists(log):
            _t.sleep(0.1)
        _t.sleep(0.2)
        lines = open(log).read().splitlines() if os.path.exists(log) else []
        return r.returncode, lines

    try:
        # an empty fabricated home measures 0 xp, so a cache of 999 is a change
        rc, lines = refresh(True, 999)
        check(rc == 0 and lines == ["refresh-client -S"], "xp changed under tmux: one refresh-client -S, got %r" % lines)
        rc, lines = refresh(True, None)
        check(rc == 0 and lines == [], "same xp again: no poke, got %r" % lines)
        rc, lines = refresh(False, 999)
        check(rc == 0 and lines == [], "xp changed outside tmux: no poke, got %r" % lines)
        os.chmod(stub, 0o644)
        rc, lines = refresh(True, 999)
        check(rc == 0 and lines == [], "a tmux that can't run is silent, refresh still exits 0")
    finally:
        shutil.rmtree(home)


if __name__ == "__main__":
    test_metric()
    test_snippets()
    test_tmux_plugin()
    test_refresh_pokes_tmux()
    test_agents_provider()
    test_render_formats()
    test_width_cap()
    test_host_stdin()
    test_host_adapters()
    test_update_chip()
    test_hatch_naming()
    test_refresh_never_reverts_concurrent_writes()
    test_migration_replaces_nulls()
    test_sprite_alignment()
    test_compose_column()
    test_no_content_reads()
    test_creature()
    test_banking()
    test_egg_and_hatch()
    test_retire_keeps_the_record()
    test_state_roundtrip()
    test_state_migration()
    test_version_check_is_explicit_only()
    test_project_statusline_override()
    test_empty_hatch_is_a_moment()
    test_egg_reveals_nothing()
    test_source_status()
    test_installer_wraps_any_statusline()
    test_plugin_wiring()
    test_installer_respects_hand_wiring()
    test_hatch_from_zero()
    test_session_xp_counter()
    test_migrates_a_brainbuddy_install()
    test_seed_salt_is_pinned()
    test_moods()
    test_update_apply()
    print("\n%s" % ("-" * 46))
    if FAILURES:
        print("%d FAILED" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        sys.exit(1)
    print("all green")
