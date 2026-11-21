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
def ents(): return [(e.get("type","?")[10:], [round(v,1) for v in e.get("pos",[0,0,0])], e.get("health")) for e in g.ctl("entities")["entities"]]
def pos(): return g.ctl("state")["player"]["position"]
try:
    g.wait_socket(); g.ctl("wait-ready", "240", timeout=245); g.settle(); g.front()
    g.ctl("time","6000")
    for it,n in (("diamond_sword",1),("diamond_pickaxe",1),("torch",32),("bread",16),("oak_planks",64)): g.ctl("give",it,str(n))
    # HUD: platform above canopy
    g.ctl("tp","-515.5","95","-9.5"); time.sleep(3); g.settle()
    r=g.ctl("fill","-516","105","-10","-516","105","-10","stone"); print("fill",str(r)[:200])
    print("block",str(g.ctl("block","-516","105","-10"))[:200],flush=True)
    g.ctl("tp","-515.5","106","-9.5"); time.sleep(3); g.settle(); print("pos",pos(),flush=True)
    time.sleep(1)
    for i,yaw in enumerate((0,90,180,270)):
        g.ctl("look",str(yaw),"2"); time.sleep(4)
        g.ctl("screenshot",str(out/f"hud{i}.png")); time.sleep(2)
    g.ctl("key","f1","tap"); time.sleep(1)  # HUD off
    spots=[(-519.5,79,9.5,-519.5,79,13.5)]
    for i,(x,y,z,mx,my,mz) in enumerate(spots):
        g.ctl("tp",str(x),str(y),str(z)); time.sleep(2); g.settle(); print("pos",pos(),flush=True)
        g.ctl("look-at",str(mx),str(my+0.8),str(mz))
        for k,(dx,dz) in zip(("villager","cow","sheep","pig","chicken"),((0,0),(-1.5,0.5),(1.5,1),(-1,-1),(1.2,-1.2))):
            g.ctl("summon",k,str(mx+dx),str(my),str(mz+dz))
        time.sleep(1.5); g.ctl("look-at",str(mx),str(my+0.8),str(mz)); time.sleep(0.5)
        print("mobs",i,ents(),flush=True)
        g.ctl("screenshot",str(out/f"mobs{i}a.png")); time.sleep(1.5)
        print("mobs",i,ents(),flush=True)
        g.ctl("screenshot",str(out/f"mobs{i}b.png")); time.sleep(1)
    print("ok")
finally:
    g.quit(); B.trash(prof)
