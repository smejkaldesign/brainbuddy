---
name: brainbuddy-new
description: "Start a new brainbuddy egg, either replacing the current buddy or adding alongside it. Use when the user asks for a new buddy, a new egg, to start over, to reroll their creature, or to hatch something different."
user_invocable: true
---

# /brainbuddy-new

Lay a fresh egg. **Ask which mode first, then run the matching command.** Never guess, and
never pass a mode the user didn't pick.

Show them the current buddy and the two options:

```bash
PYTHONPATH="$HOME/.claude/brainbuddy/lib" python3 -m brainbuddy.cli list
```

| They want | Run |
| --- | --- |
| a clean start, done with the current one | `new --replace [name]` |
| another buddy, keeping the current one | `new --add [name]` |

```bash
PYTHONPATH="$HOME/.claude/brainbuddy/lib" python3 -m brainbuddy.cli new --replace
```

If there's no buddy yet, there's nothing to replace. Just run `new` and skip the question.

## Replace keeps the old one

`--replace` retires, it doesn't delete. The old buddy stays in `list` with its banked XP and
`focus <name>` brings it back. Say that when you confirm, because "replace" sounds destructive
and people brace for losing their level.

## Add warns first, on purpose

`--add` refuses below level 100 and prints why: a new egg starts at 0 and takes focus, so the
current buddy holds its level and stops gaining. Relay that, get a yes, then re-run with
`--yes`. Don't add `--yes` pre-emptively; the refusal is the confirmation step.

## Naming

`new` picks a name from a syllable table when none is given, because the CLI can't reach a
model. You can. Offer 3 short names that fit the species and rarity, one line each, and
mention `rename` exists if they want to change it later.

## Rules

- **Never print a filesystem path from a memory directory.** Same rule as `/brainbuddy`.
- Don't hatch it for them. `new` leaves an egg on purpose; opening it is `/brainbuddy-hatch`.
- A new egg banks XP while closed, so there's no rush to hatch and no XP lost by waiting.
