#!/bin/zsh
# Horizon M1 installer. Double-click it (first time: right-click > Open, see the README).
# Installs the Horizon launcher and the M1-tuned Horizon build, then sets up either a
# Microsoft account (normal) or an offline player (no sign-in).
set -eu

HERE="${0:A:h}"
TAG="__TAG__"
BASE="__BASE__"                  # the Horizon release the M1 build is patched on; prepare needs it
LDIR="$HOME/Library/Application Support/horizon-launcher"
GDIR="$HOME/Library/Application Support/horizon"
APP="/Applications/Horizon.app"
CLI="$APP/Contents/MacOS/horizon-launcher"
M1DIR="$LDIR/horizon-m1"

say() { print -P "%B==>%b $*"; }
die() { print -P "%F{red}%BError:%b%f $*" >&2; print "Press Return to close."; read -r _; exit 1; }
ask() { print -n "$1 "; read -r REPLY || { print "\nInput closed."; exit 1; }; }

clear 2>/dev/null || true
print -P "%BHorizon M1 installer%b  (build $TAG)\n"

[[ "$(uname -m)" == arm64 ]] || die "This build is for Apple Silicon Macs (M1/M2/M3/M4) only."
[[ -d "$HERE/Horizon.app" && -d "$HERE/game/$TAG" && -d "$HERE/game/$BASE" ]] || die "Run this from inside the unzipped \"Horizon M1\" folder."
pgrep -qx horizon-client && die "Horizon is running. Quit the game first."
pgrep -qf 'MacOS/horizon-launcher( -psn[^ ]*)?$' && die "The Horizon launcher is open. Quit it (Cmd+Q) first."

say "Clearing the download quarantine on this folder"
xattr -dr com.apple.quarantine "$HERE" 2>/dev/null || true

# 1. Launcher app
if [[ -d "$APP" ]]; then
  OLD=$(defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null || echo 0)
  NEW=$(defaults read "$HERE/Horizon.app/Contents/Info.plist" CFBundleShortVersionString)
  if [[ "$(printf '%s\n%s\n' "$OLD" "$NEW" | sort -V | tail -1)" == "$OLD" ]]; then
    say "Horizon launcher $OLD is already installed (keeping it)"
  else
    say "Updating the Horizon launcher $OLD -> $NEW"
    rm -rf "$APP"; ditto "$HERE/Horizon.app" "$APP"
  fi
else
  say "Installing the Horizon launcher to /Applications"
  ditto "$HERE/Horizon.app" "$APP" || die "Could not copy to /Applications. Drag Horizon.app there by hand, then run this again."
fi
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true

# 2. The base release and the tuned build on top of it
mkdir -p "$LDIR/versions"
for t in "$BASE" "$TAG"; do
  if [[ -d "$LDIR/versions/$t" ]]; then
    say "$t is already installed (keeping its prepared game files)"
  else
    say "Installing $t"
    rm -rf "$LDIR/versions/$t.partial"
    ditto "$HERE/game/$t" "$LDIR/versions/$t.partial"
    mv "$LDIR/versions/$t.partial" "$LDIR/versions/$t"
  fi
  : > "$LDIR/versions/$t/.installed"
done

# 3. Select it and stop auto-updates from replacing or pruning it
"$CLI" settings selected-version "$TAG" >/dev/null || die "The launcher refused the build. Send the text above to whoever gave you this."
"$CLI" settings install-new-versions off >/dev/null
"$CLI" settings prune-old-versions off >/dev/null
say "Selected $TAG in the launcher"

# 4. Starter graphics settings tuned for an 8 GB M1 (only if the game has none yet)
mkdir -p "$GDIR"
if [[ ! -e "$GDIR/horizon-graphics.txt" ]]; then
  cp "$HERE/extras/horizon-graphics.txt" "$GDIR/horizon-graphics.txt"
  say "Added M1 starter graphics settings"
fi

# 5. Offline helper (always installed, so you can switch later)
mkdir -p "$M1DIR"
cp "$HERE/extras/play-offline.sh" "$M1DIR/play-offline.sh"
chmod +x "$M1DIR/play-offline.sh"
print "$TAG" > "$M1DIR/version.txt"

