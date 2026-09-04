# terminalcreature for tmux

A [tpm](https://github.com/tmux-plugins/tpm) plugin. Add to `~/.tmux.conf`, then `prefix + I`:

    set -g @plugin 'smejkaldesign/terminalcreature'
    set -g status-right '#{creature} %H:%M'
    set -g status-right-length 80

`#{creature}` becomes a call to `creature.sh render --format tmux`, which finds terminalcreature
on PATH or under `~/.claude/terminalcreature/lib`. `terminalcreature snippet tmux` prints the same config.
