#!/usr/bin/env python3
"""u7a bench: DAILY vs STOCK vs R11 on the M1 Air. Reuses the flow of tools/horizon-offline-test.py
(disposable profile, 52-pack stack from the v3 migration, native options candidate, horizon-ctl bench/fly)
but takes builds straight from ~/Library/Application Support/horizon-launcher/versions and a
pre-generated seed-0 world cloned per run (the old tests/base-smoke fixture no longer exists).

  bench.py genworld            build the template world (R11, seed 0, corridor generated)
  bench.py run --scenarios packs makeup --order D,S,R,R,S,D ...   run a block
"""
import argparse, csv, json, os, re, subprocess, sys, threading, time
from pathlib import Path

HOME = Path.home()
VERS = HOME / "Library/Application Support/horizon-launcher/versions"
HZ = HOME / "Developer/Horizon"
MIG = HZ / "outputs/horizon-converter/2026-11-04-Tanush-f42-v3"
SHADER = HZ / "outputs/horizon-runtime/game/shaderpacks/MakeUp-UltraFast-9.6.zip"
OUT = HZ / "outputs/bench-2026-11-10"
SCRATCH = Path("/private/tmp/claude-503/-Users-tanushmalhotra--claude-spares-spare-eGaSaI/8d128168-f675-40ad-b495-8887043fa141/scratchpad")
PROFILES = SCRATCH / "prof"
TEMPLATE = SCRATCH / "template/Horizon-Test"
BUILDS = {"D": "native-fdc87ae-m1-daily1-341aea300aca", "S": "nightly-2026-11-08-fdc87ae", "R": "native-f42-m1-r11-ef12b7f4368d", "N": "native-fdc87ae-m1-daily2-e2ee606a0b00", "T3": "native-fdc87ae-m1-daily3-4b6a81c9bdf9", "F4": "native-fdc87ae-m1-daily4-48183177b078", "F5": "native-fdc87ae-m1-daily5-6d28a2f92dc9", "F6": "native-fdc87ae-m1-daily6-7603f3a77f14"}
NAMES = {"D": "DAILY", "S": "STOCK", "R": "R11", "N": "DAILY2", "T3": "DAILY3", "F4": "DAILY4", "F5": "DAILY5", "F6": "DAILY6"}
FLY = ["-527.5", "95", "57.5", "-399.5", "95", "57.5"]
COOLDOWN = 45


def sh(cmd, t=15):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=t)


def idle_s():
    out = sh(["ioreg", "-c", "IOHIDSystem"]).stdout
    m = re.search(r"HIDIdleTime\D*(\d+)", out)
    return int(m.group(1)) // 10**9 if m else -1


def swap_used_m():
    return float(sh(["sysctl", "vm.swapusage"]).stdout.split("used = ")[1].split("M")[0])


class UserActive(Exception):
    pass


def gate(max_wait=900):
    """Idle>=120, no game, AC, thermal 0. Wait for transient failures; raise UserActive if idle<60."""
    t0 = time.time()
    while True:
        probs = []
        i = idle_s()
        if i < 60:
            raise UserActive(f"idle {i}s")
        if i < 120:
            probs.append(f"idle {i}s<120")
        if sh(["pgrep", "-x", "horizon-client"]).returncode == 0:
            probs.append("horizon-client running")
        if sh(["pgrep", "-f", "PineconeMC"]).returncode == 0:
            probs.append("java game running")
        if "AC Power" not in sh(["pmset", "-g", "batt"]).stdout.splitlines()[0]:
            probs.append("not AC")
        th = sh(["notifyutil", "-g", "com.apple.system.thermalpressurelevel"]).stdout.strip().split()[-1]
        if th != "0":
            probs.append(f"thermal {th}")
        if "CGSSessionScreenIsLocked" in sh(["ioreg", "-n", "Root", "-d1"]).stdout and \
                re.search(r"CGSSessionScreenIsLocked\D*(Yes|1)", sh(["ioreg", "-n", "Root", "-d1"]).stdout):
            probs.append("screen locked")
        if not probs:
            return {"idle_s": i, "thermal": th, "waited_s": round(time.time() - t0), "swap_M": swap_used_m()}
        if time.time() - t0 > max_wait:
            raise RuntimeError("gate timeout: " + "; ".join(probs))
        time.sleep(15)


def mute(state):
    sh(["osascript", "-e", f"set volume output muted {'true' if state else 'false'}"])


def get_mute():
    return sh(["osascript", "-e", "output muted of (get volume settings)"]).stdout.strip() == "true"


