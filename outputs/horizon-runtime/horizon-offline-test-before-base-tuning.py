#!/usr/bin/env python3
"""Run one bounded local Horizon measurement in a fresh disposable profile."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "outputs/horizon-runtime"
RELEASE = RUNTIME / "launcher-data/versions/nightly-2026-11-01-c9d474d"
MIGRATION = ROOT / "outputs/horizon-converter/2026-11-02-Tanush-v2"
SHADERS = {"mellow": "Mellow v3.4.1a.zip", "complementary": "ComplementaryReimagined_r5.9.3.zip",
           "makeup": "MakeUp-UltraFast-9.6.zip", "miniature": "miniature-shader-2.19.zip",
           "ilikvanilla": "I Like Vanilla v1.5.0b.zip", "superduper": "superDuperVanilla.zip",
           "sildurs": "Sildur's Vibrant Shaders v2.02 Lite.zip", "bsl": "BSL_v10.1.8.zip",
           "bliss": "Bliss_v2.1.2_(Chocapic13_Shaders_edit).zip", "unbound": "ComplementaryUnbound_r5.9.3.zip"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["base", "packs", *SHADERS, *(k + "-bare" for k in SHADERS)], required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=30)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--compatibility-only", action="store_true")
    parser.add_argument("--packs-first", type=int)
    parser.add_argument("--diagnose-startup", action="store_true")
    parser.add_argument("--resolution-scale", type=int, choices=[50, 75, 100], default=100)
    parser.add_argument("--fps-cap", type=int, choices=[60, 120, 260], default=260)
    parser.add_argument("--workers", type=int, choices=range(0, 8), default=0)
    parser.add_argument("--flight", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]{1,60}", args.label) or not 5 <= args.seconds <= 120 or not 0 <= args.warmup <= 60:
        parser.error("Invalid label or measurement interval")
    if not os.environ.get("HORIZON_TEST_QUEUE"):
        parser.error("Run inside the shared device-testing turn")
    profile = RUNTIME / "tests" / args.label
    profile.mkdir(mode=0o700, exist_ok=False)
    (profile / "saves").mkdir()
    subprocess.run(["/bin/cp", "-cR", str(RUNTIME / "tests/base-smoke/saves/Horizon-Test"), str(profile / "saves/Horizon-Test")], check=True)
    selection = ["vanilla"]
    manifest = json.loads((MIGRATION / "manifest.json").read_text())
    if args.case != "base" and not args.case.endswith("-bare"):
        selection = manifest["resourcepack_selection"]
        if args.packs_first is not None:
            if not 1 <= args.packs_first <= 52:
                parser.error("Pack subset must contain 1..52 file packs")
            selection = selection[:args.packs_first + 1]
        (profile / "resourcepacks").mkdir()
        for selected in selection:
            if selected == "vanilla":
                continue
            pack = MIGRATION / "resourcepacks" / selected.removeprefix("file/")
            if pack.is_symlink() or not pack.is_file():
                raise ValueError("Only validated staged ZIP packs are expected")
            subprocess.run(["/bin/cp", "-c", str(pack), str(profile / "resourcepacks" / pack.name)], check=True)
    (profile / "options.txt").write_text(f'maxFps:{args.fps_cap}\nenableVsync:false\nsimulationDistance:8\npauseOnLostFocus:false\ntutorialStep:none\nresourcePacks:' + json.dumps(selection) + '\n')
    shader = SHADERS.get(args.case.removesuffix("-bare"))
    if shader:
        (profile / "shaderpacks").mkdir()
        source = (MIGRATION / "shader-source" / shader) if args.case.startswith("mellow") else ROOT / "instances/Tanush-26.3/minecraft/shaderpacks" / shader
        subprocess.run(["/bin/cp", "-c", str(source), str(profile / "shaderpacks" / shader)], check=True)
        sidecar = source.with_name(source.name + ".txt")
        if sidecar.exists():
            shutil.copyfile(sidecar, profile / "shaderpacks" / sidecar.name)
    (profile / "horizon-graphics.txt").write_text("pickedShaderPack:" + (shader or "") +
                                               f"\nresolutionScale:{args.resolution_scale}\nworkers:{args.workers}\nupscaling:native\ntaa:false\n")
    env = os.environ.copy()
    env.update(json.loads((RUNTIME / "installation.json").read_text())["environment"])
    env["HORIZON_HOME"] = str(profile)
    env.pop("HORIZON_SHADER_PACK", None)
    socket = f"/private/tmp/horizon-{args.label}.sock"
    command = [str(RELEASE / "horizon-client"), "--resources", str(RELEASE / ".local/horizon-client/26.3"),
               "--game-dir", str(profile), "--home", str(profile), "--world", "Horizon-Test", "--creative",
               "--render-distance", "12", "--width", str(args.width), "--height", str(args.height),
               "--name", "HorizonTest", "--control", "--control-socket", socket,
               "--smoke-report", str(profile / "smoke.json")]
    record = {"case": args.case, "command": command, "profile": str(profile), "shader_requested": shader,
              "pack_selection": selection, "runtime_revision": "c9d474dd9116e84c243f8992d75c11314df56f06",
              "complete": False, "visual_parity_verified": False, "seconds": args.seconds}
    record["compatibility_only"] = args.compatibility_only
    record["world_resolution_scale_percent"] = args.resolution_scale
    record["fps_cap"] = args.fps_cap
    record["workers_configured"] = args.workers
    record["background_workload"] = "Xcode/DeviceHub active; user approved testing under normal background load"
    output = profile / "result.json"

    def save():
        output.write_text(json.dumps(record, indent=2) + "\n")

    def system_snapshot():
        values = {}
        for key, arguments in {"process": ["/bin/ps", "-p", str(process.pid), "-o", "rss=,%cpu="],
                               "vm_stat": ["/usr/bin/vm_stat"], "swap": ["/usr/sbin/sysctl", "vm.swapusage"],
                               "thermal": ["/usr/bin/pmset", "-g", "therm"]}.items():
            result = subprocess.run(arguments, capture_output=True, text=True, timeout=10)
            values[key] = {"exit_code": result.returncode, "output": result.stdout.strip()}
        return values

    def ctl(*arguments, timeout=30):
        result = subprocess.run([str(RELEASE / "horizon-ctl"), "--socket", socket, "--timeout", str(timeout), *map(str, arguments)],
                                env=env, capture_output=True, text=True, timeout=timeout + 5)
        try:
            value = json.loads(result.stdout)
        except ValueError:
            raise RuntimeError(f"Control failed: {result.stdout[-500:]} {result.stderr[-500:]}")
        if result.returncode or "error" in value:
            raise RuntimeError(str(value))
        return value

    with (profile / "console.log").open("w") as console:
        process = subprocess.Popen(command, env=env, stdout=console, stderr=subprocess.STDOUT, cwd=profile)
        record["pid"] = process.pid
        save()
        try:
            deadline = time.monotonic() + 120
            diagnostic_at = time.monotonic() + 15
            diagnosed = False
            while not Path(socket).exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Client exited or control socket did not become ready")
                if args.diagnose_startup and not diagnosed and time.monotonic() > diagnostic_at:
                    for name, command in {"sample": ["/usr/bin/sample", str(process.pid), "1", "1", "-file", str(profile / "startup-sample.txt")],
                                          "files": ["/usr/sbin/lsof", "-nP", "-p", str(process.pid)],
                                          "process": ["/bin/ps", "-p", str(process.pid), "-o", "pid=,etime=,%cpu=,rss=,vsz="]}.items():
                        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
                        (profile / f"diagnostic-{name}.txt").write_text(result.stdout + result.stderr)
                    diagnosed = True
                time.sleep(0.25)
            record["ready"] = ctl("wait-ready", "240", timeout=245)
            print(json.dumps({"event": "ready", "pid": process.pid, "profile": str(profile)}), flush=True)
            ctl("time", "1000")
            ctl("look", "0", "0")
            if not args.compatibility_only:
                ctl("gpu-passes", "on")
            # Finite warmup is outside the measured interval.
            if args.warmup and not args.compatibility_only:
                ctl("bench", args.warmup, timeout=args.warmup + 15)
            record["before"] = ctl("status")
            record["active_resourcepacks"] = ctl("options-get", "resourcePacks")
            record["system_before"] = system_snapshot()
            record["screenshot"] = ctl("screenshot", str(profile / "scene.png"))
            if not args.compatibility_only:
                record["measurement"] = ctl("bench", args.seconds, timeout=args.seconds + 15)
            record["system_after"] = system_snapshot()
            record["after"] = ctl("status")
            if args.flight and not args.compatibility_only:
                record["flight"] = ctl("fly", "-527.5", "95", "57.5", "-399.5", "95", "57.5", "16", "10", "raw", timeout=45)
                record["after_flight"] = ctl("status")
                record["flight_settled"] = ctl("wait-ready", "120", timeout=125)
                record["flight_screenshot"] = ctl("screenshot", str(profile / "after-flight.png"))
            record["complete"] = True
        except Exception as exc:
            record["error"] = str(exc)
        finally:
            if process.poll() is None:
                try:
                    ctl("quit", timeout=15)
                except Exception:
                    process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    while process.poll() is None:
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            print(json.dumps({"event": "retaining-queue-until-owned-client-exits", "pid": process.pid}), flush=True)
            record["exit_code"] = process.returncode
            record["shader_diagnostics"] = [line for line in (profile / "console.log").read_text(errors="replace").splitlines()
                                            if "shader" in line.lower()][-300:]
            record["shader_activation"] = "unverified" if shader else "not-requested"
            save()
    print(json.dumps({"result": str(output), "complete": record["complete"], "error": record.get("error"), "exit_code": record["exit_code"]}), flush=True)
    return 0 if record["complete"] and record["exit_code"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
