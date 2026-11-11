#!/usr/bin/env python3
"""Compare staged shaders on the same native-resolution scene in one device lease."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parents[1]
MIGRATION = ROOT / "outputs/horizon-converter/2026-11-04-Tanush-f42-v3"
SOURCE_SHADERS = ROOT / "instances/Tanush-26.3/minecraft/shaderpacks"
RELEASE = "nightly-2026-11-03-f42ef42"
REVISION = "f42ef42ef6ceccb3c6a20bea2481d87949a51c81"
SHADERS = {
    "makeup": "MakeUp-UltraFast-9.6.zip",
    "miniature": "miniature-shader-2.19.zip",
    "complementary": "ComplementaryReimagined_r5.9.3.zip",
}
STATIC_SECONDS = 20
SIZE = [2560, 1440]
DISPLAY = {"width": 2880, "height": 1800, "refresh_hz": 60, "scale": 2.0}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shader_hashes(directory, filename):
    paths = (directory / filename, directory / f"{filename}.txt")
    return {
        path.name: digest(path) if index == 0 or path.exists() else None
        for index, path in enumerate(paths)
    }


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def camera(state):
    return state["player"]["position"], state["yaw"], state["pitch"]


def review_result(result, profile, selection, manifest_hash, shader, fps_cap=60, flight_capture=None):
    check(result.get("complete") is True and result.get("exit_code") == 0,
          "Harness did not complete with a clean client exit")
    check(result["runtime_revision"] == REVISION and result["scene"] == "cow" and
          result["render_mode"] == "onscreen" and result["fps_cap"] == fps_cap and
          result["world_resolution_scale_percent"] == 100 and
          result["workers_configured"] == 0 and result["frame_pacing"] == "efficient" and
          result["shader_requested"] == shader,
          "Runtime or requested scene settings changed")
    check(result["migration_manifest_sha256"] == manifest_hash and
          result["pack_selection"] == selection and
          result["active_resourcepacks"]["options"]["resourcePacks"]["value"] == selection,
          "Active resource pack stack or source manifest changed")
    live_options = result["effective_visual_options"]["options"]
    check(all(live_options[key]["value"] == value for key, value in {
        "renderDistance": 12, "simulationDistance": 8, "fov": 95, "cloudRange": 64,
        "maxFps": fps_cap, "enableVsync": False,
    }.items()), "Effective visual settings or frame cap changed")
    if flight_capture:
        check(result.get("flight_capture_mode") == flight_capture, "Unexpected flight capture mode")
    before, after, flight_end = (result[key] for key in ("before", "after", "after_flight"))
    for state in (before, after, flight_end):
        renderer = state["renderer"]
        check(state["screen"] == "playing" and state["display"] == DISPLAY and
              renderer["size"] == SIZE and renderer["backend"] == "Metal" and
              renderer["gpu"] == "Apple M1" and renderer["present_mode"] == "Immediate",
              "Renderer surface or display changed")
        check(state["input"]["counts"]["user"] == before["input"]["counts"]["user"],
              "User input entered a measured interval")
    check(camera(before) == camera(after) == ([-527.5, 69.0, 57.5], 0.0, 15.0) and
          camera(flight_end) == ([-399.5, 95.0, 57.5], -90.0, 10.0) and
          before["chunks"] == after["chunks"] == 637 and
          result["fixture"]["identity_and_no_ai_verified"] is True and
          result["fixture"]["cow"]["pos"] == [-527.5, 69.05, 60.5],
          "Camera, settled scene, or cow fixture changed")

    screenshots = []
    for name in ("scene.png", "after-flight.png"):
        path = profile / name
        with path.open("rb") as handle:
            header = handle.read(24)
        check(header[:8] == b"\x89PNG\r\n\x1a\n" and
              [int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")] == SIZE,
              f"Unexpected screenshot geometry for {name}")
        screenshots.append(str(path))

    loader_evidence = []
    shader_diagnostics = []
    if shader:
        prefix = f"shader pack {shader}: "
        shader_diagnostics = [line for line in result["shader_diagnostics"] if line.startswith(prefix)]
        loader_evidence = [line for line in shader_diagnostics
                           if re.match(r"folder `[^`]*`, [1-9][0-9]* programs \(", line[len(prefix):])]
        check(loader_evidence, "No shader loader report showing active post programs")

    metrics = ("seconds", "frames", "avg_fps", "low_1pct_fps", "p95_ms", "p99_ms", "max_ms", "cpu", "gpu")
    phases = {}
    for phase, key, duration in (("static", "measurement", STATIC_SECONDS), ("flight", "flight", 16)):
        sample = result[key]
        check(sample["frames"] > 0 and duration - 1 <= sample["seconds"] <= duration + 1,
              f"Incomplete {phase} measurement")
        phases[phase] = {key: sample.get(key) for key in metrics}
    return {
        **phases,
        "screenshots": screenshots,
        "shader_loader_evidence": loader_evidence,
        "shader_diagnostics": shader_diagnostics,
        "end_of_flight_columns": flight_end["chunks"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="r1", help="Fresh batch suffix")
    parser.add_argument("--uncapped", action="store_true", help="Use Horizon's Unlimited setting with VSync off")
    args = parser.parse_args()
    fps_cap = 260 if args.uncapped else 60
    if not re.fullmatch(r"[a-z0-9-]{1,12}", args.tag):
        parser.error("Batch suffix must have 1–12 lowercase letters, digits, or hyphens")

    summary_path = RUNTIME / f"shader-followup-f42-{args.tag}.json"
    if summary_path.exists():
        parser.error("Batch already exists. Use a fresh --tag.")
    manifest = MIGRATION / "manifest.json"
    manifest_bytes = manifest.read_bytes()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    migration = json.loads(manifest_bytes)
    selection = migration["resourcepack_selection"]
    check(migration["source_unchanged"] is True and len(selection) == 53 and
          selection.count("vanilla") == 1 and sum(pack.startswith("file/") for pack in selection) == 52,
          "Expected the verified v3 stack with 52 file packs and vanilla")

    summary = {"mode": "onscreen uncapped renderer comparison" if args.uncapped else "onscreen capped renderer comparison",
               "fps_limit": "unlimited" if args.uncapped else 60,
               "foreground_independently_verified": False, "visual_parity_verified": False,
               "runtime_revision": REVISION, "manifest_sha256": manifest_hash,
               "results": [], "complete": False}
    env = {**os.environ, "HORIZON_TEST_QUEUE": "1"}
    for case in ("packs", *SHADERS):
        check(shutil.disk_usage(RUNTIME).free >= 4 * 2**30, "Less than 4 GiB free")
        for process in ("horizon-client", "java", "Xcode", "xcodebuild", "cargo", "rustc"):
            preflight = subprocess.run(["pgrep", "-x", process], capture_output=True, timeout=10)
            check(preflight.returncode == 1, f"Unexpected {process} preflight result {preflight.returncode}")
        label = f"f42-{case}-shader-onscreen-{args.tag}"
        profile = RUNTIME / "tests" / label
        check(not profile.exists(), f"Profile already exists: {label}")
        shader = SHADERS.get(case)
        initial_hashes = shader_hashes(SOURCE_SHADERS, shader) if shader else {}
        command = [sys.executable, "tools/horizon-offline-test.py", "--runtime", RELEASE,
                   "--case", case, "--label", label, "--migration", str(MIGRATION),
                   "--native-options-candidate", str(MIGRATION / "native-settings-candidate.json"),
                   "--scene", "cow", "--width", "1280", "--height", "720", "--resolution-scale", "100",
                   "--fps-cap", str(fps_cap), "--workers", "0", "--frame-pacing", "efficient",
                   "--warmup", "15", "--seconds", str(STATIC_SECONDS), "--flight"]
        if args.uncapped:
            command.append("--capture-flight-end")
        completed = subprocess.run(command, cwd=ROOT, env=env)
        result_path = profile / "result.json"
        entry = {"case": case, "label": label, "result": str(result_path), "exit_code": completed.returncode,
                 "valid_timing": False}
        try:
            check(completed.returncode == 0, "Harness failed. Inspect the profile's result and console log.")
            if shader:
                check(shader_hashes(SOURCE_SHADERS, shader) == initial_hashes and
                      shader_hashes(profile / "shaderpacks", shader) == initial_hashes,
                      "Shader archive or settings sidecar changed")
                entry["shader_hashes"] = initial_hashes
            entry.update(review_result(json.loads(result_path.read_text()), profile, selection, manifest_hash,
                                       shader, fps_cap, "endpoint" if args.uncapped else None))
            entry["valid_timing"] = True
        except (KeyError, OSError, ValueError) as error:
            entry["error"] = str(error)
        summary["results"].append(entry)
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps({"case": case, "valid_timing": entry["valid_timing"],
                          "error": entry.get("error"), "summary": str(summary_path)}), flush=True)
        if case == "packs" and not entry["valid_timing"]:
            return 1
    summary["complete"] = all(entry["valid_timing"] for entry in summary["results"])
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if summary["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
