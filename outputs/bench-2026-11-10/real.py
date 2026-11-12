#!/usr/bin/env python3
"""Real-profile bench: the player's own settings (options.txt, horizon-graphics.txt, shader sidecar,
every enabled resource pack) at the real window size (fullscreen 2880x1800), on the bench template world.
Measures FPS like bench.py plus the true memory cost on Apple silicon: phys_footprint (RSS hides
compressed and GPU memory), its peak, swap growth, and the game's memory census.

  real.py --order F7,F7@rd10,F7 --tag r1 [--variant rd10:opt.renderDistance=10] [--windowed]
"""
import argparse, json, re, subprocess, threading, time
from pathlib import Path
import bench as B

GAME = B.HOME / "Library/Application Support/horizon"


def footprint_mb(pid):
    out = B.sh(["footprint", "-p", str(pid)], t=30).stdout
    m = re.search(r"phys_footprint:\s+([\d.]+)\s*(KB|MB|GB)", out)
    pk = re.search(r"phys_footprint_peak:\s+([\d.]+)\s*(KB|MB|GB)", out)
    f = lambda x: None if not x else float(x.group(1)) * {"KB": 1 / 1024, "MB": 1, "GB": 1024}[x.group(2)]
    return f(m), f(pk)


def real_stage(profile, build, scenario, world_from, variant=None):
    profile.mkdir(parents=True, exist_ok=False)
    (profile / "saves").mkdir()
    subprocess.run(["/bin/cp", "-cR", str(world_from), str(profile / "saves/Horizon-Test")], check=True)
    opts = dict(l.split(":", 1) for l in (GAME / "options.txt").read_text().splitlines() if ":" in l)
    sel = json.loads(opts["resourcePacks"])
    (profile / "resourcepacks").mkdir()
    for s in sel:
        if s != "vanilla":
            subprocess.run(["/bin/cp", "-cR", str(GAME / "resourcepacks" / s.removeprefix("file/")), str(profile / "resourcepacks")], check=True)
    opts.update(maxFps=opts.get("maxFps", "60"), pauseOnLostFocus="false", inactivityFpsLimit="minimized", tutorialStep="none")
    if ARGS.uncapped:
        opts["maxFps"] = "260"
    if ARGS.windowed:
        opts["fullscreen"] = "false"
    (profile / "options.txt").write_text("".join(f"{k}:{v}\n" for k, v in opts.items()))
    gfx = (GAME / "horizon-graphics.txt").read_text()
    (profile / "horizon-graphics.txt").write_text(gfx)
    shader = re.search(r"^pickedShaderPack:(.*)$", gfx, re.M).group(1).strip()
    if scenario == "packs":
        B.override(profile / "horizon-graphics.txt", {"pickedShaderPack": ""})
        shader = ""
    if shader:
        (profile / "shaderpacks").mkdir()
        for f in (shader, shader + ".txt"):
            if (GAME / "shaderpacks" / f).exists():
                subprocess.run(["/bin/cp", "-c", str(GAME / "shaderpacks" / f), str(profile / "shaderpacks")], check=True)
    v = B.VARIANTS.get(variant) if variant else None
    if v:
        if v["gfx"]: B.override(profile / "horizon-graphics.txt", v["gfx"])
        if v["opt"]: B.override(profile / "options.txt", v["opt"])
        if v["pack"]:
            assert shader, "pack.* needs a shader"
            B.override(profile / "shaderpacks" / (shader + ".txt"), v["pack"])
    return sel


class RealGame(B.Game):
    def __init__(self, build, profile, label):
        self.rel = B.VERS / B.BUILDS[build]
        self.profile = profile
        self.sock = f"/private/tmp/horizon-{label}.sock"
        self.rss_peak = 0
        self.fp = []  # (t, phys_footprint MB)
        self._stop = False
        rd = dict(l.split(":", 1) for l in (profile / "options.txt").read_text().splitlines() if ":" in l).get("renderDistance", "12")
        cmd = [str(self.rel / "horizon-client"), "--resources", str(self.rel / ".local/horizon-client/26.3"),
               "--game-dir", str(profile), "--home", str(profile), "--world", "Horizon-Test", "--creative",
               "--render-distance", rd, "--name", "HorizonTest",
               "--control", "--control-socket", self.sock, "--smoke-report", str(profile / "smoke.json")]
        if ARGS.windowed:
            cmd += ["--width", "1280", "--height", "720"]
        env = B.os.environ.copy()
        env["HORIZON_HOME"] = str(profile)
        env.pop("HORIZON_SHADER_PACK", None)
        env.update(B.CUR_ENV)
        self.console = (profile / "console.log").open("w")
        self.p = subprocess.Popen(cmd, env=env, stdout=self.console, stderr=subprocess.STDOUT, cwd=profile)
        self.env = env
        self.t0 = time.time()
        self.th = threading.Thread(target=self._rss, daemon=True)
        self.th.start()

    def _rss(self):
        n = 0
        while not self._stop and self.p.poll() is None:
            r = B.sh(["ps", "-p", str(self.p.pid), "-o", "rss="]).stdout.strip()
            if r.isdigit():
                self.rss_peak = max(self.rss_peak, int(r))
            if n % 5 == 0:
                cur, _ = footprint_mb(self.p.pid)
                if cur:
                    self.fp.append((round(time.time() - self.t0, 1), cur))
            n += 1
            time.sleep(1)


