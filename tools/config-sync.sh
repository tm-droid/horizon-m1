#!/bin/sh
# Copy Horizon's live settings into this repo (snapshot) or back to the game (restore).
#   tools/config-sync.sh snapshot   live -> config/   (then commit)
#   tools/config-sync.sh restore    config/ -> live   (game and launcher must be closed)
# Not tracked on purpose: accounts.json, servers.dat, command_history.txt.
set -eu
REPO=$(cd "$(dirname "$0")/.." && pwd)
GAME="$HOME/Library/Application Support/horizon"
LAUNCHER="$HOME/Library/Application Support/horizon-launcher"
DEST="$REPO/config"

FILES_GAME="horizon-graphics.txt options.txt horizon-mods.txt horizon-player.txt"
FILES_LAUNCHER="settings.json instances.json"

case "${1:-}" in
snapshot)
  mkdir -p "$DEST/game/shaderpacks" "$DEST/game/config" "$DEST/launcher"
  for f in $FILES_GAME; do [ -f "$GAME/$f" ] && cp -p "$GAME/$f" "$DEST/game/$f"; done
  for f in "$GAME"/shaderpacks/*.txt; do [ -f "$f" ] && cp -p "$f" "$DEST/game/shaderpacks/"; done
  rsync -a --delete "$GAME/config/" "$DEST/game/config/"
  for f in $FILES_LAUNCHER; do cp -p "$LAUNCHER/$f" "$DEST/launcher/$f"; done
  echo "snapshot written to $DEST; review with: git -C \"$REPO\" diff -- config"
  ;;
restore)
  if pgrep -x horizon-client >/dev/null || pgrep -f '/Horizon.app/' >/dev/null; then
    echo "Horizon is running. Quit the game and launcher first (they rewrite these files)." >&2
    exit 1
  fi
  for f in $FILES_GAME; do [ -f "$DEST/game/$f" ] && cp -p "$DEST/game/$f" "$GAME/$f"; done
  for f in "$DEST"/game/shaderpacks/*.txt; do [ -f "$f" ] && cp -p "$f" "$GAME/shaderpacks/"; done
  rsync -a "$DEST/game/config/" "$GAME/config/"
  for f in $FILES_LAUNCHER; do cp -p "$DEST/launcher/$f" "$LAUNCHER/$f"; done
  echo "restored from $DEST"
  ;;
*)
  echo "usage: $0 snapshot|restore" >&2
  exit 2
  ;;
esac
