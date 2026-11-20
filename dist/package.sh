#!/bin/zsh
# Build the friend-ready release zip from the live launcher + selected build. Never uploads.
# Usage: dist/package.sh [TAG]   (default: the launcher's selected version)
# Output: dist/out/Horizon-M1-<short>.zip and its .sha256
set -eu
D="${0:A:h}"
L="$HOME/Library/Application Support/horizon-launcher"
TAG="${1:-$(/usr/bin/python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["selected"])' "$L/settings.json")}"
V="$L/versions/$TAG"
SHORT="${${TAG##*-m1-}%%-*}"            # native-fdc87ae-m1-daily7-73de... -> daily7
OUT="$D/out"; ST="$OUT/stage/Horizon M1"; ZIP="$OUT/Horizon-M1-$SHORT.zip"
[[ -x "$V/horizon-client" ]] || { echo "no build at $V" >&2; exit 1; }
[[ -d "$D/LICENSES" ]] || { echo "dist/LICENSES missing" >&2; exit 1; }

rm -rf "$OUT/stage" "$ZIP" "$ZIP.sha256"; mkdir -p "$ST/game"
ditto --noextattr --noqtn /Applications/Horizon.app "$ST/Horizon.app"
# The base release and the build, without .local/ (Mojang assets prepared on this Mac: never shipped) and without install markers.
BASE=$(/usr/bin/python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["base"])' "$V/native-mods.json")
[[ -x "$L/versions/$BASE/horizon-client" ]] || { echo "base $BASE not installed" >&2; exit 1; }
for t in "$BASE" "$TAG"; do
  rsync -a --exclude '/.local' --exclude '/.installed' --exclude '.DS_Store' "$L/versions/$t/" "$ST/game/$t/"
done
sed -e "s/__TAG__/$TAG/" -e "s/__BASE__/$BASE/" "$D/install.command" > "$ST/Install Horizon M1.command"
chmod +x "$ST/Install Horizon M1.command"
ditto "$D/extras" "$ST/extras"
ditto "$D/LICENSES" "$ST/LICENSES"
cp "$D/READ-ME-FIRST.txt" "$ST/READ ME FIRST.txt"
find "$ST" -name .DS_Store -delete
# Build metadata (source-patches.json etc.) records absolute local paths; the launcher never reads them.
grep -rIl -- "$HOME" "$ST/game" | while IFS= read -r f; do sed -i '' "s#$HOME#~#g" "$f"; done
# Rust embeds build paths (cargo registry under this home) in panic messages. Swap the user name for a
# same-length placeholder so offsets stay valid, then re-sign ad hoc (the edit breaks the old signature).
ANON="${USER//?/u}"
for t in "$BASE" "$TAG"; do
  G="$ST/game/$t"; B="$G/Horizon.app/Contents/MacOS/horizon-client"
  grep -aq -- "/Users/$USER/" "$G/horizon-client" || continue
  LC_ALL=C perl -pi -e "s#/Users/\Q$USER\E/#/Users/$ANON/#g" "$G/horizon-client"
  codesign -f -s - "$G/horizon-client" 2>/dev/null
  # The app bundle's executable is the same program (a hard link in the launcher's copy).
  [[ -f "$B" ]] && cp "$G/horizon-client" "$B"
done

# Privacy scan: nothing personal in any file, text or binary.
FAIL=0
for pat in accounts.json servers.dat latest.log play-offline.out '*.log'; do
  hits=$(find "$ST" -name "$pat" | head -5); [[ -z "$hits" ]] || { echo "FORBIDDEN FILE: $hits"; FAIL=1; }
done
NEEDLES=("$USER" "$(id -F 2>/dev/null || echo __none__)")
[[ -r "$L/accounts.json" ]] && NEEDLES+=($(/usr/bin/python3 -c 'import json,sys;a=json.load(open(sys.argv[1]));print(" ".join(a.get("offline") or []))' "$L/accounts.json"))
for n in $NEEDLES; do
  [[ ${#n} -ge 3 ]] || continue
  t=$(grep -rIil -- "$n" "$ST" | head -5 || true)
  [[ -z "$t" ]] || { echo "PERSONAL STRING in text files: $t"; FAIL=1; }
  b=$(grep -rail -- "$n" "$ST" | wc -l | tr -d ' ')
  (( b == 0 )) || { echo "PERSONAL STRING in $b binary file(s)"; FAIL=1; }
done
grep -rIEl '[A-Za-z0-9._%+-]+@(gmail|outlook|hotmail|icloud|yahoo)\.' "$ST" | head -3 | sed 's/^/EMAIL in: /' | grep . && FAIL=1
(( FAIL == 0 )) || { echo "privacy scan failed; zip not built" >&2; exit 1; }

(cd "$OUT/stage" && ditto -c -k --keepParent "Horizon M1" "$ZIP")
(cd "$OUT" && shasum -a 256 "${ZIP:t}" | tee "${ZIP:t}.sha256")
du -h "$ZIP"
