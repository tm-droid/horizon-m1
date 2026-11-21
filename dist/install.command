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
HELP="Need help? Message whoever sent you Horizon, or open an issue: https://github.com/tm-droid/horizon-m1/issues"
die() { print -P "%F{red}%BError:%b%f $*" >&2; print "$HELP"; print "Press Return to close."; read -r _; exit 1; }
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
# An update reuses the game files an older build already prepared, when both builds use the same
# preparer: the launcher's `versions` command copies them in. Then no Minecraft install is needed again.
PREPARED="$LDIR/versions/$TAG/.local/horizon-client/26.3/horizon-resources.json"
if [[ ! -e "$PREPARED" ]]; then
  "$CLI" versions >/dev/null 2>&1 || true
  [[ -e "$PREPARED" ]] && say "Reused the game files your previous Horizon build prepared"
fi

# 3. Select it and stop auto-updates from replacing or pruning it
"$CLI" settings selected-version "$TAG" >/dev/null || die "The launcher refused the build. Send the text above to whoever gave you this."
"$CLI" settings install-new-versions off >/dev/null
"$CLI" settings prune-old-versions off >/dev/null
say "Selected $TAG in the launcher"

# 4. The author's settings tuned for an 8 GB M1: video, controls, mod keys and mod configs.
#    Each file is added only if the player has none yet, so their own settings are never replaced.
mkdir -p "$GDIR/config"
if [[ ! -e "$GDIR/horizon-graphics.txt" ]]; then
  cp "$HERE/extras/horizon-graphics.txt" "$GDIR/horizon-graphics.txt"
  say "Added M1 graphics settings"
fi
for f in options.txt horizon-mods.txt; do
  [[ -e "$GDIR/$f" ]] || cp "$HERE/extras/settings/$f" "$GDIR/$f"
done
cp -Rn "$HERE/extras/settings/config/" "$GDIR/config/" 2>/dev/null || true
# A small minimap (64 instead of the mod's default 128), only if the player has no minimap settings yet.
MM="$GDIR/horizon-mods/.horizon-mod-data/minimap_worldmap_waypoints_reworked"
if [[ ! -e "$MM/settings.ini" ]]; then
  mkdir -p "$MM"; cp "$HERE/extras/minimap/settings.ini" "$MM/settings.ini"
fi

# 5. Offline helper (always installed, so you can switch later)
mkdir -p "$M1DIR"
cp "$HERE/extras/play-offline.sh" "$M1DIR/play-offline.sh"
chmod +x "$M1DIR/play-offline.sh"
print "$TAG" > "$M1DIR/version.txt"

# 6. The full look: resource packs + shader. Never overwrites pack files; keeps the player's own packs enabled.
print ""
print -P "%BInstall the full look (64 resource packs + MakeUp shader)?%b"
print "  1) Full look   all packs + shader (recommended, about 45 fps on an M1 Air)"
print "  2) Fast look   same without Optimized Bushy Leaves (about 58 fps)"
print "  3) Plain       no packs, no shader (fastest)"
REPLY="${HM1_LOOK:-}"
[[ -n "$REPLY" ]] || ask "Type 1, 2 or 3 and press Return [1]:"
[[ -z "$REPLY" ]] && REPLY=1
if [[ "$REPLY" == [12] ]]; then
  LOOK="$REPLY"
  mkdir -p "$GDIR/resourcepacks" "$GDIR/shaderpacks"
  cp -n "$HERE/extras/resourcepacks/"*.zip "$GDIR/resourcepacks/" 2>/dev/null || true
  cp -n "$HERE/extras/shaderpacks/"* "$GDIR/shaderpacks/" 2>/dev/null || true
  SHADER=$(cd "$HERE/extras/shaderpacks" && command ls *.zip | head -1)
  # JavaScript for Automation, built into macOS. (/usr/bin/python3 is only a stub that pops up a
  # "install developer tools" dialog on Macs without the Xcode Command Line Tools.)
  /usr/bin/osascript -l JavaScript - "$HERE/extras/pack-order.json" "$GDIR" "$LOOK" "$SHADER" <<'JS' >/dev/null || die "Could not write the game settings."
ObjC.import('Foundation');
function run(argv) {
  const [orderF, gd, look, shader] = argv;
  const read = p => { const s = $.NSString.stringWithContentsOfFileEncodingError(p, $.NSUTF8StringEncoding, null); return s.isNil() ? null : s.js; };
  const write = (p, t) => { if (!$(t).writeToFileAtomicallyEncodingError(p, true, $.NSUTF8StringEncoding, null)) throw new Error('cannot write ' + p); };
  const full = JSON.parse(read(orderF));
  let packs = full.filter(p => look === '1' || !p.includes('Optimized Bushy Leaves'));
  // Keep packs the player enabled themselves, on top (last wins).
  const opts = read(gd + '/options.txt');
  const line = opts === null ? undefined : opts.split(/\r?\n/).find(l => l.startsWith('resourcePacks:'));
  if (line) { try { packs = packs.concat(JSON.parse(line.slice(14)).filter(p => !full.includes(p))); } catch (e) {} }
  const put = (path, key, value, extra) => {
    const t = read(path);
    const lines = t === null ? extra.slice() : t.split(/\r?\n/);
    if (t !== null && lines[lines.length - 1] === '') lines.pop();
    const i = lines.findIndex(l => l.startsWith(key + ':'));
    if (i >= 0) lines[i] = key + ':' + value; else lines.push(key + ':' + value);
    write(path, lines.join('\n') + '\n');
  };
  put(gd + '/options.txt', 'resourcePacks', JSON.stringify(packs), ['incompatibleResourcePacks:[]']);
  put(gd + '/horizon-graphics.txt', 'pickedShaderPack', shader, []);
  return '';
}
JS
  say "Installed the look (resource packs + $SHADER)"
