# brainbuddy

A terminal creature that lives in your Claude Code statusline, hatches from an egg, and evolves through five forms as your memory system grows.

Compact, inline in your statusline:

```
◔+ Lv35     ->  <><> Lv35
```

Or the full creature on its own rows, right-aligned (`density sprite`):

```
████░░░░░░  eric-brain ⎇ main
                                                  ___
                                                ( > < )
                                                <|///|>
                                                 /   \
                                                 ^   ^
                                                Drain Lv35
```

```
    ___        Rura  Wisp Uncommon

  ( - - )      Level 35   Fledgling   ▪▪▪▫▫▫
  <|~~~|>      █████░░░░░  632 / 648 xp
   /   \       Next form at level 40 (801 xp)
   ^   ^
               Recall 70  Depth 65  Drive 52  Streak 70  Ferment 40
```

## It never opens your memories

This is the important bit, so it goes first.

brainbuddy sizes your memory system by **counting files**. It uses `glob` and `stat`, and that's all. It never calls `open()`, never reads a byte of content, never parses frontmatter, never counts words.

That isn't a promise about what it does with your data. It's a statement that it never has your data. Memory directories hold notes about work, clients, and employers, and the safest way to handle that is to never load it. The guarantee is enforced two ways in the test suite: a runtime trap that patches every file-reading builtin and asserts none fire during a measurement, and a static pass that tokenizes `metric.py` and fails if a reader appears anywhere in the code.

It also makes no network calls of any kind. There is no telemetry, no update check, no analytics.

One consequence worth knowing: brainbuddy never prints a path it matched, in any mode including `doctor`. Filenames alone leak more than people expect.

## Install

```bash
git clone <this repo> && cd brainbuddy
./install.sh
```

The installer composes with an existing statusline rather than replacing it. If `statusLine.command` already points at a script, it appends a fenced block and keeps a `.pre-brainbuddy.bak`. If nothing is configured, it writes one. `./install.sh --uninstall` strips the block back out.

Using a vault layout instead of stock Claude Code memory:

```bash
./install.sh --vault ~/dev/my-brain/MyBrain
```

The installer leaves an egg in your statusline. Open it:

```bash
/brainbuddy-hatch
```

## How levelling works

XP is a weighted count of memory artifacts:

| Source | Weight |
|---|---|
| durable memories | ×3 |
| knowledge notes | ×2 |
| projects | ×2 |
| session logs | ×1 |
| decision records | ×2 |

Durable facts are worth more than session logs because they cost more to produce.

```
level = floor(100 * sqrt(xp / 5000))
```

A square root curve, so early memories move the needle and later ones don't. Level 100 sits at 5,000 XP.

| Level | Form |
|---|---|
| 0-19 | Hatchling |
| 20-39 | Fledgling |
| 40-59 | Adept |
| 60-79 | Sage |
| 80+ | Ascendant |

Level keeps climbing past 100. Evolution stops at Ascendant.

## The egg is a state, not a level

A buddy is an **egg** until you hatch it, whatever level it is. The statusline shows egg art and no level, `/brainbuddy-hatch` opens it, and only then do you see what you got. Level 0 is a Hatchling, a baby with a face, not an egg.

Eggs bank XP while closed. So on a fresh install the first egg inherits the memory you already have, and hatching reveals a buddy several forms in rather than a level 0 blank. That reveal is the point of the zero state: install, see an egg, open it, meet something that already reflects how much you've written.

A buddy added later with `/brainbuddy-new --add` starts at 0 and does hatch as a Hatchling, because XP banks per creature.

## Display modes

`density` picks how much room it takes:

| mode | looks like | notes |
|---|---|---|
| `minimal` | `◔` | one glyph |
| `compact` | `<><> Lv35` | default, ~10 columns inline |
| `full` | `<><> Drain Lv35 +` | adds name and rarity mark |
| `sprite` | the 5-row creature | its own rows, gains detail each evolution |

`sprite_height 3` cuts the creature to three rows. It keeps the evolution beats but **drops detail**: the head-top and the feet come off, so the Fledgling loses its `___` and `^   ^`. Use it when vertical space matters more than the full silhouette.

`sprite` right-aligns to the `columns` setting, which has to be declared rather than measured. A statusline script is handed nothing that is a terminal: stdin is the JSON pipe, stdout is captured, stderr isn't a tty either, and `/dev/tty` isn't attached. To find the number, `density ruler` prints a column ruler as the statusline, so read the last digit you can see and pass it to `config columns <n>`.

`compose "<text>"` is the other way in, and the one the statusline shim uses. It merges your own statusline text with the creature as a **left column**, sharing row one with your first row so it reads as a column starting at the top. Left rather than right on purpose: a fixed-width column needs no measurement at all, so the host's box can be any width and the art still lands whole.

In `sprite` mode put the call at the **end** of your statusline script, since it emits its own rows.

## The roster

At level 100 you can hatch another egg. New creatures **start at 0**, always.

That works because XP banks per creature rather than deriving from your total memory size. Only the **focused** creature gains XP; the others hold their level and wait. So focus is a real choice about who you're building, and a second egg doesn't inherit the hundred levels the first one earned.

Deleting memories never de-levels anyone. The high-water mark only rises, because tidying up shouldn't be punished.

## Commands

```
brainbuddy card              the full creature card
brainbuddy new [name]        lay an egg (--replace or --add)
brainbuddy hatch             open the egg, revealing the level it earned
brainbuddy focus <name>      choose who banks new xp
brainbuddy list              the roster
brainbuddy rename <old> <new>
brainbuddy retire <name>     retires, keeps the record and its xp
brainbuddy hide              drop it from the statusline, keeps banking xp
brainbuddy show              put it back
brainbuddy config [key val]  provider, vault_root, xp_max, density, columns, unicode, hidden
brainbuddy simulate <xp>     preview any level without touching real state
brainbuddy doctor            what can it see, and why is it zero
brainbuddy render            the statusline segment
brainbuddy compose "<text>"  your statusline text, creature as a left column
```

`/brainbuddy-new`, `/brainbuddy-hatch`, `/brainbuddy-hide` and `/brainbuddy-show` are also their own slash commands, so "hatch it" or "hide my brainbuddy" reaches them without going through `/brainbuddy`.

## Provenance

Anthropic shipped a terminal pet in Claude Code (`/buddy`, April 2026). It's a nice idea with no progression: species and stats are recomputed from your user ID every session and never change. brainbuddy is a clean-room rebuild of the *concept* with the missing half added, growth you actually earn.

No code, species names, sprite art, stat names, or hashing details were taken from it. The species list, the five stats, the sprites, and the levelling system here are original. Not affiliated with or endorsed by Anthropic.

## Tests

```bash
python3 tests/test_brainbuddy.py
```

Fixtures are synthetic and generated into a temp directory. No real memory directory is touched.