CUR_ENV = {}  # extra game env for the current run (variant env.*)
VARIANTS = {}  # name -> {"gfx": {k: v}, "opt": {k: v}, "pack": {k: v}}; order token BUILD@NAME


def parse_variant(s):
    """NAME:gfx.resolutionScale=85,pack.SHARPENING=0.7,opt.weatherRadius=5"""
    name, _, body = s.partition(":")
    v = {"gfx": {}, "opt": {}, "pack": {}, "env": {}}
    for kv in filter(None, body.split(",")):
        k, _, val = kv.partition("=")
        kind, _, key = k.partition(".")
        v[kind][key] = val
    VARIANTS[name] = v


def override(path, kv):
    """Set key:value / key=value lines in a settings file, appending missing keys."""
    sep = "=" if path.suffix == ".txt" and path.name.endswith(".zip.txt") else ":"
    lines = path.read_text().splitlines() if path.exists() else []
    done = set()
    for i, l in enumerate(lines):
        k = l.split(sep, 1)[0]
        if k in kv:
            lines[i] = f"{k}{sep}{kv[k]}"; done.add(k)
    lines += [f"{k}{sep}{v}" for k, v in kv.items() if k not in done]
    path.write_text("\n".join(lines) + "\n")


def stage(profile, build, scenario, world_from, variant=None):
    profile.mkdir(parents=True, exist_ok=False)
    (profile / "saves").mkdir()
    subprocess.run(["/bin/cp", "-cR", str(world_from), str(profile / "saves/Horizon-Test")], check=True)
    manifest = json.loads((MIG / "manifest.json").read_text())
    selection = list(manifest["resourcepack_selection"])
    (profile / "resourcepacks").mkdir()
    for s in selection:
        if s != "vanilla":
            subprocess.run(["/bin/cp", "-c", str(MIG / "resourcepacks" / s.removeprefix("file/")), str(profile / "resourcepacks")], check=True)
    cand = json.loads((MIG / "native-settings-candidate.json").read_text())
    opts = dict(l.split(":", 1) for l in cand["candidate_text"].splitlines() if ":" in l)
    opts.update(maxFps="260", enableVsync="false", simulationDistance="8", pauseOnLostFocus="false",
                inactivityFpsLimit="minimized", tutorialStep="none", resourcePacks=json.dumps(selection))
    (profile / "options.txt").write_text("".join(f"{k}:{v}\n" for k, v in opts.items()))
    shader = ""
    if scenario == "makeup":
        shader = SHADER.name
        (profile / "shaderpacks").mkdir()
        subprocess.run(["/bin/cp", "-c", str(SHADER), str(profile / "shaderpacks")], check=True)
        side = SHADER.with_name(SHADER.name + ".txt")
        if side.exists():
            subprocess.run(["/bin/cp", "-c", str(side), str(profile / "shaderpacks")], check=True)
    (profile / "horizon-graphics.txt").write_text(
        f"pickedShaderPack:{shader}\nresolutionScale:100\nworkers:0\nframePacing:efficient\nupscaling:native\ntaa:false\nhdr:false\nbatteryMode:false\n")
    v = VARIANTS.get(variant) if variant else None
    if v:
        override(profile / "horizon-graphics.txt", v["gfx"]) if v["gfx"] else None
        override(profile / "options.txt", v["opt"]) if v["opt"] else None
        if v["pack"]:
            assert shader, "pack.* override needs the makeup scenario"
            override(profile / "shaderpacks" / (shader + ".txt"), v["pack"])
    return selection


