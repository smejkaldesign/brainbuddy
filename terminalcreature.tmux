#!/usr/bin/env bash
# tpm only runs *.tmux files at the plugin root. the plugin itself lives in tmux/
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tmux/terminalcreature.tmux" "$@"
