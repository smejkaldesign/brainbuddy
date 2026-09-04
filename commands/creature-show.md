---
name: creature-show
description: "Show the terminalcreature creature in the Claude Code statusline again. Use when the user asks to show, restore, bring back, unhide, or turn on their terminalcreature, pet, or creature in the status bar."
user_invocable: true
---

# /creature-show

Put the creature back in the statusline after `/creature-hide`.

```bash
PYTHONPATH="$HOME/.claude/terminalcreature/lib" python3 -m terminalcreature.cli show
```

Print the one-line confirmation the CLI returns.

It kept eating while it was hidden, so level and progress reflect everything written to the
vault in the meantime. Expect it to come back further along than it left.

If it still doesn't appear, the cause is almost always the statusline script rather than this
setting. `doctor` is the next step, not a reinstall.

## Rules

- **Never print a filesystem path from a memory directory.** Same rule as `/creature`.
