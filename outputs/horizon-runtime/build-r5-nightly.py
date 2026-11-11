#!/usr/bin/env python3
"""Build the reviewed r5 patch stack on nightly 66f3981; never selects a version.

Queue only: env HORIZON_TEST_QUEUE=1 <python> build-r5-nightly.py
--dry-run clones/applies/verifies source only: no Cargo or installation. No downloads.
The trial contains the performance stack, not f42's zoom/CEM or seven optional mods.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parents[1]
DATA = RUNTIME / "launcher-data"
PATCHES = ROOT / "outputs/horizon-native"
SOURCE = ROOT / "outputs/horizon-src-nightly/nightly-2026-11-05-66f3981"
BASE_TAG = "nightly-2026-11-05-66f3981"
BASE = DATA / "versions" / BASE_TAG
REVISION = "66f3981f522b24c250b21523a70080965b940424"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("HORIZON_TEST_QUEUE"):
        raise SystemExit("Refusing to run outside the device queue: set HORIZON_TEST_QUEUE")
    revision = run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], capture_output=True).stdout.strip()
    dirty = run(["git", "-C", str(SOURCE), "status", "--porcelain"], capture_output=True).stdout
    if revision != REVISION or dirty:
        raise SystemExit("Pristine nightly source identity changed or working tree is dirty")
    if shutil.disk_usage(RUNTIME).free < 5 * 2**30:
        raise SystemExit("Need at least 5 GiB available")
    if not args.dry_run:
        gates = load("r5_gates", RUNTIME / "run-u9c-makeup-trim.py")
        problems = gates.gate_problems(check_idle=False)
        if problems:
            raise SystemExit("Build gates failed: " + "; ".join(problems))
    names = [line.split("#", 1)[0].strip() for line in (PATCHES / "r5-stack.txt").read_text().splitlines()]
    names = [name for name in names if name]
    if len(names) != 13 or len(set(names)) != len(names):
        raise SystemExit("Expected thirteen unique r5 patches (four original patches are upstream-covered)")
    paths = [PATCHES / f"{name}-66f3981" / f"{name}.patch" for name in names]
    for path in paths:
        if not path.is_file():
            raise SystemExit(f"Missing patch: {path}")
    if not (BASE / ".local/horizon-client/26.3").is_dir() or not (BASE / "horizon-ctl").is_file():
        raise SystemExit("The matching nightly resources/control tool must be installed and prepared first")
    lab = RUNTIME / "m1-performance-r5" / time.strftime("%Y%m%d-%H%M%S")
    lab.mkdir(parents=True, exist_ok=False)
    # Keep a checkpoint and fully refresh the build workspace each time.
    work = RUNTIME / "m1-performance-r5/candidate-source"
    if work.exists():
        run(["/bin/cp", "-cR", str(work), str(lab / "previous-source")])
    run(["rsync", "-a", "--delete", "--exclude=.git", "--exclude=.local", "--exclude=target",
         "--exclude=.horizon-mixins-stage.json", str(SOURCE) + "/", str(work) + "/"])
    patch_hashes = {}
    for name, path in zip(names, paths):
        run(["git", "apply", "--check", str(path)], cwd=work)
        run(["git", "apply", "--whitespace=nowarn", str(path)], cwd=work)
        patch_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"r5 patch {name}: OK", flush=True)
    # The target directory is shared with other source revisions. Cargo's
    # workspace-relative depfiles can reuse their artifacts when rsync imports
    # older mtimes, even though the source content differs. Invalidate every
    # local input; registry dependency artifacts remain available for reuse.
    for path in work.rglob("*"):
        if path.is_file() and not path.is_symlink():
            path.touch()
    run(["/bin/cp", "-cR", str(work), str(lab / "source")])
    # Reuse the existing build supervisor: process-group cleanup, disk reserve,
    # deadline, clean Rust environment and the pinned 1.99.1 toolchain.
    build = load("r5_build_helpers", RUNTIME / "build-nightly-6475f62.py")
    build.LAB = lab
    build.STATUS = lab / "build-status.json"
    files = build.inventory(work)
    identity = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    version = f"native-66f3981-m1-r5-{identity[:12]}"
    destination = DATA / "versions" / version
    if destination.exists():
        raise SystemExit(f"Version already exists: {version}")
    command = [str(build.TOOLCHAIN / "bin/cargo"), "build", "--offline", "--locked", "--profile", "fast",
               "--manifest-path", str(work / "Cargo.toml"), "-p", "horizon-client", "--bin", "horizon-client"]
    record = {"complete": False, "runtime_verified": False, "source_revision": REVISION,
              "base_version": BASE_TAG, "candidate_version": version, "source_digest": identity,
              "workspace": str(work), "source_snapshot": str(lab / "source"),
              "patches": patch_hashes, "upstream_covered": ["qos-backport", "sprite-compress", "colortex-lazy-b", "a66f8fa2"],
              "mods": [], "profile": "fast", "rust": "1.99.1", "command": command, "samples": []}
    build.save(record)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "version": version, "workspace": str(work), "patches": len(names)}))
        return
    build.preflight(5)
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, build.cancellation)
    build_env = build.cargo_env()
    build_env["DYLD_FALLBACK_LIBRARY_PATH"] = str(build.TOOLCHAIN / "lib")
    build.compile_client(command, build_env, record, "r5")
    if build.inventory(work) != files:
        raise SystemExit("Source changed during compilation; refusing installation")
    if destination.exists():
        raise SystemExit(f"Version already exists: {version}")
    installation = destination.with_name(destination.name + ".new")
    if installation.exists():
        raise SystemExit(f"Staging destination already exists: {installation}")
    run(["/bin/cp", "-cR", str(BASE), str(installation)])
    shutil.copy2(build.CARGO_TARGET / "fast/horizon-client", installation / "horizon-client")
    record.update(complete=True, binary_sha256=build.digest(installation / "horizon-client"))
    metadata = {"base": BASE_TAG, "horizon": REVISION, "target": "client", "rust": "1.99.1",
                "profile": "performance", "mods": [],
                "build_method": "direct-cargo-source-patches", "source_patch_digest": identity}
    (installation / "native-mods.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (installation / "source-patches.json").write_text(json.dumps(record, indent=2) + "\n")
    (installation / ".installed").touch()
    os.rename(installation, destination)
    build.save(record)
    print(json.dumps({"installed": str(destination), "selected": False}), flush=True)


if __name__ == "__main__":
    main()
