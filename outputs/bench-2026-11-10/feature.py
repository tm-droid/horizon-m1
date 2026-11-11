#!/usr/bin/env python3
"""u7a tasks 2+3: disposable-profile boots using the REAL game-home options/packs/graphics/mods settings.
  feature.py compat --build S --pack no|yes   boot, summon CEM mobs + lanterns, save latest.log
  feature.py mods                              DAILY boot, drive via horizon-ctl, save screenshots
The real game home is only read. Saves are cloned from the bench template world."""
import json, subprocess, sys, time
from pathlib import Path
import bench as B

REAL = Path.home() / "Library/Application Support/horizon"
OUT = B.OUT


def stage(label, opts_text, survival=False):
    prof = B.PROFILES / label
    prof.mkdir(parents=True, exist_ok=False)
    (prof / "saves").mkdir()
    subprocess.run(["/bin/cp", "-cR", str(B.TEMPLATE), str(prof / "saves/Horizon-Test")], check=True)
    (prof / "resourcepacks").mkdir()
    for z in (REAL / "resourcepacks").iterdir():
        subprocess.run(["/bin/cp", "-c", str(z), str(prof / "resourcepacks")], check=True)
    (prof / "shaderpacks").mkdir()
    for z in (REAL / "shaderpacks").glob("MakeUp-UltraFast-9.6.zip*"):
        subprocess.run(["/bin/cp", "-c", str(z), str(prof / "shaderpacks")], check=True)
    (prof / "options.txt").write_text(opts_text)
    (prof / "horizon-graphics.txt").write_text((REAL / "horizon-graphics.txt").read_text())
    for f in ("horizon-mods.txt", "horizon-player.txt"):
        if (REAL / f).exists():
            (prof / f).write_text((REAL / f).read_text())
    return prof


def opts(pack):
    t = (REAL / "options.txt").read_text()
    has = "Horizon-Tanush-Compat-2026-11-10.zip" in t
    if pack == "no" and has:
        t = t.replace(',"file/Horizon-Tanush-Compat-2026-11-10.zip"', "")
    t = t.replace("fullscreen:true", "fullscreen:false").replace("maxFps:60", "maxFps:120")
    return t + "pauseOnLostFocus:false\n"


def boot(build, label, o):
    g = B.gate()
    prof = stage(label, o)
    game = B.Game(build, prof, label)
    game.wait_socket()
    game.ctl("wait-ready", "240", timeout=245)
    game.ctl("time", "1000")
    return game, prof, g


def finish(game, prof, label):
    game.quit()
    (OUT / "logs").mkdir(exist_ok=True)
    for f in ("logs/latest.log", "console.log"):
        if (prof / f).exists():
            (OUT / "logs" / f"{label}-{Path(f).name}").write_bytes((prof / f).read_bytes())
    B.trash(prof)


def compat(build, pack):
    label = f"compat-{B.NAMES[build]}-pack{pack}"
    was = B.get_mute(); B.mute(True)
    game, prof, g = boot(build, label, opts(pack))
    try:
        game.settle()
        px, py, pz = -527.5, 95, 57.5
        for i, mob in enumerate(["salmon", "cow", "warm_cow", "cold_cow", "guardian", "elder_guardian"]):
            game.ctl("command", f"summon minecraft:{mob} {px - 6 + 2 * i} {py} {pz + 5} {{NoAI:1b,NoGravity:1b,PersistenceRequired:1b,Silent:1b}}")
        y = py - 3
        game.ctl("command", f"setblock {px} {y} {pz + 8} minecraft:iron_chain")
        game.ctl("command", f"setblock {px + 2} {y} {pz + 8} minecraft:lantern[hanging=true]")
        game.ctl("command", f"setblock {px + 4} {y} {pz + 8} minecraft:soul_lantern[hanging=true]")
        game.ctl("look", "0", "5")
        game.ctl("wait", "100")
        game.ctl("screenshot", str(OUT / f"{label}.png"))
        game.ctl("wait", "60")
    finally:
        finish(game, prof, label)
        B.mute(was)
    print("done", label, g)


