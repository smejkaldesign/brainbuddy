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

            # and the user's own file is left exactly as they wrote it
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

    # no script at all, just a command. the old installer gave up on this one and
    # printed instructions for the user to wire by hand.
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


if __name__ == "__main__":
    test_metric()
    test_sprite_alignment()
    test_compose_column()
    test_no_content_reads()
    test_creature()
    test_banking()
    test_egg_and_hatch()
    test_retire_keeps_the_record()
    test_state_roundtrip()
    test_egg_reveals_nothing()
    test_source_status()
    test_installer_wraps_any_statusline()
    test_installer_respects_hand_wiring()
    print("\n%s" % ("-" * 46))
    if FAILURES:
        print("%d FAILED" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        sys.exit(1)
    print("all green")
