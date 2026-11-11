#!/usr/bin/env python3
"""Within-launch live A/B for Horizon: ONE client process, arms toggled through the control socket.

Design: docs/horizon-converter/research/R13-fast-bench.md. Blocks run in ABBA order (A B B A, repeated
--cycles times). Each block applies its arm's control commands, waits for terrain, discards a settle
period, then measures one deterministic flight (default) or a static window. The unit of analysis is the
ABBA group: d = mean(B) - mean(A) inside the group, which cancels linear drift. Output: per-arm mean,
paired diff and a t-based 95% CI over groups.

  python3 -I run-live-ab.py --dry-run                         # validate only, launches nothing
  python3 -I run-live-ab.py --preset cull --cycles 3          # run (inside the device-testing turn)
  python3 -I run-live-ab.py --preset cull --aa                # A/A: B arm = A arm, expect diff ~ 0
  python3 -I run-live-ab.py --a "render-distance 12" --b "render-distance 8"   # custom; ';' joins commands

Needs the framework python for --scene flight window checks only if Quartz is wanted; none is required.
Reuses from tools/horizon-offline-test.py: ROOT, RUNTIME, RUNTIME_REVISIONS, SHADERS (that file has no
reusable launch function, only main(), so profile staging/launch/ctl are mirrored from its lines 120-300).
"""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics as st
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load_harness():
    spec = importlib.util.spec_from_file_location("horizon_offline_test", ROOT / "tools/horizon-offline-test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # module level only defines constants; main() is guarded
    return module


HARNESS = load_harness()
RUNTIME = HARNESS.RUNTIME
RUNTIME_ID = "nightly-2026-11-03-f42ef42"
BUILDS = {"control": "native-f42-m1-control-09391c2a8210", "r3": "native-f42-m1-r3-6b039bd4b49f"}
MIGRATIONS = {"v3": ROOT / "outputs/horizon-converter/2026-11-04-Tanush-f42-v3",
              "v4": ROOT / "outputs/horizon-converter/2026-11-05-Tanush-f42-v4"}
# Live-toggleable knobs (control.rs: section-cull 380, gpu-passes 390, section-sides 399, gpu-culling 409,
# render-distance 743; options.rs: options-set 59). Each arm = list of control commands.
PRESETS = {
    "cull": ("gpu-culling on", "gpu-culling off"),
    "section-cull": ("section-cull on", "section-cull off"),
    "section-sides": ("section-sides on", "section-sides off"),
    "rd": ("render-distance 12", "render-distance 8"),           # positive control: big, known direction
    "clouds": ("options-set renderClouds true", "options-set renderClouds false"),
}
LIVE_COMMANDS = {"gpu-culling": ("on", "off"), "section-cull": ("on", "off"), "section-sides": ("on", "off"),
                 "gpu-passes": ("on", "off"), "render-distance": None, "options-set": None}
FLY_THERE = ("-527.5", "95", "57.5", "-399.5", "95", "57.5")
FLY_BACK = ("-399.5", "95", "57.5", "-527.5", "95", "57.5")
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 20: 2.086, 30: 2.042}


# ---------------------------------------------------------------- pure helpers (self-tested in --dry-run)
def parse_arm(text):
    """'gpu-culling on; render-distance 8' -> [['gpu-culling','on'], ['render-distance','8']]; validates verbs."""
    cmds = [part.split() for part in text.split(";") if part.strip()]
    if not cmds:
        raise ValueError("empty arm")
    for cmd in cmds:
        verb, args = cmd[0], cmd[1:]
        if verb not in LIVE_COMMANDS:
            raise ValueError(f"'{verb}' is not a known live-toggle command (allowed: {sorted(LIVE_COMMANDS)})")
        allowed = LIVE_COMMANDS[verb]
        if verb == "options-set" and len(args) < 2:
            raise ValueError("options-set needs KEY VALUE")
        if verb == "render-distance" and not (len(args) == 1 and args[0].isdigit() and 2 <= int(args[0]) <= 128):
            raise ValueError("render-distance needs N in 2..128")
        if allowed and (len(args) != 1 or args[0] not in allowed):
            raise ValueError(f"{verb} needs one of {allowed}")
    return cmds


