# Changelog

Notable changes, newest first. Versions follow semver; the version lives in
`terminalcreature/__init__.py` and each release is the matching `v*` tag.

## 3.1.0 (2026-09-04)

The turn-end card. Six agents with no statusline get the creature anyway: a
one-line card the host shows when a turn ends, through its own hook or plugin
channel, crediting session XP the same way the statusline does.

### Added

- Card hosts: Codex CLI, Gemini CLI, Mistral Vibe, Augment auggie, opencode
  and Amp. `terminalcreature install --host <name>` writes one hook entry
  (Codex: `Stop` in `~/.codex/hooks.json`; Gemini: `hooks.AfterAgent` in
  `~/.gemini/settings.json`; Vibe: a marked `post_agent` block in
  `~/.vibe/hooks.toml`; auggie: `hooks.Stop` in `~/.augment/settings.json`)
  or one plugin file (`~/.config/opencode/plugins/terminalcreature.js` on
  opencode's `session.idle`, `~/.config/amp/plugins/terminalcreature/index.js`
  on Amp's `agent.end`). All six contracts, the four hook schemas and both
  plugin APIs, were confirmed from the hosts' docs as of September 2026; none
  was guessed. Hooks you already had on the same event stay, `uninstall
  --host` removes only ours and restores the backup byte for byte when nothing
  else changed, and `--host all` now covers the hook hosts whose config dir
  exists (plugin hosts are named outright). Codex runs hooks only after a
  one-time `/hooks` approval in its TUI, and the install message says so.
  `./install.sh --host <name>` passes the card hosts through.
- `terminalcreature hookcard --host <name>`, what those hooks run. It reads
  the host's JSON on stdin, credits session XP like `render` does, and prints
  the host's envelope (`{"systemMessage": …}` for Codex, Gemini and auggie,
  `{"system_message": …}` for Vibe, a bare line for the opencode and Amp
  plugins) around a plain one-line card: short sprite, name, level, bar, `+N
  xp` this session, and the evolution when a stage moved. No escape codes,
  never a path, always exit 0.
- The `hookcard` setting picks the cadence. `changes`, the default, shows the
  first turn of a session, then whenever the session's XP or stage changed,
  otherwise every tenth turn; `always` shows every turn; `off` shows none and
  leaves the hook in place. A quiet turn prints nothing, except on Gemini,
  which parses the reply and gets `{}`.
- `doctor` lists the card hosts after the statusline hosts, then the plugin
  hosts, with a note when bun or node is missing for a wired plugin.
- `install --box`, the opposite of `--inline`, for Cursor and Qwen where inline
  is the default. Passing both is an error.

### Changed

- Cursor hands the shim its `render_width_chars`, and the segment is capped to
  it when no `--width` is given.
- `snippet` and the settings commands quote paths, so a home directory with a
  space in it works.
- Every host shim, Claude Code's included, falls back to a `terminalcreature`
  on PATH when `~/.claude/terminalcreature/lib` is missing, so a `pipx`
  install wires the same way the bootstrap does.

### Notes

- No breaking change. Nothing is written to a card host until you run
  `install --host <name>` for it, and a 3.0 install keeps its statuslines,
  roster and provider as they were.
- Vibe and auggie get a card but don't feed XP yet: the `agents` provider
  still counts the fourteen agents it did in 3.0.

## 3.0.0 (2026-09-04)

Any terminal, any agent. The creature is no longer a Claude Code accessory:
it draws in five agents' native statuslines, in tmux and every common prompt,
and it eats the memory of whichever coding agents live on this machine.

### Added

