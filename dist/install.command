#!/bin/zsh
# Horizon M1 installer. Double-click it (first time: right-click > Open, see the README).
# Installs the Horizon launcher and the M1-tuned Horizon build, then sets up either a
# Microsoft account (normal) or an offline player (no sign-in). Running it again updates: it keeps the
# answers given last time (HM1_ASK=1 asks again). HM1_START=1 starts the game at the end.
set -eu

HERE="${0:A:h}"
TAG="__TAG__"
SHORT="__SHORT__"                # TAG without the commit and hash: what players see (daily7-fix3)
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
print -P "%BHorizon M1 installer%b  (build $SHORT)\n"

[[ "$(uname -m)" == arm64 ]] || die "This build is for Apple Silicon Macs (M1/M2/M3/M4) only."
[[ -d "$HERE/Horizon.app" && -d "$HERE/game/$TAG" && -d "$HERE/game/$BASE" ]] || die "Run this from inside the unzipped \"Horizon M1\" folder."
pgrep -qx horizon-client && die "Horizon is running. Quit the game first."
pgrep -qf 'MacOS/horizon-launcher( -psn[^ ]*)?$' && die "The Horizon launcher is open. Quit it (Cmd+Q) first."

# Answers from the last run. An update with all of them asks nothing.
PREV=$(cat "$M1DIR/version.txt" 2>/dev/null || true)
SAVED_LOOK=$(cat "$M1DIR/look.txt" 2>/dev/null || true)
SAVED_MODE=$(cat "$M1DIR/mode.txt" 2>/dev/null || true)
SAVED_NAME=$(cat "$M1DIR/player.txt" 2>/dev/null || true)
UPDATE=0
if [[ -z "${HM1_ASK:-}" && "$SAVED_LOOK" == [123] && ( "$SAVED_MODE" == microsoft || ( "$SAVED_MODE" == offline && -n "$SAVED_NAME" ) ) ]]; then
  UPDATE=1
  : ${HM1_LOOK:=$SAVED_LOOK}
  [[ "$SAVED_MODE" == offline ]] && { : ${HM1_MODE:=2}; : ${HM1_NAME:=$SAVED_NAME}; } || : ${HM1_MODE:=1}
  WHO="Microsoft account"; [[ "$HM1_MODE" == 2 ]] && WHO="offline as ${HM1_NAME:-}"
  print "Updating${PREV:+ from ${${PREV##*-m1-}%-*}}. Keeping your choices: look $HM1_LOOK, $WHO."
  print "(To change them, run the installer with HM1_ASK=1.)\n"
fi

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
# Old M1 builds this installer put in (they carry the .installed marker) take about 1 GB each. Keep this one,
# its base release and the one it replaces (a fallback: Settings > selected version in the launcher).
for d in "$LDIR/versions/"*-m1-*(N/); do
  t="${d:t}"
  [[ "$t" == "$TAG" || "$t" == "$BASE" || "$t" == "$PREV" || ! -e "$d/.installed" ]] && continue
  rm -rf "$d" && say "Removed the old build ${${t##*-m1-}%-*}"
done

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

# 5. The Horizon M1 app's script (update check, then start) and the offline helper, always installed so
#    the player can switch later.
mkdir -p "$M1DIR"
for f in start.sh play-offline.sh; do
  cp "$HERE/extras/$f" "$M1DIR/$f"; chmod +x "$M1DIR/$f"
done
print "$TAG" > "$M1DIR/version.txt"
rm -f "$M1DIR/skipped.txt" "$M1DIR/update.command"

# "Horizon M1" in Launchpad (~/Applications), for both Microsoft and offline players. Replaces the older
# "Horizon Offline" app.
make_app() {
  OAPP="$HOME/Applications/Horizon M1.app"
  mkdir -p "$HOME/Applications"; rm -rf "$OAPP" "$HOME/Applications/Horizon Offline.app"
  osacompile -o "$OAPP" -e "do shell script quoted form of \"$M1DIR/start.sh\"" 2>/dev/null \
    || die "Could not make the Horizon M1 app."
  cp "$APP/Contents/Resources/horizon.icns" "$OAPP/Contents/Resources/applet.icns" 2>/dev/null || true
  touch "$OAPP"
}

