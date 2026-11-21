#!/bin/zsh
# Horizon M1 uninstaller. Double-click it (first time: right-click > Open).
# Moves Horizon to the Trash (nothing is deleted for good). Your worlds are kept unless you say otherwise.
set -eu

LDIR="$HOME/Library/Application Support/horizon-launcher"
GDIR="$HOME/Library/Application Support/horizon"
ask() { print -n "$1 "; read -r REPLY || { print "\nInput closed."; exit 1; }; }
# macOS 15+ has /usr/bin/trash; older macOS asks Finder (it may ask once to allow Terminal to control Finder).
trash() {
  [[ -e "$1" ]] || return 0
  if [[ -x /usr/bin/trash ]]; then /usr/bin/trash "$1"
  else osascript -e "tell application \"Finder\" to delete (POSIX file \"$1\" as alias)" >/dev/null; fi
  print "  moved to Trash: $1"
}

clear 2>/dev/null || true
print -P "%BHorizon M1 uninstaller%b\n"
if pgrep -qx horizon-client || pgrep -qf 'MacOS/horizon-launcher( -psn[^ ]*)?$'; then
  print "Quit Horizon (the game and the launcher) first, then run this again."; ask "Press Return to close."; exit 1
fi
print "This moves to the Trash:"
print "  /Applications/Horizon.app, ~/Applications/Horizon M1.app,"
print "  and the launcher folder with the installed builds."
ask "Continue? (y/n)"
[[ "$REPLY" == [yY]* ]] || { print "Nothing changed."; exit 0; }

trash "/Applications/Horizon.app"
trash "$HOME/Applications/Horizon M1.app"
trash "$HOME/Applications/Horizon Offline.app"   # made by older installers
trash "$LDIR"

print ""
print "Your worlds, settings and resource packs are in ~/Library/Application Support/horizon."
ask "Move them to the Trash too? Type DELETE to do it, or just press Return to keep them:"
if [[ "$REPLY" == DELETE ]]; then
  trash "$GDIR"
else
  print "  kept: $GDIR"
fi
print ""
print -P "%F{green}%BDone.%b%f Empty the Trash to free the space. You can close this window."
