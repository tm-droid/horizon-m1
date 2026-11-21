#!/bin/zsh
# Horizon M1 uninstaller. Double-click it (first time: right-click > Open).
# Moves to the Trash (nothing is deleted for good) only what the Horizon M1 installer added. If you had Horizon
# before, your launcher, its other versions and your settings stay, and Horizon M1's changes to the launcher
# are undone. Your worlds are kept unless you say otherwise.
set -eu

LDIR="$HOME/Library/Application Support/horizon-launcher"
GDIR="$HOME/Library/Application Support/horizon"
APP="/Applications/Horizon.app"
CLI="$APP/Contents/MacOS/horizon-launcher"
M1DIR="$LDIR/horizon-m1"
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
# Any launcher process but `horizon-launcher mcp` (the server agents use), whatever its arguments.
if pgrep -qx horizon-client || pgrep -lf 'MacOS/horizon-launcher' | grep -qv 'horizon-launcher mcp$'; then
  print "Quit Horizon (the game and the launcher) first, then run this again."; ask "Press Return to close."; exit 1
fi
if [[ ! -d "$M1DIR" && ! -d "$HOME/Applications/Horizon M1.app" && ! -d "$HOME/Applications/Horizon Offline.app" ]]; then
  print "Horizon M1 is not installed here. Nothing changed."; exit 0
fi

# What the installer noted: the player's setup before Horizon M1 (before.txt, key=value), the versions it put
# in (versions.txt, plus the current build in version.txt) and the game files it added (added.txt).
typeset -A B
if [[ -r "$M1DIR/before.txt" ]]; then
  while IFS='=' read -r k v; do [[ -z "$k" ]] || B[$k]="$v"; done < "$M1DIR/before.txt"
fi
typeset -U MINE
MINE=(${(f)"$(cat "$M1DIR/versions.txt" "$M1DIR/version.txt" 2>/dev/null || true)"})
HAD=(${=B[versions]:-})
MINE=(${MINE:|HAD})
ADDED=(${(f)"$(cat "$M1DIR/added.txt" 2>/dev/null || true)"})
# A copy: the helper folder may be in the Trash by the time it is read.
ADDF=$(mktemp); trap 'rm -f "$ADDF"' EXIT; print -rl -- $ADDED > "$ADDF"

# ALL=1: the player had no Horizon before Horizon M1, so the launcher and its folder go too.
ALL=0
if [[ "${B[known]:-0}" == 1 ]]; then
  [[ "${B[app]:-1}" == 0 && "${B[ldir]:-1}" == 0 ]] && ALL=1
  GHAD=${B[gdir]:-1}
else
  print "This Horizon M1 was installed by an older installer, which kept no record of what you had before."
  ask "Did you use Horizon (the launcher or its game) before installing Horizon M1? (y/n)"
  [[ "$REPLY" == [yY]* ]] || ALL=1
  GHAD=$(( 1 - ALL ))
  print ""
fi

print "This moves to the Trash:"
if (( ALL )); then
  print "  /Applications/Horizon.app, ~/Applications/Horizon M1.app,"
  print "  and the launcher folder with the installed builds."
else
  print "  ~/Applications/Horizon M1.app and the Horizon M1 helper folder"
  for t in $MINE; do
    if [[ -d "$LDIR/versions/$t" ]]; then print "  the build $t"; fi
  done
  [[ "${B[minecraft]:-1}" == 0 && -d "$LDIR/minecraft" ]] && print "  the Minecraft files Horizon M1 downloaded"
  [[ "${B[app]:-1}" == 0 ]] && print "  /Applications/Horizon.app"
  print "You had Horizon before, so your launcher, its other versions and your accounts stay,"
  print "and its settings go back to what they were."
fi
ask "Continue? (y/n)"
[[ "$REPLY" == [yY]* ]] || { print "Nothing changed."; exit 0; }

if (( ALL )); then
  trash "$APP"
  trash "$HOME/Applications/Horizon M1.app"
  trash "$HOME/Applications/Horizon Offline.app"   # made by older installers
  trash "$LDIR"
