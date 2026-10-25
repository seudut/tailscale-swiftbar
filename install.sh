#!/bin/sh
# ============================================================
# SwiftBar plugin installer (no sudo required)
#
# Usage:
#   sh install.sh                       # from a checkout / release zip
#   curl -fsSL https://raw.githubusercontent.com/seudut/tailscale-swiftbar/main/install.sh | sh
#
# Copies tailnet.10s.py into the SwiftBar plugin folder, makes it executable,
# and starts/refreshes SwiftBar.
# ============================================================
set -eu

RAW_URL="https://raw.githubusercontent.com/seudut/tailscale-swiftbar/main/tailnet.10s.py"
SELF_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || pwd)
DEST_DIR="$HOME/Library/Application Support/SwiftBar/Plugins"
DEST="$DEST_DIR/tailnet.10s.py"
SRC="$SELF_DIR/tailnet.10s.py"

mkdir -p "$DEST_DIR"

if [ -f "$SRC" ]; then
  cp "$SRC" "$DEST"
  echo "installed from local file: $SRC"
else
  echo "local plugin not found, downloading from $RAW_URL"
  curl -fsSL "$RAW_URL" -o "$DEST"
fi
chmod +x "$DEST"

# Remove an empty leftover directory created by an old SwiftBar support-dir bug.
if [ -d "$DEST_DIR/Users" ] && [ -z "$(find "$DEST_DIR/Users" -type f -print -quit 2>/dev/null)" ]; then
  rm -rf "$DEST_DIR/Users"
fi

echo "plugin installed: $DEST"
echo "refresh interval: 10s (rename to tailnet.5s.py / tailnet.1m.py to change)"
echo

if pgrep -x SwiftBar >/dev/null 2>&1; then
  open -g "swiftbar://refreshallplugins" 2>/dev/null || true
  echo "SwiftBar is running; refresh triggered"
else
  open -a SwiftBar 2>/dev/null || open -a "/Applications/SwiftBar.app"
  echo "SwiftBar started (keep the default plugin folder if asked)"
fi
