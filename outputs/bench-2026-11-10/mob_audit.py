#!/usr/bin/env python3
"""Mob visual audit launcher: stages a throwaway real-look profile, runs F7 ONCE with a control socket,
and stays up until the game exits (drive it with horizon-ctl --socket /private/tmp/horizon-mobaudit.sock).
On exit: copies logs to the scratchpad and removes the profile. Usage: mob_audit.py [windowed]"""
import sys, types, time, subprocess, shutil
from pathlib import Path
import real, bench as B
real.ARGS = types.SimpleNamespace(windowed=sys.argv[1:2] == ["windowed"], uncapped=True)
OUT = Path(__file__).with_name("mobaudit")
B.PROFILES = OUT / "prof"; B.PROFILES.mkdir(exist_ok=True)
if subprocess.run(["pgrep", "-x", "horizon-client"]).returncode == 0:
    sys.exit("game already running")
prof = B.PROFILES / "mobaudit"; subprocess.run(["rm", "-rf", str(prof)])
real.real_stage(prof, "F7", "makeup", B.TEMPLATE, "mobaudit")
_G = real.GAME
subprocess.run(["/bin/cp", str(_G / "horizon-mods.txt"), str(prof / "horizon-mods.txt")], check=True)
subprocess.run(["/bin/cp", "-cR", str(_G / "config/jade"), str(prof / "config/jade")], check=True)
MM = prof / "horizon-mods/.horizon-mod-data/minimap_worldmap_waypoints_reworked"; MM.mkdir(parents=True)
(MM / "settings.ini").write_text("enabled=true\ncorner=top_right\nsize=64\nshape=square\nzoom=1\nrotate=false\nmini_dimension=player\nworld_dimension=player\noverworld_coordinates=true\nnether_coordinates=true\n")
g = real.RealGame("F7", prof, "mobaudit")
print("launched pid", g.p.pid, flush=True)
try:
    g.p.wait()
finally:
    g.quit()
    for n in ("console.log",):
        shutil.copy(prof / n, OUT / n)
    logs = prof / "logs"
    if logs.exists():
        shutil.copytree(logs, OUT / "logs", dirs_exist_ok=True)
    B.trash(prof)
    print("done, logs copied", flush=True)
