#!/usr/bin/env bash
# tpm entry point. swaps #{creature} in status-left and status-right for a call
# to the helper beside this file, so the placeholder works from any install
# location. the same shape as tmux-battery.
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
placeholder='#{creature}'
creature="#($CURRENT_DIR/creature.sh render --format tmux)"
# bash 5.2 would otherwise read an & in the clone path as "the matched text"
shopt -u patsub_replacement 2>/dev/null || true

update_option() {
  local option="$1"
  local value
  value="$(tmux show-option -gqv "$option")"
  # only rewrite what carries the placeholder, so an untouched option stays untouched
  case "$value" in
    *"$placeholder"*) tmux set-option -gq "$option" "${value//"$placeholder"/$creature}" ;;
  esac
}

update_option status-left
update_option status-right
