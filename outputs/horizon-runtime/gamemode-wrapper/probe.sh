#!/bin/zsh
# usage: probe.sh <client-exe> <label> [seconds]   (run ONLY via device-testing-queue)
# Starts client fullscreen at title screen, records gamepolicyd logs.
set -u; HGM_FS="${HGM_FS---fullscreen}"
EXE="$1"; LABEL="$2"; SECS="${3:-20}"
B="/Users/tanushmalhotra/Library/Application Support/ElyPrismLauncher"; R="$B/outputs/horizon-runtime"
VER="$R/launcher-data/versions/nightly-2026-11-03-f42ef42"
OUT="$R/gamemode-wrapper/out"; mkdir -p "$OUT"
D=$(mktemp -d /private/tmp/gm-probe.XXXX)
pmset -g batt | head -1; pgrep -f PineconeMC && { echo PineconeMC running; exit 1; }
/usr/bin/log stream --style compact --predicate 'process == "gamepolicyd" OR process == "GamePolicyAgent" OR subsystem == "com.apple.gamepolicy"' > "$OUT/$LABEL.log" 2>&1 &
LP=$!
sleep 2
HORIZON_HOME="$D" "$EXE" --resources "$VER/.local/horizon-client/26.3" --game-dir "$D" --home "$D" --name HorizonTest ${=HGM_FS} > "$OUT/$LABEL.console" 2>&1 &
CP=$!
sleep 6
osascript -e "tell application \"System Events\" to set frontmost of (first process whose unix id is $CP) to true" 2>&1
sleep "$SECS"
kill $CP 2>/dev/null; sleep 3; kill -9 $CP 2>/dev/null
sleep 2; kill $LP
echo "pid=$CP exe=$EXE"; grep -ci "game mode" "$OUT/$LABEL.log"
grep -i "label\|game mode\|enabled\|disabled" "$OUT/$LABEL.log" | cut -c1-220 | tail -15
rm -rf "$D"
