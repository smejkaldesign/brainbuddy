---
name: creature
description: "Show and manage your terminalcreature, the statusline creature that evolves as your memory system grows. Hatch, focus, rename, retire, hide, show, and configure."
user_invocable: true
---

# /creature

Front end for the `terminalcreature` CLI. Buddies feed off memories and grow as the second brain
grows. Everything runs locally; nothing here reaches the network.

Run commands as:

```bash
PYTHONPATH="$HOME/.claude/terminalcreature/lib" python3 -m terminalcreature.cli <command>
```

## If nothing is wired up yet

Installing the plugin delivers these commands but can't set `statusLine`, so on a fresh
plugin install there is no library and no creature. If `~/.claude/terminalcreature/lib` is missing,
don't run a subcommand. Say the statusline isn't wired yet, offer to do it, and on a yes run:

```bash
"$(cat ~/.claude/terminalcreature/plugin-root)/install.sh" --no-commands
```

It wraps whatever statusline they already have rather than replacing it, and ends on the egg.
Relay its output, then point at `/creature-hatch`. `--no-commands` matters: without it the
installer copies these same five files into `~/.claude/commands`, and every one of them shows
up twice in the picker.

## No arguments

Show the card:

```bash
PYTHONPATH="$HOME/.claude/terminalcreature/lib" python3 -m terminalcreature.cli card
```

Print the output as-is inside a code block so the ASCII art keeps its alignment. Then offer, in one short line, whatever is most relevant: hatching a first creature if the roster is empty, or hatching a new one if the focused creature has hit level 100.

## With arguments

Map the request onto a subcommand. Run it, then show the result.

| Ask | Command |
|---|---|
| "hatch", "new egg" | `hatch [name]` |
| "focus X", "switch to X" | `focus X` |
| "list", "roster", "show all" | `list` |
| "rename X to Y" | `rename X Y` |
| "retire X" | `retire X` |
| "new buddy", "start over", "reroll" | hand off to `/creature-new` |
| "hatch it", "open the egg" | hand off to `/creature-hatch` |
| "hide it", "hide my terminalcreature", "get it off my statusline" | `hide` |
| "show it", "bring it back", "unhide" | `show` |
| "settings", "config" | `config` |
| set an option | `config <key> <value>` |
| "what can it see", "why is it 0" | `doctor` |
| "what counts as xp", "how do I level it up" | `sources` |
| "what would level N look like" | `simulate <xp>` |

Settable keys: `provider` (`auto`, `agents`, `claude`, `folder` or `vault`; `auto` is the default and picks `agents` when two or more coding agents are installed, else `claude`), `vault_root`, `xp_max`, `density` (`compact`, `minimal`, `full`, `sprite`, `ruler`), `sprite_height`, `border`, `columns`, `unicode`, `hidden`.

`hide`, `show`, `new` and `hatch` are also their own commands (`/creature-hide`, `/creature-show`, `/creature-new`, `/creature-hatch`), so a bare "hide my terminalcreature" or "hatch it" reaches them without going through this one.

## Naming a new creature

`new` picks a name from a syllable table when none is given, because the CLI can't reach a model. You can. When hatching without a name, suggest 3 short names that fit the species and rarity the hatch produced, and offer to rename it. Keep it to one line per name.

## Eggs are a state, not a level

A creature is an **egg** until it's hatched, whatever its level. `new` lays one, `/creature-hatch` opens it, and the statusline shows egg art with no level until then. Level 0 is a Hatchling, a baby with a face, not an egg.

An egg banks XP while closed, so hatching reveals the level it earned rather than 0. Don't spoil that level before the user runs hatch.

## Adding a second buddy

`new --add` always asks first, at any level, and prints why: the new egg starts at 0 and takes focus, so the current buddy holds its level and stops gaining. Relay it, get a yes, re-run with `--yes`.

`new --replace` retires instead of deleting. The old buddy keeps its banked XP and `focus <name>` brings it back, so say that when confirming.

## Rules

- **Never print a filesystem path from a memory directory.** The tool never emits one; don't add one. Filenames leak more than they look like they do.
- Don't offer to edit `state.json` by hand. Species, rarity, and shiny are recomputed from the seed on every load, so hand-edits get overwritten and it looks like a bug.
- If `doctor` reports 0 counts, never suggest a reinstall. `doctor` already names which of the three causes it is: a root that isn't there, a real but empty root, or markdown the provider's layout doesn't match. Relay its wording.
- **A user with no memory system isn't misconfigured.** When `doctor` or `sources` says nothing has been written down yet, don't send them digging through `provider` and `vault_root`. Offer to set up memory instead: the prompt those commands print is the thing to act on, and you can act on it directly rather than making them paste it back at you.
