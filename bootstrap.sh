#!/bin/bash
# brainbuddy bootstrap. fetches the latest release and hands off to its installer.

# pipefail is a bashism, so bash has to be confirmed before it gets set
if [ -z "${BASH_VERSION:-}" ]; then
  echo "this shell isn't bash, and the installer it runs is. pipe it to bash instead of sh." >&2
  exit 1
fi
set -euo pipefail

REPO="smejkaldesign/brainbuddy"
API="https://api.github.com/repos/$REPO"
WORKDIR=""

cleanup() {
  if [ -n "$WORKDIR" ]; then rm -rf "$WORKDIR"; fi
}
trap cleanup EXIT

die() { echo "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

have python3 || die "no python3 on this machine, and brainbuddy is python. install 3.9 or newer, then run this again."
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null ||
  die "the python3 here is older than 3.9, which is as far back as brainbuddy goes. upgrade it, then run this again."
have tar || die "no tar, so there's nothing here to unpack the download with. install it, then run this again."

if have curl; then
  DL=curl
elif have wget; then
  DL=wget
else
  die "no curl and no wget, so there's nothing here to download with. install either one, then run this again."
fi

# $1 url, to stdout
fetch() {
  if [ "$DL" = curl ]; then curl -fsSL "$1"; else wget -qO- "$1"; fi
}

# $1 url, $2 file to write
fetch_file() {
  if [ "$DL" = curl ]; then curl -fsSL "$1" -o "$2"; else wget -qO "$2" "$1"; fi
}

# the tag only exists inside the release json, and jq is not a fair thing to ask
# of a one-line install for the sake of one field
latest_tag() {
  fetch "$API/releases/latest" 2>/dev/null |
    sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1
}

WORKDIR="$(mktemp -d)"
SRC="$WORKDIR/brainbuddy"
TARBALL="$WORKDIR/release.tar.gz"
mkdir -p "$SRC"

if [ -n "${BRAINBUDDY_TARBALL:-}" ]; then
  # escape hatch for mirrors, offline installs and testing this script. takes a
  # url or a tarball already on disk
  case "$BRAINBUDDY_TARBALL" in
    http://*|https://*)
      echo "fetching brainbuddy from BRAINBUDDY_TARBALL"
      fetch_file "$BRAINBUDDY_TARBALL" "$TARBALL" || die "that download failed. check the url in BRAINBUDDY_TARBALL, then run this again."
      ;;
    *)
      echo "installing brainbuddy from the tarball in BRAINBUDDY_TARBALL"
      cp "$BRAINBUDDY_TARBALL" "$TARBALL" || die "there's no tarball at the path in BRAINBUDDY_TARBALL. point it at one, then run this again."
      ;;
  esac
else
  TAG="$(latest_tag || true)"
  if [ -n "$TAG" ]; then
    echo "fetching brainbuddy $TAG"
    fetch_file "$API/tarball/$TAG" "$TARBALL" ||
      die "github had the $TAG release but wouldn't hand it over. check your connection, then run this again."
  else
    # nothing tagged yet, so the default branch is the only thing there is to install
    echo "fetching brainbuddy from the default branch, since nothing is tagged yet"
    fetch_file "$API/tarball" "$TARBALL" ||
      die "couldn't reach github for the source. check your connection, then run this again."
  fi
fi

tar -xzf "$TARBALL" -C "$SRC" --strip-components=1 ||
  die "the download didn't unpack, so it arrived truncated or isn't a tarball. run this again."
[ -f "$SRC/install.sh" ] || die "the download has no install.sh in it, so it isn't brainbuddy. run this again."

# the installer has the last word here, egg included, so its output goes straight through
bash "$SRC/install.sh" "$@"
