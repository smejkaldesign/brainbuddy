# brainbuddy as a Claude Code plugin

This repo is installable as a plugin. `.claude-plugin/plugin.json` is the manifest;
`commands/` and `hooks/hooks.json` are picked up by auto-discovery, so the five slash
commands are listed once and live in one place.

Schemas verified against:

- <https://code.claude.com/docs/en/plugins-reference>
- <https://code.claude.com/docs/en/plugin-marketplaces>

## The wiring problem

A plugin install copies files into the plugin cache. It cannot set `statusLine`: a plugin's
own `settings.json` only honours the `agent` and `subagentStatusLine` keys, and there is no
post-install hook to run. So a plugin install alone leaves the user with commands, no library
and no creature.

The gap is closed in two places, both pointing at the same `install.sh` that a git-clone user
runs by hand:

1. **`SessionStart` hook** (`scripts/plugin-session-start.sh`). Every session it records the
   current `${CLAUDE_PLUGIN_ROOT}` to `~/.claude/brainbuddy/plugin-root`, because that path
   changes on every plugin update. Then it checks both halves of a working install, the
   library on disk and a `statusLine` pointing at the shim. If either is missing it returns
   `additionalContext` telling Claude the statusline isn't wired and naming the exact command.
   When wired it exits silently, so the steady state costs nothing.
2. **`/brainbuddy`**, which checks for `~/.claude/brainbuddy/lib` before running anything and
   offers the same command instead of failing on a missing module.

Neither runs the installer unasked. Wiring edits `~/.claude/settings.json`, and that is the
user's file. Both paths end where the clone path ends: an egg in the statusline and
`/brainbuddy-hatch`.

`install.sh --no-commands` is the plugin-side flag. Without it the installer copies the same
five command files into `~/.claude/commands`, and each one appears twice in the picker.
Uninstall respects it too and leaves the plugin's copies alone.

## Marketplace repo, for RICK

`marketplace.json` here is ready to copy, not live. Create a public repo
`smejkaldesign/claude-plugins`, put this file at `.claude-plugin/marketplace.json` in its
root (the directory name matters, the marketplace is only found there), and push. Users then
run `/plugin marketplace add smejkaldesign/claude-plugins` followed by
`/plugin install brainbuddy@smejkal-design`. The marketplace repo holds only that one file;
the plugin itself is fetched from this repo by the `github` source, so shipping a plugin
change means pushing here, not there. One thing to watch: `version` is pinned in
`plugin.json`, so installed users only pull an update when that string changes. Bump it on
release or they sit on the cached copy.
