"""Paste-in configs for the surfaces outside a coding agent's statusline.

Every template calls `render` the way its host runs commands: a shell string
for tmux, starship, zsh and fish, an argv for oh-my-posh and wezterm, which
exec without a shell and so never expand ~. Home is always written relative,
never expanded, so a snippet pasted into a dotfiles repo carries no username.
"""

import os
import shutil

from . import state as state_mod

SURFACES = ("tmux", "starship", "zsh", "fish", "omp", "wezterm")

# the tmux default. under it the creature is cut off mid-word
TMUX_RIGHT_LENGTH = 80


def _tilde(path):
    home = os.path.expanduser("~")
    if path == home or path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path


def resolve_binary(state_dir=None, which=shutil.which):
    """How a surface should call us. {"shell": str, "argv": [str]}, both ~-relative.

    The pipx or pip entry point when it is on PATH, else the library the
    installer keeps under the state dir, run the way the statusline shim does.
    """
    found = which("terminalcreature")
    if found:
        return {"shell": _tilde(found), "argv": [_tilde(found)]}
    lib = _tilde(os.path.join(state_dir or state_mod.STATE_DIR, "lib"))
    # $HOME rather than ~ in the shell form: ~ only expands at the start of a
    # word, and this one sits after PYTHONPATH=
    return {
        "shell": "env PYTHONPATH=%s python3 -m terminalcreature.cli" % lib.replace("~", "$HOME", 1),
        "argv": ["env", "PYTHONPATH=" + lib, "python3", "-m", "terminalcreature.cli"],
    }


def _split_home(piece):
    """("PYTHONPATH=", "/.claude/x") for a piece carrying ~/, else None."""
    i = piece.find("~/")
    if i < 0 or (i > 0 and piece[i - 1] != "="):
        return None
    return piece[:i], piece[i + 1:]


def _lua_piece(piece):
    parts = _split_home(piece)
    if parts is None:
        return "'%s'" % piece
    prefix, rest = parts
    home = "wezterm.home_dir .. '%s'" % rest
    return "'%s' .. %s" % (prefix, home) if prefix else home


def _omp_piece(piece):
    parts = _split_home(piece)
    if parts is None:
        return '\\"%s\\"' % piece
    prefix, rest = parts
    return '(printf \\"%s%%s%s\\" .Env.HOME)' % (prefix, rest)


def _status_right_length():
    """What the running tmux server has, or None outside tmux."""
    if not os.environ.get("TMUX") or not shutil.which("tmux"):
        return None
    import subprocess

    try:
        out = subprocess.run(["tmux", "show-option", "-gv", "status-right-length"],
                             capture_output=True, text=True, timeout=2).stdout
        return int(out.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _tmux(b):
    current = _status_right_length()
    if current is not None and current >= TMUX_RIGHT_LENGTH:
        length = ["# your status-right-length is already %d, nothing to raise" % current]
    else:
        why = ("yours is %d" % current) if current is not None else "tmux's default is 40"
        length = ["# %s, which cuts the creature off mid-word" % why,
                  "set -g status-right-length %d" % TMUX_RIGHT_LENGTH]
    return "\n".join([
        "# ~/.tmux.conf. the creature in the right status, redrawn every status-interval",
        "# seconds (tmux's default is 15; the refresh also pokes tmux when xp changes)",
        "set -g status-interval 5",
    ] + length + [
        "set -g status-right '#(%s render --format tmux --width 40) %%H:%%M'" % b["shell"],
        "",
        "# or with tpm: add the plugin and put #{creature} wherever you like",
        "# set -g @plugin 'smejkaldesign/terminalcreature'",
        "# set -g status-right '#{creature} %H:%M'",
    ])


def _starship(b):
    return "\n".join([
        "# ~/.config/starship.toml. add $custom.creature (or $custom) to format or",
        "# right_format. command_timeout defaults to 500 ms; render reads a cache, so",
        "# it stays well inside. if colours show as literal codes, use --format plain",
        "[custom.creature]",
        "command = '%s render --format ansi'" % b["shell"],
        "when = true",
        'format = "[$output]($style)"',
        '# empty on purpose: the output already carries its colour',
        'style = ""',
        'shell = ["sh"]',
    ])


def _zsh(b):
    call = "%s render --format ansi" % b["shell"]
    return "\n".join([
        "# ~/.zshrc. the creature as the right prompt, redrawn on every prompt",
        "setopt PROMPT_SUBST",
        "RPROMPT='$(%s)'" % call,
        "",
        "# or from precmd, which some frameworks prefer over a substitution:",
        '# _creature_precmd() { RPROMPT="$(%s)" }' % call,
        "# precmd_functions+=(_creature_precmd)",
        "# powerlevel10k: instant prompt wants this async. run the call through a",
        "# zsh-async worker (github.com/mafredri/zsh-async) and set RPROMPT in its callback",
    ])


def _fish(b):
    return "\n".join([
        "# ~/.config/fish/functions/fish_right_prompt.fish. one line only, fish forbids more",
        'function fish_right_prompt -d "terminalcreature"',
        "    %s render --format ansi" % b["shell"],
        "end",
    ])


def _omp(b):
    # which found it on PATH, and oh-my-posh runs inside that shell, so the bare
    # name is the one form that needs no home expansion
    argv = ["terminalcreature"] if len(b["argv"]) == 1 else b["argv"]
    pieces = " ".join(_omp_piece(p) for p in argv + ["render", "--format", "plain"])
    caveat = [] if len(argv) == 1 else ["// .Env.HOME inside a cmd argument is unverified; with the pip entry point on PATH, none is needed"]
    return "\n".join([
        "// oh-my-posh theme json: one more segment in a block. cmd takes the command",
        "// name then its arguments (ohmyposh.dev/docs/configuration/templates).",
        "// plain format because whether ansi survives the template is unverified",
    ] + caveat + [
        "{",
        '  "type": "text",',
        '  "style": "plain",',
        '  "foreground": "#98c379",',
        '  "template": " {{ cmd %s }} "' % pieces,
        "}",
    ])


def _wezterm(b):
    argv = ", ".join(_lua_piece(p) for p in b["argv"] + ["render", "--format", "plain"])
    return "\n".join([
        "-- ~/.wezterm.lua. the creature in the right status, redrawn every",
        "-- status_update_interval ms. merge into your config if you already have one",
        "local wezterm = require 'wezterm'",
        "local config = wezterm.config_builder()",
        "config.status_update_interval = 1000",
        "wezterm.on('update-status', function(window, pane)",
        "  local ok, out = wezterm.run_child_process { %s }" % argv,
        "  window:set_right_status(ok and (out:gsub('\\n', '')) or '')",
        "end)",
        "return config",
    ])


TEMPLATES = {
    "tmux": _tmux, "starship": _starship, "zsh": _zsh,
    "fish": _fish, "omp": _omp, "wezterm": _wezterm,
}


def render_snippet(surface, binary=None, state_dir=None):
    """The paste-in config for one surface, or None for a surface we don't know."""
    fn = TEMPLATES.get(surface)
    if fn is None:
        return None
    return fn(binary or resolve_binary(state_dir))


def poke_tmux(env=None):
    """Ask tmux to redraw its status line now instead of at the next interval.

    Fire and forget: the refresh must not wait on tmux, and no failure here
    may reach the caller.
    """
    env = os.environ if env is None else env
    if not env.get("TMUX") or not shutil.which("tmux"):
        return False
    try:
        import subprocess

        subprocess.Popen(["tmux", "refresh-client", "-S"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    except Exception:
        return False
