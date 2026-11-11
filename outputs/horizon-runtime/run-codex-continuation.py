#!/usr/bin/env python3
"""Queued reference, smoke and paired r4 checks using the established U9c gates/reviewer."""
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
spec = importlib.util.spec_from_file_location("u9c", RUNTIME / "run-u9c-makeup-trim.py")
U9 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(U9)
HOPELESS_FPS = 15


def gate_problems(check_idle=True):
    problems = U9.gate_problems(check_idle=check_idle)
    if U9.sh(["pgrep", "-f", r"/CoreSimulator/Profiles/.*/SpringBoard\.app/SpringBoard"]).returncode != 1:
        problems.append("iOS Simulator device still booted (its window may be closed)")
    return problems


def hopeless(entry):
    value = (entry.get("static") or {}).get("avg_fps")
    if value is None and Path(entry["result"]).is_file():
        value = (json.loads(Path(entry["result"]).read_text()).get("measurement") or {}).get("avg_fps")
    return isinstance(value, (int, float)) and value < HOPELESS_FPS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("reference", "smoke", "compare"), required=True)
    parser.add_argument("--version", default="native-f42-m1-r3-6b039bd4b49f")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.tag.replace("-", "").isalnum() or not 1 <= args.rounds <= 5:
        parser.error("tag must be alphanumeric/hyphens; rounds must be 1..5")
    old = "native-f42-m1-r3-6b039bd4b49f"
    cases = ["makeup"] if args.mode == "reference" else ["makeup", "packs"]
    rounds = args.rounds if args.mode == "compare" else 1
    arms = {"r3": old, "candidate": args.version} if args.mode == "compare" else {"candidate": args.version}
    options = (RUNTIME / "checkpoints/codex-20261106/outputs__horizon-runtime__game__shaderpacks__MakeUp-UltraFast-9.6.zip.txt"
               if args.mode == "reference" else U9.TRIM_FILE)
    migration = U9.MIGRATIONS["v4"]
    info = {"selection": json.loads((migration / "manifest.json").read_text())["resourcepack_selection"],
            "manifest_hash": U9.R3.digest(migration / "manifest.json")}
    matrix = [(case, arm, rnd) for rnd in range(1, rounds + 1) for case in cases
              for arm in (list(arms) if rnd % 2 else list(reversed(arms)))]
    for case, arm, rnd in matrix:
        label = f"cx-{args.tag}-{case}-{arm}-{rnd}"
        if len(label) > 60 or (RUNTIME / "tests" / label).exists():
            parser.error(f"invalid or existing profile: {label}")
        if not (U9.VERSIONS / arms[arm] / "horizon-client").is_file():
            parser.error(f"missing build {arms[arm]}")
    if not options.is_file():
        parser.error(f"missing options: {options}")
    if args.dry_run:
        print(json.dumps({"matrix": matrix, "builds": arms, "shader_options": str(options)}, indent=2))
        return 0
    if not os.environ.get("HORIZON_TEST_QUEUE"):
        parser.error("run through the shared device queue with HORIZON_TEST_QUEUE=1")
    summary_path = RUNTIME / f"codex-{args.tag}.json"
    if summary_path.exists():
        parser.error("summary already exists; choose a fresh tag")
    summary = {"mode": args.mode, "builds": arms, "plan": matrix, "results": [], "complete": False}
    hashes = {arm: U9.R3.digest(U9.VERSIONS / version / "horizon-client") for arm, version in arms.items()}
    option_hash = U9.R3.digest(options)
    env = {k: v for k, v in os.environ.items() if k != "HORIZON_GPU_CULL"}
    env["HORIZON_TEST_QUEUE"] = "1"
    keepawake = subprocess.Popen(["caffeinate", "-i"])

    def save():
        temp = summary_path.with_suffix(".tmp")
        temp.write_text(json.dumps(summary, indent=2) + "\n")
        os.replace(temp, summary_path)

    try:
        for index, (case, arm, rnd) in enumerate(matrix):
            if index:
                time.sleep(U9.COOLDOWN)
            ok, problems = U9.wait_gates(print, probe=gate_problems)
            if not ok:
                raise RuntimeError(f"gates failed: {problems}")
            if U9.R3.digest(options) != option_hash or U9.R3.digest(U9.VERSIONS / arms[arm] / "horizon-client") != hashes[arm]:
                raise RuntimeError("benchmark inputs changed")
            label = f"cx-{args.tag}-{case}-{arm}-{rnd}"
            profile = RUNTIME / "tests" / label
            entry = {"case": case, "arm": arm, "round": rnd, "label": label,
                     "native_version": arms[arm], "result": str(profile / "result.json"), "valid": False}
            summary["results"].append(entry)
            save()
            command = [sys.executable, str(ROOT / "tools/horizon-offline-test.py"), "--runtime", U9.REVIEW.RELEASE,
                       "--native-version", arms[arm], "--case", case, "--label", label,
                       "--migration", str(migration), "--native-options-candidate", str(migration / "native-settings-candidate.json"),
                       "--scene", "cow", "--width", "1280", "--height", "720", "--resolution-scale", "100",
                       "--fps-cap", "260", "--workers", "0", "--frame-pacing", "efficient",
                       "--warmup", "15", "--seconds", "20", "--flight"]
            if case == "makeup":
                command.extend(["--shader-options-file", str(options)])
            sampler = U9.R3.Sampler()
            awake = subprocess.Popen(["caffeinate", "-d", "-t", "3600"])
            try:
                sampler.start()
                entry["exit_code"] = subprocess.run(command, cwd=ROOT, env=env).returncode
                result = json.loads((profile / "result.json").read_text())
                entry["static"] = result.get("measurement")
                entry["flight"] = result.get("flight")
                entry["hopeless"] = hopeless(entry)
                U9.REVIEW.check(entry["exit_code"] == 0, "harness failed")
                U9.REVIEW.check(result.get("native_executable_sha256") == hashes[arm], "native binary mismatch")
                review = U9.REVIEW.review_result(result, profile, info["selection"], info["manifest_hash"],
                                                "MakeUp-UltraFast-9.6.zip" if case == "makeup" else None,
                                                260, "settled")
                entry.update(review)
                entry["tainted"] = bool(U9.R3.TAINT.search((profile / "console.log").read_text(errors="replace")))
                entry["valid"] = not entry["tainted"]
                if entry["tainted"]:
                    entry["error"] = "input from a person during measurement"
            except Exception as error:
                entry["error"] = str(error)
                entry["hopeless"] = hopeless(entry)
            finally:
                sampler.stop.set()
                sampler.join(timeout=40)
                entry["memory"] = sampler.summary()
                awake.terminate()
                # Retain measurements, worlds and screenshots; release throwaway
                # texture caches/pack clones as the established U9/U12 runners do.
                if profile.parent == RUNTIME / "tests" and profile.name.startswith("cx-"):
                    try:
                        for name in (".horizon-cache", "resourcepacks"):
                            if (profile / name).exists():
                                shutil.rmtree(profile / name)
                    except OSError as error:
                        entry["cleanup_error"] = str(error)
                save()
            print(json.dumps({k: entry.get(k) for k in ["label", "valid", "hopeless", "error", "static"]}), flush=True)
            if not entry["valid"] or entry["hopeless"]:
                summary["aborted"] = f"stopped after {label}; inspect this run before scheduling more"
                save()
                return 1
        summary["complete"] = True
        save()
        return 0
    finally:
        keepawake.terminate()


if __name__ == "__main__":
    sys.exit(main())
