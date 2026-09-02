---
name: brainbuddy-hatch
description: "Open a brainbuddy egg and reveal the creature inside. Use when the user asks to hatch, open the egg, crack it, or see what their new buddy turned out to be."
user_invocable: true
---

# /brainbuddy-hatch

Open the egg.

```bash
PYTHONPATH="$HOME/.claude/brainbuddy/lib" python3 -m brainbuddy.cli hatch
```

Print what the CLI returns. It emits the reveal and then the full card, so don't also run
`card` afterwards.

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

- **Never print a filesystem path from a memory directory.** Same rule as `/brainbuddy`.
- Don't describe the creature before hatching, even if you can read the state. The reveal is
  the point.
