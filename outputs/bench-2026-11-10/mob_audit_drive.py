#!/usr/bin/env python3
"""Drive a running mob_audit.py game: python3 mob_audit_drive.py setup | run GROUPFILE.json | (groups inline in GROUPS)
Each group: [name, [[type, "nbt", dx(optional)]...], {"ai":bool,"y":float}]"""
import json, subprocess, sys, time, os, math
from pathlib import Path
OUT = Path(__file__).with_name("mobaudit")
SHOTS = OUT / "shots"; SHOTS.mkdir(exist_ok=True)
REL = Path.home() / "Library/Application Support/horizon-launcher/versions/native-fdc87ae-m1-daily7-73decc0fdc30"
CH = 1000
SOCK = "/private/tmp/horizon-mobaudit.sock"
CX, CZ, GY = -527.5, 57.5, 150

def ctl(*a, timeout=30):
    r = subprocess.run([str(REL / "horizon-ctl"), "--socket", SOCK, "--timeout", str(timeout), *map(str, a)], capture_output=True, text=True, timeout=timeout + 5)
    try: return json.loads(r.stdout)
    except Exception: return {"error": r.stdout[-200:] + r.stderr[-200:]}

def setup():
    ctl("key", "f1", "tap") if False else None
    ctl("time", "6000"); ctl("command", "weather clear"); ctl("command", "gamerule doMobSpawning false")
    ctl("command", "gamerule advance_time false"); ctl("command", "gamerule doDaylightCycle false")

def cam(px, pz, tx, tz, ty=GY + 0.8):
    yaw = -math.degrees(math.atan2(tx - px, tz - pz))
    d = math.hypot(tx - px, tz - pz)
    pitch = math.degrees(math.atan2(GY + 1.62 - ty, d))
    ctl("tp", px, GY, pz); ctl("look", round(yaw, 1), round(pitch, 1))

def crop(src, dst):
    subprocess.run(["sips", "-c", str(CH), "1500", str(src), "--out", str(dst)], capture_output=True)
    subprocess.run(["sips", "-Z", "760", str(dst)], capture_output=True)

def run(groups):
    for name, mobs, *opt in groups:
        o = opt[0] if opt else {}
        ctl("command", "kill @e[type=!player]"); time.sleep(1.2); ctl("command", "kill @e[type=!player]"); ctl("command", "kill @e[type=experience_orb]"); time.sleep(0.5)
        cx, cz = o.get("c", (CX, CZ)); n = len(mobs); res = []
        for i, m in enumerate(mobs):
            t, nbt = m[0], m[1]
            x = cx + (i - (n - 1) / 2) * o.get("sp", 1.9); z = cz - (i - (n - 1) / 2) * o.get("zs", 1.1); y = GY + o.get("y", 0)
            tags = ["Rotation:[0f,0f]"] + ([] if o.get("ai") else ["NoAI:1b"])
            if nbt: tags.append(nbt)
            r = ctl("command", f"summon minecraft:{t} {x} {y} {z} {{{','.join(tags)}}}")
            res.append((t, (r.get("chat") or [r.get("error")])[0]))
        time.sleep(o.get("wait", 3.0))
        f, s, k = SHOTS / f"{name}_f.png", SHOTS / f"{name}_s.png", SHOTS / f"{name}_b.png"
        d = o.get("d", 4.2)
        cam(cx - d * .6, cz + d * .8, cx, cz, o.get("ty", GY + 0.8)); time.sleep(0.8); ctl("screenshot", f)
        cam(cx + d, cz, cx, cz, o.get("ty", GY + 0.8)); time.sleep(0.8); ctl("screenshot", s)
        crop(f, SHOTS / f"{name}_fc.png"); crop(s, SHOTS / f"{name}_sc.png")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", SHOTS / f"{name}_fc.png", "-i", SHOTS / f"{name}_sc.png", "-filter_complex", "hstack", SHOTS / f"{name}_m.png"])
        ents = ctl("entities", 20).get("entities", [])
        print(name, [(e["type"][10:], "B" if e.get("baby") else "", round(e["pos"][1], 1)) for e in ents], [r for r in res if "Summoned" not in str(r[1])], flush=True)
        for x in ("_fc", "_sc"): (SHOTS / f"{name}{x}.png").unlink(missing_ok=True)

if __name__ == "__main__":
    if sys.argv[1] == "setup": setup()
    else: run(json.load(open(sys.argv[2])))
