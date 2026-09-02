---
name: brainbuddy-hide
description: "Hide the brainbuddy creature from the Claude Code statusline. Use when the user asks to hide, remove, turn off, or get rid of their brainbuddy, pet, or creature in the status bar."
user_invocable: true
---

# /brainbuddy-hide

Take the creature out of the statusline. Nothing is uninstalled and no XP is lost; the bar
just renders without it until `/brainbuddy-show`.

```bash
PYTHONPATH="$HOME/.claude/brainbuddy/lib" python3 -m brainbuddy.cli hide
```

Print the one-line confirmation the CLI returns. Then say, in one short line, that
`/brainbuddy-show` brings it back.

The statusline picks this up on its next render, which is immediate. No restart.

## Rules

- **Never print a filesystem path from a memory directory.** Same rule as `/brainbuddy`.
- Don't edit `state.json` by hand to do this. `hidden` is a real setting and the CLI owns it.
- If the user asks to hide it *permanently*, or to uninstall, this is not that command. Say so
  and point at the installer, rather than deleting anything.
