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
    parser.add_argument("--frame-pacing", choices=["efficient", "precise"], default="efficient")
    parser.add_argument("--offscreen", action="store_true", help="Relative renderer screening; not on-screen gameplay FPS")
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
    # Control bench/fly do not exempt scripted runs from the 60-second AFK cap.
    # Match the built-in benchmark's override; a minimized window still throttles.
    (profile / "options.txt").write_text(f'maxFps:{args.fps_cap}\nenableVsync:false\nsimulationDistance:8\npauseOnLostFocus:false\ninactivityFpsLimit:minimized\ntutorialStep:none\nresourcePacks:' + json.dumps(selection) + '\n')
    shader = SHADERS.get(args.case.removesuffix("-bare"))
    if shader:
        (profile / "shaderpacks").mkdir()
        source = (MIGRATION / "shader-source" / shader) if args.case.startswith("mellow") else ROOT / "instances/Tanush-26.3/minecraft/shaderpacks" / shader
        subprocess.run(["/bin/cp", "-c", str(source), str(profile / "shaderpacks" / shader)], check=True)
        sidecar = source.with_name(source.name + ".txt")
        if sidecar.exists():
            shutil.copyfile(sidecar, profile / "shaderpacks" / sidecar.name)
    (profile / "horizon-graphics.txt").write_text("pickedShaderPack:" + (shader or "") +
                                               f"\nresolutionScale:{args.resolution_scale}\nworkers:{args.workers}\nframePacing:{args.frame_pacing}\nupscaling:native\ntaa:false\nhdr:false\nbatteryMode:false\n")
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
    if args.offscreen:
        command.extend(["--offscreen", "--no-pause"])
    record = {"case": args.case, "command": command, "profile": str(profile), "shader_requested": shader,
              "pack_selection": selection, "runtime_revision": "c9d474dd9116e84c243f8992d75c11314df56f06",
              "complete": False, "visual_parity_verified": False, "seconds": args.seconds}
    record["visual_validation"] = "pending image review"
    record["performance_candidate_accepted"] = False
    record["compatibility_only"] = args.compatibility_only
    record["world_resolution_scale_percent"] = args.resolution_scale
    record["fps_cap"] = args.fps_cap
    record["workers_configured"] = args.workers
    record["frame_pacing"] = args.frame_pacing
    record["inactivity_fps_limit"] = "minimized"
    record["render_mode"] = "offscreen-screening" if args.offscreen else "onscreen"
    record["onscreen_fps_verified"] = False
    record["background_workload"] = "User approved normal Xcode/DeviceHub background load; see process snapshots for observed activity"
    output = profile / "result.json"

    def save():
        output.write_text(json.dumps(record, indent=2) + "\n")

    def system_snapshot():
        values = {}
        for key, arguments in {"process": ["/bin/ps", "-p", str(process.pid), "-o", "rss=,%cpu="],
                               "background_processes": ["/bin/ps", "-Aww", "-o", "pid=,%cpu=,rss=,comm="],
                               "vm_stat": ["/usr/bin/vm_stat"], "swap": ["/usr/sbin/sysctl", "vm.swapusage"],
                               "thermal": ["/usr/bin/pmset", "-g", "therm"]}.items():
            try:
                result = subprocess.run(arguments, capture_output=True, text=True, timeout=3 if key == "background_processes" else 10)
            except subprocess.TimeoutExpired:
                values[key] = {"exit_code": None, "error": "Optional system diagnostic timed out"}
                continue
            lines = result.stdout.strip()
            if key == "background_processes" and result.returncode == 0:
                lines = "\n".join(sorted(lines.splitlines(), key=lambda line: float(line.split()[1]), reverse=True)[:15])
            values[key] = {"exit_code": result.returncode, "output": lines}
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

    def settle_terrain():
        # Radius12's native server subscription contains637 columns (lan/hub.rs).
        # wait-ready counts queued work, so it can miss running generation jobs.
        started = time.monotonic()
        previous = None
        stable = 0
        samples = []
        while time.monotonic() - started < 240:
            state = ctl("status")
            active = {key: state["streaming"].get(key, 0) for key in
                      ["queued", "generating", "decorating", "lighting", "finishing", "meshing"]}
            fingerprint = (state["chunks"], state["renderer"]["resident_sections"])
            quiet = (state["chunks"] >= 637 and state["pending_chunks"] == 0 and
                     state["pending_uploads"] == 0 and state["dirty_light"] == 0 and not any(active.values()))
            stable = stable + 1 if quiet and fingerprint == previous else 1 if quiet else 0
            samples.append({"elapsed": round(time.monotonic() - started, 2), "chunks": state["chunks"],
                            "resident_sections": fingerprint[1], "active": active, "quiet": quiet})
            if stable >= 5:
                return {"seconds": time.monotonic() - started, "required_columns": 637, "samples": samples}
            previous = fingerprint
            time.sleep(1)
        raise RuntimeError("Full radius12 terrain did not settle within240seconds")

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
            record["effective_inactivity_limit"] = ctl("options-get", "inactivityFpsLimit")
            record["effective_fps_cap"] = ctl("options-get", "maxFps")
            if record["effective_inactivity_limit"]["options"]["inactivityFpsLimit"]["value"] != "minimized" or record["effective_fps_cap"]["options"]["maxFps"]["value"] != args.fps_cap:
                raise RuntimeError("Effective frame limits do not match the requested benchmark settings")
            ctl("time", "1000")
            ctl("look", "0", "0")
            if not args.compatibility_only:
                ctl("gpu-passes", "on")
                record["terrain_ready"] = settle_terrain()
            # Finite warmup is outside the measured interval.
            if args.warmup and not args.compatibility_only:
                ctl("bench", args.warmup, timeout=args.warmup + 15)
            record["ready_after_warmup"] = ctl("wait-ready", "120", timeout=125)
            ctl("time", "1000")
            record["before"] = ctl("status")
            if not args.compatibility_only and record["before"]["chunks"] < 637:
                raise RuntimeError("Full radius12 terrain was lost before measurement")
            if args.offscreen and (record["before"]["renderer"]["size"] != [2560, 1440] or
                                   record["before"]["renderer"]["backend"] != "Metal" or
                                   record["before"]["renderer"]["gpu"] != "Apple M1"):
                raise RuntimeError("Offscreen screening must match the2560x1440 Metal Apple M1 target")
            record["active_resourcepacks"] = ctl("options-get", "resourcePacks")
            record["system_before"] = system_snapshot()
            record["screenshot"] = ctl("screenshot", str(profile / "scene.png"))
            if args.offscreen:
                header = (profile / "scene.png").read_bytes()[:24]
                if header[:8] != b"\x89PNG\r\n\x1a\n" or [int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")] != [2560, 1440]:
                    raise RuntimeError("Offscreen screenshot dimensions do not match the target")
            if not args.compatibility_only:
                record["measurement"] = ctl("bench", args.seconds, timeout=args.seconds + 15)
                if record["measurement"].get("seconds", 0) < args.seconds - 1:
                    raise RuntimeError("Renderer did not present frames across the full measured interval")
            record["system_after"] = system_snapshot()
            record["after"] = ctl("status")
            if not args.compatibility_only and record["after"]["chunks"] < 637:
                raise RuntimeError("Full radius12 terrain was lost during measurement")
            if args.flight and not args.compatibility_only:
                record["flight"] = ctl("fly", "-527.5", "95", "57.5", "-399.5", "95", "57.5", "16", "10", "raw", timeout=45)
                if record["flight"].get("frames", 0) == 0 or record["flight"].get("seconds", 0) < 15:
                    raise RuntimeError("Renderer did not present frames across the full flight interval")
                record["after_flight"] = ctl("status")
                settle_started = time.monotonic()
                record["flight_settled"] = ctl("wait-ready", "120", timeout=125)
                record["flight_settle_seconds"] = time.monotonic() - settle_started
                record["flight_terrain_ready"] = settle_terrain()
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
