#!/usr/bin/env python3
"""One shared-queue full-stack check; no production game writes."""
from pathlib import Path
import json, os, subprocess, sys
root = Path(__file__).resolve().parents[2]
os.chdir(root)
for name in ("horizon-client", "java"):
    result = subprocess.run(["pgrep", "-x", name], capture_output=True, text=True, timeout=10)
    if result.returncode != 1:
        raise SystemExit(f"Refusing test: {name} process check returned {result.returncode}")
migration = root / "outputs/horizon-converter/2026-11-04-Tanush-f42-v3"
manifest = json.loads((migration / "manifest.json").read_text())
if manifest.get("source_unchanged") is not True:
    raise SystemExit("Migration source check did not pass")
subprocess.run([sys.executable, "-m", "py_compile", "tools/horizon-offline-test.py"], check=True)
os.environ["HORIZON_TEST_QUEUE"] = "1"
raise SystemExit(subprocess.call([sys.executable, "tools/horizon-offline-test.py",
    "--runtime", "nightly-2026-11-03-f42ef42", "--case", "packs",
    "--label", "f42-full-stack-sourceopts-r1", "--migration", str(migration),
    "--native-options-candidate", str(migration / "native-settings-candidate.json"),
    "--scene", "cow", "--resolution-scale", "100", "--fps-cap", "60",
    "--workers", "0", "--frame-pacing", "efficient", "--warmup", "20",
    "--seconds", "30", "--flight"]))
