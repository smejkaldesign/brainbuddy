<p align="center">
  <img src="site/assets/terminalcreature-logo.svg" width="247" alt="TERMINAL CREATURE" />
</p>

<h3 align="center">A small creature lives in your statusline. It is always hungry.</h3>

<p align="center">
  An egg sits in your terminal's statusline, and it eats what you remember.<br />
  Every note you write is a meal, every meal is XP. Keep it fed and it hatches, then grows through five forms<br />
  across eight species, with a one-in-a-hundred shiny. It counts your files and never reads them. How rare is yours?
</p>

<br />

<p align="center">
  <a href="https://terminalcreature.com"><strong>Website</strong></a> &nbsp;&middot;&nbsp;
  <a href="https://pypi.org/project/terminalcreature/"><strong>PyPI</strong></a> &nbsp;&middot;&nbsp;
  <a href="CHANGELOG.md"><strong>Changelog</strong></a> &nbsp;&middot;&nbsp;
  <a href="https://github.com/smejkaldesign/terminalcreature/issues"><strong>Report a bug</strong></a> &nbsp;&middot;&nbsp;
  <a href="CONTRIBUTING.md"><strong>Contribute</strong></a>
</p>

<p align="center">
  <a href="https://pypi.org/project/terminalcreature/"><img src="https://img.shields.io/pypi/v/terminalcreature?color=ffb627&label=pypi" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/python-3.9%E2%80%933.13-3776AB?logo=python&logoColor=white" alt="Python 3.9 to 3.13" />
  <a href="https://github.com/smejkaldesign/terminalcreature/actions/workflows/ci.yml"><img src="https://github.com/smejkaldesign/terminalcreature/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <img src="https://img.shields.io/badge/dependencies-0-4ade80" alt="Zero dependencies" />
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT" /></a>
</p>

```
day one                                  a few hundred notes later
+-----------+                            +-----------+
|    ___    |  [====......]  my-brain    |   .\|/.   |  [====......]  my-brain
|   /   \   |  Unhatched                 |  ( o o )  |  Drain . Sage Lv65 [=====.] +16 XP
|  ( ooo )  |                            |  /|ooo|\  |
|   \___/   |                            |   |___|   |
+-----------+                            |  /     \  |
                                         +-----------+
```

<p align="center"><sub>Shown in ascii mode. With <code>unicode true</code> (the default) the box is drawn with line glyphs and the bars with block characters.</sub></p>

---

## Why terminalcreature exists

A second brain only pays off if you keep writing to it, and nothing in a terminal rewards that. Streaks punish weekends. Timers reward sitting still. terminalcreature rewards the one thing that matters: a durable note landed on disk.

Every note you write is XP. The creature evolves through five forms as your vault grows, and it never loses a level when you tidy up. Not a streak you can drop, not a timer. Feed it or it sits there. That's the whole loop.

## How It Works

```
your notes                terminalcreature                    statusline
----------------  -->  ----------------------  -->  ---------------------------
~/.claude/projects/*/     glob + stat only           +-----------+
  memory/*.md             (never open())             |   ( ' ' ) |  Zask . Adept Lv44
~/notes/**/*.md                |                     |  <|+++|>  |  [===...] +12 XP
a structured vault        weighted count = xp        |   /|_|\   |
                               |                     +-----------+
                     level = 100 * sqrt(xp / xp_max)
                               |
                     sprite = f(level, seed)
```

The egg banks XP from the moment it exists, including everything you'd written before you installed anything. So the first hatch isn't a blank slate, it's a reveal:

```
$ terminalcreature hatch

  the egg cracks

       _^_
     ( ' ' )
      /$$$\
       ^ ^

  Zask, a Legendary Nim (shiny)
  Lv41 Adept
```

## Works with

One creature, any terminal, any agent. It lives in an agent's own statusline where the agent has one, shows up as a one-line card after each turn where the agent has a hook or plugin channel instead, and draws in tmux or your prompt everywhere else. XP comes from whichever coding agents have written memory on this machine, not just the one you're looking at.

