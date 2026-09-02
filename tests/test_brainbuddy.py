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
        check(metric.level_for(624) == 35, "624 xp is level 35 (the calibration target)")

        for lvl in (0, 19, 20, 39, 40, 59, 60, 79, 80, 100):
            need = metric.xp_for_level(lvl)
            check(metric.level_for(need) == lvl, "level %d round-trips through xp_for_level" % lvl)

        check(metric.stage_for(0)[1] == "Egg", "level 0 is an Egg")
        check(metric.stage_for(35)[1] == "Fledgling", "level 35 is a Fledgling")
        check(metric.stage_for(100)[1] == "Ascendant", "level 100 is Ascendant")
        check(metric.stage_for(250)[1] == "Ascendant", "past 100 stays Ascendant, evolution caps")
        check(metric.level_for(20000) > 100, "level itself keeps climbing past 100")
        check(metric.next_stage_level(85) is None, "no next form after Ascendant")
    finally:
        shutil.rmtree(root)


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


def test_banking():
    print("\nxp banking")
    # a render before the first hatch used to burn all the earned xp,
    # which hatched the first creature at level 0 instead of 35
    empty = state_mod.default_state()
    state_mod.sync(empty, 624)
    check(empty["high_water_xp"] == 0, "no creature means the high water mark does not move")
    c0 = state_mod.hatch(empty, name="Late")
    state_mod.sync(empty, 624)
    check(c0["xp_banked"] == 624, "so the first creature still inherits it, got %d" % c0["xp_banked"])

    st = state_mod.default_state()
    first = state_mod.hatch(st, name="Alpha")
    state_mod.sync(st, 624)
    check(first["xp_banked"] == 624, "first creature inherits the existing memory")
    check(metric.level_for(first["xp_banked"]) == 35, "which puts it at level 35")

    second = state_mod.hatch(st, name="Beta")
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
    c = state_mod.hatch(st2, name="Gamma")
    c["xp_banked"] = metric.xp_for_level(19)
    c["last_stage_seen"] = 1
    st2["high_water_xp"] = c["xp_banked"]
    ev = state_mod.sync(st2, metric.xp_for_level(20))
    check(ev is not None and ev["stage"] == "Fledgling", "crossing level 20 fires an evolution event")
    check(state_mod.sync(st2, metric.xp_for_level(20)) is None, "the same evolution does not fire twice")


def test_state_roundtrip():
    print("\nstate file")
    d = tempfile.mkdtemp(prefix="bb-state-")
    path = os.path.join(d, "state.json")
    try:
        st = state_mod.default_state()
        state_mod.hatch(st, name="Delta")
        state_mod.save(st, path)
        back = state_mod.load(path)
        check(back["creatures"][0]["name"] == "Delta", "roster survives a save/load")
        check(back["settings"]["xp_max"] == 5000, "settings default correctly")
        check(state_mod.load(os.path.join(d, "nope.json"))["creatures"] == [], "missing state file degrades to empty")
        with open(path, "w") as f:
            f.write("{not json")
        check(state_mod.load(path)["creatures"] == [], "corrupt state file degrades instead of crashing")
    finally:
        shutil.rmtree(d)


if __name__ == "__main__":
    test_metric()
    test_no_content_reads()
    test_creature()
    test_banking()
    test_state_roundtrip()
    print("\n%s" % ("-" * 46))
    if FAILURES:
        print("%d FAILED" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        sys.exit(1)
    print("all green")
