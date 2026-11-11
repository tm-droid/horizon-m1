#!/usr/bin/env python3
"""Run the existing native-pack comparison against an explicitly selected r5 trial."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parents[1]
BASE = "nightly-2026-11-05-66f3981"
REVISION = "66f3981f522b24c250b21523a70080965b940424"


def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("--version", required=True)
    args, remaining = parser.parse_known_args()
    if not re.fullmatch(r"native-66f3981-m1-r5-[0-9a-f]{12}", args.version):
        parser.error("--version must name an installed r5 candidate")
    version = RUNTIME / "launcher-data/versions" / args.version
    metadata = json.loads((version / "native-mods.json").read_text())
    if metadata.get("base") != BASE or metadata.get("horizon") != REVISION or metadata.get("target") != "client":
        parser.error("r5 metadata does not match the pinned nightly client")
    migration = ROOT / "outputs/horizon-converter/2026-11-06-Tanush-66f3981-v4"
    spec = importlib.util.spec_from_file_location("r5_native_runner", RUNTIME / "run-u12-native-packs.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.BUILDS = {"r5": args.version}
    runner.MIGRATIONS = {"v4": migration}
    runner.ARM_DEFS = {"r5-v4-t": ("r5", "v4", {"HORIZON_SHADER_PACK_TIMING": "1"})}
    runner.REVIEW.RELEASE = BASE
    runner.REVIEW.REVISION = REVISION
    if not any(arg == "--arm" or arg.startswith("--arm=") for arg in remaining):
        remaining.extend(["--arm", "r5-v4-t"])
    if not any(arg == "--cases" or arg.startswith("--cases=") for arg in remaining):
        remaining.extend(["--cases", "makeup,n-daybreak020"])
    sys.argv = [sys.argv[0], *remaining]
    return runner.main()


if __name__ == "__main__":
    sys.exit(main())
