#!/bin/sh
# Stop the old-code U9b runner at its next failed first attempt (during the 30 s cooldown, before
# any retry), then re-queue U9b --resume so the patched hopeless rule decides. Exits when U9b ends.
R="$(cd "$(dirname "$0")" && pwd)"
Q=~/Documents/Codex/2026-10-30/realtime-voice-chat-2/outputs/device-testing-queue.py
P=/Library/Frameworks/Python.framework/Versions/3.13/bin/python3
start=$(wc -l < "$R/u9b-queue.log")
while pgrep -f "run-u9b-shaders.py --tag u9b" >/dev/null; do
  if tail -n +"$((start + 1))" "$R/u9b-queue.log" | grep -q '"attempt": 1, "valid": false'; then
    pkill -f "run-u9b-shaders.py --tag u9b"
    sleep 5
    nohup python3 "$Q" run --owner minecraft -- "$P" "$R/run-u9b-shaders.py" --tag u9b --resume >> "$R/u9b-queue.log" 2>&1 &
    echo "stopped U9b at a failed attempt 1, re-queued with --resume"
    exit 0
  fi
  sleep 3
done
echo "U9b ended on its own"
