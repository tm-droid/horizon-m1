#!/bin/zsh
# Switch Horizon between the full-look setup and faster presets measured on a MacBook Air M1 8 GB
# (real-profile bench, MakeUp shader, 64 packs, fullscreen 2880x1800, 2026-11-12):
#   pretty  your normal setup (all packs, resolutionScale 85, render distance 12)  ~46 fps, 3.4 GB
#   fast    Optimized Bushy Leaves off (everything else unchanged)               ~58 fps, 3.1 GB
#   max     fast + resolutionScale 70 + render distance 10                       fastest, softer image
#   status  print the current mode
# The game must be closed (it rewrites options.txt on exit). The first switch away from pretty
# saves the pretty values to .horizon-perf-pretty.json in the game folder; pretty restores them.
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
DROP = ("Optimized Bushy Leaves",)

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
    packs = json.loads(get(OPT, "resourcePacks"))
    if any(d in p for p in packs for d in DROP):
        return "pretty"
    return "max" if get(GFX, "resolutionScale") == "70" else "fast"

if mode == "status":
    print(f"mode: {current()}  resolutionScale {get(GFX, 'resolutionScale')}  renderDistance {get(OPT, 'renderDistance')}")
    sys.exit()
if mode not in ("pretty", "fast", "max"):
    sys.exit("usage: horizon-perf.sh pretty|fast|max|status")

if current() == "pretty":
    json.dump({"resourcePacks": get(OPT, "resourcePacks"), "renderDistance": get(OPT, "renderDistance"),
               "resolutionScale": get(GFX, "resolutionScale")}, open(SAVE, "w"), indent=1)
if not os.path.exists(SAVE):
    sys.exit(f"no saved pretty settings at {SAVE}; nothing to restore")
saved = json.load(open(SAVE))

if mode == "pretty":
    put(OPT, "resourcePacks", saved["resourcePacks"])
    put(OPT, "renderDistance", saved["renderDistance"])
    put(GFX, "resolutionScale", saved["resolutionScale"])
    os.remove(SAVE)
else:
    packs = [p for p in json.loads(saved["resourcePacks"]) if not any(d in p for d in DROP)]
    put(OPT, "resourcePacks", json.dumps(packs, separators=(",", ":")))
    put(OPT, "renderDistance", "10" if mode == "max" else saved["renderDistance"])
    put(GFX, "resolutionScale", "70" if mode == "max" else saved["resolutionScale"])
print(f"switched to {mode}")
PY