- Native statusline hosts beyond Claude Code: Cursor CLI, GitHub Copilot CLI,
  Qwen Code and Factory Droid. `terminalcreature install --host <name>` wires
  one (`--host all` wires every host that's installed), `uninstall --host`
  puts it back, and `./install.sh --host <name>` passes straight through.
  Each host gets its own shim (`statusline-terminalcreature-<host>.sh`), its
  own wrapped command and its own settings backup. Cursor and Qwen default to
  inline because their custom statusline replaces the native footer. Copilot's
  settings file is JSONC: comments survive in the backup and the file is
  written back as plain JSON.
- `--format ansi|tmux|plain` and `--width <n>` on `render`, `compose` and
  `card`, with `TERMINALCREATURE_FORMAT` as the environment default. `tmux`
  emits `#[fg=…]` styles, `plain` strips colour for surfaces that would show
  the codes.
- `terminalcreature snippet <surface>`: paste-in configs for tmux, Starship,
  zsh, fish, oh-my-posh and WezTerm. Home is written as `$HOME` or
  `.Env.HOME`, never expanded, so a snippet in a dotfiles repo carries no
  username.
- A tpm plugin: `set -g @plugin 'smejkaldesign/terminalcreature'` and
  `#{creature}` in `status-right`. Inside tmux the background refresh runs
  `tmux refresh-client -S` when XP changes, so the status line redraws at
  once rather than on the next interval.
- The `agents` provider: memory, rules and session logs of fourteen coding
  agents (Claude Code, Codex, Gemini CLI, Copilot CLI, Cursor, Qwen Code,
  Droid, opencode, Amp, Goose, Continue, Kiro, Cline, Crush), weighted
  memories and instructions ×3, rules ×2, session logs ×1. Still glob and stat
  only, enforced by the same tests. `terminalcreature sources` prints a count
  per agent and a not-found line, never a path.
- `doctor` gains a hosts block: each host, whether it's installed, whether
  it's wired.
- The shim reads the caller's stdin shape, so the session counter works in
  every native host.

### Changed

- The default provider is `auto`: `agents` when two or more coding agents
  are installed, else `claude`. An existing install that set `provider`
  explicitly keeps it; a stock install with only Claude Code on the machine
  measures exactly what it did before.
- `install.sh` reports the provider it actually finds, including `auto` and
  `agents`, instead of labelling every unset provider as stock Claude Code
  memory.

### Notes

- No breaking change for an existing Claude Code install. The state dir stays
  `~/.claude/terminalcreature/`, the Claude shim keeps its name, roster and
  settings carry forward, and re-running the bootstrap you installed with is
  the upgrade.
- Host contracts, honestly: Copilot and Cursor were read off the shipped CLI
  bundles and exercised live. Qwen's is docs-derived. Droid's is docs-derived
  and unverified against a real install; the adapter accepts both the
  documented shape and a flat camelCase one, and bug reports are welcome.
- Codex CLI, Gemini CLI, opencode, Amp and Goose have no statusline to wire
  yet. They feed XP and draw in tmux or the prompt; a hooks card is planned
  for 3.1.

## 2.2.0

- `/creature-update` and `terminalcreature update --apply`: check pypi for a
  newer release and, if there is one, download it and run its installer over
  this one. Roster, settings and the wrapped statusline all stay; only the
  library and shim change. Plugin installs keep their own command files.

## 2.1.0

- The creature blinks: a closed-eye beat for 0.4s out of every 5, on the
  clock, so the statusline's own redraw timing doesn't matter. When the
  session counter rises it holds a happy face for two seconds. Eyes only:
  the art never changes width, and an egg has no eyes to move.
- Site: updated wordmark, ASCII-creature favicon, social image rendered
  from the wordmark for link previews, story-led hero copy in the always-hungry
  voice, more room in the hero.

## 2.0.0

- Renamed: brainbuddy is now **terminalcreature**. New package, module, CLI
  (`terminalcreature`), slash commands (`/creature`, `/creature-hatch`,
  `/creature-new`, `/creature-hide`, `/creature-show`), state dir
  (`~/.claude/terminalcreature/`), shim, and `TERMINALCREATURE_TARBALL`.
- The installer migrates an existing brainbuddy install in place: state, XP
  cache, and settings move over, the old command files are removed, and a
  stub is left at the old shim path so project-level statuslines keep
  drawing. Re-run the bootstrap you installed with; the old URL redirects.
- Creatures are unchanged. The seed salt keeps its original value on
  purpose, so every buddy hatched under the old name is the same creature.
- New wordmark on the site and README; site at terminalcreature.com.

## 1.3.0

- brainbuddy is now **terminalcreature**. This is the last release under the
  old name and it changes nothing else. To move over, re-run the bootstrap you
  installed with (the old URL redirects), or `pipx install terminalcreature`.
  Your creature, roster, and settings migrate in place. New home:
  <https://github.com/smejkaldesign/terminalcreature>.

## 1.2.0

- Opt-in update alert: `config update_check true` lets the background refresh
  ask pypi once a day for the latest version number, and a yellow `⬆ update`
  chip appears at the end of the statusline when a release is out, leaving on
  its own after you upgrade. Off by default, asked once after the hatch, and
  the render path still never touches the network in either setting; the
  socket test now proves both. Existing installs get a one-time offer from
  `/brainbuddy`, and `doctor` reports the check's state and last run.

## 1.1.0

- An egg renders as Unhatched everywhere, never as a name. The name is chosen
  at the hatch: two ideas from the new `brainbuddy names`, your own via
  `hatch --name <n>`, or let it name itself and find out at the reveal.
- The session counter (`+N XP`) moved to the right of the progress bar, so the
  caption reads level, bar, then what this session added.

## 1.0.0

The first public release: install it with one command, and the owner's costs
stay at zero because everything lives on your machine.

- Fixed: a background refresh no longer writes back the roster it loaded before
  the scan, which could silently revert an egg laid or hatched while it ran.
- Fixed: the leak guard no longer skips files whose names contain spaces, and it
  now catches capitalized and `/home/` paths too.
- Fixed: `--uninstall` recognizes a statusline that names the shim through `~`
  instead of deleting the shim and leaving the statusline pointing at it.
- Fixed: a non-numeric `config xp_max`/`columns`/`sprite_height` or `simulate`
  argument gets a one-line answer instead of a traceback carrying a home path.
- Upgrades keep your buddy. `state.json` carries a schema version, and a file
  written by any earlier version is brought forward on load: nothing is dropped,
  missing fields are filled, and a focus pointing at a creature that isn't there
  falls back to the roster rather than rendering as no buddy at all.
- `brainbuddy update` and `brainbuddy doctor --check` ask PyPI whether there's a
  newer version. They're the only two commands that go online, and only when you
  run them; the statusline never does, and a test asserts it. No network is not
  an error, it's one line and exit 0.
- `doctor` names a project-level statusline. If a repo's own
  `.claude/settings.json` sets `statusLine`, that wins inside the repo and the
  creature never draws there. Doctor says so and prints the two-step fix with
  your own command already in it. It only ever reads that file.
- Windows: `install.sh` and `bootstrap.sh` name WSL and Git Bash when they're
  run by something that isn't bash. There's no PowerShell version.
- Hatching with no memory system is a moment rather than a silent Lv0. The
  reveal is unchanged; the level is followed by what it means and what to feed.
- One-line install: `bootstrap.sh` fetches the latest tagged release, unpacks it
  to a temp dir and runs its `install.sh` with whatever flags you passed, so the
  usual path is one command instead of a clone. It falls back to the default
  branch until a release exists.
- PyPI packaging: `pipx install brainbuddy` / `uvx brainbuddy` now work; the
  installed entry point is the same `brainbuddy` command the shim calls.
- Release workflow: tagging `vX.Y.Z` tests, builds, and publishes to PyPI via
  trusted publishing.
- `brainbuddy doctor` reports the installed version.
- Installable as a Claude Code plugin: a `SessionStart` hook notices an unwired
  install and offers `install.sh --no-commands`, which ends on the same egg.

## 0.1.0

Everything before packaging: the creature, the egg-and-hatch flow, three XP
providers, the statusline wrap installer, five slash commands, the leak guard,
and the test suite.
