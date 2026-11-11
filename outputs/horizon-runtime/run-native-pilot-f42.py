#!/usr/bin/env python3
"""Run the official/native guardian smoke pair inside one shared device queue turn."""
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
BASE = "nightly-2026-11-03-f42ef42"
ENGINE = "f42ef42ef6ceccb3c6a20bea2481d87949a51c81"
MIXINS = "e8cd0aa38cffef49cb2e088ef716baa107148c02"


def read_json(path):
    return json.loads(path.read_text())


def executable_sha256(path):
    with path.open("rb") as binary:
        return hashlib.file_digest(binary, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_version", help="Installed native version reported by the guarded launcher")
    parser.add_argument("--run-tag", default="r1", help="Fresh profile suffix")
    args = parser.parse_args()
    if not re.fullmatch(r"native-[a-zA-Z0-9._-]{1,120}", args.native_version):
        parser.error("Invalid native version directory name")
    if not re.fullmatch(r"[a-z0-9-]{1,20}", args.run_tag):
        parser.error("Invalid profile suffix")

    status = read_json(RUNTIME / "zoom-build-status-2026-11-04.json")
    if (status.get("complete") is not True or status.get("cleanup_verified") is not True or
            status.get("exit_code") != 0 or status.get("desired_engine_revision") != ENGINE):
        raise SystemExit("Guarded f42 native build has no verified successful completion")

    release = RUNTIME / "launcher-data/versions" / args.native_version
    binary = release / "horizon-client"
    expected = {"base": BASE, "horizon": ENGINE, "horizon_mixins": MIXINS,
                "rust": "1.99.1", "profile": "performance", "target": "client"}
    native = read_json(release / "native-mods.json")
    if (not (release / ".installed").is_file() or not binary.is_file() or not os.access(binary, os.X_OK) or
            any(native.get(key) != value for key, value in expected.items()) or
            sorted(mod["id"] for mod in native.get("mods", [])) != ["cem_alias_f42", "zoom"]):
        raise SystemExit("Installed native metadata does not match the reviewed f42 pilot")
    binary_sha = executable_sha256(binary)
    print(json.dumps({"native_version": args.native_version, "native_executable_sha256": binary_sha,
                      "native_build": native}), flush=True)

    manifest = read_json(MIGRATION / "manifest.json")
    selection = manifest["resourcepack_selection"]
    if (manifest.get("source_unchanged") is not True or len(selection) != 53 or
            selection.count("vanilla") != 1 or sum(pack.startswith("file/") for pack in selection) != 52):
        raise SystemExit("Expected the validated v3 stack with 52 file packs and vanilla")

    env = os.environ.copy()
    env["HORIZON_TEST_QUEUE"] = "1"
    for case in ("official", "native"):
        if shutil.disk_usage(RUNTIME).free < 4 * 2**30:
            raise SystemExit("Less than 4 GiB free; not starting guardian smoke")
        for name in ("horizon-client", "java"):
            check = subprocess.run(["pgrep", "-x", name], capture_output=True, timeout=10)
            if check.returncode != 1:
                raise SystemExit(f"Refusing guardian smoke: {name} process check returned {check.returncode}")

        label = f"f42-guardian-{case}-{args.run_tag}"
        profile = RUNTIME / "tests" / label
        command = [sys.executable, "tools/horizon-offline-test.py", "--runtime", BASE,
                   "--case", "packs", "--label", label, "--migration", str(MIGRATION),
                   "--native-options-candidate", str(MIGRATION / "native-settings-candidate.json"),
                   "--scene", "guardian", "--offscreen", "--resolution-scale", "100",
                   "--fps-cap", "60", "--workers", "0", "--frame-pacing", "efficient",
                   "--warmup", "10", "--seconds", "10"]
        if case == "native":
            if executable_sha256(binary) != binary_sha:
                raise SystemExit("Native binary changed after preflight")
            command.extend(["--native-version", args.native_version, "--zoom-smoke"])
        subprocess.run(command, cwd=ROOT, env=env, check=True)

        result_path = profile / "result.json"
        result = read_json(result_path)
        if (result.get("complete") is not True or result.get("exit_code") != 0 or
                result.get("pack_selection") != selection or
                result.get("fixture", {}).get("identity_and_no_ai_verified") is not True):
            raise SystemExit(f"{label} failed the full-stack guardian checks")
        if case == "native" and (result.get("native_executable_sha256") != binary_sha or
                                 result.get("zoom_smoke", {}).get("wheel_hotbar_guard_verified") is not True):
            raise SystemExit(f"{label} failed the native binary or Zoom control checks")
        print(json.dumps({"result": str(result_path), "case": case,
                          "cem_diagnostic_lines": result["cem_diagnostics"]["count"],
                          "screenshots": [str(path) for path in sorted(profile.glob("*.png"))],
                          "visual_parity_verified": False, "performance_comparison_valid": False}), flush=True)


if __name__ == "__main__":
    main()
