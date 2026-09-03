# brainbuddy

A terminal creature that lives in your Claude Code statusline, hatches from an egg, and grows on a diet of your own memories.

```
day one
┌───────────┐
│    ___    │  ████░░░░░░  my-brain ⎇ main
│   /   \   │  🥚 Zask · egg · /brainbuddy-hatch
│  ( ooo )  │
│   \___/   │
└───────────┘

a few hundred notes later
┌───────────┐
│   .\|/.   │  ████░░░░░░  my-brain ⎇ main
│  ( o o )  │  🥚 Drain · Sage Lv65 █████░
│  /|ooo|\  │
│   |___|   │
│  /     \  │
└───────────┘
```

Every durable note you write is XP, so it grows as your second brain grows, through five forms from hatchling to fully grown. Not a streak you can drop by taking a weekend off, and not a timer. Feed it or it sits there. That's the whole loop.

The egg banks XP from the moment it exists, including everything you'd already written before you installed anything. So the first hatch isn't a blank slate, it's a reveal:

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

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/smejkaldesign/brainbuddy/main/bootstrap.sh | bash
```

Then, in Claude Code:

```
/brainbuddy-hatch
```

That's it. The installer wraps whatever statusline you already have rather than replacing it, lays your first egg, and tells you how to open it. The hatch is a short guided setup the first time: it goes looking for your notes, offers what it found with a file count each, and opens the egg at whatever level your writing has already earned.

**Requirements:** bash, Python 3.9 or newer, tar, and either curl or wget. Nothing else; brainbuddy is stdlib Python with no dependencies. Pipe the script to `bash`, not to `sh`, or it will tell you to.

**Windows:** run it under **WSL** or **Git Bash**. Both are supported routes. PowerShell and cmd are not, because the statusline shim is a shell script.

The bootstrap passes any flags straight through to the installer, so you can point it at your notes in the same breath:

```bash
curl -fsSL https://raw.githubusercontent.com/smejkaldesign/brainbuddy/main/bootstrap.sh | bash -s -- --folder ~/notes
```

### Two ways this goes

**You already keep notes.** An Obsidian vault, a folder of markdown, Claude Code's own memory: the hatch flow finds it, counts it, and your first creature opens several forms in. This is the moment the whole design is built around, and it's why the egg banks XP instead of starting everyone at zero.

**You don't keep notes yet.** Then there's nothing to count and your buddy sits at level 0, which is a fair reading rather than a bug. The hatch flow offers to set a memory system up, and the climb from there is the point. See [Where XP comes from](#where-xp-comes-from).

---

## Privacy promise

Short enough to check yourself.

- **It counts your files without ever opening them.** The only filesystem calls in `metric.py` are `glob` and `stat`. It never calls `open()` on a note, never reads a byte of content, never parses frontmatter, and the test suite fails if a code path tries. That isn't a promise about what it does with your data, it's a statement that it never has your data.
- **It never prints a path it matched**, in any mode including `doctor`, which reports a home-relative root and counts rather than filenames. Filenames alone leak more than people expect.
- **All state is local**, at `~/.claude/brainbuddy/`. The roster, your settings, and the XP cache. Nothing else, nowhere else.
- **Zero network at runtime.** No telemetry, no analytics, no background phone-home. Nothing brainbuddy runs on your statusline ever touches the network, on any render.
- **The only network calls are the ones you run on purpose.** Two of them: the installer downloading a release tarball from `api.github.com`, and the version check in `brainbuddy update` and `brainbuddy doctor --check`, which reads pypi's public package metadata to compare version numbers. One request per invocation, no retries, no caching. Both are unauthenticated GETs, and neither sends anything about you or your memory.

Three tests enforce this. A runtime trap patches every file-reading builtin and asserts none fire during a measurement. A static pass tokenizes `metric.py` and fails if a reader appears in the code at all. A third records every socket call and fails if anything other than `update` and `doctor --check` opens one, which is the rule that keeps the statusline honest: it renders several times a second, so a background check there would be indistinguishable from telemetry. On top of that a leak guard runs in CI and as a `pre-push` hook, failing the build if an absolute home path or a vault-shaped filename ever reaches the repo.

---

## Other ways to install

**Clone it** if you want to read the code first or contribute. This is the same installer the bootstrap runs:

```bash
git clone https://github.com/smejkaldesign/brainbuddy && cd brainbuddy
./install.sh
```

**As a Claude Code plugin**, coming soon; the manifest ships in this repo and the marketplace listing follows.

**From PyPI**, once the first release is tagged (`pipx install brainbuddy`): you get the CLI and nothing else. It does not wire your statusline, which is most of what brainbuddy is. Use it if you want the commands on your PATH; run `install.sh` or the bootstrap if you want a creature.

**Behind a mirror, or offline?** `BRAINBUDDY_TARBALL` is the bootstrap's escape hatch. Set it to a URL or to a tarball already on disk, and it installs from that instead of reaching for a release.

### Installer flags

| Flag | What it does |
|---|---|
| `--folder <path>` | count a folder of markdown notes (the usual case for an existing notes dir) |
| `--vault <path>` | count a structured vault layout |
| `--statusline <cmd>` | wrap this command instead of the one in `settings.json` |
| `--inline` | one-line segment after your statusline instead of the boxed column |
| `--no-wire` | install the library and commands only, wire it yourself |
| `--no-commands` | skip the slash commands, when something else already ships them |
| `--uninstall` | unwire, restore your old statusline, remove the commands |

Re-running it is safe and is how you pick up new commands. It won't wrap itself twice and it leaves an existing buddy alone. If you installed a version before wrapping existed, re-running strips the block it appended to your script.

### How the wiring works

The installer **wraps** your existing statusline rather than replacing or editing it. It points `statusLine.command` at a small generated shim, and the shim runs whatever command was there before, on the same stdin Claude Code hands it, then draws the creature to the left of that output. Your own script is never modified.

That's why it works with a statusline it can't parse: `bash ~/statusline.sh`, a `~`-relative path, a one-liner, or a script that ends in `exit 0`. It keeps a `settings.json.pre-brainbuddy.bak`, and `--uninstall` puts your original command back.

**Project-level statuslines need one manual step.** The installer only reads and writes `~/.claude/settings.json`. If a repo sets its own `statusLine` in `<repo>/.claude/settings.json`, that wins inside the repo and the installer never sees it. Wrap it explicitly, then point the project at the shim:

```bash
./install.sh --statusline "/path/to/repo/.claude/statusline.sh"
# then in <repo>/.claude/settings.json:
#   "statusLine": { "type": "command", "command": "~/.claude/brainbuddy/statusline-brainbuddy.sh" }
```

`wrapped-command` is a single file, so one command gets wrapped for every repo. Pick the statusline you want everywhere.

---

## The first hatch asks two questions

`/brainbuddy-hatch` is a short guided setup the first time, because the two things it can't
guess are the two that decide everything afterwards:

1. **Where do your memories live?** It looks for an Obsidian vault, a notes folder and Claude
   Code's own memory, then offers what it found with a file count each rather than asking you
   cold. That sets `provider` and `vault_root`.
2. **Score what's already written, or start from 0?** Scoring is the default and opens the egg
   several forms in, which is the moment the whole design is built around. `--from-zero`
   baselines what's there so only new notes count, for people who'd rather have the climb.

Both questions are skipped on later eggs, which inherit the setup the first one established.
Neither is asked if there's already a source configured and counting.

## The session counter

To the right of the level, the caption shows what your buddy has eaten **in this session**:

```
🥚 Neux · Sage Lv66 +16 XP ██░░░░
```

It baselines the first time a session draws itself, so a new session opens at nothing rather
than claiming credit for the whole vault, and it's tracked per session id because several are
usually open at once. It stays hidden until there's something to show, so statusline width
isn't spent on `+0 XP` all day.

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

**Eggs bank XP while closed**, so waiting costs nothing. On a fresh install the first egg inherits the memory you already have and usually hatches several forms in rather than as a blank. Install, see an egg, open it, meet something that already reflects how much you've written. A buddy added *later* with `--add` starts at 0 and does hatch as a Hatchling, because XP banks per creature.

---

## The evolution ladder

Six sprites: the egg, then five forms, gaining detail at every step.

```
    ___        _^_        _^_        \|/       .\|/.     *.\|/.*
   /   \     ( ' ' )    ( ' ' )    ( ' ' )    ( ' ' )   \( ' ' )/
  ( ooo )     /+++\     <|+++|>    <|+++|>    /|+++|\    /|+++|\
   \___/       ^ ^       /   \      /|_|\      |___|     =|___|=
                         ^   ^      ^   ^     /     \    ^     ^

    egg     Hatchling  Fledgling    Adept       Sage    Ascendant
 unhatched     0-19      20-39      40-59      60-79     80-100
