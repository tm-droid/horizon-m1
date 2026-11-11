#!/bin/bash
# NOT auto-run. Queues live A/B validation behind running benches: A/A first (noise floor), then rd positive control.
Q="$HOME/Documents/Codex/2026-10-30/realtime-voice-chat-2/outputs/device-testing-queue.py"
PY=/Library/Frameworks/Python.framework/Versions/3.13/bin/python3
R="$HOME/Developer/Horizon/outputs/horizon-runtime"
python3 "$Q" run --owner minecraft -- $PY "$R/run-live-ab.py" --aa --a "gpu-culling on" --cycles 3 --tag aa1
python3 "$Q" run --owner minecraft -- $PY "$R/run-live-ab.py" --preset rd --cycles 3 --tag rd1