class Game:
    def __init__(self, build, profile, label):
        self.rel = VERS / BUILDS[build]
        self.profile = profile
        self.sock = f"/private/tmp/horizon-{label}.sock"
        self.rss_peak = 0
        self._stop = False
        cmd = [str(self.rel / "horizon-client"), "--resources", str(self.rel / ".local/horizon-client/26.3"),
               "--game-dir", str(profile), "--home", str(profile), "--world", "Horizon-Test", "--creative",
               "--render-distance", "12", "--width", "1280", "--height", "720", "--name", "HorizonTest",
               "--control", "--control-socket", self.sock, "--smoke-report", str(profile / "smoke.json")]
        env = os.environ.copy()
        env["HORIZON_HOME"] = str(profile)
        env.pop("HORIZON_SHADER_PACK", None)
        env.update(CUR_ENV)
        self.console = (profile / "console.log").open("w")
        self.p = subprocess.Popen(cmd, env=env, stdout=self.console, stderr=subprocess.STDOUT, cwd=profile)
        self.env = env
        self.th = threading.Thread(target=self._rss, daemon=True)
        self.th.start()

    def _rss(self):
        while not self._stop and self.p.poll() is None:
            r = sh(["ps", "-p", str(self.p.pid), "-o", "rss="]).stdout.strip()
            if r.isdigit():
                self.rss_peak = max(self.rss_peak, int(r))
            time.sleep(1)

    def ctl(self, *a, timeout=30):
        r = subprocess.run([str(self.rel / "horizon-ctl"), "--socket", self.sock, "--timeout", str(timeout), *map(str, a)],
                           env=self.env, capture_output=True, text=True, timeout=timeout + 5)
        try:
            v = json.loads(r.stdout)
        except ValueError:
            raise RuntimeError(f"ctl {a[0]} failed: {r.stdout[-300:]} {r.stderr[-300:]}")
        if r.returncode or "error" in v:
            raise RuntimeError(f"ctl {a[0]}: {str(v)[:300]}")
        return v

    def wait_socket(self, t=150):
        end = time.time() + t
        while not Path(self.sock).exists():
            if self.p.poll() is not None or time.time() > end:
                raise RuntimeError("client exited / socket never appeared")
            time.sleep(0.25)

    def settle(self, limit=240):
        t0, prev, stable = time.time(), None, 0
        while time.time() - t0 < limit:
            s = self.ctl("status")
            act = [s["streaming"][k] for k in ["queued", "generating", "decorating", "lighting", "finishing", "meshing"]]
            fp = (s["chunks"], s["renderer"]["resident_sections"])
            quiet = s["chunks"] >= 637 and s["pending_chunks"] == 0 and s["pending_uploads"] == 0 and s["dirty_light"] == 0 and not any(act)
            stable = stable + 1 if quiet and fp == prev else (1 if quiet else 0)
            if stable >= 5:
                return round(time.time() - t0, 1)
            prev = fp
            time.sleep(1)
        raise RuntimeError("terrain did not settle")

    def front(self):
        sh(["osascript", "-e", f'tell application "System Events" to set frontmost of (first process whose unix id is {self.p.pid}) to true'])
        time.sleep(1)

    def quit(self):
        try:
            if self.p.poll() is None:
                try:
                    self.ctl("quit", timeout=15)
                except Exception:
                    self.p.terminate()
                try:
                    self.p.wait(timeout=40)
                except subprocess.TimeoutExpired:
                    self.p.kill()
                    self.p.wait()
        finally:
            self._stop = True
            self.console.close()


def trash(path):
    """Remove a disposable run profile. Only scratch profiles are removed outright (the Trash
    never frees disk space; the disk filled on 2026-11-11)."""
    path = Path(path).resolve()
    if PROFILES.resolve() in path.parents:
        subprocess.run(["rm", "-rf", str(path)])
    else:
        dest = HOME / ".Trash" / f"{path.name}-{int(time.time())}"
        subprocess.run(["mv", str(path), str(dest)])


def genworld():
    gate()
    prof = PROFILES / "genworld"
    prof.mkdir(parents=True, exist_ok=False)
    (prof / "saves").mkdir()
    (prof / "options.txt").write_text("renderDistance:12\nsimulationDistance:8\nmaxFps:260\nenableVsync:false\npauseOnLostFocus:false\ninactivityFpsLimit:minimized\ntutorialStep:none\n")
    (prof / "horizon-graphics.txt").write_text("pickedShaderPack:\nresolutionScale:100\nworkers:0\n")
    g = Game("R", prof, "genworld")
    was = get_mute(); mute(True)
    try:
        g.wait_socket(); print("ready", g.ctl("wait-ready", "240", timeout=245).get("ok", True), flush=True)
        g.ctl("time", "1000"); g.ctl("look", "0", "15")
        st = g.ctl("status"); print("pos", st["player"]["position"], flush=True)
        g.settle()
        for a, b in ((FLY[:3], FLY[3:]), (FLY[3:], FLY[:3])):
            g.ctl("fly", *a, *b, "75", "10", timeout=120)
            g.settle()
            print("leg done", flush=True)
        g.ctl("tp", "-527.5", "95", "57.5")
        g.settle()
        g.ctl("save", timeout=60)
        time.sleep(3)
    finally:
        g.quit()
        mute(was)
    TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["mv", str(prof / "saves/Horizon-Test"), str(TEMPLATE)], check=True)
    print("template", TEMPLATE, sh(["du", "-sh", str(TEMPLATE)]).stdout.strip(), flush=True)


