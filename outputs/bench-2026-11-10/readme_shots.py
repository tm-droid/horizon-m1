#!/usr/bin/env python3
"""README screenshots on the real profile (63 packs + MakeUp). Usage: readme_shots.py [explore]"""
import sys, types, time, subprocess
import real, bench as B
real.ARGS = types.SimpleNamespace(windowed=False, uncapped=True)
name = "readme"
out = B.OUT / "shots-readme"; out.mkdir(exist_ok=True)
# (tag, time, x, y, z, yaw, pitch)
SHOTS = [
    ("day", 6000, -527.5, 95, 57.5, 0, 5), ("day2", 6000, -527.5, 95, 57.5, 90, 5),
    ("day3", 6000, -527.5, 95, 57.5, 180, 5), ("day4", 6000, -527.5, 95, 57.5, 270, 5),
    ("sunset", 12000, -527.5, 95, 57.5, 270, 3), ("sunset2", 12000, -527.5, 95, 57.5, 90, 3),
    ("night", 18000, -527.5, 95, 57.5, 0, -35),
    ("mobs", 6000, -527.5, 95, 57.5, 270, 8, {"ctl": [["summon", "villager", "-530.5", "95", "57.5"], ["summon", "cow", "-531", "95", "59"], ["summon", "pig", "-531", "95", "56", "baby"], ["summon", "sheep", "-532.5", "95", "58"]]}),
    ("hud", 6000, -527.5, 95, 57.5, 270, 5, {"hud": True}),
]
if sys.argv[1:2] == ["custom"]:
    import json; SHOTS = [tuple(s) for s in json.load(open(sys.argv[2]))]
subprocess.run(["pgrep", "-x", "horizon-client"], check=False)
prof = B.PROFILES / f"sky-{name}"; subprocess.run(["rm", "-rf", str(prof)])
real.real_stage(prof, "F7", "makeup", B.TEMPLATE, name)
_G = real.GAME
subprocess.run(["/bin/cp", str(_G / "horizon-mods.txt"), str(prof / "horizon-mods.txt")], check=True)
subprocess.run(["/bin/cp", "-cR", str(_G / "config/jade"), str(prof / "config/jade")], check=True)
MM = prof / "horizon-mods/.horizon-mod-data/minimap_worldmap_waypoints_reworked"; MM.mkdir(parents=True)
(MM / "settings.ini").write_text("""# Minimap Reworked settings
enabled=true
corner=top_right
size=64
shape=square
zoom=1
rotate=false
mini_dimension=player
world_dimension=player
overworld_coordinates=true
nether_coordinates=true
""")
g = real.RealGame("F7", prof, f"sky{name}")
try:
    g.wait_socket(); g.ctl("wait-ready", "240", timeout=245); g.settle(); g.front()
    g.ctl("key", "f1", "tap")
    hud = False
    for tag, t, x, y, z, yaw, pitch, *ex in SHOTS:
        ex = ex[0] if ex else {}
        if bool(ex.get("hud")) != hud:
            g.ctl("key", "f1", "tap"); hud = bool(ex.get("hud"))
        g.ctl("tp", str(x), str(y), str(z)); g.ctl("time", str(t)); g.ctl("look", str(yaw), str(pitch))
        for c in ex.get("ctl", []):
            try: g.ctl(*c)
            except Exception as e: print("ctl fail", c, str(e)[:200], flush=True)
        time.sleep(3); g.settle(); time.sleep(3)
        for c in ex.get("post", []):
            g.ctl(*c)
        if ex.get("post"):
            time.sleep(4)
            print(tag, [(e.get("type","?")[10:], [round(v,1) for v in e.get("pos",[0,0,0])], e.get("health")) for e in g.ctl("entities")["entities"]], flush=True)
        g.ctl("screenshot", str(out / f"{tag}.png")); time.sleep(2)
    print("ok")
finally:
    g.quit(); B.trash(prof)
