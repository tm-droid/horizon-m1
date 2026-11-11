#!/bin/zsh
# usage: ab.sh <A|B> <n>  -- A=bare, B=GM wrapper; fullscreen, MakeUp, uncapped (260). Run via queue only.
B="/Users/tanushmalhotra/Library/Application Support/ElyPrismLauncher"; R="$B/outputs/horizon-runtime"; G="$R/gamemode-wrapper"
Q=/Users/tanushmalhotra/Documents/Codex/2026-10-30/realtime-voice-chat-2/outputs/device-testing-queue.py
arm=$1; n=$2
if [ $arm = A ]; then export HGM_EXE="$R/launcher-data/versions/nightly-2026-11-03-f42ef42/horizon-client"; else export HGM_EXE="$G/Horizon GM.app/Contents/MacOS/horizon-client"; fi
export HGM_FULLSCREEN=1 HORIZON_TEST_QUEUE=1
cd "$B"
/usr/bin/log stream --style compact --predicate 'process == "gamepolicyd"' > "$G/out/ab-$arm$n.gplog" 2>&1 &
LP=$!
pmset -g batt | head -1
python3 "$G/horizon-offline-test-gm.py" --runtime nightly-2026-11-03-f42ef42 --case makeup --label gm-${arm:l}-$n --scene cow --width 1280 --height 720 --resolution-scale 100 --fps-cap 260 --workers 0 --frame-pacing efficient --warmup 15 --seconds 20 --flight
kill $LP