| Agent | Native statusline | Turn-end card | Prompt or tmux | Feeds XP |
| :--- | :---: | :---: | :---: | :---: |
| Claude Code | ✓ | – | ✓ | ✓ |
| Cursor CLI | ✓ | – | ✓ | ✓ |
| GitHub Copilot CLI | ✓ | – | ✓ | ✓ |
| Qwen Code | ✓ | – | ✓ | ✓ |
| Factory Droid | ✓ | – | ✓ | ✓ |
| Codex CLI | – | ✓ | ✓ | ✓ |
| Gemini CLI | – | ✓ | ✓ | ✓ |
| Mistral Vibe | – | ✓ | ✓ | – |
| Augment auggie | – | ✓ | ✓ | – |
| opencode | – | ✓ | ✓ | ✓ |
| Amp | – | ✓ | ✓ | ✓ |
| Goose | – | – | ✓ | ✓ |
| Continue | – | – | ✓ | ✓ |
| Kiro | – | – | ✓ | ✓ |
| Cline | – | – | ✓ | ✓ |
| Crush | – | – | ✓ | ✓ |
| aider | – | – | ✓ | – |
| Warp | – | – | ✓ | – |

**Native statusline** means `install --host <name>` wires it and the session counter works. The Cursor and Copilot contracts were read off the shipped CLI bundles and exercised live; Qwen's comes from its docs. Droid's is docs-only and has not been run against a real install, so treat it as a first draft and file a bug if it misbehaves.

**Turn-end card** means the agent has no statusline but does have a documented turn-end hook or plugin channel, so `install --host <name>` gives it a one-line creature card after each turn instead. All six contracts were read from the hosts' docs as of September 2026; see [the turn-end card](#codex-gemini-vibe-auggie-opencode-amp-the-turn-end-card) for what each one writes.

| Surface | How |
| :--- | :--- |
| tmux | `terminalcreature snippet tmux`, or the tpm plugin |
| Starship | `terminalcreature snippet starship` |
| zsh | `terminalcreature snippet zsh`, as the right prompt |
| fish | `terminalcreature snippet fish` |
| oh-my-posh | `terminalcreature snippet omp` |
| WezTerm | `terminalcreature snippet wezterm` |
| Kitty, Zellij, iTerm2 | manual: call `render --format plain` from their status hooks |
| Ghostty, Alacritty, Windows Terminal | no status area of their own; use the prompt or tmux inside them |

