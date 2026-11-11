#!/usr/bin/env python3
"""Compare source-patched and control f42 native clients in an interleaved matrix."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parents[1]
VERSIONS = RUNTIME / "launcher-data/versions"
CONTROL_SEED = "native-f42ef42-898af830522b"
CONTROL_SEED_SHA256 = "d96a7246310077b4794892e381da75a10902059cf7ec10b7d92a1fde37ebd069"
BUILD_STATUS = RUNTIME / "m1-performance/build-status.json"  # --build-status overrides (e.g. m1-performance-r2/build-status.json)
SPEC = importlib.util.spec_from_file_location("shader_review", RUNTIME / "run-shader-followup-f42.py")
REVIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REVIEW)


def read_json(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def verify_builds(build_status=BUILD_STATUS):
    status = read_json(build_status)
    require(status.get("complete") is True and status.get("cleanup_verified") is True and
            status.get("exit_code") == 0 and not status.get("error") and
            status.get("source_revision") == REVIEW.REVISION and
            status.get("rust") == "1.99.1" and status.get("profile") == "fast",
            "Candidate has no verified successful matching native build")
    candidate = status.get("candidate_version", "")
    require(re.fullmatch(r"native-f42-m1-(r[23]-)?[a-f0-9]{12}", candidate), "Invalid candidate version name")
    control_version = status.get("built_control_version", "")
    require(re.fullmatch(r"native-f42-m1-control-[a-f0-9]{12}", control_version), "Invalid fresh control version name")
    seed = read_json(VERSIONS / CONTROL_SEED / "native-mods.json")
    expected = {"base": REVIEW.RELEASE, "horizon": REVIEW.REVISION,
                "horizon_mixins": "e8cd0aa38cffef49cb2e088ef716baa107148c02",
                "rust": "1.99.1", "profile": "performance", "target": "client"}
    require(all(seed.get(key) == value for key, value in expected.items()) and
            sorted(mod["id"] for mod in seed.get("mods", [])) == ["cem_alias_f42", "zoom"] and
            status.get("control_metadata") == seed and
            digest(VERSIONS / CONTROL_SEED / "horizon-client") == CONTROL_SEED_SHA256,
            "Seed build does not match the f42 Zoom/CEM source provenance")
    control_source_digest = hashlib.sha256(json.dumps(status["source_files"], sort_keys=True).encode()).hexdigest()
    require(control_source_digest == status.get("control_source_digest"), "Fresh control source digest mismatch")
    control = read_json(VERSIONS / control_version / "native-mods.json")
    require(all(control.get(key) == seed.get(key) for key in (*expected, "mods", "hooks")) and
            control.get("build_method") == "direct-cargo-control" and
            control.get("source_patch_digest") == control_source_digest and
            control.get("control_seed_version") == CONTROL_SEED,
            "Fresh control compiler profile, compatibility mods or source identity differs")
    control_provenance = read_json(VERSIONS / control_version / "source-patches.json")
    # A build that reused an installed control has no built_control_sha256; take it from the control's own provenance.
    status.setdefault("built_control_sha256", control_provenance.get("built_control_sha256", control_provenance.get("binary_sha256")))
    require(control_provenance.get("build_method") == "direct-cargo-control" and
            control_provenance.get("source_patch_digest") == control_source_digest and
            control_provenance.get("control_seed_version") == CONTROL_SEED and
            control_provenance.get("source_files") == status["source_files"] and
            control_provenance.get("built_control_sha256", control_provenance.get("binary_sha256")) == status["built_control_sha256"],
            "Installed fresh control provenance differs from the build record")
    metadata = read_json(VERSIONS / candidate / "native-mods.json")
    require(all(metadata.get(key) == control.get(key) for key in (*expected, "mods", "hooks")) and
            metadata.get("build_method") == "direct-cargo-source-patches" and
            metadata.get("control_version") == control_version and
            metadata.get("source_patch_digest") == status.get("candidate_source_digest"),
            "Candidate compiler profile, compatibility mods, or source identity differs")
    provenance = read_json(VERSIONS / candidate / "source-patches.json")
    require(provenance == {k: v for k, v in status.items() if k in provenance or k != "built_control_sha256"}, "Installed source-patch provenance differs from build status")
    source_digest = hashlib.sha256(json.dumps(status["candidate_files"], sort_keys=True).encode()).hexdigest()
    require(source_digest == status["candidate_source_digest"], "Candidate source digest mismatch")
    hashes = {"control": status["built_control_sha256"], "candidate": status["binary_sha256"]}
    versions = {"control": control_version, "candidate": candidate}
    for role, version in versions.items():
        directory = VERSIONS / version
        require((directory / ".installed").is_file() and os.access(directory / "horizon-client", os.X_OK) and
                digest(directory / "horizon-client") == hashes[role], f"Unverified {role} executable")
    return versions, hashes, metadata, source_digest


COOLDOWN = 60
TAINT = re.compile(r"input from a person", re.I)


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=15)


def swap():
    return sh(["sysctl", "vm.swapusage"]).stdout.strip()


def safety_gate():
    """AC power, unlocked screen, no build processes, no Java Minecraft."""
    problems = []
    batt = sh(["pmset", "-g", "batt"]).stdout
    if "AC Power" not in batt.splitlines()[0]:
        problems.append(f"not on AC: {batt.splitlines()[0]}")
    try:
        import Quartz
        locked = Quartz.CGSessionCopyCurrentDictionary().get("CGSSessionScreenIsLocked", 0)
        if locked not in (0, None, False):
            problems.append(f"screen locked: {locked}")
    except Exception as error:  # cannot prove unlocked -> fail closed
        locked = f"unknown ({error!r})"
        problems.append(f"cannot read lock state: {error!r}")
    therm = sh(["pmset", "-g", "therm"]).stdout
    if re.search(r"(Thermal|Performance|CPU)[^\n]*level[^\n]*=\s*[1-9]|CPU_Speed_Limit\s*=\s*(?!100)\d+", therm):
        problems.append("thermal throttling: " + " | ".join(therm.split("\n")[:4]))
    for process in ("xcodebuild", "cargo", "rustc"):
        if sh(["pgrep", "-x", process]).returncode != 1:
            problems.append(f"{process} running")
    if sh(["pgrep", "-f", "PineconeMC"]).returncode != 1:
        problems.append("PineconeMC java running")
    return {"ok": not problems, "problems": problems, "swap": swap(), "batt": batt.splitlines()[0], "locked": locked}


def plan_for(mode, repeats, cases):
    if mode == "u4":
        return [("makeup", "control")] * 2
    plan = []
    for case in cases:
        for _ in range(repeats):
            plan += [(case, role) for role in ("control", "candidate", "candidate", "control")]
            plan += [(case, role) for role in ("candidate", "control", "control", "candidate")]
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="r2", help="Fresh matrix suffix")
    parser.add_argument("--mode", choices=["ab", "u4"], default="ab",
                        help="u4 = makeup/control twice (harness verification); ab = ABBA/BAAB per case")
    parser.add_argument("--repeats", type=int, default=1, help="ABBA+BAAB groups per case (1 -> 4 runs per build per case)")
    parser.add_argument("--cases", nargs="+", default=["packs", "makeup"], choices=["packs", "makeup"])
    parser.add_argument("--retry-tainted", type=int, default=1)
    parser.add_argument("--build-status", type=Path, default=BUILD_STATUS, help="Candidate build-status.json")
    parser.add_argument("--sequence", nargs="+", metavar="CASE:ROLE", help="Explicit run order (e.g. makeup:candidate makeup:control) instead of ABBA/BAAB")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]{1,12}", args.tag):
        parser.error("Tag must have 1–12 lowercase letters, digits, or hyphens")
    summary_path = RUNTIME / f"m1-performance-matrix-{args.tag}.json"
    if summary_path.exists():
        parser.error("Matrix already exists; use a fresh tag")
    versions, binary_hashes, candidate_metadata, source_digest = verify_builds(args.build_status)
    manifest_path = REVIEW.MIGRATION / "manifest.json"
    manifest_hash = digest(manifest_path)
    manifest = read_json(manifest_path)
    selection = manifest["resourcepack_selection"]
    require(manifest.get("source_unchanged") is True and len(selection) == 53 and
            selection.count("vanilla") == 1 and sum(pack.startswith("file/") for pack in selection) == 52,
            "Expected the validated v3 selection with all 52 file packs")
    shader = REVIEW.SHADERS["makeup"]
    shader_hashes = REVIEW.shader_hashes(REVIEW.SOURCE_SHADERS, shader)
    matrix = plan_for(args.mode, args.repeats, args.cases)
    if args.sequence:
        matrix = [tuple(item.split(":")) for item in args.sequence]
    summary = {
        "complete": False, "aborted": None, "mode": "onscreen uncapped same-profile native source-patch comparison",
        "comparison": "ABBA then BAAB per case; A=control, B=candidate" if args.mode == "ab" else "u4 harness verification: makeup/control x2",
        "plan": [list(item) for item in matrix], "python": sys.executable,
        "performance_claim_limit": "Source patch overhead uses matched fast-profile clients; publisher release is not compared",
        "flight_capture_mode": "settled", "flight_background_sampling": "none",
        "runtime_revision": REVIEW.REVISION, "versions": versions, "binary_sha256": binary_hashes,
        "candidate_source_digest": source_digest, "candidate_metadata": candidate_metadata,
        "manifest_sha256": manifest_hash, "makeup_shader_hashes": shader_hashes, "results": [],
    }

    def save():
        temporary = summary_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(summary, indent=2) + "\n")
        os.replace(temporary, summary_path)

    save()
    env = {**os.environ, "HORIZON_TEST_QUEUE": "1"}

    def run_once(index, case, role, attempt):
        suffix = "" if attempt == 1 else f"-redo{attempt - 1}"
        label = f"f42-m1-{case}-{role}-{index}-{args.tag}{suffix}"
        profile = RUNTIME / "tests" / label
        entry = {"index": index, "case": case, "role": role, "label": label, "attempt": attempt,
                 "native_version": versions[role], "result": str(profile / "result.json"), "valid": False,
                 "tainted": False}
        if index > 1 or attempt > 1:
            import time
            time.sleep(COOLDOWN)  # cooldown between runs (u6b)
        gate = safety_gate()
        entry["gate"] = gate
        if not gate["ok"]:
            entry["error"] = "SAFETY GATE FAILED: " + "; ".join(gate["problems"])
            entry["gate_failed"] = True
            return entry
        try:
            require(shutil.disk_usage(RUNTIME).free >= 4 * 2**30, "Less than 4 GiB free")
            for process in ("horizon-client", "java", "Xcode", "xcodebuild", "cargo", "rustc"):
                preflight = subprocess.run(["pgrep", "-x", process], capture_output=True, timeout=10)
                require(preflight.returncode == 1, f"Unexpected {process} preflight result {preflight.returncode}")
            require(not profile.exists(), f"Profile already exists: {label}")
            require(digest(manifest_path) == manifest_hash and
                    REVIEW.shader_hashes(REVIEW.SOURCE_SHADERS, shader) == shader_hashes,
                    "Migration or shader source changed during matrix")
            require(digest(VERSIONS / versions[role] / "horizon-client") == binary_hashes[role],
                    "Native executable changed during matrix")
            command = [sys.executable, "tools/horizon-offline-test.py", "--runtime", REVIEW.RELEASE,
                       "--native-version", versions[role], "--case", case, "--label", label,
                       "--migration", str(REVIEW.MIGRATION), "--native-options-candidate",
                       str(REVIEW.MIGRATION / "native-settings-candidate.json"), "--scene", "cow",
                       "--width", "1280", "--height", "720", "--resolution-scale", "100",
                       "--fps-cap", "260", "--workers", "0", "--frame-pacing", "efficient",
                       "--warmup", "15", "--seconds", "20", "--flight"]
            completed = subprocess.run(command, cwd=ROOT, env=env)
            entry["exit_code"] = completed.returncode
            entry["swap_after"] = swap()
            entry["swap_delta_M"] = float(entry["swap_after"].split("used = ")[1].split("M")[0]) - float(gate["swap"].split("used = ")[1].split("M")[0])
            console = profile / "console.log"
            if console.is_file() and TAINT.search(console.read_text(errors="replace")):
                entry["tainted"] = True
            require(completed.returncode == 0, "Harness failed; inspect raw result and console log")
            result = read_json(profile / "result.json")
            require(result.get("native_version") == versions[role] and
                    result.get("native_executable_sha256") == binary_hashes[role], "Runtime native identity mismatch")
            entry.update(REVIEW.review_result(result, profile, selection, manifest_hash,
                                              shader if case == "makeup" else None, 260, "settled"))
            if case == "makeup":
                require(REVIEW.shader_hashes(profile / "shaderpacks", shader) == shader_hashes and
                        REVIEW.shader_hashes(REVIEW.SOURCE_SHADERS, shader) == shader_hashes,
                        "Shader archive or sidecar changed")
            for key in ("system_before", "system_after", "front_error", "front_error_bench", "window_before_bench",
                        "window_after_bench", "flight_attempts", "flight_settle_seconds",
                        "flight_full_settle_seconds", "startup_to_full_scene_seconds"):
                entry[key] = result.get(key)
            entry["flight_endpoint"] = {key: result["after_flight"][key] for key in
                                        ("chunks", "pending_chunks", "pending_uploads", "streaming", "renderer")}
            entry["valid"] = not entry["tainted"]
            if entry["tainted"]:
                entry["error"] = "tainted: 'input from a person' in console log"
        except (KeyError, OSError, ValueError, subprocess.SubprocessError) as error:
            entry["error"] = str(error)
        return entry

    for index, (case, role) in enumerate(matrix, 1):
        for attempt in range(1, args.retry_tainted + 2):
            entry = run_once(index, case, role, attempt)
            summary["results"].append(entry)
            save()
            print(json.dumps({"index": index, "case": case, "role": role, "attempt": attempt, "valid": entry["valid"],
                              "tainted": entry["tainted"], "error": entry.get("error"), "summary": str(summary_path)}),
                  flush=True)
            if entry["valid"] or entry.get("gate_failed") or not entry["tainted"]:
                break
        if not entry["valid"]:
            summary["aborted"] = entry.get("error")
            save()
            return 1
    summary["complete"] = True
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