# 6. The full look: resource packs + shader. Never overwrites pack files; keeps the player's own packs enabled.
print ""
print -P "%BInstall the full look (63 resource packs + MakeUp shader)?%b"
print "  1) Full look   all packs + shader (about 45 fps on an M1 Air)"
print "  2) Fast look   same without Optimized Bushy Leaves (about 58 fps)"
print "  3) Plain       no packs, no shader (fastest)"
ask "Type 1, 2 or 3 and press Return:"
if [[ "$REPLY" == [12] ]]; then
  LOOK="$REPLY"
  mkdir -p "$GDIR/resourcepacks" "$GDIR/shaderpacks"
  cp -n "$HERE/extras/resourcepacks/"*.zip "$GDIR/resourcepacks/" 2>/dev/null || true
  cp -n "$HERE/extras/shaderpacks/"* "$GDIR/shaderpacks/" 2>/dev/null || true
  SHADER=$(cd "$HERE/extras/shaderpacks" && command ls *.zip | head -1)
  /usr/bin/python3 - "$HERE/extras/pack-order.json" "$GDIR" "$LOOK" "$SHADER" <<'PY' || die "Could not write the game settings."
import json, sys
order_f, gd, look, shader = sys.argv[1:]
full = json.load(open(order_f))
packs = [p for p in full if look == "1" or "Optimized Bushy Leaves" not in p]
# Keep packs the player enabled themselves, on top (last wins).
try:
    line = next(l for l in open(f"{gd}/options.txt", encoding="utf-8") if l.startswith("resourcePacks:"))
    packs += [p for p in json.loads(line.split(":", 1)[1]) if p not in full]
except (FileNotFoundError, StopIteration, ValueError):
    pass
def put(path, key, value, extra=()):
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except FileNotFoundError:
        lines = list(extra)
    new = f"{key}:{value}"
    for i, l in enumerate(lines):
        if l.startswith(key + ":"):
            lines[i] = new; break
    else:
        lines.append(new)
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
put(f"{gd}/options.txt", "resourcePacks", json.dumps(packs, separators=(",", ":")), ["incompatibleResourcePacks:[]"])
put(f"{gd}/horizon-graphics.txt", "pickedShaderPack", shader)
PY
  say "Installed the look (resource packs + $SHADER)"
fi

print ""
print -P "%BHow will you play?%b"
print "  1) Microsoft account  (normal: multiplayer servers, your skin)"
print "  2) Offline            (no sign-in: singleplayer and LAN only)"
ask "Type 1 or 2 and press Return:"
case "$REPLY" in
  2)
    NAME=""
    while [[ ! "$NAME" =~ '^[A-Za-z0-9_]{3,16}$' ]]; do
      ask "Pick a player name (3-16 letters, numbers or _):"; NAME="$REPLY"
    done
    print "$NAME" > "$M1DIR/player.txt"

    say "Preparing the game's textures and sounds from your Minecraft: Java Edition install"
    print "   (needs Minecraft Java 26.3 installed and launched once, from the official launcher,"
    print "    Prism, Modrinth App, MultiMC, ATLauncher or GDLauncher)"
    until [[ -d "$LDIR/versions/$TAG/.local/horizon-client/26.3" ]] || "$CLI" prepare --version "$TAG"; do
      print ""
      print "Horizon could not find Minecraft Java 26.3. Launch 26.3 once in your Minecraft launcher,"
      print "or drag your launcher's game folder (the one holding 'versions' and 'assets') into this window."
      ask "Folder (or Return to try again, q to quit):"
      [[ "$REPLY" == q ]] && die "Not prepared. Run this installer again when Minecraft 26.3 is installed."
      if [[ -n "$REPLY" ]]; then
        DIR="${${REPLY%% }//\\ / }"; DIR="${DIR//\'/}"
        "$CLI" settings minecraft-dir "$DIR" >/dev/null || print "That folder was refused."
      fi
    done

    say "Making 'Horizon Offline' in your Applications folder"
    OAPP="$HOME/Applications/Horizon Offline.app"
    mkdir -p "$HOME/Applications"; rm -rf "$OAPP"
    osacompile -o "$OAPP" -e "do shell script quoted form of \"$M1DIR/play-offline.sh\"" 2>/dev/null
    cp "$APP/Contents/Resources/"*.icns "$OAPP/Contents/Resources/applet.icns" 2>/dev/null || true
    touch "$OAPP"
    print ""
    print -P "%F{green}%BDone.%b%f Open %BHorizon Offline%b (Launchpad or ~/Applications) to play as $NAME."
    ask "Start it now? (y/n)"
    [[ "$REPLY" == [yY]* ]] && open "$OAPP"
    ;;
  *)
    print ""
    print -P "%F{green}%BDone.%b%f The Horizon launcher opens now:"
    print "  1. Sign in with the Microsoft account that owns Minecraft: Java Edition."
    print "  2. Press Play. The first start prepares the game (a few minutes), later ones are fast."
    print "  Do not press Install on a newer release unless you want to leave the M1 build."
    open "$APP"
    ;;
esac
print "You can close this window."