fi

print ""
print -P "%BHow will you play?%b"
print "  1) Microsoft account  (normal: multiplayer servers, your skin)"
print "  2) Offline            (no sign-in: singleplayer, LAN and offline-mode servers)"
REPLY="${HM1_MODE:-}"
[[ -n "$REPLY" ]] || ask "Type 1 or 2 and press Return:"
case "$REPLY" in
  2)
    NAME="${HM1_NAME:-}"
    while [[ ! "$NAME" =~ '^[A-Za-z0-9_]{3,16}$' ]]; do
      ask "Pick a player name (3-16 letters, numbers or _):"; NAME="$REPLY"
    done
    print "$NAME" > "$M1DIR/player.txt"

    # Any launcher folder on this Mac that holds Minecraft 26.3 (official launcher, Prism and its forks,
    # MultiMC, Modrinth App, ATLauncher, GDLauncher...), tried one by one.
    auto_prepare() {
      local d
      for d in "$HOME/Library/Application Support/"*(N/) "$HOME/.minecraft"(N/); do
        [[ "${d:t}" == horizon* ]] && continue
        [[ -d "$d/assets" || -d "$d/meta/assets" ]] || continue
        [[ -n "$(find "$d" -maxdepth 5 -type d -name 26.3 2>/dev/null | head -1)" ]] || continue
        print "   Found Minecraft 26.3 in ${d/#$HOME/~}, preparing from it (a few minutes)"
        "$CLI" prepare --minecraft "$d" --version "$TAG" >>"$M1DIR/prepare.log" 2>&1 && return 0
        print "   That folder did not work (details: ${M1DIR/#$HOME/~}/prepare.log)"
      done
      return 1
    }

    say "Preparing the game's textures and sounds from your Minecraft: Java Edition install"
    print "   (needs Minecraft Java 26.3 installed and launched once, from the official launcher,"
    print "    Prism, Modrinth App, MultiMC, ATLauncher or GDLauncher)"
    until [[ -d "$LDIR/versions/$TAG/.local/horizon-client/26.3" ]] || "$CLI" prepare --version "$TAG" || auto_prepare; do
      print ""
      print "Horizon could not find Minecraft Java 26.3. Pick one:"
      print "  d       download it from Mojang (sign in once with a Microsoft account that owns Minecraft)"
      print "  Return  try again, after launching 26.3 once in your Minecraft launcher"
      print "  folder  drag your launcher's game folder (the one holding 'versions' and 'assets') into this window"
      ask "Type d, press Return, drag a folder, or type q to quit:"
      [[ "$REPLY" == q ]] && die "Not prepared. Run this installer again when Minecraft 26.3 is installed."
      if [[ "$REPLY" == d ]]; then
        print "A browser page opens: type the code shown here and sign in."
        "$CLI" account sign-in && "$CLI" prepare --download --version "$TAG" || print "The download did not finish."
      elif [[ -n "$REPLY" ]]; then
        DIR="${${REPLY%% }//\\ / }"; DIR="${DIR//\'/}"
        "$CLI" settings minecraft-dir "$DIR" >/dev/null || print "That folder was refused."
      fi
    done

    say "Making the 'Horizon Offline' app (you will find it in Launchpad)"
    OAPP="$HOME/Applications/Horizon Offline.app"
    mkdir -p "$HOME/Applications"; rm -rf "$OAPP"
    osacompile -o "$OAPP" -e "do shell script quoted form of \"$M1DIR/play-offline.sh\"" 2>/dev/null
    cp "$APP/Contents/Resources/"*.icns "$OAPP/Contents/Resources/applet.icns" 2>/dev/null || true
    touch "$OAPP"
    print ""
    print -P "%F{green}%BDone.%b%f Next time, open %BHorizon Offline%b from Launchpad to play as $NAME"
    print "  (or Finder > Go > Home > Applications). It shows no window of its own: the game opens after a few seconds."
    ask "Start it now? (y/n)"
    [[ "$REPLY" == [yY]* ]] && open "$OAPP"
    ;;
  *)
    print ""
    print -P "%F{green}%BDone.%b%f The Horizon launcher opens now:"
    print "  1. Sign in with the Microsoft account that owns Minecraft: Java Edition."
    print "  2. Press Play. The first start prepares the game (a few minutes), later ones are fast."
    print "  Do not press Install on a newer release unless you want to leave the M1 build."
    print "  Want more mods or packs? See \"Add your own mods and packs\" in the guide:"
    print "  https://github.com/tm-droid/horizon-m1#add-your-own-mods-and-packs"
    open "$APP"
    ;;
esac
print "You can close this window."
