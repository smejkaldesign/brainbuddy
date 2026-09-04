---
name: creature-update
description: "Check for a newer terminalcreature release and install it, keeping the creature. Use when the user asks to update, upgrade, or get the latest version of their terminalcreature, pet, creature, or statusline buddy."
user_invocable: true
---

# /creature-update

Ask pypi whether a newer terminalcreature is out, and if one is, install it over this one.
The creature, its XP, the roster and every setting stay exactly as they are; only the library
and the statusline shim change. This is the one `/creature` command that goes online, and it
does so because the user asked.

```bash
PYTHONPATH="$HOME/.claude/terminalcreature/lib" python3 -m terminalcreature.cli update --apply
```

Print what the CLI returns. The first line is the version check; the rest is the installer's
output when there was something to install. Its last line already says the statusline picks the
new version up on its next redraw, so don't add a restart instruction.

## If the user only wants to know

If the request is a question ("is there an update?", "am I current?") rather than an
instruction, drop `--apply` so nothing is downloaded:

```bash
PYTHONPATH="$HOME/.claude/terminalcreature/lib" python3 -m terminalcreature.cli update
```

Print the one line it returns. Offer to apply it only if the line says a newer version is out.

## Rules

- **Never print a filesystem path from a memory directory.** Same rule as `/creature`.
- Don't reinstall from scratch, `pip install`, or run the website's bootstrap when this fails;
  the CLI's message says what went wrong and whether the old version is still wired (it is,
  unless the message says otherwise). Relay it.
- If `~/.claude/terminalcreature/lib` is missing there is nothing to update. Point at `/creature`,
  which knows how to wire a fresh install.
- Under a plugin install the installer is told to leave the command files alone, so nothing
  here ever produces a second `/creature` in the picker. Don't pass extra flags to fix that.
