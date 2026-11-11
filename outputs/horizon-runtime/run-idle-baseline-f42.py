#!/usr/bin/env python3
"""Serial uncapped, on-screen baseline of pinned Horizon and the full pack stack."""
import argparse
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
runtime = Path(__file__).resolve().parent
migration = root / "outputs/horizon-converter/2026-11-04-Tanush-f42-v3"
os.chdir(root)
os.environ["HORIZON_TEST_QUEUE"] = "1"
parser = argparse.ArgumentParser()
parser.add_argument("--packs-after-base", action="store_true", help="Resume a pair whose base run already passed")
args = parser.parse_args()


def signature(state):
    renderer = state["renderer"]
    return renderer["size"], renderer["backend"], renderer["gpu"], renderer["present_mode"], state["display"]


def camera(state):
    return state["player"]["position"], state["yaw"], state["pitch"]


expected = None
for case in ("base", "packs"):
    reuse_base = case == "base" and args.packs_after_base
    if not reuse_base and shutil.disk_usage(runtime).free < 4 * 2**30:
        raise SystemExit("Not starting baseline with less than 4 GiB free")
    for name in ("horizon-client", "java", "Xcode", "cargo", "rustc", "xcodebuild"):
        check = subprocess.run(["pgrep", "-x", name], capture_output=True, timeout=10)
        if check.returncode != 1:
            raise SystemExit(f"Refusing idle baseline: {name} process check returned {check.returncode}")
    label = f"f42-{case}-idle-uncapped-r1"
    print(f"{'Rechecking' if reuse_base else 'Starting'} {label}", flush=True)
    if not reuse_base:
        subprocess.run([sys.executable, "tools/horizon-offline-test.py",
                    "--runtime", "nightly-2026-11-03-f42ef42", "--case", case, "--label", label,
                    "--migration", str(migration), "--native-options-candidate",
                    str(migration / "native-settings-candidate.json"), "--scene", "cow",
                    "--width", "1280", "--height", "720", "--resolution-scale", "100",
                    "--fps-cap", "260", "--workers", "0", "--frame-pacing", "efficient",
                    "--warmup", "15", "--seconds", "25", "--flight"], check=True)
    result = json.loads((runtime / "tests" / label / "result.json").read_text())
    before, after, flight = (result[key] for key in ("before", "after", "after_flight"))
    states = (before, after, flight)
    if expected is None:
        expected = signature(before)
    if (result.get("complete") is not True or result.get("exit_code") != 0 or
        result.get("render_mode") != "onscreen" or result.get("fps_cap") != 260 or
        expected[:4] != ([2560, 1440], "Metal", "Apple M1", "Immediate") or
        any(signature(state) != expected or state["screen"] != "playing" or
            state["input"]["counts"]["user"] != before["input"]["counts"]["user"] for state in states) or
        camera(before) != camera(after) or
        flight["player"]["position"] != [-399.5, 95.0, 57.5] or
        len(result["pack_selection"]) != (1 if case == "base" else 53)):
        raise SystemExit(f"{label}: benchmark validity gate failed; inspect result.json")
    metrics = ("frames", "seconds", "avg_fps", "low_1pct_fps", "p99_ms", "cpu", "gpu")
    print(json.dumps({"label": label, "display": expected[-1], **{
        name: {key: result[phase].get(key) for key in metrics}
        for name, phase in (("static", "measurement"), ("flight", "flight"))
    }}), flush=True)
