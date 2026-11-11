#!/usr/bin/env python3
"""Two isolated settings comparisons using the measured full-stack f42 scene."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

runtime = Path(__file__).resolve().parent
root = runtime.parents[1]
spec = importlib.util.spec_from_file_location("shader_review", runtime / "run-shader-followup-f42.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
migration = review.MIGRATION
manifest = migration / "manifest.json"
manifest_hash = review.digest(manifest)
selection = json.loads(manifest.read_text())["resourcepack_selection"]
summary_path = runtime / "settings-audit-f42-2026-11-05.json"
if summary_path.exists():
    raise SystemExit("Settings comparison output already exists")
summary = {"complete": False, "results": [], "visual_acceptance": "pending"}
env = {**os.environ, "HORIZON_TEST_QUEUE": "1"}
cases = [
    ("upload-auto", "packs", []),
    ("upload-512", "packs", ["--upload-budget-kib", "512"]),
    ("makeup-cloud-control", "makeup", []),
    ("makeup-native-cloud-off", "makeup", ["--disable-vanilla-clouds"]),
]
for name, case, extra in cases:
    if shutil.disk_usage(runtime).free < 4 * 2**30:
        raise SystemExit("Less than 4 GiB free")
    for process in ("java", "horizon-client", "Xcode", "xcodebuild", "cargo", "rustc"):
        check = subprocess.run(["pgrep", "-x", process], capture_output=True, timeout=10)
        if check.returncode != 1:
            raise SystemExit(f"Device preflight failed for {process} ({check.returncode})")
    label = f"f42-{name}-audit-r1"
    profile = runtime / "tests" / label
    shader = review.SHADERS.get(case)
    source_hashes = review.shader_hashes(review.SOURCE_SHADERS, shader) if shader else {}
    command = [
        sys.executable, "tools/horizon-offline-test.py", "--runtime", review.RELEASE,
        "--case", case, "--label", label, "--migration", str(migration),
        "--native-options-candidate", str(migration / "native-settings-candidate.json"),
        "--scene", "cow", "--fps-cap", "260", "--resolution-scale", "100",
        "--workers", "0", "--frame-pacing", "efficient", "--warmup", "15",
        "--seconds", "20", "--flight", *extra,
    ]
    completed = subprocess.run(command, cwd=root, env=env)
    result_path = profile / "result.json"
    entry = {"name": name, "result": str(result_path), "exit_code": completed.returncode}
    try:
        if completed.returncode:
            raise ValueError("Harness did not complete")
        result = json.loads(result_path.read_text())
        entry.update(review.review_result(result, profile, selection, manifest_hash, shader, 260, "settled"))
        if shader and (review.shader_hashes(review.SOURCE_SHADERS, shader) != source_hashes or
                       review.shader_hashes(profile / "shaderpacks", shader) != source_hashes):
            raise ValueError("Shader source or sidecar changed")
        expected_clouds = "false" if "--disable-vanilla-clouds" in extra else "true"
        if result["effective_visual_options"]["options"]["renderClouds"]["value"] != expected_clouds:
            raise ValueError("Live cloud setting mismatch")
        if name == "upload-512":
            graphics = result["settings_experiment"]["graphics_file_readback"]
            if graphics["uploadBudgetKiB"] != "512":
                raise ValueError("Upload setting readback mismatch")
        entry["flight_settle_seconds"] = result["flight_full_settle_seconds"]
        entry["flight_pending_uploads"] = result["after_flight"]["pending_uploads"]
        entry["flight_resident_sections"] = result["after_flight"]["renderer"]["resident_sections"]
        entry["flight_drawn_sections"] = result["after_flight"]["renderer"]["drawn_sections"]
        entry["flight_uploaded_bytes"] = (
            result["after_flight"]["renderer"]["uploaded_bytes"] -
            result["after"]["renderer"]["uploaded_bytes"]
        )
        entry["shader_hashes"] = source_hashes
        entry["valid"] = True
    except (OSError, KeyError, ValueError) as error:
        entry.update(valid=False, error=str(error))
    summary["results"].append(entry)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"case": name, "valid": entry["valid"], "error": entry.get("error")}), flush=True)
    if not entry["valid"]:
        raise SystemExit("Stopping after invalid settings experiment")
summary["complete"] = True
summary_path.write_text(json.dumps(summary, indent=2) + "\n")