def mods():
    label = "mods-DAILY"
    was = B.get_mute(); B.mute(True)
    game, prof, g = boot("D", label, opts("yes"))
    shots = OUT / "modshots"; shots.mkdir(exist_ok=True)
    res = {"errors": []}

    def step(*a, **k):
        try:
            return game.ctl(*a, **k)
        except Exception as e:
            res["errors"].append(f"{a[:3]}: {str(e)[:160]}")

    def shot(name):
        step("screenshot", str(shots / f"{name}.png")); step("wait", "5")

    try:
        game.settle()
        step("command", "fill -532 93 52 -523 93 64 minecraft:stone")
        step("command", "tp @s -527.5 94 57.5")
        step("command", "gamemode survival")
        step("look", "0", "10")
        step("command", "effect give @s minecraft:hunger 30 40")
        step("command", "item replace entity @s armor.head with minecraft:diamond_helmet")
        step("command", "item replace entity @s armor.chest with minecraft:iron_chestplate")
        step("command", "effect give @s minecraft:speed 300 1")
        step("command", "item replace entity @s weapon.mainhand with minecraft:diamond_sword")
        step("wait", "200")
        game.front()
        sc = shots / "screen-front.png"
        subprocess.run(["screencapture", "-x", str(sc)])
        subprocess.run(["sips", "-Z", "1000", str(sc)], capture_output=True)
        res["locked_cgs"] = B.sh(["ioreg", "-n", "Root", "-d1"]).stdout.count("CGSSessionScreenIsLocked")
        shot("01-base-hud")
        step("key", "c", "down"); step("wait", "30")
        shot("02-zoom-c"); step("key", "c", "up"); step("wait", "20")
        step("time", "18000"); step("wait", "20")
        shot("03-night-no-fullbright")
        step("key", "j", "tap"); step("wait", "20")
        shot("04-night-fullbright-j")
        step("key", "j", "tap"); step("time", "1000"); step("wait", "20")
        step("command", "setblock -527 94 61 minecraft:diamond_block")
        step("command", "tp @s -527.5 94 57.5")
        step("look-at-block", "-527", "94", "61")
        step("wait", "40")
        shot("05-jade-block")
        res["looking_at"] = step("looking-at")
        step("attack"); step("wait", "3")
        shot("06-after-swing")
        res["status"] = step("status")
    except Exception as e:
        res["error"] = str(e)
    finally:
        (OUT / "mods-run.json").write_text(json.dumps({"gate": g, "res": res}, indent=1, default=str)[:20000])
        finish(game, prof, label)
        B.mute(was)
    print("done mods", res.get("error"), res["errors"])


def apple():
    label = "apple-DAILY"
    was = B.get_mute(); B.mute(True)
    game, prof, g = boot("D", label, opts("yes"))
    shots = OUT / "modshots"; errs = []

    def step(*a, **k):
        try:
            return game.ctl(*a, **k)
        except Exception as e:
            errs.append(f"{a[:3]}: {str(e)[:160]}")

    try:
        game.settle()
        step("command", "fill -532 93 52 -523 93 64 minecraft:stone")
        step("command", "tp @s -527.5 94 57.5")
        step("command", "gamemode survival")
        step("look", "0", "10")
        step("command", "damage @s 8 minecraft:generic")
        step("command", "effect give @s minecraft:hunger 4 60")
        step("wait", "100")
        step("command", "item replace entity @s weapon.mainhand with minecraft:golden_carrot 3")
        step("wait", "30")
        step("screenshot", str(shots / "07-appleskin-golden-carrot.png"))
        step("command", "item replace entity @s weapon.mainhand with minecraft:diamond_sword")
        step("wait", "30")
        step("screenshot", str(shots / "08-appleskin-sword.png"))
    finally:
        (OUT / "apple-run.json").write_text(json.dumps({"errors": errs}))
        finish(game, prof, label)
        B.mute(was)
    print("done apple", errs)


if __name__ == "__main__":
    B.PROFILES.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == "compat":
        a = dict(zip(sys.argv[2::2], sys.argv[3::2]))
        compat(a["--build"], a["--pack"])
    elif sys.argv[1] == "apple":
        apple()
    else:
        mods()