def block_order(cycles):
    return ["A", "B", "B", "A"] * cycles


def t_crit(df):
    if df < 1:
        return float("nan")
    keys = sorted(T975)
    return T975[next((k for k in keys if k >= df), keys[-1])] if df <= 30 else 1.96


def block_metric(block):
    """FPS for one block from raw frame_ms (1000/mean) else from the summary's avg_fps."""
    series = block.get("frame_ms") or []
    if series:
        return 1000.0 / (sum(series) / len(series))
    return block.get("avg_fps")


def analyze(blocks, metric=block_metric):
    """blocks: list of dicts with 'arm' ('A'/'B') in run order; groups of 4 (ABBA). Returns summary dict."""
    vals = [(b["arm"], metric(b)) for b in blocks]
    vals = [(a, v) for a, v in vals if v is not None]
    arm = {k: [v for a, v in vals if a == k] for k in "AB"}
    out = {"n_blocks": len(vals), "mean": {k: (st.fmean(v) if v else None) for k, v in arm.items()},
           "sd": {k: (st.stdev(v) if len(v) > 1 else None) for k, v in arm.items()}}
    deltas = []
    for i in range(0, len(blocks) - len(blocks) % 4, 4):
        grp = [(b["arm"], metric(b)) for b in blocks[i:i + 4]]
        if any(v is None for _, v in grp):
            continue
        a = [v for k, v in grp if k == "A"]
        b = [v for k, v in grp if k == "B"]
        if len(a) == 2 and len(b) == 2:
            deltas.append(st.fmean(b) - st.fmean(a))
    out["group_deltas"] = deltas
    n = len(deltas)
    if n:
        m = st.fmean(deltas)
        sd = st.stdev(deltas) if n > 1 else float("nan")
        half = t_crit(n - 1) * sd / math.sqrt(n) if n > 1 else float("nan")
        out["diff"] = {"mean_B_minus_A": m, "sd": sd, "n_groups": n, "ci95": [m - half, m + half],
                       "pct_of_A": (100 * m / out["mean"]["A"]) if out["mean"]["A"] else None}
    return out


