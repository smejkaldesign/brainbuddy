# brainbuddy

A terminal creature that lives in your Claude Code statusline, hatches from an egg, and evolves through five forms as your memory system grows.

It measures how much you've written down. Not how long you've used it, not a streak you can lose by taking a weekend off. Write more durable notes, it grows. That's the whole loop.

```
  ___     ████░░░░░░  my-brain ⎇ main
 /   \    Zask · egg · /brainbuddy-hatch
( +++ )
 \___/
```

```
 .\|/.    ████░░░░░░  my-brain ⎇ main
( o o )   Drain · Sage · Lv65 █████░
/|ooo|\
|___|
/     \
```

The creature is a fixed-width column on the left of whatever your statusline already prints. It needs no width measurement, so your box can be any size and the art still lands whole.

---

## It never opens your memories

This is the important bit, so it goes first.

brainbuddy sizes your memory system by **counting files**. It uses `glob` and `stat`, and that's all. It never calls `open()`, never reads a byte of content, never parses frontmatter, never counts words.

That isn't a promise about what it does with your data. It's a statement that it never has your data. Memory directories hold notes about work, clients, and employers, and the safest way to handle that is to never load it. The guarantee is enforced two ways in the test suite: a runtime trap that patches every file-reading builtin and asserts none fire during a measurement, and a static pass that tokenizes `metric.py` and fails if a reader appears anywhere in the code.

It also makes no network calls of any kind. There is no telemetry, no update check, no analytics.

One consequence worth knowing: brainbuddy never prints a path it matched, in any mode including `doctor`. Filenames alone leak more than people expect.

---

## The lifecycle

```
   install.sh
       │
       ▼
    ┌──────┐   /brainbuddy-hatch    ┌───────────┐  write notes   ┌────────────┐
    │ egg  │ ────────────────────►  │ Hatchling │ ────────────►  │  evolves   │
    └──────┘      the reveal        └───────────┘   xp climbs    │  to Lv100  │
       ▲                                                         └────────────┘
       │ /brainbuddy-new                                               │
       └───────────────────────────────────────────────────────────────┘
              --replace (retire this one)  ·  --add (keep both)
```

Five steps, and only two of them need you:

1. **Install.** `./install.sh` wires the statusline and lays your first egg.
2. **An egg appears** in your statusline. It shows no level, no species, no rarity.
3. **You hatch it** with `/brainbuddy-hatch`. That's the reveal.
4. **It levels on its own** as your vault grows. Evolutions announce themselves.
5. **At 100 it's fully grown.** Start another with `/brainbuddy-new`, any time you like.

---

## The egg is a state, not a level

A buddy is an **egg** until you hatch it, whatever level it is. Level 0 is a Hatchling, a baby with a face, not an egg.

That matters because of what an egg hides. Species, rarity, shiny and stats are all derived from the creature's seed and fixed the moment the egg exists, so an egg that displays them has nothing left to reveal. An unhatched egg deliberately shows none of it:

```
$ brainbuddy list
* ◌ Zask       egg    unhatched

$ brainbuddy card

       ___
      /   \
     ( ooo )
      \___/

  Zask  unhatched
  0 xp banked and counting
  /brainbuddy-hatch to find out what it is
```

Then you open it:

```
$ brainbuddy hatch

  the egg cracks

       _^_
     ( ' ' )
      /$$$\
       ^ ^

  Zask, a Legendary Nim (shiny)
  Lv0 Hatchling
```

**Eggs bank XP while closed.** So there's no rush, and no XP is lost by waiting. On a fresh install the first egg inherits the memory you already have, which usually means it hatches several forms in rather than as a level 0 blank. That's the point of the zero state: install, see an egg, open it, meet something that already reflects how much you've written.

A buddy added *later* with `/brainbuddy-new --add` starts at 0 and does hatch as a Hatchling, because XP banks per creature.

---

## Install

```bash
git clone <this repo> && cd brainbuddy
./install.sh
```

The installer composes with an existing statusline rather than replacing it. If `statusLine.command` already points at a script, it appends a fenced block and keeps a `.pre-brainbuddy.bak`. If nothing is configured, it writes one.

| Flag | What it does |
|---|---|
| `--vault <path>` | use a vault layout instead of stock Claude Code memory |
| `--statusline <path>` | wire into a specific script, for project-level setups |
| `--no-wire` | install the library and commands only, wire it yourself |
| `--uninstall` | strip the wiring back out and restore backups |

Re-running the installer is safe and is how you pick up new commands. It leaves an existing buddy alone and reports the provider it actually has configured rather than resetting anything.

Then open your first egg:

```bash
/brainbuddy-hatch
```

---

## How levelling works

XP is a weighted count of memory artifacts. Durable facts are worth more than session logs because they cost more to produce, and generated index files are excluded so they can't inflate the count for free.

| Source | Glob | Weight | Excluded |
|---|---|---|---|
| memories | `auto-memory/*.md` | ×3 | `MEMORY.md`, `index.md` |
| knowledge | `05-knowledge/*.md` | ×2 | `index.md` |
| projects | `04-projects/*.md` | ×2 | `index.md` |
| decisions | `memory/decisions/*.md` | ×2 | |
| sessions | `memory/sessions/*.md` | ×1 | |

