#!/bin/sh
# Install (or update) the TOTEM cheatsheet desktop widget into Übersicht.
#
#   ./install.sh                 widget + wallsnap (frosted glass)
#   ./install.sh --with-keyglow  also build keyglow (key highlighting); it is NOT started,
#                                see README.md before running it
#
# Re-run after editing anything in this folder: Übersicht reloads the widget by itself.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
repo=$(dirname "$here")
dest="$HOME/Library/Application Support/Übersicht/widgets/totem-cheatsheet.widget"

with_keyglow=0
case "${1:-}" in
  "") ;;
  --with-keyglow) with_keyglow=1 ;;
  *) echo "usage: $0 [--with-keyglow]" >&2; exit 2 ;;
esac

command -v swiftc >/dev/null || {
  echo "swiftc not found: install the Xcode command line tools (xcode-select --install)" >&2
  exit 1
}
[ -d "/Applications/Übersicht.app" ] || echo "note: Übersicht is not installed (brew install --cask ubersicht)" >&2

mkdir -p "$dest"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Build into a temp dir and move into place, so the widget never runs a half-written binary.
echo "building wallsnap…"
swiftc -O "$here/wallsnap.swift" -o "$tmp/wallsnap"
mv -f "$tmp/wallsnap" "$dest/wallsnap"

if [ "$with_keyglow" = 1 ]; then
  echo "building keyglow (not started)…"
  swiftc -O "$here/keyglow.swift" -o "$tmp/keyglow"
  mv -f "$tmp/keyglow" "$dest/keyglow"
fi

# Point the widget at this checkout's SVG, then install it last: that triggers the reload.
sed "s|^const SVG = .*|const SVG = \"$repo/totem-keymap-cheatsheet.svg\";|" "$here/index.jsx" > "$tmp/index.jsx"
mv -f "$tmp/index.jsx" "$dest/index.jsx"

# Sources live in the repo only.
rm -f "$dest"/*.swift

echo "installed in: $dest"