---

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/smejkaldesign/terminalcreature/main/bootstrap.sh | bash
```

Then, in Claude Code:

```
/creature-hatch
```

That's it. The installer wraps whatever statusline you already have rather than replacing it, lays your first egg, and tells you how to open it. The hatch is a short guided setup the first time: it looks for your notes, offers what it found with a file count each, and opens the egg at whatever level your writing has already earned.

Point it at your notes in the same breath; the bootstrap passes flags straight through to the installer:

```bash
curl -fsSL https://raw.githubusercontent.com/smejkaldesign/terminalcreature/main/bootstrap.sh | bash -s -- --folder ~/notes
```

### Requirements

| | |
| :--- | :--- |
| **Runtime** | Python 3.9 or newer, stdlib only. No dependencies, ever. |
| **Installer** | bash, tar, and either curl or wget. Pipe to `bash`, not `sh`. |
| **macOS / Linux** | Supported, including the stock macOS bash 3.2. |
| **Windows** | Under **WSL** or **Git Bash**. PowerShell and cmd are not, because the statusline shim is a shell script. |

### The first hatch asks three questions

`/creature-hatch` guides the first egg, because the things it can't guess are the ones that decide everything afterwards:

1. **Where do your memories live?** It looks for an Obsidian vault, a notes folder, and Claude Code's own memory, then offers what it found with a file count each. That sets `provider` and `vault_root`.
2. **Score what's already written, or start from 0?** Scoring is the default and opens the egg several forms in. `--from-zero` baselines what's there so only new notes count, for people who'd rather have the climb.
3. **What's it called?** Two fresh ideas from `terminalcreature names`, your own, or let the egg name itself at the reveal. Until it hatches the statusline just says Unhatched.

Later eggs inherit the first two answers. The name is asked for every egg.

### Other ways to install

| Route | What you get |
| :--- | :--- |
| **Clone and run `./install.sh`** | The same installer the bootstrap runs, if you want to read the code first. |
| **`pipx install terminalcreature`** | The CLI on your PATH and nothing else. It does not wire your statusline, which is most of what terminalcreature is. |
| **Claude Code plugin** | Coming soon. The manifest and marketplace listing ship in this repo. |
| **Offline or behind a mirror** | Set `TERMINALCREATURE_TARBALL` to a URL or a tarball on disk and the bootstrap installs from that. |

### Installer flags

| Flag | What it does |
| :--- | :--- |
| `--folder <path>` | count a folder of markdown notes (the usual case for an existing notes dir) |
| `--vault <path>` | count a structured vault layout |
| `--statusline <cmd>` | wrap this command instead of the one in `settings.json` |
| `--inline` | one-line segment after your statusline instead of the boxed column |
| `--no-wire` | install the library and commands only, wire it yourself |
| `--no-commands` | skip the slash commands, when something else already ships them |
| `--uninstall` | unwire, restore your old statusline, remove the commands |
| `--host <name>` | wire `cursor`, `copilot`, `qwen`, `droid` or `all` instead of Claude Code; a card host (`codex`, `gemini`, `vibe`, `auggie`, `opencode`, `amp`) passes through to the CLI |

The CLI's own `install` takes the same `--host`, `--inline` and `--statusline`, plus `--box` for the reverse of `--inline` on the hosts that default to inline. The two are opposites, so passing both is an error.

Re-running is safe and is how you pick up new commands. It won't wrap itself twice and it leaves an existing buddy alone.

### Cursor, Copilot, Qwen, Droid

The bootstrap above installs the library and wires Claude Code. The same installer wires the other native hosts, one at a time or all at once:

```bash
./install.sh --host cursor       # or copilot, qwen, droid
./install.sh --host all          # every host that's installed on this machine
```

Once the library is in place the CLI does the same without the installer, and undoes it:

```bash
terminalcreature install --host copilot [--inline|--box] [--statusline <cmd>]
terminalcreature uninstall --host copilot
```

Each host gets its own shim and its own backup of its settings file, so wiring Cursor never touches Claude Code's `settings.json`. Three things worth knowing:

- **Cursor and Qwen default to inline.** Their custom statusline replaces the native footer rather than adding rows to it, so the one-line segment keeps whatever the wrapped command printed on the same line. On the other hosts `--inline` opts in; on these two `--box` opts out and puts the creature on the left as a column.
- **Cursor says how wide it is.** It hands the shim a `render_width_chars`, and the segment is capped to it when no `--width` is given, so the creature never wraps the footer.
- **Copilot's settings file is JSONC.** Comments are tolerated on read, the file is written back as plain JSON, and the backup keeps the commented original. `uninstall` restores that backup byte for byte when nothing else has changed since.

`terminalcreature doctor` lists every host it knows, whether it's installed, and whether it's wired.

### Codex, Gemini, Vibe, auggie, opencode, Amp: the turn-end card

These six have no statusline to wire, but each has a documented channel that shows a line to you when a turn ends. `install --host <name>` uses it: one hook entry for Codex CLI, Gemini CLI, Mistral Vibe and Augment auggie, one small plugin file for opencode and Amp. `--host all` covers every card host whose config dir exists, plugin hosts included.

```bash
terminalcreature install --host codex        # or gemini, vibe, auggie
terminalcreature install --host opencode     # or amp
terminalcreature uninstall --host codex
```

From then on the host shows a one-line card after a turn:

```
<oo> Kein Lv24 ███░░░░░ +40 xp  evolved into Fledgling
```

Short sprite, name, level, bar, the XP eaten this session when there is some, and the evolution when a stage moved. Plain text, since the host draws it, and never a path, since the host may log it. The card credits session XP the same way the statusline does, so the roster and level are one number everywhere.

**Cadence.** A card after every turn would be noise, so `config hookcard <value>` decides when it shows:

| Value | When the card shows |
| :--- | :--- |
| `changes` | the first turn of a session, then whenever the session's XP or stage changed, otherwise every tenth turn. The default. |
| `always` | every turn |
| `off` | never. The hook stays installed and XP keeps banking. |

A quiet turn prints nothing (Gemini gets `{}`, since it parses the reply as JSON), and the hook always exits 0, so a broken pet never fails a turn.

| Host | Where the hook lives | Worth knowing |
| :--- | :--- | :--- |
| Codex CLI | a `Stop` entry in `~/.codex/hooks.json` | Codex runs hooks only once you approve them with `/hooks` inside its TUI. The install message says so. |
| Gemini CLI | `hooks.AfterAgent` in `~/.gemini/settings.json` | JSONC on read, written back as plain JSON, the backup keeps your comments. |
| Mistral Vibe | a marked `post_agent` block appended to `~/.vibe/hooks.toml` | The rest of the file is never parsed or rewritten. |
| Augment auggie | `hooks.Stop` in `~/.augment/settings.json` | |
| opencode | `~/.config/opencode/plugins/terminalcreature.js` | The plugin runs under bun or node. |
| Amp | `~/.config/amp/plugins/terminalcreature/index.js` | The plugin runs under bun. |

Any hooks you already had on the same event stay where they are; ours is appended, and `uninstall` removes only ours, restoring the backup byte for byte when nothing else changed since. The plugin hosts need their runtime on your PATH to load the plugin: `install` writes the file either way, and `doctor` notes when bun or node is missing.

### How the wiring works

The installer **wraps** your existing statusline rather than editing it. It points `statusLine.command` at a small generated shim; the shim runs whatever command was there before, on the same stdin the host hands it, then draws the creature to the left of that output. Your own script is never modified. It keeps a `settings.json.pre-terminalcreature.bak`, and `--uninstall` puts the original command back.

Every host follows the same pattern under `~/.claude/terminalcreature/`. Claude Code keeps `statusline-terminalcreature.sh` and `wrapped-command`; the others get `statusline-terminalcreature-<host>.sh` and `wrapped-command-<host>`, and each host's settings file gets its own `.pre-terminalcreature.bak` next to it. The shim works out which host is calling from the JSON on stdin, so the session counter reads the right fields in every one of them.

The card hosts follow the same layout. Each hook host gets `hookcard-<host>.sh` in that directory, which is what its hook entry points at, and its hook config gets the same `.pre-terminalcreature.bak` next to it. opencode and Amp have no hook config to edit; they get a plugin file instead, `~/.config/opencode/plugins/terminalcreature.js` or `~/.config/amp/plugins/terminalcreature/index.js`, which runs `terminalcreature hookcard` and shows what comes back. Every shim, Claude Code's included, runs the library under `~/.claude/terminalcreature/lib` when it's there and falls back to a `terminalcreature` on your PATH when it isn't, so a `pipx` install wires the same way.

**Project-level statuslines need one manual step.** The installer only touches `~/.claude/settings.json`. If a repo sets its own `statusLine` in `<repo>/.claude/settings.json`, wrap it explicitly, then point the project at the shim:

```bash
./install.sh --statusline "/path/to/repo/.claude/statusline.sh"
# then in <repo>/.claude/settings.json:
#   "statusLine": { "type": "command", "command": "~/.claude/terminalcreature/statusline-terminalcreature.sh" }
```

---

## The Creature

### Species and rarity

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

| Rarity | Odds | Mark |
| :--- | :--- | :--- |
| Common | 60% | |
| Uncommon | 25% | `+` |
| Rare | 10% | `*` |
| Epic | 4% | `**` |
| Legendary | 1% | `***` |

The mark carries the tier without relying on colour, so it reads on a mono terminal or to a colour-blind user. On top of that, a **1% shiny** roll remakes the body motif: symbols become `$` (`<|+++|>` becomes `<|$$$|>`) and letters go uppercase (`<|ooo|>` becomes `<|OOO|>`).

All of it is a pure function of the seed. Hand-editing `state.json` can't promote a Common into a shiny Legendary; derived values are recomputed on every load and win.

### The evolution ladder

Six sprites: the egg, then five forms gaining detail at every step.

```
    ___        _^_        _^_        \|/       .\|/.     *.\|/.*
   /   \     ( ' ' )    ( ' ' )    ( ' ' )    ( ' ' )   \( ' ' )/
  ( ooo )     /+++\     <|+++|>    <|+++|>    /|+++|\    /|+++|\
   \___/       ^ ^       /   \      /|_|\      |___|     =|___|=
                         ^   ^      ^   ^     /     \    ^     ^

    egg     Hatchling  Fledgling    Adept       Sage    Ascendant
 unhatched     0-19      20-39      40-59      60-79     80-100
