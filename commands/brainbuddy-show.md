---
name: brainbuddy-show
description: "Show the brainbuddy creature in the Claude Code statusline again. Use when the user asks to show, restore, bring back, unhide, or turn on their brainbuddy, pet, or creature in the status bar."
user_invocable: true
---

# /brainbuddy-show

Put the creature back in the statusline after `/brainbuddy-hide`.

```bash
PYTHONPATH="$HOME/.claude/brainbuddy/lib" python3 -m brainbuddy.cli show
```

Print the one-line confirmation the CLI returns.

XP kept accruing while it was hidden, so level and progress reflect everything written to the
vault in the meantime. Expect it to come back further along than it left.

If it still doesn't appear, the cause is almost always the statusline script rather than this
setting. `doctor` is the next step, not a reinstall.

## Rules

- **Never print a filesystem path from a memory directory.** Same rule as `/brainbuddy`.
