# Changelog

Notable changes, newest first. Versions follow semver; the version lives in
`brainbuddy/__init__.py` and each release is the matching `v*` tag.

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