```

### The egg is a state, not a level

A buddy is an **egg** until you hatch it, whatever level it is. Level 0 is a Hatchling, a baby with a face, not an egg. Species, rarity, shiny, and stats are fixed the moment the egg exists, so an unhatched egg shows none of it:

```
$ terminalcreature card

       ___
      /   \
     ( ooo )
      \___/

  Unhatched
  0 xp eaten and counting
  /creature-hatch to find out what it is
```

**Eggs bank XP while closed**, so waiting costs nothing. A buddy added later with `--add` starts at 0 and hatches as a Hatchling, because XP banks per creature.

---

## XP and Levelling

### Where XP comes from

XP is a weighted count of files in a memory system, so terminalcreature needs one to point at. Five providers, set with `/creature config provider <name>`:

| Provider | Counts | Point it somewhere |
| :--- | :--- | :--- |
| `auto` | `agents` when two or more coding agents are installed, else `claude` | default, nothing to set |
| `agents` | the memory, rules and session logs of every coding agent on this machine | nothing to set |
| `claude` | stock Claude Code memory, `~/.claude/projects/*/memory/*.md` | nothing to set |
| `folder` | every `.md` under a directory, recursively | `config vault_root ~/notes` |
| `vault` | a structured vault, weighted per directory | `config vault_root ~/brain` |

`agents` knows fourteen of them and counts whichever have a root directory here: Claude Code, Codex, Gemini CLI, Copilot CLI, Cursor, Qwen Code, Droid, opencode, Amp, Goose, Continue, Kiro, Cline and Crush. An agent that isn't installed reads as absent rather than as an agent with nothing written. `terminalcreature sources` shows the count per agent, names and numbers only, never a file:

```
$ terminalcreature sources
claude: memories 2
codex: memories 1, instructions 1, sessions 1
gemini: instructions 1
cursor: rules 1
not found: copilot, qwen, droid, opencode, amp, goose, continue, kiro, cline, crush
counting 18 xp of memory across 4 agents. /creature shows your buddy.
```

`terminalcreature doctor` says which provider is live, whether the root is there, what it counted, what your buddy banked of that, and which hosts it can draw in:

```
$ terminalcreature doctor
provider: auto (agents when two or more are installed, else claude)
root: ~ (found)
  instructions 2
  memories   3
  rules      1
  sessions   1
source xp 18 -> level 10 (what a new egg would bank)
Zask banked 18 -> level 10 (Hatchling)
stdin: no session on stdin
hosts:
  claude   Claude Code         native, wired
  cursor   Cursor CLI          native, not wired
  copilot  GitHub Copilot CLI  not installed
  qwen     Qwen Code           not installed
  droid    Factory Droid       not installed
  codex    Codex CLI           card, wired
  gemini   Gemini CLI          card, not wired
  vibe     Mistral Vibe        not installed
  auggie   Augment auggie      not installed
  opencode opencode            card, wired (runtime bun or node not found)
  amp      Amp                 not installed
prompt surfaces (tmux, starship, shells): see `terminalcreature snippet`
```

The hosts block runs statusline hosts first, then the card hosts, then the plugin hosts, with a note when a plugin host's runtime is missing.

A zero reading has three causes, and `doctor` names the one you've got:

- **the root isn't there**: wrong path, or no agent has written memory yet
- **the root is real but empty**: nothing to do but write things down
- **the root has markdown the provider's layout doesn't match**: pointing `vault` at a plain notes folder does this, and the fix is `provider folder`

**No memory system at all?** Then your buddy sits at level 0, which is a fair reading rather than a bug. The installer and `doctor` both hand you a prompt for it:

> "Set up a persistent memory system for this project: one markdown file per durable fact in your memory directory, an index listing them, and write to it as we work."

### How levelling works

Durable facts are worth more than session logs because they cost more to produce, and generated index files are excluded so they can't inflate the count for free. `claude` counts one source at ×3, `folder` counts every note at ×2, `agents` weights by kind across every agent (memories and instruction files ×3, rules ×2, session logs ×1), and `vault` weights per directory:

| Source | Glob | Weight | Excluded |
| :--- | :--- | :--- | :--- |
| memories | `auto-memory/*.md` | ×3 | `MEMORY.md`, `index.md` |
| knowledge | `05-knowledge/*.md` | ×2 | `index.md` |
| projects | `04-projects/*.md` | ×2 | `index.md` |
| decisions | `memory/decisions/*.md` | ×2 | |
| sessions | `memory/sessions/*.md` | ×1 | |

```
level = min(100, floor(100 * sqrt(xp / xp_max)))
```

A square root curve, so early memories move the needle hard and later ones don't. **Level 100 is fully grown** and the curve stops there. `xp_max` is the XP at level 100 and the one dial that controls pace; the default of **1500** puts a well-established vault around 65.

| Level | XP needed | Roughly |
| :--- | :--- | :--- |
| 5 | 4 | a couple of notes |
| 10 | 16 | ~5 durable memories |
| 20 | 61 | ~20 durable memories |
| 40 | 241 | ~80 durable memories |
| 65 | 634 | ~211 durable memories |
| 100 | 1,500 | ~500 durable memories |

Want it slower? `terminalcreature config xp_max 5000` triples the distance. Deleting memories never de-levels anyone: the high-water mark only rises, because tidying up shouldn't be punished.

### The session counter

Right of the level bar, the caption shows what your buddy has eaten **in this session**:

```
Neux . Sage Lv66 [==....] +16 XP
```

It baselines the first time a session draws itself and is tracked per session id, since several are usually open at once. It stays hidden until there's something to show.

---

## The Statusline

`density` picks how much room the **inline** segment takes (`render`, or an `--inline` install):

| Mode | Looks like | Notes |
| :--- | :--- | :--- |
| `minimal` | `◔` | one glyph, filling as you evolve (`◌ ○ ◔ ◑ ◕ ●`, or `. o c C O @` in ascii) |
| `compact` | `<><> Lv65` | default, ~10 columns inline |
| `full` | `<><> Drain Lv65` | adds the name |
| `sprite` | the 5-row creature | its own rows, right-aligned to `columns` |
| `ruler` | a column ruler | a measuring aid, not a creature |

`compose "<text>"` is what the installed shim uses by default: your own text with the creature as a **left column**, sharing row one. The column is boxed in dark grey; `config border false` drops the box and gets two rows of height back. `sprite_height 3` cuts the creature to three rows and keeps the evolution beats:

```
+-----------+
|   .\|/.   |  [====......]  my-brain (main)        .\|/.    [====......]  my-brain (main)
|  ( o o )  |  Drain . Sage Lv65 [=====.]          ( o o )   Drain . Sage Lv65 [=====.]
|  /|ooo|\  |                                      /|ooo|\
|   |___|   |                                       |___|
|  /     \  |                                      /     \
+-----------+
   border true                                        border false
```

Either way the column is pinned to the creature's **widest** form, so your text doesn't shift the day it evolves into an Ascendant. `sprite` needs a width and a statusline script is handed no terminal, so `density ruler` prints a ruler: read the last digit you can see and pass it to `config columns <n>`.

`/creature-hide` takes the creature out without uninstalling anything. XP keeps banking while it's hidden.

### tmux, your prompt, and other terminals

The same `render` draws anywhere that can run a command. `snippet` prints a paste-in config for each surface it knows:

```
terminalcreature snippet tmux | starship | zsh | fish | omp | wezterm
```

The tmux one, for example:

```
$ terminalcreature snippet tmux
# ~/.tmux.conf. the creature in the right status, redrawn every status-interval
# seconds (tmux's default is 15; the refresh also pokes tmux when xp changes)
set -g status-interval 5
# tmux's default is 40, which cuts the creature off mid-word
set -g status-right-length 80
set -g status-right '#(env PYTHONPATH=$HOME/.claude/terminalcreature/lib python3 -m terminalcreature.cli render --format tmux --width 40) %H:%M'
```

Or with tpm, add the plugin and put `#{creature}` wherever you like:

```
set -g @plugin 'smejkaldesign/terminalcreature'
set -g status-right '#{creature} %H:%M'
```

`render`, `compose` and `card` take `--format ansi|tmux|plain` (`ansi` is the default, or set `TERMINALCREATURE_FORMAT`) and `--width N` to cap the columns. `tmux` writes `#[fg=…]` styles instead of escape codes; `plain` is for anything that shows colours as literal codes, which is what the WezTerm and oh-my-posh snippets use. Inside tmux, the background refresh runs `tmux refresh-client -S` when XP changes, so the status line redraws the moment a note lands rather than on the next interval.

### The roster

Keep several creatures. Only the **focused** one gains XP; the others hold their level and wait.

```
$ terminalcreature list
  O Drain      Lv65   Sage       Common
* o Zask       Lv0    Hatchling  Legendary shiny

* = focused (the one gaining xp)
```

`/creature-new` asks before it acts: `--replace` retires the current buddy and focuses a new egg, `--add` keeps it active and focuses a new egg. **Neither deletes anything.** A retired buddy keeps its banked XP and `focus <name>` brings it back. There's no level requirement, since the tradeoff is identical at level 12 and level 99.

---

## Commands and Settings

```
terminalcreature new               lay an egg (--replace or --add, --yes to confirm)
terminalcreature hatch [--name <n>] [--from-zero]  open the egg, naming it as it opens
terminalcreature names             two fresh name ideas for the egg
terminalcreature card              the full creature card
terminalcreature list              the roster
terminalcreature focus <name>      choose who banks new xp, un-retires
terminalcreature rename <old> <new>
terminalcreature retire <name>     retires, keeps the record and its xp
terminalcreature hide / show       drop it from the statusline, or bring it back
terminalcreature config [key val]  see settings, or set one
terminalcreature simulate <xp>     preview any level without touching real state
terminalcreature sources           what it can count, and what to do if that's nothing
terminalcreature doctor            what can it see, and why is it zero
terminalcreature doctor --check    the same, plus a version check against pypi
terminalcreature update            ask pypi whether there's a newer terminalcreature
terminalcreature update --apply    and install it if there is, keeping your creature
terminalcreature render            the one-line statusline segment
terminalcreature compose "<text>"  your statusline text, creature as a left column
    render, compose and card take --format ansi|tmux|plain and --width <n>
terminalcreature snippet <surface> paste-in config for tmux, starship, zsh, fish, omp or wezterm
terminalcreature install --host <h>   wire a host's statusline: claude, cursor, copilot, qwen, droid or all
    --inline puts the creature after the host's text, --box on the left as a column
terminalcreature install --host <h>   a turn-end card instead: codex, gemini, vibe, auggie, opencode or amp
terminalcreature uninstall --host <h> put that host back and drop its shim or plugin file
terminalcreature hookcard --host <h>  what a card host's hook runs: reads its JSON on stdin, prints the card
terminalcreature refresh           recompute the xp cache
```

Six are slash commands in Claude Code, so plain language reaches them without the CLI: `/creature`, `/creature-new`, `/creature-hatch`, `/creature-hide`, `/creature-show`, `/creature-update`.

After an `install.sh` or bootstrap install there's no `terminalcreature` on your PATH: the library is imported by the statusline, not installed as a binary. The slash commands reach everything you'd normally want. For the rest, alias it, or `pipx install terminalcreature`:

```bash
alias terminalcreature='PYTHONPATH="$HOME/.claude/terminalcreature/lib" python3 -m terminalcreature.cli'
```

| Setting | Values | Default |
| :--- | :--- | :--- |
| `provider` | `auto`, `agents`, `claude`, `folder` or `vault` | `auto` |
| `vault_root` | path, for `folder` and `vault` | |
| `xp_max` | XP at level 100, the pace dial | `1500` |
| `density` | `minimal` `compact` `full` `sprite` `ruler` | `compact` |
| `sprite_height` | `3` or `5` | `5` |
| `border` | box the `compose` column, costs 2 rows | `true` |
| `columns` | right-align width for `sprite` | `0` |
| `unicode` | `true` or `false` | `true` |
| `hidden` | `true` or `false` | `false` |
| `update_check` | `true` or `false`, the once-a-day check behind the `⬆ update` chip | `false` |
| `hookcard` | `changes`, `always` or `off`: when the turn-end card shows on a card host | `changes` |

---

## Privacy Promise

Short enough to check yourself.

- **It counts your files without ever opening them.** The only filesystem calls in `metric.py` are `glob` and `stat`, and that holds across every agent the `agents` provider counts. It never calls `open()` on a note, a rules file or a session log, never reads a byte of content, never parses frontmatter. That isn't a promise about what it does with your data; it's a statement that it never has your data.
- **It never prints a path it matched**, in any mode including `doctor` and `sources`, which report a home-relative root, product names and counts rather than filenames. An agent it can't find is named as not found, never as a path it looked in. The turn-end card is plain text with no path in it either, because a host may log what its hooks print.
- **All state is local**, at `~/.claude/terminalcreature/`: the roster, your settings, the XP cache, and the per-host shims. Nothing else, nowhere else.
- **A host's config is backed up before it's touched, and only our entry is touched.** Wiring a statusline host changes one key; wiring a card host appends one hook entry, or writes one plugin file that is ours alone. Every other hook you have stays, and `uninstall` removes only ours, restoring the backup byte for byte when nothing else changed since.
- **The render never opens a socket, and by default neither does anything it starts.** No telemetry, no analytics, no phone-home. Inside tmux the refresh runs `tmux refresh-client -S`, a call to your own tmux server on this machine, and that's the whole list.
- **The only network calls are the ones you allowed.** The installer (and `terminalcreature update --apply`) downloading a release tarball from `api.github.com`; `terminalcreature update` and `doctor --check` reading pypi's public package metadata; and, if you opt in with `config update_check true`, that same version request once a day from the background refresh so the yellow `⬆ update` chip can appear. It's off by default and asked as a question. Every one is an unauthenticated GET that sends nothing about you or your memory.

Three tests enforce this. A runtime trap patches every file-reading builtin and asserts none fire during a measurement. A static pass tokenizes `metric.py` and fails if a reader appears in the code at all. A third guards every socket call, including in the background processes a render spawns: opted out, an aged cache plus a render produces zero network from any process; opted in, exactly one attempt per day, never from the render itself. A leak guard runs in CI and as a `pre-push` hook, failing the build if an absolute home path or a vault-shaped filename ever reaches the repo.

---

## Under the Hood

| | |
| :--- | :--- |
| **The shim wraps, it doesn't edit** | `statusLine.command` points at a generated shim, one per host; your original command is saved next to it and run by it. A script that already calls terminalcreature is detected and left alone. |
| **One render, three dialects** | `ansi` for terminals and prompts, `tmux` for its `#[…]` styles, `plain` for the rest. The art never changes width between them. |
| **A cache on the hot path** | `render` reads a cached XP value and spawns the recount in the background, blocking only on a cold start. |
| **High-water mark** | New XP is the delta above the highest total ever seen, so deleting notes can't take a level away, and a render before your first hatch can't burn the XP waiting for it. |
| **Derived beats persisted** | Species, rarity, shiny, and accent are recomputed from the seed on every load and overwrite whatever is on disk. Only id, seed, name, hatch time, and banked XP persist. |
| **Counting is all it does** | The measurement path is `glob` and `stat` only, enforced by a runtime trap and a static check. |

## Repository Structure

```
terminalcreature/
├── terminalcreature/            # the package, stdlib only
│   ├── cli.py             #   commands
│   ├── render.py          #   statusline segment, compose, card
│   ├── state.py           #   roster, settings, xp cache
│   ├── metric.py          #   providers: glob + stat, nothing else
│   ├── hosts.py           #   per-host statusline adapters, hook hosts and stdin shapes
│   ├── plugins.py         #   the opencode and amp card plugins, generated from templates
│   ├── snippets.py        #   paste-in configs for tmux, starship, shells, wezterm
│   ├── creature.py        #   seed → species, rarity, shiny
│   └── sprites.py         #   stage templates × species motifs
├── commands/              # the Claude Code slash commands
├── tmux/                  # the tpm plugin behind #{creature}
├── site/                  # the website, deployed by pages.yml
├── install.sh             # wraps your statusline, lays the egg
├── bootstrap.sh           # curl | bash entry: fetches a release, runs install.sh
├── scripts/leak-guard.sh  # fails on machine paths and vault-shaped filenames
├── tests/                 # stdlib test suite, incl. the privacy traps
├── .claude-plugin/        # plugin manifest
└── marketplace/           # marketplace listing
```

## Development

```bash
git clone https://github.com/smejkaldesign/terminalcreature && cd terminalcreature
python3 tests/test_terminalcreature.py     # synthetic fixtures in a temp dir; no real memory touched
./scripts/leak-guard.sh              # the same check CI runs
git config core.hooksPath .githooks  # optional pre-push copy of the guard
```

No virtualenv, nothing to install, no build step. Run the CLI from the clone with `python3 -m terminalcreature.cli card`. CI runs the suite on Python 3.9 through 3.13, builds the wheel, and installs under the stock macOS bash 3.2.

## Contributing

Small project, short rules: stdlib only, Python 3.9 floor, one change per PR, new behavior gets a test, and the privacy tests must keep passing. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Provenance

Anthropic shipped a terminal pet in Claude Code (`/buddy`, April 2026). Nice idea, no progression: species and stats are recomputed from your user ID every session and never change. terminalcreature is a clean-room rebuild of the *concept* with the missing half added, growth you actually earn. No code, species names, sprite art, stat names, or hashing details were taken from it. Not affiliated with or endorsed by Anthropic.

## License

MIT. See [LICENSE](LICENSE). &copy; 2026 Smejkal Design.
