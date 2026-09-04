#!/bin/sh
# runs terminalcreature from wherever it is installed: the pip or pipx entry
# point when it is on PATH, else the library the installer keeps under ~/.claude,
# the same way the statusline shim runs it
if command -v terminalcreature >/dev/null 2>&1; then
  exec terminalcreature "$@"
fi
PYTHONPATH="$HOME/.claude/terminalcreature/lib" exec python3 -m terminalcreature.cli "$@"
