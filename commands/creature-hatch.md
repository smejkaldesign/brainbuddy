---
name: creature-hatch
description: "Open a terminalcreature egg and reveal the creature inside. Use when the user asks to hatch, open the egg, crack it, or see what their new buddy turned out to be."
user_invocable: true
---

# /creature-hatch

Open the egg. Buddies feed off memories, so a **first** hatch is a short guided setup: ask what
it gets to eat, ask whether the existing pile counts, ask what to call it, then open it.

## Step 1: is this a first hatch?

```bash
PYTHONPATH="$HOME/.claude/terminalcreature/lib" python3 -m terminalcreature.cli sources
```

Exit 0 means it's already counting something. Exit 1 means it isn't, and the output says why.

**Ask questions 2a and 2b when** this is the roster's first hatch, or `sources` exited 1.
Otherwise skip those two, don't re-ask on every egg, and go straight to Step 2c. A second
buddy from `/creature-new --add` inherits the setup the first one established. The naming
question (2c) is per-egg and never skipped.

## Step 2a: what does it get to feed on?

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
sit at level 0 with nothing to eat until something gets written, and offer to set a memory
system up. `sources` prints a prompt for exactly that, and you can act on it directly rather
than making them paste it back.

Confirm with `doctor` before moving on. If it reports 0, fix that now rather than hatching into
a creature that can't grow.

## Step 2b: score what's already written, or start from 0?

Ask this second, because it only makes sense once there's a source and a count to talk about.
Give them the real number from `doctor`:

- **Score existing** (default): the egg eats everything already written, so it opens several
  forms in. Most people want this; it's the moment the design is built around.
- **Start from 0**: `--from-zero` puts the existing pile off the menu so only new notes feed it.
  For someone who wants the climb rather than the reveal, or whose vault is decades of
  imported material.

Both are legitimate. Don't editorialise beyond one line each, and don't tell them the level
either choice would produce, because that spoils the reveal.

## Step 2c: name it

Ask on **every** hatch, not just the first: the egg has no name until it's opened, and this
is the one chance to choose it. Fetch two fresh ideas first:

```bash
PYTHONPATH="$HOME/.claude/terminalcreature/lib" python3 -m terminalcreature.cli names
```

Offer exactly these, letting them type their own via the free-text option:

1. The first suggestion from `names`
2. The second suggestion from `names`
3. **Let it name itself** — the egg picked a name when it was laid, revealed at the hatch
4. Their own name, typed in (the built-in Other/custom option)

Don't reveal what "let it name itself" resolves to; that's part of the reveal. Names cap at
24 characters.

## Step 3: open it

```bash
PYTHONPATH="$HOME/.claude/terminalcreature/lib" python3 -m terminalcreature.cli hatch
```

Add `--from-zero` if that's what they picked, and `--name <their choice>` unless they chose
to let it name itself. Print what the CLI returns; it emits the reveal and then the full
card, so don't also run `card` afterwards.

`hatch` measures the source fresh rather than trusting the cache, so a provider set seconds
earlier is scored correctly.

## Step 4: offer the daily update check (after the reveal, never before)

Once, right after the reveal lands. Nothing bureaucratic gets to stand in front of the payoff,
so this always comes after the creature is on screen. Ask exactly this, default No:

> Want it to check once a day whether a newer terminalcreature exists? One request to pypi.org for
> a version number; nothing about you or your notes goes anywhere. Off unless you say yes.

On yes: `config update_check true`. Either way: `config update_check_asked true`, and never
ask again, on this egg or any later one. When it's on and a newer version exists, a yellow
`⬆ update` chip appears at the end of the statusline caption and leaves on its own after the
upgrade.

## It opens at the level it earned

An egg banks XP the whole time it's closed, so hatching reveals whatever level that XP adds
up to, not level 0. On a fresh install the first egg inherits the memory that already exists,
which usually means it comes out several forms in. That's the intended surprise: **don't
spoil the level before running the command.**

A buddy created later with `/creature-new --add` starts at 0 and hatches as a Hatchling.
Both are correct; the difference is whether there was banked XP waiting.

## Hatching with nothing to count

If there's no memory system yet, hatch anyway. The reveal is the same one everybody gets, and
the species, rarity and shiny are already decided; the only thing missing is the level. `hatch`
prints its own lines for this: that Lv0 is the floor rather than a bad roll, and what to feed it.

Print those and stop. Don't add encouragement of your own on top, don't apologise for the level,
and don't suggest re-hatching later for a better one, which isn't a thing. If they want the
memory system set up, `sources` carries the prompt for it and you can act on it directly.

## If there's nothing to open

- No buddy at all → point at `/creature-new`, don't create one silently.
- Already hatched → say so and show `card` instead. Hatching twice does nothing.

## Rules

- **Never print a filesystem path from a memory directory.** The root someone typed themselves
  is fine, and naming it is the whole point of Step 2a. Individual note filenames are not.
- Don't describe the creature before hatching, even if you can read the state. The reveal is
  the point.
- Don't pass `--from-zero` unless they chose it. Scoring what's already written is the default
  and the better first experience.
