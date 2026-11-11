#!/usr/bin/env python3
"""Overrides matrix on the f42 M1 control build: base vs env/option arms, sequential runs.

Run inside a device-testing-queue turn. Usage: run-overrides-matrix.py --tag T --sequence packs:base packs:w6 ...
Results append to overrides-matrix-<tag>.json (one entry per run, keyed by sequence index).
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parents[1]
spec = importlib.util.spec_from_file_location("mx", RUNTIME / "run-m1-performance-matrix.py")
mx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mx)
REVIEW = mx.REVIEW
CONTROL = "native-f42-m1-control-09391c2a8210"
COOLDOWN = 60

# arm -> harness args (env via --env, graphics lines via --graphics-line)
ARMS = {
    "base": [],
    "w6": ["--env", "HORIZON_WORKER_THREADS=6"],
    "w4": ["--env", "HORIZON_WORKER_THREADS=4"],
    "ub2048": ["--graphics-line", "uploadBudgetKiB:2048"],
    "cullall": ["--env", "HORIZON_GPU_CULL=all"],
    "cloudsoff": ["--disable-vanilla-clouds"],
    "combo": ["--env", "HORIZON_GPU_CULL=all", "--disable-vanilla-clouds", "--graphics-line", "uploadBudgetKiB:2048"],
    "shadowcache": ["--graphics-line", "shadowCache:true"],
}


def gate():
    g = mx.safety_gate()
    try:
        import Quartz
        if Quartz.CGDisplayIsAsleep(Quartz.CGMainDisplayID()):
            g["problems"].append("display asleep")
            g["ok"] = False
    except Exception as error:
        g["problems"].append(f"display state unknown: {error!r}")
        g["ok"] = False
    return g


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True)
    p.add_argument("--sequence", nargs="+", required=True, metavar="CASE:ARM")
    args = p.parse_args()
    out = RUNTIME / f"overrides-matrix-{args.tag}.json"
    summary = json.loads(out.read_text()) if out.exists() else {"results": []}
    manifest_path = REVIEW.MIGRATION / "manifest.json"
    manifest_hash = mx.digest(manifest_path)
    selection = json.loads(manifest_path.read_text())["resourcepack_selection"]
    shader = REVIEW.SHADERS["makeup"]
    shader_hashes = REVIEW.shader_hashes(REVIEW.SOURCE_SHADERS, shader)
    binary = mx.digest(RUNTIME / "launcher-data/versions" / CONTROL / "horizon-client")
    env = {**os.environ, "HORIZON_TEST_QUEUE": "1"}
    first = True
    for i, item in enumerate(args.sequence, 1):
        parts = item.split(":")
        case, arm = parts[0], parts[1]
        rnd = int(parts[2]) if len(parts) > 2 else None
        label = f"ovr-{case}-{arm}-{args.tag}-{i}"
        profile = RUNTIME / "tests" / label
        entry = {"seq": i, "case": case, "arm": arm, "label": label, "valid": False, "tag": args.tag, "round": rnd}
        if not first:
            time.sleep(COOLDOWN)
        first = False
        g = gate()
        entry["gate"] = g
        if not g["ok"]:
            entry["error"] = "GATE: " + "; ".join(g["problems"])
            summary["results"].append(entry)
            out.write_text(json.dumps(summary, indent=1))
            print(json.dumps(entry["error"]), flush=True)
            return 1
        try:
            mx.require(shutil.disk_usage(RUNTIME).free >= 4 * 2**30, "Less than 4 GiB free")
            for proc in ("horizon-client", "java", "Xcode", "xcodebuild", "cargo", "rustc"):
                mx.require(subprocess.run(["pgrep", "-x", proc], capture_output=True).returncode == 1, f"{proc} running")
            mx.require(not profile.exists(), "profile exists")
            cmd = [sys.executable, "tools/horizon-offline-test-ovr.py", "--runtime", REVIEW.RELEASE,
                   "--native-version", CONTROL, "--case", case, "--label", label,
                   "--migration", str(REVIEW.MIGRATION), "--native-options-candidate",
                   str(REVIEW.MIGRATION / "native-settings-candidate.json"), "--scene", "cow",
                   "--width", "1280", "--height", "720", "--resolution-scale", "100",
                   "--fps-cap", "260", "--workers", "0", "--frame-pacing", "efficient",
                   "--warmup", "15", "--seconds", "20", "--flight", *ARMS[arm]]
            entry["cmd_extra"] = ARMS[arm]
            done = subprocess.run(cmd, cwd=ROOT, env=env)
            entry["exit_code"] = done.returncode
            mx.require(done.returncode == 0, "Harness failed")
            result = json.loads((profile / "result.json").read_text())
            mx.require(result.get("native_executable_sha256") == binary, "binary mismatch")
            entry.update(REVIEW.review_result(result, profile, selection, manifest_hash,
                                              shader if case == "makeup" else None, 260, "settled"))
            for key in ("static", "flight", "flight_settle_seconds", "flight_full_settle_seconds",
                        "startup_to_full_scene_seconds", "overrides"):
                if result.get(key) is not None or key not in entry:
                    entry[key] = result.get(key)
            entry["static"] = result["measurement"]
            entry["swap_after"] = mx.swap()
            console = profile / "console.log"
            tainted = console.is_file() and mx.TAINT.search(console.read_text(errors="replace"))
            entry["tainted"] = bool(tainted)
            entry["valid"] = not tainted
            entry["scene"] = str(profile / "scene.png")
        except Exception as error:  # noqa: BLE001
            entry["error"] = repr(error)
        summary["results"].append(entry)
        out.write_text(json.dumps(summary, indent=1))
        s = entry.get("static") or {}
        f = entry.get("flight") or {}
        print(json.dumps({"seq": i, "case": case, "arm": arm, "valid": entry["valid"], "err": entry.get("error"),
                          "s_fps": s.get("avg_fps"), "f_fps": f.get("avg_fps")}), flush=True)
        # Own profile only, after the harness exited: drop heavy caches, keep result/scene/console.
        for sub in (".horizon-cache", "resourcepacks", "saves"):
            shutil.rmtree(profile / sub, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
