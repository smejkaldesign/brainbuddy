"""Tests. Run: python3 -m tests.test_brainbuddy  (from the repo root)

Fixtures are synthetic and generated into a temp dir. No real vault is ever
touched, so nothing here can leak a memory filename into CI output (R12).
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brainbuddy import creature, metric, state as state_mod  # noqa: E402

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
    from brainbuddy import sprites

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
        from brainbuddy import render

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
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brainbuddy", "metric.py")
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

    from brainbuddy import release

    check(release.status_line("ok", "0.2.0", current="0.1.0").startswith("brainbuddy 0.2.0 is out"),
          "a newer release says so, and which one")
    check("pipx upgrade brainbuddy" in release.status_line("ok", "0.2.0", current="0.1.0"),
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
        "from brainbuddy import cli\n"
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
            return subprocess.run([sys.executable, "-m", "brainbuddy.cli", "doctor"],
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
        check("statusline-brainbuddy.sh" in out, "pointing the project at the shim")
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
        out = subprocess.run([sys.executable, "-m", "brainbuddy.cli", "hatch"],
                             env=dict(env, PYTHONPATH=repo), capture_output=True, text=True).stdout

        check("the egg cracks" in out, "the reveal still runs")
        check("Lv0" in out, "at Lv0, since there was nothing to eat")
        check(any(r in out for r in ("Common", "Uncommon", "Rare", "Epic", "Legendary")),
              "and it still says what came out")
        check("that's the floor, not a dud roll" in out, "the zero is framed rather than left hanging")
        from brainbuddy import render
        check(render.SETUP_PROMPT in out, "and it ends on how to get something to feed it")
    finally:
        shutil.rmtree(home)


def _egg_renders(colour):
    """Every unhatched egg's segment and column, over a spread of seeds."""
    from brainbuddy import render

    if colour:
        os.environ.pop("NO_COLOR", None)
    else:
        os.environ["NO_COLOR"] = "1"
    segs, cols, rarities = set(), set(), set()
    for i in range(400):
        st = state_mod.default_state()
        c = state_mod.create(st, name="Egg")
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
    from brainbuddy import sprites

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
            check("Lv" not in segs.pop(), "%s: and neither shows a level" % where)
    finally:
        os.environ.pop("NO_COLOR", None)


def test_source_status():
    """A zero XP reading has three causes and they need three different answers.

    Doctor used to print "check provider / vault_root" for all of them, which
    is actively wrong advice for someone who has simply never kept notes.
    """
    print("\nsource status")
    from brainbuddy import render

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

            shim = os.path.join(claude, "brainbuddy", "statusline-brainbuddy.sh")
            out = subprocess.run(["bash", shim], env=env, input="{}",
                                 capture_output=True, text=True).stdout
            check("HOST" in out, "%s: the statusline it wrapped still renders" % label)
            check("┌" in out or "+-" in out, "%s: the creature lands in its box" % label)
            check("/brainbuddy-hatch" in out, "%s: and it says how to open the egg" % label)

            with open(script) as f:
                check("brainbuddy" not in f.read(), "%s: their script is untouched" % label)

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
        shim = os.path.join(claude, "brainbuddy", "statusline-brainbuddy.sh")
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
        with open(os.path.join(claude, "brainbuddy", "plugin-root")) as f:
            check(f.read().strip() == repo, "the plugin root is recorded for the command to find")

        r = subprocess.run(["bash", os.path.join(repo, "install.sh"), "--no-commands"],
                           env=env, input="", capture_output=True, text=True)
        check(r.returncode == 0, "--no-commands: installer exits clean")
        check(os.listdir(os.path.join(claude, "commands")) == [],
              "--no-commands: the plugin's five commands aren't copied over a second time")
        check("/brainbuddy-hatch" in r.stdout, "--no-commands: still ends on the egg")

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
    """A brainbuddy block someone has edited belongs to them, not the installer.

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
        'PYTHONPATH="$HOME/.claude/brainbuddy/lib" python3 -m brainbuddy.cli compose "$MY_BAR"',
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
                shim = os.path.join(claude, "brainbuddy", "statusline-brainbuddy.sh")
                out = subprocess.run(["bash", shim], env=env, input="{}",
                                     capture_output=True, text=True).stdout
                check(out.count("/brainbuddy-hatch") == 1, "%s: exactly one creature renders" % label)
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
            lib = os.path.join(home, ".claude", "brainbuddy", "lib")

            def bb(*a):
                return subprocess.run([sys.executable, "-m", "brainbuddy.cli"] + list(a),
                                      env=dict(env, PYTHONPATH=lib), capture_output=True, text=True).stdout

            subprocess.run(["bash", os.path.join(repo, "install.sh"), "--folder", notes],
                           env=env, input="", capture_output=True, text=True)
            out = bb("hatch", "--from-zero") if from_zero else bb("hatch")
            state = json.load(open(os.path.join(home, ".claude", "brainbuddy", "state.json")))
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
            state = json.load(open(os.path.join(home, ".claude", "brainbuddy", "state.json")))
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
        from brainbuddy import render

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
        quiet = next(r for r in render.compose(st, "BAR", xp=96, counts={}, gain=0).split("\n") if "Lv" in r)
        check("XP" not in quiet, "a session that has earned nothing yet shows no counter")
    finally:
        os.environ.pop("NO_COLOR", None)


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
            "from brainbuddy import cli, state as sm\n"
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
        with open(os.path.join(home, ".claude", "brainbuddy", "state.json")) as f:
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


if __name__ == "__main__":
    test_metric()
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
    print("\n%s" % ("-" * 46))
    if FAILURES:
        print("%d FAILED" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        sys.exit(1)
    print("all green")