def self_test():
    blocks = []
    for g, (a, b) in enumerate([(100, 90), (102, 91), (99, 88)]):
        for arm in "ABBA":
            blocks.append({"arm": arm, "avg_fps": a if arm == "A" else b})
    res = analyze(blocks)
    assert abs(res["diff"]["mean_B_minus_A"] + 10.6667) < 1e-3, res
    assert res["diff"]["ci95"][1] < 0, res
    assert parse_arm("gpu-culling on; render-distance 8") == [["gpu-culling", "on"], ["render-distance", "8"]]
    for bad in ("nope 1", "gpu-culling maybe", "render-distance 1", "options-set renderClouds"):
        try:
            parse_arm(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted bad arm {bad!r}")
    return True


def fmt_report(res, label_a, label_b, aa):
    lines = [f"{'A/A' if aa else 'A/B'}  A='{label_a}'  B='{label_b}'  blocks={res['n_blocks']}"]
    for k in "AB":
        m, s = res["mean"][k], res["sd"][k]
        lines.append(f"  arm {k}: mean {m:.2f} FPS  sd {s:.2f}" if m is not None and s is not None else f"  arm {k}: n/a")
    d = res.get("diff")
    if d:
        lines.append(f"  paired diff (B-A) over {d['n_groups']} ABBA groups: {d['mean_B_minus_A']:+.2f} FPS"
                     f" ({d['pct_of_A']:+.2f}% of A)  sd {d['sd']:.2f}  95% CI [{d['ci95'][0]:+.2f}, {d['ci95'][1]:+.2f}]")
        lines.append("  group deltas: " + ", ".join(f"{x:+.2f}" for x in res["group_deltas"]))
        if not any(map(math.isnan, d["ci95"])):
            lines.append("  verdict: " + ("CI excludes 0" if d["ci95"][0] > 0 or d["ci95"][1] < 0 else "CI includes 0")
                         + (" (A/A must include 0, else harness/order bias)" if aa else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------- inputs / staging / launch
def check_inputs(args):
    problems = []
    release = RUNTIME / "launcher-data/versions" / BUILDS[args.build]
    for name in ("horizon-client", "horizon-ctl", "native-mods.json", ".installed"):
        if not (release / name).exists():
            problems.append(f"missing {release / name}")
    mig = MIGRATIONS[args.migration]
    for name in ("manifest.json", "native-settings-candidate.json"):
        if not (mig / name).is_file():
            problems.append(f"missing {mig / name}")
    if not (RUNTIME / "tests/base-smoke/saves/Horizon-Test").is_dir():
        problems.append("missing tests/base-smoke/saves/Horizon-Test")
    if not (RUNTIME / "installation.json").is_file():
        problems.append("missing installation.json")
    if args.case not in ("base", "packs", *HARNESS.SHADERS):
        problems.append(f"unknown case {args.case}")
    shader = HARNESS.SHADERS.get(args.case)
    if shader:
        src = (mig / "shader-source" / shader) if args.case == "mellow" else \
            ROOT / "instances/Tanush-26.3/minecraft/shaderpacks" / shader
        if not src.is_file():
            src = RUNTIME / "game/shaderpacks" / shader
        if not src.is_file():
            problems.append(f"missing shader {shader}")
    return problems


def stage_profile(args, label, release):
    """Mirror of horizon-offline-test.py profile staging for base/packs/shader cases (lines 120-200)."""
    mig = MIGRATIONS[args.migration]
    profile = RUNTIME / "tests" / label
    profile.mkdir(mode=0o700, exist_ok=False)
    (profile / "saves").mkdir()
    subprocess.run(["/bin/cp", "-cR", str(RUNTIME / "tests/base-smoke/saves/Horizon-Test"),
                    str(profile / "saves/Horizon-Test")], check=True)
    selection = ["vanilla"]
    if args.case != "base":
        selection = list(json.loads((mig / "manifest.json").read_text())["resourcepack_selection"])
        (profile / "resourcepacks").mkdir()
        for sel in selection:
            if sel != "vanilla":
                pack = mig / "resourcepacks" / sel.removeprefix("file/")
                subprocess.run(["/bin/cp", "-c", str(pack), str(profile / "resourcepacks" / pack.name)], check=True)
    cand = json.loads((mig / "native-settings-candidate.json").read_text())
    opts = dict(line.split(":", 1) for line in cand["candidate_text"].splitlines() if ":" in line)
    opts.update(maxFps="260", enableVsync="false", simulationDistance="8", pauseOnLostFocus="false",
                inactivityFpsLimit="minimized", tutorialStep="none", resourcePacks=json.dumps(selection))
    (profile / "options.txt").write_text("".join(f"{k}:{v}\n" for k, v in opts.items()))
    shader = HARNESS.SHADERS.get(args.case)
    if shader:
        (profile / "shaderpacks").mkdir()
        src = (mig / "shader-source" / shader) if args.case == "mellow" else \
            ROOT / "instances/Tanush-26.3/minecraft/shaderpacks" / shader
        if not src.is_file():
            src = RUNTIME / "game/shaderpacks" / shader
        subprocess.run(["/bin/cp", "-c", str(src), str(profile / "shaderpacks" / shader)], check=True)
        side = src.with_name(src.name + ".txt")
        if side.exists():
            shutil.copyfile(side, profile / "shaderpacks" / side.name)
    (profile / "horizon-graphics.txt").write_text(
        "pickedShaderPack:" + (shader or "") + "\nresolutionScale:100\nworkers:0\nframePacing:efficient\n"
        "upscaling:native\ntaa:false\nhdr:false\nbatteryMode:false\n")
    return profile


class Client:
    def __init__(self, release, socket, env):
        self.release, self.socket, self.env = release, socket, env

    def ctl(self, *arguments, timeout=30):
        r = subprocess.run([str(self.release / "horizon-ctl"), "--socket", self.socket, "--timeout", str(timeout),
                            *map(str, arguments)], env=self.env, capture_output=True, text=True, timeout=timeout + 5)
        try:
            value = json.loads(r.stdout)
        except ValueError:
            raise RuntimeError(f"Control failed: {r.stdout[-400:]} {r.stderr[-400:]}")
        if r.returncode or "error" in value:
            raise RuntimeError(str(value))
        return value


def bring_front(pid):
    subprocess.run(["/usr/bin/osascript", "-e", 'tell application "System Events" to set frontmost of '
                    f'(first process whose unix id is {pid}) to true'], capture_output=True, text=True, timeout=10)
    time.sleep(1)


def measure(client, args, direction):
    """One measurement block; returns dict with frame_ms series. Flight = deterministic path (primary)."""
    if args.scene == "flight":
        path = FLY_THERE if direction == 0 else FLY_BACK
        r = client.ctl("fly", *path, args.seconds, "10", "raw", timeout=args.seconds + 30)
        return {"avg_fps": r.get("avg_fps"), "frames": r.get("frames"), "seconds": r.get("seconds"),
                "p99_ms": r.get("p99_ms"), "frame_ms": r.get("frame_ms"), "gpu_ms": r.get("gpu_ms")}
    client.ctl("stats", "reset")
    time.sleep(args.seconds)
    r = client.ctl("stats", "raw", "reset")
    return {k: r.get(k) for k in ("avg_fps", "frames", "seconds", "p99_ms", "frame_ms", "cpu_ms", "gpu_ms")}


def run(args, arms, label_a, label_b):
    release = RUNTIME / "launcher-data/versions" / BUILDS[args.build]
    label = f"liveab-{args.tag}-{time.strftime('%H%M%S')}"
    profile = stage_profile(args, label, release)
    socket = f"/private/tmp/horizon-{label}.sock"
    env = os.environ.copy()
    env.update(json.loads((RUNTIME / "installation.json").read_text())["environment"])
    env["HORIZON_HOME"] = str(profile)
    env.pop("HORIZON_SHADER_PACK", None)
    command = [str(release / "horizon-client"), "--resources", str(release / ".local/horizon-client/26.3"),
               "--game-dir", str(profile), "--home", str(profile), "--world", "Horizon-Test", "--creative",
               "--render-distance", "12", "--width", "1280", "--height", "720", "--name", "HorizonTest",
               "--control", "--control-socket", socket, "--smoke-report", str(profile / "smoke.json")]
    client = Client(release, socket, env)
    blocks, t0 = [], time.monotonic()
    with (profile / "console.log").open("w") as console:
        proc = subprocess.Popen(command, env=env, stdout=console, stderr=subprocess.STDOUT, cwd=profile)
        try:
            deadline = time.monotonic() + 120
            while not Path(socket).exists():
                if proc.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Client exited or control socket did not become ready")
                time.sleep(0.25)
            client.ctl("wait-ready", "240", timeout=245)
            client.ctl("time", "1000")
            client.ctl("look", "0", "0")
            client.ctl("gpu-passes", "on" if args.gpu_passes else "off")
            bring_front(proc.pid)
            client.ctl("bench", args.warmup, timeout=args.warmup + 15)       # warmup, discarded (auto-warm)
            client.ctl("wait-ready", "120", timeout=125)
            # one discarded priming flight each way so both directions have streamed their terrain
            for d in (0, 1):
                measure(client, argparse.Namespace(**{**vars(args), "scene": "flight"}), d)
            for i, which in enumerate(block_order(args.cycles)):
                for cmd in arms[which]:
                    client.ctl(*cmd)
                client.ctl("wait-ready", "60", timeout=65)
                time.sleep(args.settle)
                if args.scene == "flight":                                    # return-to-start is the settle flight
                    pass
                block = measure(client, args, i % 2)
                block.update(arm=which, idx=i, dir=i % 2, t=round(time.monotonic() - t0, 1))
                blocks.append(block)
                print(f"  blk {i:2d} {which} dir{i % 2} fps={block_metric(block)}", flush=True)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
    return blocks, profile


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--preset", choices=sorted(PRESETS), help="canned arm pair")
    p.add_argument("--a", help="arm A control commands, ';'-separated")
    p.add_argument("--b", help="arm B control commands, ';'-separated")
    p.add_argument("--aa", action="store_true", help="A/A: both arms use arm A's commands (re-applied each block)")
    p.add_argument("--cycles", type=int, default=3, help="ABBA groups (4 blocks each)")
    p.add_argument("--scene", choices=["flight", "static"], default="flight")
    p.add_argument("--seconds", type=int, default=12, help="flight duration or static window per block")
    p.add_argument("--settle", type=float, default=3.0, help="seconds to wait after applying an arm")
    p.add_argument("--warmup", type=int, default=15)
    p.add_argument("--gpu-passes", action="store_true", help="keep gpu-passes on for BOTH arms (costs a little)")
    p.add_argument("--build", choices=sorted(BUILDS), default="r3")
    p.add_argument("--migration", choices=sorted(MIGRATIONS), default="v4")
    p.add_argument("--case", default="makeup", help="harness case: base, packs or a shader key")
    p.add_argument("--tag", default="ab")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not args.preset and not args.a:
        args.preset = "cull"
    a_text, b_text = (PRESETS[args.preset] if args.preset else (args.a, args.b))
    problems = []
    if not a_text or (not b_text and not args.aa):
        problems.append("give --preset, or --a and --b (--b optional with --aa)")
        a_text = a_text or "gpu-culling on"
    try:
        arm_a = parse_arm(a_text)
        arm_b = arm_a if args.aa else parse_arm(b_text or a_text)
    except ValueError as error:
        problems.append(str(error))
        arm_a = arm_b = []
    if not 1 <= args.cycles <= 12 or not 5 <= args.seconds <= 60 or not 0 <= args.warmup <= 60:
        problems.append("cycles 1..12, seconds 5..60, warmup 0..60")
    problems += check_inputs(args)
    blocks_n = 4 * args.cycles
    est = 85 + args.warmup + 2 * (args.seconds + 3) + blocks_n * (args.seconds + args.settle + 4)

    if args.dry_run:
        try:
            self_test()
            print("self-test (stats + arm parser): OK")
        except AssertionError as error:
            problems.append(f"self-test failed: {error}")
        print(f"plan: build={BUILDS[args.build]} mig={args.migration} case={args.case} scene={args.scene}"
              f" order={''.join(block_order(args.cycles))}")
        print(f"  A={arm_a}\n  B={'(same as A, A/A)' if args.aa else arm_b}\n  ~{est:.0f}s wall, {blocks_n} blocks")
        print("input check:", "OK" if not problems else problems)
        return 0 if not problems else 2

    if problems:
        print("input problems:", problems)
        return 2
    if not os.environ.get("HORIZON_TEST_QUEUE"):
        print("Run inside the shared device-testing turn (HORIZON_TEST_QUEUE unset)")
        return 2
    # Same gates as the U9 runners: AC power, unlocked, no thermal throttle, no builds/Java MC, disk free.
    spec = importlib.util.spec_from_file_location("u9c_gates", HERE / "run-u9c-makeup-trim.py")
    gates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gates)
    ok, gate_left = gates.wait_gates(lambda msg: print(msg, flush=True))
    if not ok:
        print("gates never cleared:", gate_left)
        return 3
    blocks, profile = run(args, {"A": arm_a, "B": arm_b}, a_text, b_text)
    res = analyze(blocks)
    print(fmt_report(res, a_text, "A (A/A)" if args.aa else b_text, args.aa))
    out = RUNTIME / f"{profile.name}.json"
    out.write_text(json.dumps({"args": vars(args), "A": a_text, "B": b_text, "blocks": blocks, "result": res}, indent=1))
    print("saved", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
