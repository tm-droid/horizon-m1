#!/bin/zsh
# Start the launcher's selected Horizon build offline, as the launcher's selected
# offline account, with Agent Control on (so horizon-ctl / game_* tools can watch it).
# The launcher's own Play button needs a Microsoft account; this does not.
# Usage: tools/play-offline.sh [extra horizon-client args...]
set -eu
L="$HOME/Library/Application Support/horizon-launcher"
G="$HOME/Library/Application Support/horizon"
read -r VER NAME < <(/usr/bin/python3 - "$L" <<'PY'
import json, sys, os
L = sys.argv[1]
s = json.load(open(os.path.join(L, "settings.json")))
a = json.load(open(os.path.join(L, "accounts.json")))
print(s["selected"], a.get("offline_selected") or (a.get("offline") or ["Player"])[0])
PY
)
V="$L/versions/$VER"
[[ -x "$V/horizon-client" ]] || { echo "selected build $VER has no horizon-client" >&2; exit 1; }
if pgrep -qx horizon-client; then echo "Horizon is already running" >&2; exit 1; fi
SOCK="${TMPDIR%/}/horizon-control.sock"
LOG="$G/logs/play-offline.out"
mkdir -p "$G/logs"
echo "Horizon $VER as $NAME (control socket $SOCK)"
cd "$G"
nohup "$V/horizon-client" --resources "$V/.local/horizon-client/26.3" \
  --game-dir "$G" --home "$G" --name "$NAME" --control --control-socket "$SOCK" "$@" \
  >"$LOG" 2>&1 &
disown
