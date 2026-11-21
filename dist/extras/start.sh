#!/bin/zsh
# What the "Horizon M1" app runs. First, at most once a day, it asks GitHub whether a newer Horizon M1 build
# is out and offers to update (Update / Later / Skip this version). Then it starts the game the way the
# installer set up: offline as the picked player name, or the Horizon launcher for a Microsoft account.
# No internet or GitHub down: the check is skipped quietly. Turn checks off: touch "$M/no-updates".
set -u
L="$HOME/Library/Application Support/horizon-launcher"
M="$L/horizon-m1"
APP="/Applications/Horizon.app"
REPO="tm-droid/horizon-m1"
# Same file name in every release, so this URL always serves the newest build's manifest.
MANIFEST="${HM1_MANIFEST_URL:-https://github.com/$REPO/releases/latest/download/horizon-m1.json}"
INSTALL="https://raw.githubusercontent.com/$REPO/main/install.sh"

check_update() {
  [[ -e "$M/no-updates" ]] && return
  [[ -z "${HM1_MANIFEST_URL:-}" && -n "$(find "$M/last-check" -mmin -1200 2>/dev/null)" ]] && return
  local json new short old b
  json=$(curl -fsSL --max-time 5 "$MANIFEST" 2>/dev/null) || return
  : > "$M/last-check"
  # JavaScript for Automation parses the JSON (built into macOS; python3 may be a developer-tools stub).
  read -r new short <<<"$(osascript -l JavaScript -e 'function run(a) {
    const m = JSON.parse(a[0]); return (m.tag || "") + " " + (m.short || "");
  }' "$json" 2>/dev/null)" || return
  old=$(cat "$M/version.txt" 2>/dev/null)
  [[ -n "$new" && "$new" != "$old" && "$new" != "$(cat "$M/skipped.txt" 2>/dev/null)" ]] || return
  # "Later" is the cancel button: it and Escape make osascript fail, and the game just starts.
  b=$(osascript -e "button returned of (display dialog \"Horizon M1 $short is out (you have ${${old##*-m1-}%-*}).

Update now? It takes a few minutes in a Terminal window. Your worlds and settings are kept.\" with title \"Horizon M1\" buttons {\"Skip this version\", \"Later\", \"Update\"} default button \"Update\" cancel button \"Later\" with icon POSIX file \"$APP/Contents/Resources/horizon.icns\")" 2>/dev/null) || return
  case "$b" in
    Update)
      # A .command file made here carries no quarantine flag, so Terminal opens it without warnings or
      # automation prompts. The installer reuses the saved answers and starts the game when it is done.
      print -r -- "#!/bin/zsh
HM1_START=1 zsh -c \"\$(curl -fsSL $INSTALL)\"" > "$M/update.command"
      chmod +x "$M/update.command"
      open "$M/update.command"
      exit 0 ;;
    "Skip this version") print -r -- "$new" > "$M/skipped.txt" ;;
  esac
}

check_update
MODE=$(cat "$M/mode.txt" 2>/dev/null) || { [[ -e "$M/player.txt" ]] && MODE=offline || MODE=microsoft; }
if [[ "$MODE" == offline ]]; then
  "$M/play-offline.sh" || true    # it shows its own alert on failure
else
  open "$APP"
fi