```
level = min(100, floor(100 * sqrt(xp / xp_max)))
```

A square root curve, so early memories move the needle hard and later ones don't. **Level 100 is fully grown** and the curve stops there; the answer to "what now" is a new egg, not a number that climbs forever with nothing attached to it.

`xp_max` is the XP at level 100, and it's the one dial that controls pace. The default of **1500** is calibrated so a well-established vault of durable notes lands around 65, which leaves real headroom without the early levels crawling.

| Level | XP needed | Roughly |
|---|---|---|
| 5 | 4 | a couple of notes |
| 10 | 16 | ~5 durable memories |
| 20 | 61 | ~20 durable memories |
| 40 | 241 | ~80 durable memories |
| 65 | 634 | ~211 durable memories |
| 100 | 1,500 | ~500 durable memories |

Which means you see movement immediately rather than staring at level 0:

```
    3 xp  ->  Lv4    Hatchling
   10 xp  ->  Lv8    Hatchling
   30 xp  ->  Lv14   Hatchling
   80 xp  ->  Lv23   Fledgling
  200 xp  ->  Lv36   Fledgling
  650 xp  ->  Lv65   Sage
 1500 xp  ->  Lv100  Ascendant
```

Want it slower or faster? `brainbuddy config xp_max 5000` triples the distance. It's your pet.

Deleting memories never de-levels anyone. The high-water mark only rises, because tidying up shouldn't be punished.

---

## The evolution ladder

Six sprites: the egg, then five forms. The art gains detail at every step — limbs, a bracket, then flourishes.

```
     ___             _^_             _^_             \|/            .\|/.          *.\|/.*
    /   \          ( ' ' )         ( ' ' )         ( ' ' )         ( ' ' )        \( ' ' )/
   ( +++ )          /+++\          <|+++|>         <|+++|>         /|+++|\         /|+++|\
    \___/            ^ ^            /   \           /|_|\          |___|           =|___|=
                                    ^   ^           ^   ^          /     \         ^     ^

     egg          Hatchling       Fledgling         Adept           Sage          Ascendant
  unhatched          0-19           20-39           40-59           60-79           80-100
```

Sprite 0 is the egg and level stages start at sprite 1. That numbering is deliberate: it's what lets an existing creature's recorded stage survive the egg change without a migration.

---

## Species and rarity

Eight species. The eyes and the body motif come from the species, so a Bramble is recognisable at a glance.

```
       _^_            _^_            _^_            _^_            _^_            _^_            _^_            _^_
     ( o o )        ( - - )        ( ^ ^ )        ( . . )        ( o o )        ( x x )        ( ' ' )        ( > < )
     <|ooo|>        <|~~~|>        <|***|>        <|...|>        <|===|>        <|###|>        <|+++|>        <|///|>
      /   \          /   \          /   \          /   \          /   \          /   \          /   \          /   \
      ^   ^          ^   ^          ^   ^          ^   ^          ^   ^          ^   ^          ^   ^          ^   ^
       Mote           Wisp          Ember           Pip            Fen          Bramble          Nim           Quill
```

Rarity is rolled from the seed, with a mark that carries the tier without relying on colour, so it still reads on a mono terminal or to a colour-blind user.

| Rarity | Odds | Mark |
|---|---|---|
| Common | 60% | |
| Uncommon | 25% | `+` |
| Rare | 10% | `*` |
| Epic | 4% | `**` |
| Legendary | 1% | `***` |

On top of that, a **1% shiny** roll swaps the body motif for `$`:

```
  normal    <|+++|>
  shiny     <|$$$|>
```

All of it is a pure function of the seed, so hand-editing `state.json` can't promote a Common into a shiny Legendary. `hydrate` recomputes the bones on every load and derived values win.

---

## Display variants

`density` picks how much room it takes:

| Mode | Looks like | Notes |
|---|---|---|
| `minimal` | `◔` | one glyph, filling as you evolve |
| `compact` | `<><> Lv65` | default, ~10 columns inline |
| `full` | `<><> Drain Lv65` | adds the name |
| `sprite` | the 5-row creature | its own rows, gains detail each evolution |
| `ruler` | a column ruler | a measuring aid, not a creature |

In `minimal` the glyph itself is the progress bar:

```
  unicode   ◌ ○ ◔ ◑ ◕ ●
  ascii     . o c C O @
```

`sprite_height 3` cuts the creature to three rows. It keeps the evolution beats but **drops detail**: the head-top and the feet come off.

```
       _^_           (' ')
     ( ' ' )        <|+++|>
     <|+++|>         /   \
      /   \
      ^   ^

     height 5        height 3
```

`sprite` right-aligns to the `columns` setting, which has to be declared rather than measured. A statusline script is handed nothing that is a terminal: stdin is the JSON pipe, stdout is captured, stderr isn't a tty either, and `/dev/tty` isn't attached. To find the number, `density ruler` prints a column ruler as the statusline, so read the last digit you can see and pass it to `config columns <n>`.

