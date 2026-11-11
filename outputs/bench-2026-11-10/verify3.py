#!/usr/bin/env python3
"""Verify a new build in a disposable copy of the user's real game setup, and pre-warm its
Metal shader cache for all three dimensions (same binary path + same packs = same cache).

  verify3.py VERSION_DIR_NAME

Checks: fullbright (J) brightens a midnight MakeUp frame; third-person sprint shot for the
FA+Player lean; overworld -> nether -> end -> overworld switch timings; `memory` snapshot.
Outputs go to OUT/verify-<version>/.
"""
import json, re, struct, subprocess, sys, threading, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench  # noqa: E402

GAME = Path.home() / "Library/Application Support/horizon"


def stage_user(profile):
    profile.mkdir(parents=True, exist_ok=False)
    (profile / "saves").mkdir()
    subprocess.run(["/bin/cp", "-cR", str(bench.TEMPLATE), str(profile / "saves/Horizon-Test")], check=True)
    for d in ("resourcepacks", "config", "horizon-mods"):
        if (GAME / d).exists():
            subprocess.run(["/bin/cp", "-cR", str(GAME / d), str(profile / d)], check=True)
    (profile / "shaderpacks").mkdir()
    gfx = (GAME / "horizon-graphics.txt").read_text()
    shader = re.search(r"(?m)^pickedShaderPack:(.*)$", gfx).group(1).strip()
    for f in (shader, shader + ".txt"):
        if f and (GAME / "shaderpacks" / f).exists():
            subprocess.run(["/bin/cp", "-c", str(GAME / "shaderpacks" / f), str(profile / "shaderpacks")], check=True)
    (profile / "horizon-graphics.txt").write_text(gfx)
    for f in ("horizon-mods.txt", "horizon-player.txt"):
        if (GAME / f).exists():
            subprocess.run(["/bin/cp", "-c", str(GAME / f), str(profile / f)], check=True)
    opts = (GAME / "options.txt").read_text()
    opts = re.sub(r"(?m)^pauseOnLostFocus:.*$", "pauseOnLostFocus:false", opts)
    opts = re.sub(r"(?m)^inactivityFpsLimit:.*$", "inactivityFpsLimit:minimized", opts)
    (profile / "options.txt").write_text(opts)
    return shader


def luma(png):
    """Mean luma 0-255 of a PNG, via sips -> 64px BMP (no PIL here)."""
    bmp = png.with_suffix(".bmp")
    subprocess.run(["sips", "-Z", "64", "-s", "format", "bmp", str(png), "--out", str(bmp)],
                   capture_output=True, check=True)
    b = bmp.read_bytes()
    off, w, h, bpp = struct.unpack_from("<I", b, 10)[0], *struct.unpack_from("<iiHH", b, 18)[:2], struct.unpack_from("<H", b, 28)[0]
    step, row = bpp // 8, ((w * bpp + 31) // 32) * 4
    tot = n = 0
    for y in range(abs(h)):
        for x in range(w):
            p = off + y * row + x * step
            bl, g, r = b[p], b[p + 1], b[p + 2]
            tot += 0.2126 * r + 0.7152 * g + 0.0722 * bl; n += 1
    bmp.unlink()
    return round(tot / n, 1)


def main():
    ver = sys.argv[1]
    bench.BUILDS["T"] = ver; bench.NAMES["T"] = "TEST"
    out = bench.OUT / f"verify-{ver}"; out.mkdir(parents=True, exist_ok=True)
    rec = {"version": ver, "gate": bench.gate()}
    profile = bench.PROFILES / f"verify-{int(time.time())}"
    rec["shader"] = stage_user(profile)
    was = bench.get_mute(); bench.mute(True)
    g = bench.Game("T", profile, "verify")
    t0 = time.time()
    try:
        g.wait_socket(); g.ctl("wait-ready", "240", timeout=245)
        rec["startup_s"] = round(time.time() - t0, 1)
        rec["settle_s"] = g.settle()
        g.front()
        # fullbright under the shader pack
        g.ctl("command", "weather clear"); g.ctl("command", "time set 18000"); g.ctl("look", "0", "15")
        time.sleep(4)
        a, b = out / "night-fb-off.png", out / "night-fb-on.png"
        g.ctl("screenshot", str(a)); time.sleep(1)
        g.ctl("key", "j", "tap"); time.sleep(4)
        g.ctl("screenshot", str(b)); time.sleep(1)
        rec["fullbright"] = {"off_luma": luma(a), "on_luma": luma(b)}
        g.ctl("key", "j", "tap")
        # third-person sprint (lean check)
        g.ctl("command", "time set 1000"); g.ctl("command", "gamemode survival")
        g.ctl("key", "f5", "tap"); time.sleep(1)
        h = threading.Thread(target=lambda: g.ctl("hold", "w", "4", timeout=10));
        g.ctl("key", "ctrl", "down"); h.start(); time.sleep(2.0)
        g.ctl("screenshot", str(out / "sprint-3rd-person-1.png")); time.sleep(0.8)
        g.ctl("screenshot", str(out / "sprint-3rd-person-2.png"))
        h.join(); g.ctl("key", "ctrl", "up"); g.ctl("key", "f5", "tap"); g.ctl("key", "f5", "tap")
        g.ctl("command", "gamemode creative")
        # dimension pre-warm + timings
        dims = []
        for dim, pos in (("the_nether", "0 80 0"), ("the_end", "100 60 0"), ("overworld", "-527.5 95 57.5"),
                         ("the_nether", "0 80 0"), ("overworld", "-527.5 95 57.5")):
            t = time.time()
            g.ctl("command", f"execute in minecraft:{dim} run tp @s {pos}")
            g.ctl("wait-ready", "240", timeout=245)
            dims.append({"dim": dim, "ready_s": round(time.time() - t, 2)})
            time.sleep(3)
        rec["dimensions"] = dims
        rec["memory"] = g.ctl("memory", timeout=30)
        rec["ok"] = True
    except Exception as e:
        rec["error"] = str(e)
    finally:
        rec["peak_rss_MB"] = round(g.rss_peak / 1024, 1)
        g.quit(); bench.mute(was)
        rec["exit_code"] = g.p.returncode
    for f in ("console.log", "logs/latest.log"):
        if (profile / f).exists():
            (out / Path(f).name).write_bytes((profile / f).read_bytes())
    (out / "verify.json").write_text(json.dumps(rec, indent=2) + "\n")
    bench.trash(profile)
    print(json.dumps({k: rec.get(k) for k in ("ok", "error", "startup_s", "fullbright", "dimensions", "peak_rss_MB", "exit_code")}))


if __name__ == "__main__":
    main()