else
  # The launcher settings first, while the CLI and the versions they name are still there.
  if [[ -x "$CLI" ]]; then
    PIN=${B[pin]:-}; [[ "$PIN" == - ]] && PIN=
    if [[ -z "$PIN" ]] || ! "$CLI" instance version horizon "$PIN" >/dev/null 2>&1; then
      "$CLI" instance version horizon latest >/dev/null 2>&1 || true
    fi
    if [[ -n "${B[instance]:-}" && "${B[instance]}" != - ]]; then
      "$CLI" instance select "${B[instance]}" >/dev/null 2>&1 || true
    fi
    SEL=${B[selected]:-}
    if [[ -n "$SEL" && -z "${MINE[(r)$SEL]:-}" ]]; then
      "$CLI" settings selected-version "$SEL" >/dev/null 2>&1 || true
    fi
    # Horizon's defaults (on) when the installer saw no launcher settings.
    [[ "${B[install_new]:-true}" == false ]] && V=off || V=on
    "$CLI" settings install-new-versions $V >/dev/null 2>&1 || true
    [[ "${B[prune]:-true}" == false ]] && V=off || V=on
    "$CLI" settings prune-old-versions $V >/dev/null 2>&1 || true
    print "  launcher settings restored"
  fi
  for t in $MINE; do trash "$LDIR/versions/$t"; done
  [[ "${B[minecraft]:-1}" == 0 ]] && trash "$LDIR/minecraft"
  trash "$HOME/Applications/Horizon M1.app"
  trash "$HOME/Applications/Horizon Offline.app"   # made by older installers
  [[ "${B[app]:-1}" == 0 ]] && trash "$APP"
fi

print ""
if [[ "$GHAD" == 0 ]]; then
  print "Your worlds, settings and resource packs are in ~/Library/Application Support/horizon."
  ask "Move them to the Trash too? Type DELETE to do it, or just press Return to keep them:"
  if [[ "$REPLY" == DELETE ]]; then
    trash "$GDIR"
  else
    print "  kept: $GDIR"
  fi
elif (( ${#ADDED} )); then
  print "Horizon M1 added ${#ADDED} files to your game folder (resource packs, the shader, settings files)."
  ask "Move those to the Trash? Your worlds and your own files stay. (y/n)"
  if [[ "$REPLY" == [yY]* ]]; then
    # Take the removed packs out of the enabled list. If the shader is Horizon M1's, put back the one picked
    # before Horizon M1 (none when there was none).
    /usr/bin/osascript -l JavaScript - "$GDIR" "$ADDF" "${B[shader]:-}" <<'JS' >/dev/null || print "  could not update options.txt"
ObjC.import('Foundation');
function run(argv) {
  const [gd, addedF, before] = argv;
  const read = p => { const s = $.NSString.stringWithContentsOfFileEncodingError(p, $.NSUTF8StringEncoding, null); return s.isNil() ? null : s.js; };
  const write = (p, t) => { if (!$(t).writeToFileAtomicallyEncodingError(p, true, $.NSUTF8StringEncoding, null)) throw new Error('cannot write ' + p); };
  const added = read(addedF).split('\n').filter(Boolean);
  const packs = added.filter(a => a.startsWith('resourcepacks/')).map(a => 'file/' + a.slice(14));
  const shaders = added.filter(a => a.startsWith('shaderpacks/')).map(a => a.slice(12));
  const edit = (p, f) => { const t = read(p); if (t === null) return; const out = t.split('\n').map(f).join('\n'); if (out !== t) write(p, out); };
  edit(gd + '/options.txt', l => {
    if (!l.startsWith('resourcePacks:')) return l;
    try { return 'resourcePacks:' + JSON.stringify(JSON.parse(l.slice(14)).filter(p => !packs.includes(p))); } catch (e) { return l; }
  });
  edit(gd + '/horizon-graphics.txt', l => l.startsWith('pickedShaderPack:') && shaders.includes(l.slice(17)) ? 'pickedShaderPack:' + (before || '') : l);
  return '';
}
JS
    for f in $ADDED; do trash "$GDIR/$f" >/dev/null; done
    print "  moved ${#ADDED} files to the Trash"
  else
    print "  kept: $GDIR"
  fi
else
  print "  kept your game folder: $GDIR"
fi
# Last: the helper folder holds the record read above.
(( ALL )) || trash "$M1DIR"
print ""
print -P "%F{green}%BDone.%b%f Empty the Trash to free the space. You can close this window."