def run_once(idx, scen, b, tag):
    b, _, var = b.partition("@")
    label = f"{tag}-{idx:02d}-{scen}-{B.NAMES[b]}" + (f"-{var}" if var else "")
    rec = {"index": idx, "tag": tag, "scenario": scen, "build": B.NAMES[b] + (f"@{var}" if var else ""),
           "version": B.BUILDS[b], "label": label, "variant": B.VARIANTS.get(var), "gate": B.gate(), "valid": False,
           "windowed": ARGS.windowed}
    profile = B.PROFILES / label
    real_stage(profile, b, scen, B.TEMPLATE, var)
    B.CUR_ENV.clear(); B.CUR_ENV.update((B.VARIANTS.get(var) or {}).get("env", {}))
    swap0 = B.swap_used_m()
    t0 = time.time()
    g = RealGame(b, profile, label)
    try:
        g.wait_socket()
        g.ctl("wait-ready", "240", timeout=245)
        rec["startup_s"] = round(time.time() - t0, 1)
        g.ctl("time", "1000"); g.ctl("look", "0", "15")
        rec["settle_s"] = g.settle()
        g.front()
        g.ctl("bench", 15, timeout=30)  # warmup
        g.ctl("wait-ready", "120", timeout=125)
        g.ctl("time", "1000")
        g.front()
        st = g.ctl("bench", 15, timeout=30)
        st.pop("frame_ms", None)
        rec["static"] = st
        if st.get("seconds", 0) < 14:
            raise RuntimeError(f"static window presented only {st.get('seconds')}s")
        if var:
            (B.OUT / "shots").mkdir(exist_ok=True)
            g.ctl("screenshot", str(B.OUT / "shots" / f"{label}.png")); time.sleep(1)
        g.front()
        fl = g.ctl("fly", *B.FLY, "16", "10", timeout=45)
        fl.pop("frame_ms", None)
        rec["flight"] = fl
        if fl.get("seconds", 0) < 10:
            raise RuntimeError(f"flight presented only {fl.get('seconds')}s")
        g.settle()
        cur, peak = footprint_mb(g.p.pid)
        rec["footprint_end_MB"], rec["footprint_peak_MB"] = cur, peak
        try:
            m = g.ctl("memory", timeout=30)
            rec["memory"] = {k: m.get(k) for k in ("process", "renderer", "client_columns", "render_distance")}
        except Exception as e:
            rec["memory_err"] = str(e)
        rec["swap_delta_end_M"] = round(B.swap_used_m() - swap0, 1)
        rec["valid"] = True
    except B.UserActive:
        raise
    except Exception as e:
        rec["error"] = str(e)
    finally:
        rec["peak_rss_MB"] = round(g.rss_peak / 1024, 1)
        rec["footprint_series"] = g.fp
        g.quit()
        rec["exit_code"] = g.p.returncode
    rd = B.OUT / "runs-real"; rd.mkdir(parents=True, exist_ok=True)
    (rd / f"{label}.json").write_text(json.dumps(rec, indent=2) + "\n")
    lg = profile / "logs/latest.log"
    if lg.exists():
        errs = [l for l in lg.read_text(errors="replace").splitlines() if "/ERROR]" in l or "panic" in l]
        rec["log_errors"] = len(errs)
        (rd / f"{label}.json").write_text(json.dumps(rec | {"log_error_lines": errs[:20]}, indent=2) + "\n")
    B.trash(profile)
    return rec


def line(r):
    s, f = r.get("static", {}), r.get("flight", {})
    return (f"{r['index']:02d} {r['scenario']:6s} {r['build']:14s} valid={r['valid']} "
            f"static {s.get('avg_fps', 0):.1f}/{s.get('low_1pct_fps', 0):.1f} p99 {s.get('p99_ms', 0):.0f} "
            f"flight {f.get('avg_fps', 0):.1f}/{f.get('low_1pct_fps', 0):.1f} p99 {f.get('p99_ms', 0):.0f} "
            f"fp={r.get('footprint_end_MB')}/{r.get('footprint_peak_MB')} rss={r.get('peak_rss_MB')} "
            f"swapd={r.get('swap_delta_end_M')} logerr={r.get('log_errors')} err={r.get('error')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", nargs="+", default=["makeup"])
    ap.add_argument("--order", required=True)
    ap.add_argument("--tag", default="r")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--variant", action="append", default=[])
    ap.add_argument("--windowed", action="store_true")
    ap.add_argument("--uncapped", action="store_true", help="maxFps 260 instead of the player's cap")
    ARGS = ap.parse_args()
    for s in ARGS.variant:
        B.parse_variant(s)
    B.PROFILES.mkdir(parents=True, exist_ok=True)
    was = B.get_mute(); B.mute(True)
    idx = ARGS.start
    try:
        for scen in ARGS.scenarios:
            for ch in ARGS.order.split(","):
                if idx > ARGS.start:
                    time.sleep(B.COOLDOWN)
                try:
                    r = run_once(idx, scen, ch, ARGS.tag)
                except B.UserActive as e:
                    print("USER ACTIVE, stopping:", e, flush=True); raise SystemExit(3)
                print(line(r), flush=True)
                idx += 1
    finally:
        B.mute(was)
