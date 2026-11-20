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
cp "$D/uninstall.command" "$ST/Uninstall Horizon M1.command"; chmod +x "$ST/Uninstall Horizon M1.command"
ditto "$D/extras" "$ST/extras"
ditto "$D/LICENSES" "$ST/LICENSES"
cp "$D/READ-ME-FIRST.txt" "$ST/READ ME FIRST.txt"
# The look: every enabled resource pack (options.txt order) and the picked shader with its settings
# sidecar, from the live game. The installer copies them only if the player picks a look.
/usr/bin/python3 - "$HOME/Library/Application Support/horizon" "$ST/extras" "$ST/LICENSES/PACKS.md" <<'PY'
import json, os, re, shutil, sys, zipfile
gd, x, credits = sys.argv[1:]
line = next(l for l in open(f"{gd}/options.txt", encoding="utf-8") if l.startswith("resourcePacks:"))
order = json.loads(line.split(":", 1)[1])
os.makedirs(f"{x}/resourcepacks"); os.makedirs(f"{x}/shaderpacks")
json.dump(order, open(f"{x}/pack-order.json", "w"), ensure_ascii=False)
def text(d):  # pack.mcmeta description: string, text component or list of them
    if isinstance(d, str): return d
    if isinstance(d, list): return "".join(text(e) for e in d)
    if isinstance(d, dict): return text(d.get("text", "")) + text(d.get("extra", []))
    return ""
rows = []
for p in order:
    if not p.startswith("file/"): continue
    name = p[5:]; src = f"{gd}/resourcepacks/{name}"
    shutil.copy2(src, f"{x}/resourcepacks/{name}")
    try:
        with zipfile.ZipFile(src) as z:
            desc = text(json.loads(z.read("pack.mcmeta").decode("utf-8-sig"))["pack"].get("description", ""))
    except Exception:
        desc = ""
    clean = lambda s: re.sub(r"§.", "", s).replace("|", "/").replace("\n", " ").strip()
    rows.append(f"| {clean(name[:-4] if name.endswith('.zip') else name)} | {clean(desc)} |")
shader = next(l.split(":", 1)[1].strip() for l in open(f"{gd}/horizon-graphics.txt") if l.startswith("pickedShaderPack:"))
for f in (shader, shader + ".txt"):
    shutil.copy2(f"{gd}/shaderpacks/{f}", f"{x}/shaderpacks/{f}")
# The author's own settings (video, controls, mod keys, mod configs). The pack list and the shader are
# left out: the installer sets them from the look the player picks. lastServer is personal.
os.makedirs(f"{x}/settings")
drop = ("resourcePacks:", "incompatibleResourcePacks:", "lastServer:")
opts = [l for l in open(f"{gd}/options.txt", encoding="utf-8").read().splitlines() if not l.startswith(drop)]
open(f"{x}/settings/options.txt", "w", encoding="utf-8").write("\n".join(opts) + "\n")
gfx = ["pickedShaderPack:" if l.startswith("pickedShaderPack:") else l
       for l in open(f"{gd}/horizon-graphics.txt", encoding="utf-8").read().splitlines()]
open(f"{x}/horizon-graphics.txt", "w", encoding="utf-8").write("\n".join(gfx) + "\n")
shutil.copy2(f"{gd}/horizon-mods.txt", f"{x}/settings/horizon-mods.txt")
shutil.copytree(f"{gd}/config", f"{x}/settings/config")
with open(credits, "w") as o:
    o.write("# Resource packs and shader\n\n"
            "These packs are included as installed in the author's own game, so the look can be reproduced on\n"
            "another Mac. `Dramatic Skys M1` is Dramatic Skys with smaller sky textures for 8 GB Macs; the other\n"
            "third-party packs are unmodified. All rights stay with their authors. Packs named `Horizon-*-Compatibility`"
            ", `Tanush Fixes` and `Horizon-Texture-Fixes` were made for Horizon M1 (with the tools in this repo) from the listed mods' own\n"
            "assets. If you are an author and want a pack removed, open an issue on\n"
            "https://github.com/tm-droid/horizon-m1 and it is taken down.\n\n"
            f"Shader: `{shader}` (MakeUp Ultra Fast by Javier Garduño), with the settings file used here.\n\n"
            f"{len(rows)} resource packs, in load order (last wins):\n\n| Pack | Description (from pack.mcmeta) |\n|---|---|\n")
    o.write("\n".join(rows) + "\n")
print(f"look: {len(rows)} packs + {shader}")
PY
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
# Zipped packs hide their text from grep: scan inside every zip too.
# Third-party LICENSE files carry their authors' emails, so inside zips look for this user's own email only.
/usr/bin/python3 - "$ST" $NEEDLES "$(git config user.email 2>/dev/null || echo __none__)" <<'PY2' || FAIL=1
import pathlib, re, sys, zipfile
st, needles = sys.argv[1], [n.lower().encode() for n in sys.argv[2:] if len(n) >= 3]
bad = 0
for f in pathlib.Path(st).rglob("*.zip"):
    with zipfile.ZipFile(f) as z:
        for m in z.namelist():
            b = z.read(m); low = b.lower()
            if any(n in low for n in needles) or m.endswith((".log", "accounts.json", "servers.dat")):
                print(f"PERSONAL DATA inside {f.name}: {m}"); bad = 1
sys.exit(bad)
PY2
(( FAIL == 0 )) || { echo "privacy scan failed; zip not built" >&2; exit 1; }

(cd "$OUT/stage" && ditto -c -k --keepParent "Horizon M1" "$ZIP")
(cd "$OUT" && shasum -a 256 "${ZIP:t}" | tee "${ZIP:t}.sha256")
du -h "$ZIP"