```

Sprite 0 is the egg, so level stages start at sprite 1. That numbering is what let existing creatures survive the egg change without a migration.

---

## Species and rarity

Eight species. The eyes and the body motif come from the species, so a Bramble is recognisable at a glance.

```
     _^_            _^_            _^_            _^_
   ( o o )        ( - - )        ( ^ ^ )        ( . . )
   <|ooo|>        <|~~~|>        <|***|>        <|...|>
    /   \          /   \          /   \          /   \
    ^   ^          ^   ^          ^   ^          ^   ^
     Mote           Wisp          Ember           Pip

     _^_            _^_            _^_            _^_
   ( o o )        ( v v )        ( ' ' )        ( > < )
   <|===|>        <|###|>        <|+++|>        <|///|>
    /   \          /   \          /   \          /   \
    ^   ^          ^   ^          ^   ^          ^   ^
     Fen          Bramble          Nim           Quill
```

Rarity is rolled from the seed, with a mark that carries the tier without relying on colour, so it still reads on a mono terminal or to a colour-blind user. On top of that, a **1% shiny** roll remakes the body motif: symbols become `$` (`<|+++|>` becomes `<|$$$|>`) and letters go uppercase (`<|ooo|>` becomes `<|OOO|>`).

| Rarity | Odds | Mark |
|---|---|---|
| Common | 60% | |
| Uncommon | 25% | `+` |
| Rare | 10% | `*` |
| Epic | 4% | `**` |
| Legendary | 1% | `***` |

All of it is a pure function of the seed, so hand-editing `state.json` can't promote a Common into a shiny Legendary; `hydrate` recomputes the bones on every load and derived values win.

---

## Where XP comes from

XP is a weighted count of markdown files in a memory system, so brainbuddy needs one to point at. Three providers, set with `/brainbuddy config provider <name>`:

| Provider | Counts | Point it somewhere |
|---|---|---|
| `claude` | stock Claude Code memory, `~/.claude/projects/*/memory/*.md` | default, nothing to set |
| `folder` | every `.md` under a directory, recursively | `config vault_root ~/notes` |
| `vault` | a structured vault, weighted per directory | `config vault_root ~/brain` |

`brainbuddy doctor` says which one is live, whether the root is actually there, what it counted, and what your buddy actually banked of that. Those last two diverge if you hatched with `--from-zero`:

```
$ brainbuddy doctor
provider: folder (folder of notes)
root: ~/notes (found)
  notes      9
source xp 18 -> level 10
Zask banked 18 -> level 10 (Hatchling)
```

A zero reading has three different causes, and `doctor` names the one you've got rather than telling everyone to check their config:

- **the root isn't there**: wrong path, or Claude Code hasn't written memory yet
- **the root is real but empty**: nothing to do but write things down
- **the root has markdown the provider's layout doesn't match**: pointing `vault` at a plain notes folder does this, and the fix is `provider folder`

**No memory system at all?** Then there's nothing to count and your buddy sits at level 0, which is a fair reading rather than a bug. The installer and `doctor` both hand you a prompt for it:

> "Set up a persistent memory system for this project: one markdown file per durable fact in your memory directory, an index listing them, and write to it as we work."

XP follows on the next render once files start landing there.

---

## How levelling works

XP is a weighted count of memory artifacts. Durable facts are worth more than session logs because they cost more to produce, and generated index files are excluded so they can't inflate the count for free.

`claude` counts one source at ×3, `folder` counts every note at ×2, and `vault` weights per directory:

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

`density` picks how much room the **inline** segment takes, so it applies to `render` and to an `--inline` install, not to the boxed column:

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

`compose "<text>"` is what the installed shim uses by default, and the mode in the examples up top: your own text with the creature as a **left column**, sharing row one. Left rather than right on purpose, because a fixed-width column needs no measurement. Install with `--inline` if you'd rather have the one-line segment tacked onto the end of your statusline.

The column is boxed in dark grey by default. `config border false` drops the box and gets **two rows of height back**:

```
┌───────────┐
│   .\|/.   │  ████░░░░░░  my-brain ⎇ main
│  ( o o )  │  🥚 Drain · Sage Lv65 █████░
│  /|ooo|\  │
│   |___|   │
│  /     \  │
└───────────┘

  .\|/.    ████░░░░░░  my-brain ⎇ main
 ( o o )   🥚 Drain · Sage Lv65 █████░
 /|ooo|\
  |___|
 /     \
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

**Neither one deletes anything.** `--replace` retires, which drops it out of the active roster while keeping its banked XP; `focus <name>` brings it back. `--add` states the tradeoff and asks for `--yes`, since a new egg takes focus and the current buddy stops gaining. There's **no level requirement**, since the tradeoff is identical at level 12 and level 99, so it's a decision to make rather than a gate to clear.

New creatures start at 0, always, because XP banks per creature rather than deriving from your total memory size.

---

## Commands

```
brainbuddy new [name]        lay an egg (--replace or --add, --yes to confirm)
brainbuddy hatch [--from-zero]  open the egg; --from-zero starts at 0 instead
brainbuddy card              the full creature card
brainbuddy list              the roster
brainbuddy focus <name>      choose who banks new xp, un-retires
brainbuddy rename <old> <new>
brainbuddy retire <name>     retires, keeps the record and its xp
brainbuddy hide / show       drop it from the statusline, or bring it back
brainbuddy config [key val]  see settings, or set one
brainbuddy simulate <xp>     preview any level without touching real state
brainbuddy sources           what it can count, and what to do if that's nothing
brainbuddy doctor            what can it see, and why is it zero
brainbuddy doctor --check    the same, plus a version check against pypi
brainbuddy update            ask pypi whether there's a newer brainbuddy
brainbuddy render            the one-line statusline segment
brainbuddy compose "<text>"  your statusline text, creature as a left column
brainbuddy refresh           recompute the xp cache
```

Five are slash commands in Claude Code, so plain language reaches them without the CLI: `/brainbuddy`, `/brainbuddy-new`, `/brainbuddy-hatch`, `/brainbuddy-hide`, `/brainbuddy-show`.

After an `install.sh` or bootstrap install there's no `brainbuddy` on your PATH: the library is imported by the statusline, not installed as a binary. The five slash commands above reach everything you'd normally want. For the rest, alias it:

```bash
alias brainbuddy='PYTHONPATH="$HOME/.claude/brainbuddy/lib" python3 -m brainbuddy.cli'
```

The `brainbuddy ...` examples in this README assume that alias, or a `pipx install`, which does put the binary on your PATH.

| Setting | Values | Default |
|---|---|---|
| `provider` | `claude`, `folder` or `vault` | `claude` |
| `vault_root` | path, for `folder` and `vault` | |
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

## Under the hood

**Three providers.** `claude` counts stock Claude Code memory under `~/.claude/projects/*/memory`, `folder` walks any directory for `.md`, and `vault` counts a weighted layout. See [Where XP comes from](#where-xp-comes-from). If `doctor` reports 0 it's the provider, the root, or an empty memory system, never a reinstall.

**The shim wraps, it doesn't edit.** `statusLine.command` points at a generated shim; your original command is saved next to it and run by it, on the same stdin. Nothing is appended to your files, so there's no case where the wiring lands somewhere unreachable and reports success. A script that already calls brainbuddy itself is detected and left alone rather than wrapped twice.

**A cache, because the statusline is a hot path.** `render` reads a cached XP value and spawns the recount in the background, blocking only on a cold start. Counting the memory system is never done on that path.

**The high-water mark is the anti-punishment mechanism.** New XP is credited as the delta above the highest total ever seen, so deleting notes can't take a level away, and a render before your first hatch can't burn the XP waiting for it.

**Counting is all it ever does.** The measurement path is `glob` and `stat` only, enforced by a runtime trap and a static check. See [Privacy promise](#privacy-promise).

**State lives at `~/.claude/brainbuddy/`** holds the roster, settings, and the XP cache.

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

CI runs the suite on Python 3.9 through 3.13, plus a leak guard that fails the
build if an absolute home path or a vault-shaped filename reaches the repo.
There's a `pre-push` copy of that guard for local use, enabled with:

```bash
git config core.hooksPath .githooks
```

Stdlib only. No dependencies to install, for the tests or for the tool.

---

## License

MIT. See [LICENSE](LICENSE).