# 6. The full look: resource packs + shader. Never overwrites pack files; keeps the player's own packs enabled.
print ""
print -P "%BInstall the full look (64 resource packs + MakeUp shader)?%b"
print "  1) Full look   all packs + shader (recommended, about 45 fps on an M1 Air)"
print "  2) Fast look   same without Optimized Bushy Leaves (about 58 fps)"
print "  3) Plain       no packs, no shader (fastest)"
REPLY="${HM1_LOOK:-}"
[[ -n "$REPLY" ]] || ask "Type 1, 2 or 3 and press Return [1]:"
[[ -z "$REPLY" ]] && REPLY=1
[[ "$REPLY" == [123] ]] || REPLY=3
print "$REPLY" > "$M1DIR/look.txt"
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
    print offline > "$M1DIR/mode.txt"

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

    # Minecraft's own files from Mojang's public servers, no sign-in: the version JSON this build
    # pins (by its SHA-1), the client jar, the macOS libraries, the asset index and every asset,
    # each checked against the SHA-1 Mojang lists. They go where the launcher keeps its own
    # download ($LDIR/minecraft, the official launcher's layout), so `prepare` finds them there;
    # prepare fetches Java 25 and the server jar itself. Files already whole are kept, so a
    # stopped download goes on where it stopped. JSON is read with JavaScript for Automation:
    # macOS 12 has no jq.
    MOJANG_JS=$(cat <<'EOF'
ObjC.import('Foundation');
function run(a) {
  var d = JSON.parse($.NSString.stringWithContentsOfFileEncodingError(a[1], $.NSUTF8StringEncoding, null).js);
  var out = [], add = function (sha1, url, path) { out.push(sha1 + ' ' + url + ' ' + path); };
  if (a[0] == 'lock') return d.minecraft.version + ' ' + d.minecraft.manifest_sha1;
  if (a[0] == 'game') {
    var c = d.downloads.client, i = d.assetIndex;
    add(c.sha1, c.url, 'versions/' + d.id + '/' + d.id + '.jar');
    d.libraries.forEach(function (l) {
      var ok = !l.rules, x = l.downloads && l.downloads.artifact;
      (l.rules || []).forEach(function (r) { if (!r.os || r.os.name == 'osx') ok = r.action == 'allow'; });
      if (ok && x) add(x.sha1, x.url, 'libraries/' + x.path);
    });
    add(i.sha1, i.url, 'assets/indexes/' + i.id + '.json');
  } else {
    var seen = {};
    for (var k in d.objects) {
      var h = d.objects[k].hash;
      if (!seen[h]) { seen[h] = 1; add(h, 'https://resources.download.minecraft.net/' + h.slice(0, 2) + '/' + h, 'assets/objects/' + h.slice(0, 2) + '/' + h); }
    }
  }
  return out.join('\n');
}
EOF
)
    # One file: $1 SHA-1, $2 URL, $3 path (relative, no spaces). Kept when already whole.
    GET1='[[ -f $3 && "$(shasum -a 1 <$3)" == $1* ]] && exit 0
