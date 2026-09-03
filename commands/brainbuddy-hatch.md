---
name: brainbuddy-hatch
description: "Open a brainbuddy egg and reveal the creature inside. Use when the user asks to hatch, open the egg, crack it, or see what their new buddy turned out to be."
user_invocable: true
---

# /brainbuddy-hatch

Open the egg. On a **first** hatch this is a short guided setup: ask where the memories live,
ask whether existing notes should count, then open it.

## Step 1: is this a first hatch?

```bash
PYTHONPATH="$HOME/.claude/brainbuddy/lib" python3 -m brainbuddy.cli sources
```

Exit 0 means it's already counting something. Exit 1 means it isn't, and the output says why.

**Ask the two questions below when** this is the roster's first hatch, or `sources` exited 1.
Otherwise skip both, don't re-ask on every egg, and go straight to Step 3. A second buddy from
`/brainbuddy-new --add` inherits the setup the first one established.

## Step 2a: where do the memories live?

Don't ask this cold. Look first, then offer what you actually found:

```bash
find ~ -maxdepth 5 -name '.obsidian' -type d -not -path '*/node_modules/*' 2>/dev/null | head
ls -d ~/notes ~/Documents/notes ~/vault 2>/dev/null
ls -d ~/.claude/projects/*/memory 2>/dev/null | head -3
```

Offer the candidates with a **file count each** so the choice is concrete, then set it:

| They keep notes in | Run |
| --- | --- |
| Claude Code's own memory | `config provider claude` |
| any folder of markdown | `config provider folder` then `config vault_root <path>` |
| a structured vault (`auto-memory/`, `05-knowledge/`, `04-projects/`, `memory/sessions/`, `memory/decisions/`) | `config provider vault` then `config vault_root <path>` |

An Obsidian vault is usually `folder`, not `vault`. `vault` only scores those five directories
by name, so pointing it at ordinary notes counts zero. If you're unsure, set `folder` and check
`doctor`; `folder` walks everything and can't miss.

**Nobody keeps notes yet?** Don't force a choice. Leave the provider alone, say the buddy will
sit at level 0 until something gets written, and offer to set a memory system up. `sources`
prints a prompt for exactly that, and you can act on it directly rather than making them paste
it back.

Confirm with `doctor` before moving on. If it reports 0, fix that now rather than hatching into
a creature that can't grow.

## Step 2b: score what's already written, or start from 0?

Ask this second, because it only makes sense once there's a source and a count to talk about.
Give them the real number from `doctor`:

- **Score existing** (default): the egg banks everything already written, so it opens several
  forms in. Most people want this; it's the moment the design is built around.
- **Start from 0**: `--from-zero` baselines what's there so only new notes count. For someone
  who wants the climb rather than the reveal, or whose vault is decades of imported material.

Both are legitimate. Don't editorialise beyond one line each, and don't tell them the level
either choice would produce, because that spoils the reveal.

## Step 3: open it

```bash
PYTHONPATH="$HOME/.claude/brainbuddy/lib" python3 -m brainbuddy.cli hatch
```

Add `--from-zero` if that's what they picked. Print what the CLI returns; it emits the reveal
and then the full card, so don't also run `card` afterwards.

`hatch` measures the source fresh rather than trusting the cache, so a provider set seconds
earlier is scored correctly.

## It opens at the level it earned

An egg banks XP the whole time it's closed, so hatching reveals whatever level that XP adds
up to, not level 0. On a fresh install the first egg inherits the memory that already exists,
which usually means it comes out several forms in. That's the intended surprise: **don't
spoil the level before running the command.**

A buddy created later with `/brainbuddy-new --add` starts at 0 and hatches as a Hatchling.
Both are correct; the difference is whether there was banked XP waiting.

## If there's nothing to open

- No buddy at all → point at `/brainbuddy-new`, don't create one silently.
- Already hatched → say so and show `card` instead. Hatching twice does nothing.

## Rules

- **Never print a filesystem path from a memory directory.** The root someone typed themselves
  is fine, and naming it is the whole point of Step 2a. Individual note filenames are not.
- Don't describe the creature before hatching, even if you can read the state. The reveal is
  the point.
- Don't pass `--from-zero` unless they chose it. Scoring what's already written is the default
  and the better first experience.