def run_once(idx, scen, b, tag):
    b, _, var = b.partition("@")
    label = f"{tag}-{idx:02d}-{scen}-{NAMES[b]}" + (f"-{var}" if var else "")
    g_info = gate()
    rec = {"index": idx, "tag": tag, "scenario": scen, "build": NAMES[b] + (f"@{var}" if var else ""), "version": BUILDS[b], "label": label,
           "variant": VARIANTS.get(var),
           "gate": g_info, "valid": False}
    profile = PROFILES / label
    stage(profile, b, scen, TEMPLATE, var)
    CUR_ENV.clear(); CUR_ENV.update((VARIANTS.get(var) or {}).get("env", {}))
    swap0 = swap_used_m()
    t0 = time.time()
    g = Game(b, profile, label)
    try:
        g.wait_socket()
        g.ctl("wait-ready", "240", timeout=245)
        rec["startup_s"] = round(time.time() - t0, 1)
        g.ctl("time", "1000"); g.ctl("look", "0", "15")
        g.ctl("gpu-passes", "on")
        rec["settle_s"] = g.settle()
        g.front()
        g.ctl("bench", 15, timeout=30)  # warmup
        g.ctl("wait-ready", "120", timeout=125)
        g.ctl("time", "1000")
        g.front()
        st = g.ctl("bench", 15, timeout=30)
        rec["static"] = st
        if st.get("seconds", 0) < 14:
            raise RuntimeError(f"static window presented only {st.get('seconds')}s")
        rec["swap_delta_M"] = round(swap_used_m() - swap0, 1)
        if var:  # settings variant: keep the static view for a visual comparison (after timing)
            (OUT / "shots").mkdir(exist_ok=True)
            g.ctl("screenshot", str(OUT / "shots" / f"{label}.png")); time.sleep(1)
        g.front()
        fl = g.ctl("fly", *FLY, "16", "10", timeout=45)
        fl.pop("frame_ms", None)
        rec["flight"] = fl
        if fl.get("seconds", 0) < 10:
            raise RuntimeError(f"flight presented only {fl.get('seconds')}s")
        rec["swap_delta_end_M"] = round(swap_used_m() - swap0, 1)
        rec["valid"] = True
    except UserActive:
        raise
    except Exception as e:
        rec["error"] = str(e)
    finally:
        rec["peak_rss_MB"] = round(g.rss_peak / 1024, 1)
        g.quit()
        rec["exit_code"] = g.p.returncode
    # artifacts
    rd = OUT / "runs"; rd.mkdir(parents=True, exist_ok=True)
    (rd / f"{label}.json").write_text(json.dumps(rec, indent=2) + "\n")
    for f in ("console.log", "logs/latest.log"):
        src = profile / f
        if src.exists():
            (OUT / "logs").mkdir(exist_ok=True)
            (OUT / "logs" / f"{label}-{Path(f).name}").write_bytes(src.read_bytes())
    trash(profile)
    return rec


def line(rec):
    s, f = rec.get("static", {}), rec.get("flight", {})
    return (f"{rec['index']:02d} {rec['scenario']:6s} {rec['build']:6s} valid={rec['valid']} "
            f"static {s.get('avg_fps', 0):.1f}/{s.get('low_1pct_fps', 0):.1f} flight {f.get('avg_fps', 0):.1f}/{f.get('low_1pct_fps', 0):.1f} "
            f"rss={rec.get('peak_rss_MB')} swapd={rec.get('swap_delta_M')} err={rec.get('error')}")


def run(args):
    was = get_mute(); mute(True)
    idx = args.start
    try:
        for scen in args.scenarios:
            for ch in args.order.split(","):
                if idx > args.start or scen != args.scenarios[0]:
                    time.sleep(COOLDOWN)
                try:
                    rec = run_once(idx, scen, ch, args.tag)
                except UserActive as e:
                    print("USER ACTIVE, stopping:", e, flush=True)
                    return 3
                print(line(rec), flush=True)
                idx += 1
                if not rec["valid"] or rec["static"]["avg_fps"] < 15:
                    print("STOP: invalid or <15 FPS run; investigate", flush=True)
                    return 2
    finally:
        mute(was)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["genworld", "run"])
    ap.add_argument("--scenarios", nargs="+", default=["packs", "makeup"])
    ap.add_argument("--order", default="D,S,R,R,S,D")
    ap.add_argument("--tag", default="a")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--variant", action="append", default=[], help="NAME:gfx.k=v,opt.k=v,pack.k=v")
    a = ap.parse_args()
    for s in a.variant:
        parse_variant(s)
    PROFILES.mkdir(parents=True, exist_ok=True)
    sys.exit(genworld() or 0 if a.cmd == "genworld" else run(a))