mkdir -p ${3:h} && curl -fsSL --retry 2 -o $3.partial $2 && [[ "$(shasum -a 1 <$3.partial)" == $1* ]] && mv $3.partial $3 && exit 0
rm -f $3.partial; print -u2 "   Failed: $2"; exit 1'
    mojang_json() { osascript -l JavaScript -e "$MOJANG_JS" "$@"; }
    mojang_get() { (cd "$LDIR/minecraft" && xargs -P 8 -n 3 /bin/zsh -c "$GET1" _); }
    mojang_download() {
      local pin v sha list
      pin=$(mojang_json lock "$LDIR/versions/$TAG/research-lock.json") || return 1
      v=${pin% *}; sha=${pin#* }
      mkdir -p "$LDIR/minecraft" || return 1
      print "   Downloading Minecraft $v from Mojang (about 560 MB)"
      print "$sha https://piston-meta.mojang.com/v1/packages/$sha/$v.json versions/$v/$v.json" | mojang_get || return 1
      list=$(mojang_json game "$LDIR/minecraft/versions/$v/$v.json") || return 1
      print "   The game and $(( ${#${(f)list}} - 2 )) libraries"
      print -r -- "$list" | mojang_get || return 1
      list=$(mojang_json objects "$LDIR/minecraft/${${(f)list}[-1]##* }") || return 1
      print "   Textures and sounds: ${#${(f)list}} files"
      print -r -- "$list" | mojang_get
    }

    say "Preparing the game's textures and sounds from your Minecraft: Java Edition install"
    print "   (needs Minecraft Java 26.3 installed and launched once, from the official launcher,"
    print "    Prism, Modrinth App, MultiMC, ATLauncher or GDLauncher)"
    until [[ -d "$LDIR/versions/$TAG/.local/horizon-client/26.3" ]] || "$CLI" prepare --version "$TAG" || auto_prepare; do
      print ""
      print "Horizon could not find Minecraft Java 26.3. Pick one:"
      print "  d       download it from Mojang (about 560 MB)"
      print "  Return  try again, after launching 26.3 once in your Minecraft launcher"
      print "  folder  drag your launcher's game folder (the one holding 'versions' and 'assets') into this window"
      ask "Type d, press Return, drag a folder, or type q to quit:"
      [[ "$REPLY" == q ]] && die "Not prepared. Run this installer again when Minecraft 26.3 is installed."
      if [[ "$REPLY" == d ]]; then
        ask "Do you have a Microsoft account that owns Minecraft: Java Edition? (y/n)"
        if [[ "$REPLY" == [yY]* ]]; then
          print "A browser page opens: type the code shown here and sign in."
          "$CLI" account sign-in && "$CLI" prepare --download --version "$TAG" || print "The download did not finish."
        else
          mojang_download || print "The download did not finish. Type d to go on where it stopped."
        fi
      elif [[ -n "$REPLY" ]]; then
        DIR="${${REPLY%% }//\\ / }"; DIR="${DIR//\'/}"
        "$CLI" settings minecraft-dir "$DIR" >/dev/null || print "That folder was refused."
      fi
    done

    say "Making the 'Horizon M1' app (you will find it in Launchpad)"
    make_app
    print ""
    print -P "%F{green}%BDone.%b%f Next time, open %BHorizon M1%b from Launchpad to play as $NAME"
    print "  (or Finder > Go > Home > Applications). It shows no window of its own: the game opens after a few seconds."
    print "  It checks for new Horizon M1 builds once a day and asks before updating."
    if [[ -n "${HM1_START:-}" ]]; then
      open "$OAPP"
    else
      ask "Start it now? (y/n)"
      [[ "$REPLY" == [yY]* ]] && open "$OAPP"
    fi
    ;;
  *)
    print microsoft > "$M1DIR/mode.txt"
    say "Making the 'Horizon M1' app (you will find it in Launchpad)"
    make_app
    print ""
    if (( UPDATE )); then
      print -P "%F{green}%BUpdated to $SHORT.%b%f The Horizon launcher opens now: press Play."
      print "  Next time, open Horizon M1 from Launchpad."
      open "$APP"
      print "You can close this window."
      exit 0
    fi
    print -P "%F{green}%BDone.%b%f Next time, open %BHorizon M1%b from Launchpad: it checks for updates, then opens"
    print "  the Horizon launcher. The launcher opens now:"
    print "  1. Sign in with the Microsoft account that owns Minecraft: Java Edition."
    print "  2. Press Play. The first start prepares the game (a few minutes), later ones are fast."
    print "  Do not press Install on a newer release unless you want to leave the M1 build."
    print "  Want more mods or packs? See \"Add your own mods and packs\" in the guide:"
    print "  https://github.com/tm-droid/horizon-m1#add-your-own-mods-and-packs"
    open "$APP"
    ;;
esac
print "You can close this window."
