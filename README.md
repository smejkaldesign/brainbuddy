# brainbuddy

A terminal creature that lives in your Claude Code statusline, hatches from an egg, and evolves through five forms as your memory system grows.

It measures how much you've written down. Not how long you've used it, not a streak you can lose by taking a weekend off. Write more durable notes, it grows. That's the whole loop.

```
┌───────────┐
│    ___    │  ████░░░░░░  my-brain ⎇ main
│   /   \   │  Zask · egg · /brainbuddy-hatch
│  ( ooo )  │
│   \___/   │
└───────────┘
```

```
┌───────────┐
│   .\|/.   │  ████░░░░░░  my-brain ⎇ main
│  ( o o )  │  Drain · Sage · Lv65 █████░
│  /|ooo|\  │
│   |___|   │
│  /     \  │
└───────────┘
```

The creature is a fixed-width column on the left of whatever your statusline already prints, so your terminal can be any size and the art still lands whole. It sizes your memory by **counting files and never reading them** — see [It never opens your memories](#it-never-opens-your-memories).

---

## Install

```bash
git clone <this repo> && cd brainbuddy
./install.sh
/brainbuddy-hatch
```

The installer composes with an existing statusline rather than replacing it: if `statusLine.command` already points at a script it appends a fenced block and keeps a `.pre-brainbuddy.bak`, otherwise it writes one. It lays your first egg too.

| Flag | What it does |
|---|---|
| `--vault <path>` | use a vault layout instead of stock Claude Code memory |
| `--statusline <path>` | wire into a specific script, for project-level setups |
| `--no-wire` | install the library and commands only, wire it yourself |
| `--uninstall` | strip the wiring back out and restore backups |

Re-running it is safe and is how you pick up new commands. It leaves an existing buddy alone.

---

## The egg is a state, not a level

A buddy is an **egg** until you hatch it, whatever level it is. Level 0 is a Hatchling, a baby with a face, not an egg.

Species, rarity, shiny and stats are all derived from the creature's seed and fixed the moment the egg exists, so an egg that displays them has nothing left to reveal. An unhatched one shows none of it:

```
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

**Eggs bank XP while closed**, so waiting costs nothing. On a fresh install the first egg inherits the memory you already have and usually hatches several forms in rather than as a blank — install, see an egg, open it, meet something that already reflects how much you've written. A buddy added *later* with `--add` starts at 0 and does hatch as a Hatchling, because XP banks per creature.

---

## The evolution ladder

Six sprites: the egg, then five forms, gaining detail at every step.

```
     ___             _^_             _^_             \|/            .\|/.          *.\|/.*
    /   \          ( ' ' )         ( ' ' )         ( ' ' )         ( ' ' )        \( ' ' )/
   ( +++ )          /+++\          <|+++|>         <|+++|>         /|+++|\         /|+++|\
    \___/            ^ ^            /   \           /|_|\           |___|          =|___|=
                                    ^   ^           ^   ^          /     \         ^     ^

     egg          Hatchling       Fledgling         Adept            Sage         Ascendant
  unhatched          0-19           20-39           40-59           60-79           80-100
```

Sprite 0 is the egg, so level stages start at sprite 1. That numbering is what let existing creatures survive the egg change without a migration.

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

Rarity is rolled from the seed, with a mark that carries the tier without relying on colour, so it still reads on a mono terminal or to a colour-blind user. On top of that, a **1% shiny** roll swaps the body motif for `$` (`<|+++|>` becomes `<|$$$|>`).

| Rarity | Odds | Mark |
|---|---|---|
| Common | 60% | |
| Uncommon | 25% | `+` |
| Rare | 10% | `*` |
| Epic | 4% | `**` |
| Legendary | 1% | `***` |

All of it is a pure function of the seed, so hand-editing `state.json` can't promote a Common into a shiny Legendary — `hydrate` recomputes the bones on every load and derived values win.

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

`xp_max` is the XP at level 100 and the one dial that controls pace. The default of **1500** puts a well-established vault around 65.

| Level | XP needed | Roughly |
|---|---|---|
| 5 | 4 | a couple of notes |
| 10 | 16 | ~5 durable memories |
| 20 | 61 | ~20 durable memories |
| 40 | 241 | ~80 durable memories |
| 65 | 634 | ~211 durable memories |
| 100 | 1,500 | ~500 durable memories |

Want it slower? `brainbuddy config xp_max 5000` triples the distance. It's your pet. And deleting memories never de-levels anyone: the high-water mark only rises, because tidying up shouldn't be punished.

---

## Display variants

`density` picks how much room it takes:

| Mode | Looks like | Notes |
|---|---|---|
| `minimal` | `◔` | one glyph, filling as you evolve (`◌ ○ ◔ ◑ ◕ ●`, or `. o c C O @` in ascii) |
| `compact` | `<><> Lv65` | default, ~10 columns inline |
| `full` | `<><> Drain Lv65` | adds the name |
| `sprite` | the 5-row creature | its own rows, right-aligned to `columns` |
| `ruler` | a column ruler | a measuring aid, not a creature |

`sprite_height 3` cuts the creature to three rows. It keeps the evolution beats but drops the head-top and the feet:

```
     _^_         (' ')
   ( ' ' )      <|+++|>
   <|+++|>       /   \
    /   \
    ^   ^
   height 5     height 3
```

`compose "<text>"` is the mode the statusline shim uses, and the one in the examples up top: your own text with the creature as a **left column**, sharing row one. Left rather than right on purpose, because a fixed-width column needs no measurement.

The column is boxed in dark grey by default. `config border false` drops the box and gets **two rows of height back**:

```
┌───────────┐                                    .\|/.    ████░░░░░░  my-brain ⎇ main
│   .\|/.   │  ████░░░░░░  my-brain ⎇ main      ( o o )   Drain · Sage · Lv65 █████░
│  ( o o )  │  Drain · Sage · Lv65 █████░       /|ooo|\
│  /|ooo|\  │                                    |___|
│   |___|   │                                   /     \
│  /     \  │
└───────────┘
```

Either way the column is pinned to the creature's **widest** form, so your text doesn't shift sideways the day it evolves into an Ascendant.

`sprite` does need a width, and a statusline script is handed nothing that is a terminal. So `density ruler` prints a column ruler instead of a creature: read the last digit you can see and pass it to `config columns <n>`.

`/brainbuddy-hide` takes the creature out without uninstalling anything. XP keeps banking while it's hidden, so it comes back further along than it left.

---

## The roster

You can keep several creatures. Only the **focused** one gains XP; the others hold their level and wait.

```
$ brainbuddy list
  ◕ Drain      Lv65   Sage       Common
* ○ Zask       Lv0    Hatchling  Legendary shiny

* = focused (the one gaining xp)
```

That's why `/brainbuddy-new` asks before it acts: `--replace` retires the current buddy and focuses a new egg, `--add` keeps it active and focuses a new egg.

**Neither one deletes anything.** `--replace` retires, which drops it out of the active roster while keeping its banked XP; `focus <name>` brings it back. `--add` states the tradeoff and asks for `--yes`, since a new egg takes focus and the current buddy stops gaining. There's **no level requirement** — the tradeoff is identical at level 12 and level 99, so it's a decision to make rather than a gate to clear.

New creatures start at 0, always, because XP banks per creature rather than deriving from your total memory size.

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

Five are slash commands in Claude Code, so plain language reaches them without the CLI: `/brainbuddy`, `/brainbuddy-new`, `/brainbuddy-hatch`, `/brainbuddy-hide`, `/brainbuddy-show`.

| Setting | Values | Default |
|---|---|---|
| `provider` | `claude` or `vault` | `claude` |
| `vault_root` | path, for `provider vault` | |
| `xp_max` | XP at level 100, the pace dial | `1500` |
| `density` | `minimal` `compact` `full` `sprite` `ruler` | `compact` |
| `sprite_height` | `3` or `5` | `5` |
| `border` | box the `compose` column, costs 2 rows | `true` |
| `columns` | right-align width for `sprite` | `0` |
| `unicode` | `true` or `false` | `true` |
| `hidden` | `true` or `false` | `false` |

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

Only two steps need you: hatching the egg, and eventually starting another. Levelling and evolutions happen on their own as your vault grows.

---

## It never opens your memories

brainbuddy sizes your memory system by **counting files**. `glob` and `stat`, and that's all: it never calls `open()`, never reads a byte of content, never parses frontmatter. That isn't a promise about what it does with your data, it's a statement that it never has your data.

Two tests enforce it — a runtime trap that patches every file-reading builtin and asserts none fire during a measurement, and a static pass that tokenizes `metric.py` and fails if a reader appears in the code at all.

No network calls either: no telemetry, no update check, no analytics. And it never prints a path it matched, in any mode including `doctor`, because filenames alone leak more than people expect.

---

## Under the hood

**Two providers.** `claude` counts stock Claude Code memory under `~/.claude/projects/*/memory`; `vault` counts a layout you point at with `vault_root`. If `doctor` reports 0, it's one of those two, not a reinstall.

**A cache, because the statusline is a hot path.** `render` reads a cached XP value and spawns the recount in the background, blocking only on a cold start.

**The high-water mark is the anti-punishment mechanism.** New XP is credited as the delta above the highest total ever seen, so deleting notes can't take a level away, and a render before your first hatch can't burn the XP waiting for it.

**State lives at `~/.claude/brainbuddy/`** — the roster, settings, and the XP cache.

---

## Provenance

Anthropic shipped a terminal pet in Claude Code (`/buddy`, April 2026). Nice idea, no progression: species and stats are recomputed from your user ID every session and never change. brainbuddy is a clean-room rebuild of the *concept* with the missing half added, growth you actually earn.

No code, species names, sprite art, stat names, or hashing details were taken from it. Not affiliated with or endorsed by Anthropic.

---

## Tests

```bash
python3 tests/test_brainbuddy.py
```

Synthetic fixtures in a temp directory; no real memory directory is touched.
