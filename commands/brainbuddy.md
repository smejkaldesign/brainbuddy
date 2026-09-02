---
name: brainbuddy
description: "Show and manage your brainbuddy — the statusline creature that evolves as your memory system grows. Hatch, focus, rename, retire, and configure."
user_invocable: true
---

# /brainbuddy

Front end for the `brainbuddy` CLI. Everything runs locally; nothing here reaches the network.

Run commands as:

```bash
PYTHONPATH="$HOME/.claude/brainbuddy/lib" python3 -m brainbuddy.cli <command>
```

## No arguments

Show the card:

```bash
PYTHONPATH="$HOME/.claude/brainbuddy/lib" python3 -m brainbuddy.cli card
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
| "settings", "config" | `config` |
| set an option | `config <key> <value>` |
| "what can it see", "why is it 0" | `doctor` |
| "what would level N look like" | `simulate <xp>` |

Settable keys: `provider` (`claude` or `vault`), `vault_root`, `xp_max`, `density` (`compact`, `minimal`, `full`), `unicode`.

## Naming a new creature

`hatch` picks a name from a syllable table when none is given, because the CLI can't reach a model. You can. When hatching without a name, suggest 3 short names that fit the species and rarity the hatch produced, and offer to rename it. Keep it to one line per name.

## Hatching guardrail

`hatch` refuses if the focused creature is under level 100, because hatching starts a new creature at 0 and moves focus. That's deliberate. If the user means it, pass `--force`, but say plainly what happens first: the current creature keeps its level and stops gaining XP until refocused.

## Rules

- **Never print a filesystem path from a memory directory.** The tool never emits one; don't add one. Filenames leak more than they look like they do.
- Don't offer to edit `state.json` by hand. Species, rarity, and shiny are recomputed from the seed on every load, so hand-edits get overwritten and it looks like a bug.
- If `doctor` reports 0 counts, the fix is almost always `provider` or `vault_root`, not a reinstall.