`compose "<text>"` is the other way in, and the one the statusline shim uses. It merges your own statusline text with the creature as a **left column**, sharing row one with your first row. Left rather than right on purpose: a fixed-width column needs no measurement at all.

To take the creature out without uninstalling anything, `/brainbuddy-hide`. XP keeps banking while it's hidden, so it comes back further along than it left. `/brainbuddy-show` restores it.

---

## The roster

You can keep several creatures. Only the **focused** one gains XP; the others hold their level and wait.

```
$ brainbuddy list
  ◕ Drain      Lv65   Sage       Common
* ○ Zask       Lv0    Hatchling  Legendary shiny

* = focused (the one gaining xp)
```

That's why `/brainbuddy-new` asks before it acts:

| Mode | What happens |
|---|---|
| `--replace` | retires the current buddy and focuses a new egg |
| `--add` | keeps the current buddy active, focuses a new egg |

**Neither one deletes anything.** `--replace` retires, which records the retirement and drops it out of the active roster while keeping its banked XP. `focus <name>` brings it back and un-retires it. The standalone `retire` command behaves the same way.

`--add` states the tradeoff and asks for `--yes`: a new egg starts at 0 and takes focus, so the current buddy holds its level and stops gaining. There's **no level requirement** — the tradeoff is identical at level 12 and level 99, so it's a decision to make rather than a gate to clear.

New creatures **start at 0**, always. XP banks per creature rather than deriving from your total memory size, so a second egg doesn't inherit the levels the first one earned.

---

## Commands

```
brainbuddy new [name]        lay an egg (--replace or --add, --yes to confirm)
brainbuddy hatch             open the egg, revealing the level it earned
brainbuddy card              the full creature card
brainbuddy list              the roster
brainbuddy focus <name>      choose who banks new xp, un-retires
brainbuddy rename <old> <new>
brainbuddy retire <name>     retires, keeps the record and its xp
brainbuddy hide / show       drop it from the statusline, or bring it back
brainbuddy config [key val]  see settings, or set one
brainbuddy simulate <xp>     preview any level without touching real state
brainbuddy doctor            what can it see, and why is it zero
brainbuddy render            the one-line statusline segment
brainbuddy compose "<text>"  your statusline text, creature as a left column
brainbuddy refresh           recompute the xp cache
```

Five of these are slash commands in Claude Code, so plain language reaches them without going through the CLI: `/brainbuddy`, `/brainbuddy-new`, `/brainbuddy-hatch`, `/brainbuddy-hide`, `/brainbuddy-show`.

### Settings

| Key | Values | Default |
|---|---|---|
| `provider` | `claude` or `vault` | `claude` |
| `vault_root` | path, for `provider vault` | |
| `xp_max` | XP at level 100, the pace dial | `1500` |
| `density` | `minimal` `compact` `full` `sprite` `ruler` | `compact` |
| `sprite_height` | `3` or `5` | `5` |
| `columns` | right-align width for `sprite` | `0` |
| `unicode` | `true` or `false` | `true` |
| `hidden` | `true` or `false` | `false` |

---

## How it works under the hood

**Two providers.** `claude` counts stock Claude Code memory under `~/.claude/projects/*/memory`. `vault` counts a vault layout you point at with `vault_root`. If `doctor` reports 0, the fix is almost always one of those two, not a reinstall.

**A cache, because the statusline is a hot path.** Counting files takes long enough to notice, so `render` reads a cached XP value and spawns the recount in the background. It blocks only on a genuine cold start.

**Settings have one owner.** Background refreshes hold a whole-state copy for as long as the scan takes, so writing it back wholesale used to revert any setting changed meanwhile. Everything except `config` now re-reads settings off disk at write time.

**The high-water mark is the anti-punishment mechanism.** New XP is credited as the delta above the highest total ever seen, so deleting notes can't take a level away, and a render before your first hatch can't burn the XP that was waiting for it.

**State lives at `~/.claude/brainbuddy/`.** The roster, settings, and the XP cache. Species, rarity and shiny are recomputed from the seed on every load, so editing it by hand doesn't do what you'd hope.

---

## Provenance

Anthropic shipped a terminal pet in Claude Code (`/buddy`, April 2026). It's a nice idea with no progression: species and stats are recomputed from your user ID every session and never change. brainbuddy is a clean-room rebuild of the *concept* with the missing half added, growth you actually earn.

No code, species names, sprite art, stat names, or hashing details were taken from it. The species list, the five stats, the sprites, and the levelling system here are original. Not affiliated with or endorsed by Anthropic.

---

## Tests

```bash
python3 tests/test_brainbuddy.py
```

Fixtures are synthetic and generated into a temp directory. No real memory directory is touched. The suite covers the XP maths and the level curve including the cap at 100, the R2 no-content-reads guarantee (both the runtime trap and the static pass), seed determinism and tamper resistance, per-creature XP banking, the egg and hatch transitions, and the non-destructive retire.
