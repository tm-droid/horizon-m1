#!/usr/bin/env python3
"""Run one bounded local Horizon measurement in a fresh disposable profile."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "outputs/horizon-runtime"
RUNTIME_REVISIONS = {"nightly-2026-11-01-c9d474d": "c9d474dd9116e84c243f8992d75c11314df56f06",
                     "nightly-2026-11-03-f42ef42": "f42ef42ef6ceccb3c6a20bea2481d87949a51c81",
                     "nightly-2026-11-05-66f3981": "66f3981f522b24c250b21523a70080965b940424"}
FIXTURE_RUNTIMES = {"nightly-2026-11-03-f42ef42", "nightly-2026-11-05-66f3981"}
MIGRATION = ROOT / "outputs/horizon-converter/2026-11-04-Tanush-f42-v3"
SHADERS = {"mellow": "Mellow v3.4.1a.zip", "complementary": "ComplementaryReimagined_r5.9.3.zip",
           "makeup": "MakeUp-UltraFast-9.6.zip", "miniature": "miniature-shader-2.19.zip",
           "ilikvanilla": "I Like Vanilla v1.5.0b.zip", "superduper": "superDuperVanilla.zip",
           "sildurs": "Sildur's Vibrant Shaders v2.02 Lite.zip", "bsl": "BSL_v10.1.8.zip",
           "bliss": "Bliss_v2.1.2_(Chocapic13_Shaders_edit).zip", "unbound": "ComplementaryUnbound_r5.9.3.zip",
           "bakedpotato": "BakedPotatoFinal.zip", "sildursdefault": "Sildur's Enhanced Default v1.20 Fancy.zip"}

FRESH_FROM = (4096, 95, 4096)
FRESH_TO = (4608, 95, 4096)
FRESH_SECONDS = 32
# Radius12 plus20 chunks of conservative generation/prefetch margin.
FRESH_MARGIN_CHUNKS = 32


def fresh_corridor_chunks(start=FRESH_FROM, end=FRESH_TO, margin=FRESH_MARGIN_CHUNKS):
    return [(x, z)
            for x in range(math.floor(min(start[0], end[0]) / 16) - margin,
                           math.floor(max(start[0], end[0]) / 16) + margin + 1)
            for z in range(math.floor(min(start[2], end[2]) / 16) - margin,
                           math.floor(max(start[2], end[2]) / 16) + margin + 1)]


def verify_fresh_corridor(world, chunks=None):
    """Read only: reject stored terrain in the cloned probe corridor before launch."""
    chunks = fresh_corridor_chunks() if chunks is None else chunks
    slots = {}
    for x, z in chunks:
        slots.setdefault((x // 32, z // 32), set()).add((x % 32) + 32 * (z % 32))
    checked = []
    for directory in (world / "region", world / "dimensions/minecraft/overworld/region"):
        if directory.is_symlink():
            raise ValueError("Fresh-flight region directory must not be a symlink")
        if directory.exists() and not directory.is_dir():
            raise ValueError("Malformed fresh-flight region directory")
        for (rx, rz), required in sorted(slots.items()):
            path = directory / f"r.{rx}.{rz}.mca"
            if path.is_symlink():
                raise ValueError(f"Fresh-flight region must not be a symlink: {path}")
            if not path.exists():
                checked.append({"path": str(path), "exists": False})
                continue
            size = path.stat().st_size
            with path.open("rb") as handle:
                header = handle.read(8192)
            if len(header) != 8192 or size % 4096:
                raise ValueError(f"Malformed region header/size: {path}")
            occupied = {0, 1}
            for slot in range(1024):
                entry = int.from_bytes(header[slot * 4:slot * 4 + 4], "big")
                if not entry:
                    continue
                offset, count = entry >> 8, entry & 255
                sectors = set(range(offset, offset + count))
                if not count or offset < 2 or offset + count > size // 4096 or occupied & sectors:
                    raise ValueError(f"Malformed region location table: {path}, slot{slot}")
                occupied.update(sectors)
                if slot in required:
                    raise ValueError(f"Fresh-flight corridor already contains terrain: {path}, slot{slot}")
            checked.append({"path": str(path), "exists": True,
                            "header_sha256": hashlib.sha256(header).hexdigest()})
        for x, z in chunks:
            external = directory / f"c.{x}.{z}.mcc"
            if external.exists() or external.is_symlink():
                raise ValueError(f"Fresh-flight corridor contains external chunk data: {external}")
    return {"chunks_checked": len(chunks), "margin_chunks": FRESH_MARGIN_CHUNKS,
            "from": list(FRESH_FROM), "to": list(FRESH_TO), "region_headers": checked,
            "stored_corridor_absent_before_launch": True}


def sampled_fresh_flight(ctl, phase, interval=0.5):
    """Fly on one control connection while independent connections read status.

    Control requests have independent reply channels; a deferred fly does not
    block Game::poll_control from answering status. Sampling itself adds load.
    """
    started = time.monotonic()
    phase["status_timeline"] = []

    def fly():
        phase["request_started_seconds"] = time.monotonic() - started
        return ctl("fly", *FRESH_FROM, *FRESH_TO, FRESH_SECONDS, 10, "raw", timeout=60)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fly)
        while not future.done():
            requested = time.monotonic()
            state = ctl("status", timeout=5)
            phase["status_timeline"].append({"requested_seconds": requested - started,
                                             "received_seconds": time.monotonic() - started,
                                             "status": state})
            time.sleep(max(0, interval - (time.monotonic() - requested)))
        phase["measurement"] = future.result()
    phase["wall_seconds"] = time.monotonic() - started


def fresh_flight_hopeless(measurement):
    return measurement.get("avg_fps", float("inf")) < 15


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["base", "packs", *SHADERS, *(k + "-bare" for k in SHADERS)], required=True)
    parser.add_argument("--runtime", choices=RUNTIME_REVISIONS, default="nightly-2026-11-01-c9d474d")
    parser.add_argument("--native-version", help="Installed native build whose recorded base and revision match --runtime")
    parser.add_argument("--label", required=True)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=30)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--compatibility-only", action="store_true")
    parser.add_argument("--packs-first", type=int)
    parser.add_argument("--pack-name", action="append", default=[], help="Selected file pack basename; original layer order is retained")
    parser.add_argument("--native-options-candidate", type=Path)
    parser.add_argument("--migration", type=Path, default=MIGRATION, help="Captured migration containing selected resource packs")
    parser.add_argument("--scene", choices=["base", "cow", "guardian", "lantern", "ores", "daily-compat", "daily-compat-mobs", "daily-compat-gui", "daily-compat-family", "daily-compat-world", "daily-compat-charge", "daily-compat-light", "daily-compat-sound", "daily-compat-parts", "daily-compat-bogged", "daily-compat-ghast", "daily-compat-build"], default="base")
    parser.add_argument("--beds-only", action="store_true", help="Use the four-facing bed model fixture in daily-compat-build")
    parser.add_argument("--dynamic-light-extended", action="store_true", help="Also check moved and picked-up torch states")
    parser.add_argument("--disable-extras-dynamic-lights", action="store_true", help="Keep Extras dynamic lights off in the cave fixture")
    parser.add_argument("--extra-pack", action="append", type=Path, default=[], help="Explicit isolated compatibility overlay, appended above captured packs")
    parser.add_argument("--zoom-smoke", action="store_true", help="Exercise native C-key/wheel/release controls and capture their views")
    parser.add_argument("--part-variants", action="store_true", help="Add a named golem to the per-part texture scene")
    parser.add_argument("--diagnose-startup", action="store_true")
    parser.add_argument("--resolution-scale", type=int, choices=[50, 75, 100], default=100)
    parser.add_argument("--fps-cap", type=int, choices=[60, 120, 260], default=260)
    parser.add_argument("--workers", type=int, choices=range(0, 8), default=0)
    parser.add_argument("--frame-pacing", choices=["efficient", "precise"], default="efficient")
    parser.add_argument("--upload-budget-kib", type=int,
                        help="Set the f42 terrain upload budget per frame (1–65536 KiB)")
    parser.add_argument("--disable-vanilla-clouds", action="store_true",
                        help="Disable f42 MakeUp's unused native cloud mesh while retaining shader clouds")
    parser.add_argument("--shader-options-file", type=Path,
                        help="Copy explicit shader options into this disposable f42 profile")
    parser.add_argument("--makeup-source", type=Path, help="Use an explicit MakeUp ZIP in the disposable profile")
    parser.add_argument("--offscreen", action="store_true", help="Relative renderer screening; not on-screen gameplay FPS")
    parser.add_argument("--flight", action="store_true")
    parser.add_argument("--fresh-flight", action="store_true",
                        help="Diagnostic MakeUp first-pass/revisit flight over an ungenerated cloned-world corridor")
    parser.add_argument("--capture-flight-end", action="store_true",
                        help="Capture immediately after timed flight instead of waiting for terrain to settle")
    parser.add_argument("--presentation-ab", action="store_true", help="Compare Immediate/Fifo/Fifo/Immediate in one warmed stationary f42 session")
    args = parser.parse_args()
    migration = args.migration.resolve()
    release = RUNTIME / "launcher-data/versions" / args.runtime
    native_build = None
    if args.native_version:
        if not re.fullmatch(r"native-[a-zA-Z0-9._-]{1,120}", args.native_version):
            parser.error("Invalid native version directory name")
        release = RUNTIME / "launcher-data/versions" / args.native_version
        native_build = json.loads((release / "native-mods.json").read_text())
        if (not (release / ".installed").is_file() or native_build.get("base") != args.runtime or
                native_build.get("horizon") != RUNTIME_REVISIONS[args.runtime] or native_build.get("target") != "client"):
            parser.error("Native build identity must match the requested client base and engine revision")
    if not re.fullmatch(r"[a-z0-9-]{1,60}", args.label) or not 5 <= args.seconds <= 120 or not 0 <= args.warmup <= 60:
        parser.error("Invalid label or measurement interval")
    if not os.environ.get("HORIZON_TEST_QUEUE"):
        parser.error("Run inside the shared device-testing turn")
    if args.fresh_flight and (args.flight or args.compatibility_only or args.offscreen or
                             args.runtime != "nightly-2026-11-03-f42ef42" or
                             args.case != "makeup" or args.resolution_scale != 100):
        parser.error("Fresh flight requires an on-screen, full-resolution, timed f42 MakeUp case without --flight")
    if args.upload_budget_kib is not None and (
        args.runtime != "nightly-2026-11-03-f42ef42" or not 1 <= args.upload_budget_kib <= 65536
    ):
        parser.error("Upload budget requires f42 and a value from 1 to 65536 KiB")
    if args.disable_vanilla_clouds and (
        args.runtime != "nightly-2026-11-03-f42ef42" or args.case != "makeup"
    ):
        parser.error("Native cloud suppression requires the f42 MakeUp case")
    if args.makeup_source is not None and (args.case != "makeup" or args.makeup_source.suffix.lower() != ".zip"
                                           or args.makeup_source.is_symlink() or not args.makeup_source.is_file()):
        parser.error("MakeUp source override requires a regular ZIP and the MakeUp case")
    if (args.dynamic_light_extended or args.disable_extras_dynamic_lights) and args.scene != "daily-compat-light":
        parser.error("Dynamic light fixture options require daily-compat-light")
    shader_options_bytes = None
    shader_options_hash = None
    if args.shader_options_file is not None:
        options_source = args.shader_options_file
        if (args.runtime not in FIXTURE_RUNTIMES or
                args.case.removesuffix("-bare") not in SHADERS):
            parser.error("Shader options override requires a supported shader runtime")
        if options_source.is_symlink() or not options_source.is_file() or options_source.suffix.lower() != ".txt":
            parser.error("Shader options must be a regular .txt file without a symlink")
        with options_source.open("rb") as handle:
            shader_options_bytes = handle.read(65537)
        if len(shader_options_bytes) > 65536:
            parser.error("Shader options must be at most 64 KiB")
        shader_options_hash = hashlib.sha256(shader_options_bytes).hexdigest()
    if args.capture_flight_end and (not args.flight or args.compatibility_only):
        parser.error("Flight endpoint capture requires a timed flight")
    if args.pack_name and (args.case == "base" or args.case.endswith("-bare") or args.packs_first is not None):
        parser.error("Named pack subsets require a pack case without --packs-first")
    if args.extra_pack and (args.case == "base" or args.case.endswith("-bare")):
        parser.error("Extra overlays require a pack case")
    if args.zoom_smoke and (not native_build or "zoom" not in {mod.get("id") for mod in native_build.get("mods", [])}):
        parser.error("Zoom smoke requires a recorded native build containing Zoom")
    if args.scene != "base" and args.runtime not in FIXTURE_RUNTIMES:
        parser.error("Custom fixtures require f42 or nightly 66f3981")
    if args.scene.startswith("daily-compat"):
        supported = ("makeup", "packs") if args.scene in ("daily-compat-light", "daily-compat-charge") else ("makeup",)
        if args.case not in supported or not args.compatibility_only:
            parser.error("Daily compatibility requires a supported compatibility-only case")
    if args.part_variants and args.scene != "daily-compat-parts":
        parser.error("Part variants require the per-part texture scene")
    if args.scene == "lantern" and (args.case != "packs" or not args.compatibility_only or not args.offscreen):
        parser.error("Lantern fixture requires the offscreen pack compatibility mode")
    if args.presentation_ab and (
        args.runtime != "nightly-2026-11-03-f42ef42" or args.native_version or args.case != "packs" or
        args.packs_first is not None or args.pack_name or args.extra_pack or args.fps_cap != 60 or
        args.resolution_scale != 100 or (args.width, args.height) != (1280, 720) or
        args.offscreen or args.flight or args.compatibility_only or not args.warmup
    ):
        parser.error("Presentation comparison requires official f42, the full pack case, native 1280x720 window, cap 60 and a stationary on-screen warmup")
    native_candidate = None
    option_values = {}
    if args.native_options_candidate:
        native_candidate = json.loads(args.native_options_candidate.read_text())
        if (native_candidate.get("runtime_revision") != RUNTIME_REVISIONS[args.runtime] or
                not isinstance(native_candidate.get("candidate_text"), str)):
            parser.error("Options candidate must contain audited text for the selected runtime")
        option_values.update(line.split(":", 1) for line in native_candidate["candidate_text"].splitlines() if ":" in line)
    profile = RUNTIME / "tests" / args.label
    profile.mkdir(mode=0o700, exist_ok=False)
    (profile / "saves").mkdir()
    subprocess.run(["/bin/cp", "-cR", str(RUNTIME / "tests/base-smoke/saves/Horizon-Test"), str(profile / "saves/Horizon-Test")], check=True)
    fresh_check = verify_fresh_corridor(profile / "saves/Horizon-Test") if args.fresh_flight else None
    selection = ["vanilla"]
    manifest_bytes = (migration / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if args.case != "base" and not args.case.endswith("-bare"):
        selection = list(manifest["resourcepack_selection"])
        if args.pack_name:
            requested = {"file/" + name for name in args.pack_name}
            if len(requested) != len(args.pack_name) or not requested <= set(selection):
                parser.error("Named pack subset must contain unique packs from the captured selection")
            selection = [name for name in selection if name == "vanilla" or name in requested]
        if args.packs_first is not None:
            pack_count = sum(name != "vanilla" for name in selection)
            if not 1 <= args.packs_first <= pack_count:
                parser.error(f"Pack subset must contain 1..{pack_count} file packs")
            selection = selection[:args.packs_first + 1]
        (profile / "resourcepacks").mkdir()
        for selected in selection:
            if selected == "vanilla":
                continue
            pack = migration / "resourcepacks" / selected.removeprefix("file/")
            if pack.is_symlink() or not pack.is_file():
                raise ValueError("Only validated staged ZIP packs are expected")
            subprocess.run(["/bin/cp", "-c", str(pack), str(profile / "resourcepacks" / pack.name)], check=True)
    extra_packs = []
    for pack in args.extra_pack:
        target = profile / "resourcepacks" / pack.name
        if pack.is_symlink() or not pack.is_file() or pack.suffix.lower() != ".zip" or target.exists():
            raise ValueError("Extra overlay must be a regular ZIP with a unique basename")
        source_hash = hashlib.sha256(pack.read_bytes()).hexdigest()
        subprocess.run(["/bin/cp", "-c", str(pack), str(target)], check=True)
        staged_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if staged_hash != source_hash or hashlib.sha256(pack.read_bytes()).hexdigest() != source_hash:
            raise ValueError("Extra overlay changed during staging")
        selection.append("file/" + pack.name)
        extra_packs.append({"source": str(pack.resolve()), "sha256": staged_hash})
    # Control bench/fly do not exempt scripted runs from the 60-second AFK cap.
    # Match the built-in benchmark's override; a minimized window still throttles.
    option_values.update(maxFps=str(args.fps_cap), enableVsync="false", simulationDistance="8", pauseOnLostFocus="false",
                         inactivityFpsLimit="minimized", tutorialStep="none", resourcePacks=json.dumps(selection))
    if args.disable_vanilla_clouds:
        option_values["renderClouds"] = "false"
    (profile / "options.txt").write_text("".join(f"{key}:{value}\n" for key, value in option_values.items()))
    if args.scene == "daily-compat-light":
        state = "false" if args.disable_extras_dynamic_lights else "true"
        (profile / "horizon-extras.txt").write_text(f"dynamicLights:{state}\n")
    shader = SHADERS.get(args.case.removesuffix("-bare"))
    staged_shader_hash = None
    if shader:
        (profile / "shaderpacks").mkdir()
        source = (migration / "shader-source" / shader) if args.case.startswith("mellow") else ROOT / "instances/Tanush-26.3/minecraft/shaderpacks" / shader
        if not source.is_file():  # packs added only to Horizon (not in the Java instance)
            source = ROOT / "outputs/horizon-runtime/game/shaderpacks" / shader
        source = args.makeup_source or source
        staged_shader = profile / "shaderpacks" / shader
        subprocess.run(["/bin/cp", "-c", str(source), str(staged_shader)], check=True)
        with staged_shader.open("rb") as handle:
            staged_shader_hash = hashlib.file_digest(handle, "sha256").hexdigest()
        sidecar = source.with_name(source.name + ".txt")
        effective_sidecar = staged_shader.with_name(staged_shader.name + ".txt")
        if shader_options_bytes is not None:
            effective_sidecar.write_bytes(shader_options_bytes)
            if args.shader_options_file.is_symlink() or not args.shader_options_file.is_file():
                raise ValueError("Shader options source changed during staging")
            with args.shader_options_file.open("rb") as handle:
                source_after = handle.read(65537)
            if (hashlib.sha256(effective_sidecar.read_bytes()).hexdigest() != shader_options_hash or
                    source_after != shader_options_bytes):
                raise ValueError("Shader options changed during staging")
        elif sidecar.exists():
            shutil.copyfile(sidecar, effective_sidecar)
        if args.disable_vanilla_clouds:
            if not effective_sidecar.exists():
                raise ValueError("Native cloud suppression requires the audited MakeUp sidecar")
            cloud_settings = dict(line.split("=", 1) for line in effective_sidecar.read_text().splitlines()
                                  if "=" in line and not line.startswith("#"))
            if cloud_settings.get("V_CLOUDS") != "2":
                raise ValueError("Native cloud suppression requires the audited V_CLOUDS=2 setting")
    (profile / "horizon-graphics.txt").write_text("pickedShaderPack:" + (shader or "") +
                                               f"\nresolutionScale:{args.resolution_scale}\nworkers:{args.workers}\nframePacing:{args.frame_pacing}\nupscaling:native\ntaa:false\nhdr:false\nbatteryMode:false\n" +
                                               (f"uploadBudgetKiB:{args.upload_budget_kib}\n" if args.upload_budget_kib is not None else ""))
    env = os.environ.copy()
    env.update(json.loads((RUNTIME / "installation.json").read_text())["environment"])
    env["HORIZON_HOME"] = str(profile)
    env.pop("HORIZON_SHADER_PACK", None)
    socket = f"/private/tmp/horizon-{args.label}.sock"
    command = [str(release / "horizon-client"), "--resources", str(release / ".local/horizon-client/26.3"),
               "--game-dir", str(profile), "--home", str(profile), "--world", "Horizon-Test", "--creative",
               "--render-distance", "12", "--width", str(args.width), "--height", str(args.height),
               "--name", "HorizonTest", "--control", "--control-socket", socket,
               "--smoke-report", str(profile / "smoke.json")]
    if args.offscreen:
        command.extend(["--offscreen", "--no-pause"])
    record = {"case": args.case, "command": command, "profile": str(profile), "shader_requested": shader,
              "shader_archive_sha256": staged_shader_hash,
              "migration": str(migration), "migration_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "pack_selection": selection, "runtime_revision": RUNTIME_REVISIONS[args.runtime],
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
    record["scene"] = args.scene
    if fresh_check is not None:
        record["fresh_flight"] = {"prelaunch": fresh_check, "phases": [],
                                  "diagnostic_only": True,
                                  "counter_limit": "generated_chunks counts received/loaded columns, not world-generation completions",
                                  "sample_interval_seconds": 0.5,
                                  "sampling_overhead": "Concurrent status requests add profiling load; not a speedup comparison",
                                  "shader_archive_sha256": hashlib.sha256((profile / "shaderpacks" / shader).read_bytes()).hexdigest(),
                                  "shader_options_sha256": hashlib.sha256(effective_sidecar.read_bytes()).hexdigest() if effective_sidecar.exists() else None}
    record["extra_packs"] = extra_packs
    if args.shader_options_file is not None:
        record["shader_options_override"] = {
            "source": str(args.shader_options_file.resolve()),
            "sha256": shader_options_hash,
            "staged": str(effective_sidecar),
        }
    if args.upload_budget_kib is not None or args.disable_vanilla_clouds:
        record["settings_experiment"] = {
            "upload_budget_kib_requested": args.upload_budget_kib,
            "disable_vanilla_clouds_requested": args.disable_vanilla_clouds,
            "graphics_readback_kind": "parsed profile file, separate from live options",
        }
    if native_build:
        record["native_build"] = native_build
        record["native_version"] = args.native_version
        record["native_executable_sha256"] = hashlib.sha256((release / "horizon-client").read_bytes()).hexdigest()
        record["performance_comparison_limit"] = "Native profile differs from the official release; no cross-profile mod-overhead claim"
    record["native_options_candidate"] = native_candidate
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

    def window_state():
        # Root cause evidence: macOS stops presenting an occluded/background window, so wall time passes
        # with no recorded frames. Record who is in front and what covers the Horizon window.
        try:
            import Quartz
            windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
            top = next((w for w in windows if w.get("kCGWindowLayer") == 0), {})
            front = {"name": top.get("kCGWindowOwnerName"), "pid": top.get("kCGWindowOwnerPID")}
            above = []
            for window in windows:
                if window.get("kCGWindowOwnerPID") == process.pid:
                    return {"front_app": front["name"], "front_pid": front["pid"], "horizon_is_front": front["pid"] == process.pid,
                            "horizon_bounds": dict(window.get("kCGWindowBounds", {})), "covering_windows": above[:8]}
                if window.get("kCGWindowLayer") == 0 and window.get("kCGWindowAlpha", 1) > 0:
                    above.append({"owner": window.get("kCGWindowOwnerName"), "bounds": dict(window.get("kCGWindowBounds", {}))})
            return {"front_app": front["name"], "horizon_on_screen": False, "covering_windows": above[:8]}
        except Exception as error:
            return {"error": repr(error)}

    def bring_front():
        try:
            result = subprocess.run(["/usr/bin/osascript", "-e", 'tell application "System Events" to set frontmost of '
                                     f'(first process whose unix id is {process.pid}) to true'],
                                    capture_output=True, text=True, timeout=10)
            time.sleep(1)
            return result.stderr.strip() or None
        except Exception as error:
            return repr(error)

    def ctl(*arguments, timeout=30):
        result = subprocess.run([str(release / "horizon-ctl"), "--socket", socket, "--timeout", str(timeout), *map(str, arguments)],
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
            active = {key: state["streaming"][key] for key in
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
        record["terrain_settle_failure"] = {"required_columns": 637, "samples": samples}
        raise RuntimeError("Full radius12 terrain did not settle within240seconds")

    def compare_presentation():
        def scene_signature(state):
            return (state["renderer"]["size"], state["renderer"]["backend"], state["renderer"]["gpu"],
                    state["display"], state["screen"], state["player"]["position"], state["yaw"], state["pitch"],
                    state["chunks"], state["input"]["counts"]["user"])

        baseline = record["before"]
        signature = scene_signature(baseline)
        if (signature[:3] != ([2560, 1440], "Metal", "Apple M1") or
                baseline["display"]["refresh_hz"] != 60 or baseline["screen"] != "playing"):
            raise RuntimeError("Presentation comparison requires the 2560x1440 Metal surface on the 60 Hz display")

        samples = []
        record["presentation_ab"] = {"scene": "stationary", "samples": samples}
        for vsync, mode in [(False, "Immediate"), (True, "Fifo"), (True, "Fifo"), (False, "Immediate")]:
            ctl("options-set", "enableVsync", str(vsync).lower())
            # Wait outside the timed interval so surface reconfiguration is excluded.
            time.sleep(4)
            ctl("time", "1000")
            sample = {"requested_mode": mode, "enable_vsync": vsync}
            samples.append(sample)
            for edge in ("before", "after"):
                state = ctl("status")
                options = ctl("options-get", "maxFps", "enableVsync", "inactivityFpsLimit", "resourcePacks")["options"]
                sample[edge] = {"status": state, "options": options}
                if (scene_signature(state) != signature or state["renderer"]["present_mode"] != mode or
                        options["maxFps"]["value"] != 60 or options["enableVsync"]["value"] is not vsync or
                        options["inactivityFpsLimit"]["value"] != "minimized" or
                        options["resourcePacks"]["value"] != selection):
                    raise RuntimeError(f"Presentation sample {len(samples)} failed the {edge} scene/settings check")
                if edge == "before":
                    measurement = ctl("bench", args.seconds, timeout=args.seconds + 15)
                    sample["measurement"] = measurement
                    if (measurement.get("seconds", 0) < args.seconds - 1 or not measurement.get("frames") or
                            "p99_ms" not in measurement or "low_1pct_fps" not in measurement):
                        raise RuntimeError(f"Presentation sample {len(samples)} did not return a full timed frame summary")

    with (profile / "console.log").open("w") as console:
        launched_at = time.monotonic()
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
            record["startup_to_ready_seconds"] = time.monotonic() - launched_at
            print(json.dumps({"event": "ready", "pid": process.pid, "profile": str(profile)}), flush=True)
            record["effective_inactivity_limit"] = ctl("options-get", "inactivityFpsLimit")
            record["effective_fps_cap"] = ctl("options-get", "maxFps")
            if record["effective_inactivity_limit"]["options"]["inactivityFpsLimit"]["value"] != "minimized" or record["effective_fps_cap"]["options"]["maxFps"]["value"] != args.fps_cap:
                raise RuntimeError("Effective frame limits do not match the requested benchmark settings")
            if native_candidate:
                record["effective_visual_options"] = ctl("options-get", *native_candidate["fields"])
                for key in ["fov", "cloudRange"]:
                    if key in native_candidate["fields"] and record["effective_visual_options"]["options"][key]["value"] != native_candidate["fields"][key]["typed_value"]:
                        raise RuntimeError(f"Effective {key} does not match the source-derived candidate")
            if args.upload_budget_kib is not None:
                graphics = dict(line.split(":", 1) for line in
                                (profile / "horizon-graphics.txt").read_text().splitlines() if ":" in line)
                record["settings_experiment"]["graphics_file_readback"] = graphics
                if graphics.get("uploadBudgetKiB") != str(args.upload_budget_kib):
                    raise RuntimeError("Profile upload budget does not match the requested experiment")
            if args.disable_vanilla_clouds:
                live_clouds = ctl("options-get", "renderClouds", "cloudRange")["options"]
                record["settings_experiment"]["live_cloud_options"] = live_clouds
                if live_clouds["renderClouds"]["value"] != "false":
                    raise RuntimeError("Native clouds were not disabled by the experiment")
                if "cloudRange" in option_values and live_clouds["cloudRange"]["value"] != int(option_values["cloudRange"]):
                    raise RuntimeError("Native cloud suppression changed the requested cloud range")
            ctl("time", "1000")
            ctl("look", "0", "0")
            if not args.compatibility_only:
                ctl("gpu-passes", "on")
                record["terrain_ready"] = settle_terrain()
                record["startup_to_full_scene_seconds"] = time.monotonic() - launched_at
            if args.scene == "daily-compat":
                from horizon_daily_compat import probe
                probe(ctl, profile, record)
            elif args.scene == "daily-compat-mobs":
                from horizon_daily_compat import probe_more_mobs
                probe_more_mobs(ctl, profile, record)
            elif args.scene == "daily-compat-family":
                from horizon_daily_compat import probe_mob_family
                probe_mob_family(ctl, profile, record)
            elif args.scene == "daily-compat-charge":
                from horizon_daily_compat import probe_charged_creeper
                probe_charged_creeper(ctl, profile, record)
            elif args.scene == "daily-compat-parts":
                from horizon_daily_compat import probe_part_textures
                probe_part_textures(ctl, profile, record, variants=args.part_variants)
            elif args.scene == "daily-compat-bogged":
                from horizon_daily_compat import probe_bogged_shearing, probe_skeleton_horse, probe_ghast_harness
                record["daily_compat"] = {}
                for name, fixture in (("bogged", probe_bogged_shearing), ("skeleton_horse", probe_skeleton_horse),
                                      ("ghast_harness", probe_ghast_harness)):
                    try:
                        fixture(ctl, profile, record)
                    except (RuntimeError, KeyError, StopIteration, ValueError) as error:
                        record["daily_compat"][name] = {"complete": False, "error": f"{type(error).__name__}: {error}"}
            elif args.scene == "daily-compat-ghast":
                from horizon_daily_compat import probe_ghast_harness
                record["daily_compat"] = {}
                probe_ghast_harness(ctl, profile, record, ropes=True)
            elif args.scene == "daily-compat-light":
                from horizon_daily_compat import probe_dynamic_light
                if args.dynamic_light_extended:
                    probe_dynamic_light(ctl, profile, record, extended=True)
                else:
                    probe_dynamic_light(ctl, profile, record)
            elif args.scene == "daily-compat-sound":
                from horizon_world_compat import probe_subtitles
                probe_subtitles(ctl, profile, record)
            elif args.scene == "daily-compat-build":
                from horizon_world_compat import probe_build_surfaces
                probe_build_surfaces(ctl, profile, record, beds_only=args.beds_only)
            elif args.scene == "daily-compat-world":
                from horizon_daily_compat import probe_armor_trim
                from horizon_world_compat import probe
                probe(ctl, profile, record)
                try:
                    probe_armor_trim(ctl, profile, record)
                except (RuntimeError, KeyError, StopIteration, ValueError) as error:
                    record["world_compat"]["armor_trim"]["error"] = f"{type(error).__name__}: {error}"
                    if ctl("screen")["screen"] in ("inventory", "station"):
                        ctl("key", "esc", "tap")
            elif args.scene == "daily-compat-gui":
                from horizon_gui_compat import probe
                probe(ctl, profile, record)
            elif args.scene == "lantern":
                fixture = [
                    (-530, 71, "iron_chain", "axis=y"),
                    (-529, 71, "lantern", "hanging=true"),
                    (-528, 71, "soul_lantern", "hanging=true"),
                    (-527, 71, "copper_lantern", "hanging=true"),
                    (-526, 70, "lantern", "hanging=false"),
                ]
                ctl("command", "fill -530 72 61 -526 72 61 minecraft:stone")
                ctl("command", "fill -530 69 61 -526 69 61 minecraft:stone")
                for x, y, name, state in fixture:
                    ctl("command", f"setblock {x} {y} 61 minecraft:{name}[{state}]")
                ctl("wait", "20")
                readback = []
                for x, y, name, state in fixture:
                    block = ctl("block", x, y, 61)
                    if not block["loaded"] or block["block"] != f"minecraft:{name}" or state not in block["state"]:
                        raise RuntimeError(f"Lantern fixture state mismatch: {block}")
                    readback.append(block)
                record["lantern_fixture"] = {"block_readback": readback, "terrain_ready": settle_terrain()}
            elif args.scene == "ores":
                # Dark sealed room (player at -527.5,69,57.5 faces +z); ore wall 2.5 blocks ahead at z=60.
                ctl("command", "fill -533 68 55 -522 73 60 minecraft:stone hollow")
                ore_rows = {
                    71: ["diamond_ore", "deepslate_diamond_ore", "redstone_ore[lit=true]", "deepslate_redstone_ore[lit=true]",
                         "emerald_ore", "deepslate_emerald_ore", "lapis_ore", "deepslate_lapis_ore"],
                    70: ["gold_ore", "deepslate_gold_ore", "iron_ore", "deepslate_iron_ore",
                         "copper_ore", "deepslate_copper_ore", "coal_ore", "deepslate_coal_ore"],
                    69: ["nether_quartz_ore", "nether_gold_ore", "ancient_debris", "glowstone",
                         "magma_block", "sea_lantern", "redstone_ore[lit=false]", "deepslate_redstone_ore[lit=false]"]}
                placed = []
                for y, names in ore_rows.items():
                    for i, spec in enumerate(names):
                        x = -531 + i
                        ctl("command", f"setblock {x} {y} 60 minecraft:{spec}")
                        placed.append((x, y, spec))
                ctl("wait", "40")
                readback = []
                for x, y, spec in placed:
                    name, _, state = spec.partition("[")
                    block = ctl("block", x, y, 60)
                    if not block["loaded"] or block["block"] != f"minecraft:{name}" or (state and state.rstrip("]") not in block["state"]):
                        raise RuntimeError(f"Ore fixture state mismatch: {block}")
                    readback.append(block)
                ctl("look", "0", "0")
                ctl("wait", "40")
                record["ore_fixture"] = {"rows": {str(y): n for y, n in ore_rows.items()}, "x_start": -531, "z": 60,
                                         "block_readback_count": len(readback), "verified": True,
                                         "terrain_ready": settle_terrain()}
            elif args.scene != "base":
                entity_type = args.scene
                before_entities = ctl("entities", "16", entity_type)["entities"]
                platform = "fill -530 68 59 -525 68 63 minecraft:grass_block" if entity_type == "cow" else "fill -530 68 59 -525 71 63 minecraft:water"
                no_gravity = "" if entity_type == "cow" else "NoGravity:1b,"
                record["fixture"] = {
                    "entity_type": entity_type,
                    "platform": ctl("command", platform),
                    "summon": ctl("command", f'summon minecraft:{entity_type} -527.5 69.05 60.5 {{UUID:[I;28211,0,0,1],NoAI:1b,{no_gravity}PersistenceRequired:1b,Silent:1b,Invulnerable:1b,Rotation:[180.0f,0.0f]}}'),
                    "settle_ticks": ctl("wait", "20")}
                entities = ctl("entities", "16", entity_type)["entities"]
                previous_ids = {entity["id"] for entity in before_entities}
                spawned = [entity for entity in entities if entity["id"] not in previous_ids and
                           abs(entity["pos"][0] + 527.5) < 0.1 and abs(entity["pos"][2] - 60.5) < 0.1]
                if len(spawned) != 1:
                    raise RuntimeError("Deterministic entity fixture was not observed unambiguously")
                record["fixture"][entity_type] = spawned[0]
                record["fixture"]["server_mobs"] = ctl("mobs", "16")
                record["fixture"]["no_ai_readback"] = ctl("command", "data get entity 00006e33-0000-0000-0000-000000000001 NoAI")
                readback = record["fixture"]["no_ai_readback"]
                if not readback.get("ok") or not any(isinstance(line, str) and re.search(r"has the following entity data:\s*1b\s*$", line)
                                                      for line in readback.get("chat", [])):
                    raise RuntimeError("Known fixture UUID/NoAI flag was not confirmed by entity-data readback")
                record["fixture"]["identity_and_no_ai_verified"] = True
                ctl("look", "0", "15")
                record["fixture_terrain_ready"] = settle_terrain()
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
            if record["active_resourcepacks"]["options"]["resourcePacks"]["value"] != selection:
                raise RuntimeError("Effective resource-pack selection differs from the requested ordered subset")
            record["system_before"] = system_snapshot()
            record["screenshot"] = ctl("screenshot", str(profile / "scene.png"))
            if args.offscreen:
                header = (profile / "scene.png").read_bytes()[:24]
                if header[:8] != b"\x89PNG\r\n\x1a\n" or [int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")] != [2560, 1440]:
                    raise RuntimeError("Offscreen screenshot dimensions do not match the target")
            if args.scene == "lantern":
                ctl("time", "13000")
                ctl("wait", "20")
                record["lantern_fixture"]["night"] = ctl("screenshot", str(profile / "night.png"))
            if args.presentation_ab:
                compare_presentation()
            elif not args.compatibility_only:
                record["front_error_bench"] = bring_front()
                record["window_before_bench"] = window_state()
                record["measurement"] = ctl("bench", args.seconds, timeout=args.seconds + 15)
                record["window_after_bench"] = window_state()
                if record["measurement"].get("seconds", 0) < args.seconds - 1:
                    raise RuntimeError("Renderer did not present frames across the full measured interval")
            record["system_after"] = system_snapshot()
            record["after"] = ctl("status")
            if not args.compatibility_only and record["after"]["chunks"] < 637:
                raise RuntimeError("Full radius12 terrain was lost during measurement")
            if args.scene in ("cow", "guardian"):
                record["fixture"]["after"] = ctl("entities", "16", entity_type)
                fixture_after = [entity for entity in record["fixture"]["after"]["entities"] if entity["id"] == record["fixture"][entity_type]["id"]]
                if len(fixture_after) != 1 or max(abs(a-b) for a, b in zip(fixture_after[0]["pos"], record["fixture"][entity_type]["pos"])) > 0.05:
                    raise RuntimeError("Entity fixture moved during the measured interval")
                record["idle_sequence"] = []
                for index in range(3):
                    if index:
                        ctl("wait", "20")
                    record["idle_sequence"].append(ctl("screenshot", str(profile / f"idle-{index}.png")))
            if args.flight and not args.compatibility_only:
                # Frame stats sum only presented frames, so wall time without presentation (occluded or
                # backgrounded window) shows up as seconds < 16. Keep the check; re-front the window,
                # retry once, and record every attempt (with window state) as data.
                record["flight_attempts"] = []
                for attempt in range(2):
                    record["front_error"] = bring_front()
                    state_before = window_state()
                    wall = time.monotonic()
                    flight = ctl("fly", "-527.5", "95", "57.5", "-399.5", "95", "57.5", "16", "10", "raw", timeout=45)
                    record["flight_attempts"].append({
                        "attempt": attempt + 1, "wall_seconds": time.monotonic() - wall,
                        "presented_seconds": flight.get("seconds"), "frames": flight.get("frames"),
                        "max_ms": flight.get("max_ms"), "window_before": state_before, "window_after": window_state()})
                    record["flight"] = flight
                    if flight.get("frames", 0) > 0 and flight.get("seconds", 0) >= 15:
                        break
                    if attempt == 0:
                        ctl("fly", "-399.5", "95", "57.5", "-527.5", "95", "57.5", "4", "10", timeout=20)
                if record["flight"].get("frames", 0) == 0 or record["flight"].get("seconds", 0) < 15:
                    raise RuntimeError("Renderer did not present frames across the full flight interval")
                record["after_flight"] = ctl("status")
                if not args.capture_flight_end:
                    settle_started = time.monotonic()
                    record["flight_settled"] = ctl("wait-ready", "120", timeout=125)
                    record["flight_settle_seconds"] = time.monotonic() - settle_started
                    record["flight_terrain_ready"] = settle_terrain()
                    record["flight_full_settle_seconds"] = time.monotonic() - settle_started
                record["flight_capture_mode"] = "endpoint" if args.capture_flight_end else "settled"
                record["flight_screenshot"] = ctl("screenshot", str(profile / "after-flight.png"))
            if args.fresh_flight:
                probe = record["fresh_flight"]
                for name in ("first-pass", "revisit"):
                    phase = {"name": name, "from": list(FRESH_FROM), "to": list(FRESH_TO)}
                    probe["phases"].append(phase)
                    ctl("tp", *FRESH_FROM)
                    # A zero-length flight establishes creative hover without
                    # generating the forward route before its measurement.
                    ctl("fly", *FRESH_FROM, *FRESH_FROM, 0.1, 10, timeout=15)
                    ctl("look", -90, 10)
                    phase["origin_settle"] = settle_terrain()
                    ctl("time", 1000)
                    phase["front_error"] = bring_front()
                    phase["window_before"] = window_state()
                    phase["system_before"] = system_snapshot()
                    phase["before"] = ctl("status")
                    if (phase["before"]["dimension"] != "minecraft:overworld" or
                            phase["before"]["render_distance"] != 12 or
                            max(abs(a - b) for a, b in zip(phase["before"]["player"]["position"], FRESH_FROM)) > 0.25):
                        raise RuntimeError("Fresh-flight origin/dimension/radius did not match the validated corridor")
                    phase["pack_selection"] = ctl("options-get", "resourcePacks")["options"]["resourcePacks"]["value"]
                    if phase["pack_selection"] != selection:
                        raise RuntimeError("Fresh-flight resource-pack selection changed")
                    phase["console_start_offset"] = (profile / "console.log").stat().st_size
                    sampled_fresh_flight(ctl, phase)
                    phase["console_end_offset"] = (profile / "console.log").stat().st_size
                    phase["after"] = ctl("status")
                    phase["window_after"] = window_state()
                    phase["system_after"] = system_snapshot()
                    phase["screenshot"] = ctl("screenshot", str(profile / f"fresh-{name}.png"))
                    measurement = phase["measurement"]
                    phase["hopeless"] = fresh_flight_hopeless(measurement)
                    if measurement.get("frames", 0) == 0 or measurement.get("seconds", 0) < FRESH_SECONDS - 1:
                        raise RuntimeError("Fresh-flight did not present the full interval; no retry")
                    if phase["before"]["input"]["counts"]["user"] != phase["after"]["input"]["counts"]["user"]:
                        raise RuntimeError("Fresh-flight was interrupted by user input")
                    if max(abs(a - b) for a, b in zip(phase["after"]["player"]["position"], FRESH_TO)) > 0.25:
                        raise RuntimeError("Fresh-flight endpoint did not match the requested route")
                    save()
                    if phase["hopeless"]:
                        probe["stopped"] = "Sub15FPS result is final; no revisit or retry"
                        break
                probe["complete"] = True
            if args.zoom_smoke:
                zoom = {"before": ctl("status"), "views": {}, "visual_verified": False,
                        "numeric_factor_runtime_verified": False}
                record["zoom_smoke"] = zoom
                selected = zoom["before"]["selected"]
                ctl("key", "c", "down")
                for stage, steps in [("held", None), ("wheel-up", 1), ("maximum", 10), ("minimum", -12)]:
                    if steps is not None:
                        ctl("scroll-at", "0", "0", steps)
                    ctl("wait", "20")
                    state = ctl("status")
                    if state["selected"] != selected:
                        raise RuntimeError("Zoom did not claim the held-key wheel event")
                    zoom["views"][stage] = {"status": state, "screenshot": ctl("screenshot", str(profile / f"zoom-{stage}.png"))}
                ctl("key", "c", "up")
                ctl("wait", "20")
                zoom["views"]["released"] = ctl("screenshot", str(profile / "zoom-released.png"))
                ctl("key", "c", "down")
                ctl("wait", "20")
                zoom["views"]["repressed"] = ctl("screenshot", str(profile / "zoom-repressed.png"))
                ctl("key", "c", "up")
                ctl("wait", "20")
                zoom["wheel_hotbar_guard_verified"] = True
                zoom["after"] = ctl("status")
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
            cem_lines = [line for line in (profile / "console.log").read_text(errors="replace").splitlines() if "custom entity model" in line.lower()]
            record["cem_diagnostics"] = {"count": len(cem_lines), "sample": cem_lines[:100], "sample_truncated": len(cem_lines) > 100, "full_evidence": "console.log"}
            save()
    print(json.dumps({"result": str(output), "complete": record["complete"], "error": record.get("error"), "exit_code": record["exit_code"]}), flush=True)
    return 0 if record["complete"] and record["exit_code"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
