#!/bin/zsh
# Switch Horizon between the full-look setup and a faster preset measured on a MacBook Air M1 8 GB
# (real-profile bench, MakeUp shader, 63 packs, fullscreen 2880x1800, 2026-11-12):
#   pretty  your normal setup (all packs, resolutionScale 85, render distance 12)  ~58 fps, 3.1 GB
#   max     pretty + resolutionScale 70 + render distance 10                     fastest, softer image
#   status  print the current mode
# Optimized Bushy Leaves (-12 fps, -320 MB) was removed from the look on 2026-11-21, so the old
# "fast" preset (pretty without it) is now the same as pretty.
# The game must be closed (it rewrites options.txt on exit). Switching to max saves the pretty
# values to .horizon-perf-pretty.json in the game folder; pretty restores them.
set -eu
G="$HOME/Library/Application Support/horizon"
MODE="${1:-status}"
if [[ "$MODE" != status ]] && pgrep -qx horizon-client; then
  echo "Horizon is running. Quit the game first." >&2; exit 1
fi
exec /usr/bin/python3 - "$G" "$MODE" <<'PY'
import json, os, re, sys
G, mode = sys.argv[1], sys.argv[2]
OPT, GFX, SAVE = (os.path.join(G, f) for f in ("options.txt", "horizon-graphics.txt", ".horizon-perf-pretty.json"))

def get(path, key):
    m = re.search(rf"^{key}:(.*)$", open(path).read(), re.M)
    return m.group(1) if m else None

def put(path, key, val):
    s = open(path).read()
    s2, n = re.subn(rf"^{key}:.*$", lambda _: f"{key}:{val}", s, flags=re.M)
    if not n:
        s2 = s.rstrip("\n") + f"\n{key}:{val}\n"
    open(path, "w").write(s2)

def current():
    return "max" if os.path.exists(SAVE) else "pretty"

if mode == "status":
    print(f"mode: {current()}  resolutionScale {get(GFX, 'resolutionScale')}  renderDistance {get(OPT, 'renderDistance')}")
    sys.exit()
if mode not in ("pretty", "max"):
    sys.exit("usage: horizon-perf.sh pretty|max|status")
if mode == current():
    sys.exit(f"already {mode}")

if mode == "max":
    json.dump({"renderDistance": get(OPT, "renderDistance"), "resolutionScale": get(GFX, "resolutionScale")},
              open(SAVE, "w"), indent=1)
    put(OPT, "renderDistance", "10")
    put(GFX, "resolutionScale", "70")
else:
    saved = json.load(open(SAVE))
    put(OPT, "renderDistance", saved["renderDistance"])
    put(GFX, "resolutionScale", saved["resolutionScale"])
    os.remove(SAVE)
print(f"switched to {mode}")
PY
