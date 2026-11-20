#!/bin/zsh
# Start the Horizon M1 build offline (no Microsoft sign-in), as the name picked in the installer.
# Singleplayer, LAN and offline-mode servers only. Log: ~/Library/Application Support/horizon/logs/play-offline.out
set -eu
L="$HOME/Library/Application Support/horizon-launcher"
G="$HOME/Library/Application Support/horizon"
M="$L/horizon-m1"
VER=$(<"$M/version.txt")
NAME=$(<"$M/player.txt")
V="$L/versions/$VER"
fail() { osascript -e "display alert \"Horizon Offline\" message \"$1\"" >/dev/null 2>&1 || echo "$1" >&2; exit 1; }
[[ -x "$V/horizon-client" ]] || fail "The M1 build is missing. Run Install Horizon M1 again."
[[ -d "$V/.local/horizon-client/26.3" ]] || fail "Game files are not prepared yet. Run Install Horizon M1 again and choose Offline."
pgrep -qx horizon-client && fail "Horizon is already running."
mkdir -p "$G/logs"
cd "$G"
nohup "$V/horizon-client" --resources "$V/.local/horizon-client/26.3" \
  --game-dir "$G" --home "$G" --name "$NAME" "$@" >"$G/logs/play-offline.out" 2>&1 &
disown
