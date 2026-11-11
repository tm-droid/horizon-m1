#!/usr/bin/env python3
"""Build the r3 performance candidate (r2 transforms + particle-cull, adaptive-upload, pbr-cpu-drop, anim-frame-compact) from an immutable source copy.

Copy of build-m1-performance-r2.py (2026-11-06). Set R3_SKIP=<name,..> to leave named r3 transforms out (fallback if one fails to compile).

Differs from build-m1-performance.py only in: separate lab dir (m1-performance-r3), extra source transforms
(PERF_MODS), a derived expected-file set, and reuse of an already built control installation.
Set R2_WITH_SPRITE=1 to also chain sprite-compress-f42 (does not apply to the current stage game.rs, see
docs/horizon-converter/u6-patches-2026-11-05.md).
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parents[1]
DATA = RUNTIME / "launcher-data"
LAB = RUNTIME / "m1-performance-r3"
# Applied in this order after cloud-prep and shadow-scratch. sprite-compress must precede the u6 patches
# (it requires pristine assets.rs).
PERF_MODS = ["qos-backport-f42", "jobpool-qos-f42", "sprite-compress-f42",
             "emissive-bsearch-f42", "pass-merge-f42", "shadow-dedup-f42"]
R3_MODS = ["particle-cull-f42", "adaptive-upload-f42", "pbr-cpu-drop-f42", "anim-frame-compact-f42"]
PERF_MODS += [name for name in R3_MODS if name not in os.environ.get("R3_SKIP", "").split(",")]
# sprite-compress must precede emissive-bsearch (it requires pristine assets.rs); jobpool-qos follows qos-backport (shared lib.rs).
REVISION = "f42ef42ef6ceccb3c6a20bea2481d87949a51c81"
CONTROL = DATA / "versions/native-f42ef42-898af830522b"
SOURCE = DATA / "native/stage"
WORKSPACE = LAB / "candidate-source"
STATUS = LAB / "build-status.json"
cancelled = None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(record):
    temporary = STATUS.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n")
    os.replace(temporary, STATUS)


def cancellation(signum, _frame):
    global cancelled
    if cancelled is None:
        cancelled = signum


def exited(pid):
    return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None


def live_group(pgid):
    listing = subprocess.check_output(["/bin/ps", "-ax", "-o", "pgid=,stat="], text=True, timeout=10)
    return any(int(group) == pgid and not state.startswith("Z")
               for group, state in (line.split() for line in listing.splitlines()))


def cleanup(process):
    deadline = None
    while True:
        try:
            if exited(process.pid) and not live_group(process.pid):
                process.wait()
                return
            if deadline is None:
                os.killpg(process.pid, signal.SIGTERM)
                deadline = time.monotonic() + 20
            elif time.monotonic() >= deadline:
                os.killpg(process.pid, signal.SIGKILL)
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            try:
                print(f"Retaining device lease until owned build group is clear: {error}", flush=True)
            except OSError:
                pass
        time.sleep(1)


def compile_client(command, env, record, role):
    if cancelled:
        raise SystemExit(128 + cancelled)
    started = time.monotonic()
    record["phase"] = role
    with (LAB / f"cargo-{role}.log").open("w") as log:
        process = subprocess.Popen(command, cwd="/", env=env, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            record["pid"] = process.pid
            record["cleanup_verified"] = False
            while not exited(process.pid):
                free = shutil.disk_usage(RUNTIME).free
                elapsed = time.monotonic() - started
                record["samples"].append({"phase": role, "seconds": round(elapsed, 1), "free_bytes": free})
                if free < 4 * 2**30 or elapsed > 2700 or cancelled:
                    record["error"] = f"Build stopped at reserve, deadline or cancellation ({free}, {elapsed:.1f}, {cancelled})"
                save(record)
                if record.get("error"):
                    break
                for _ in range(20):
                    if cancelled or exited(process.pid):
                        break
                    time.sleep(1)
        except Exception as error:
            record["error"] = f"Monitoring failed: {type(error).__name__}: {error}"
        finally:
            cleanup(process)
            record["exit_code"] = process.returncode
            record["cleanup_verified"] = True
            record[f"{role}_build_seconds"] = time.monotonic() - started
            if cancelled:
                record["error"] = f"Cancelled by signal {cancelled}"
            save(record)
    if record.get("error") or process.returncode:
        raise SystemExit(f"{role} compile failed, see build-status.json and cargo-{role}.log")


def install_client(destination, metadata, provenance):
    if destination.exists():
        raise SystemExit("Source build installation already exists")
    installation = destination.with_name(destination.name + ".new")
    installation.mkdir()
    shutil.copy2(DATA / "native/target/fast/horizon-client", installation / "horizon-client")
    shutil.copy2(CONTROL / "horizon-ctl", installation / "horizon-ctl")
    subprocess.run(["/bin/cp", "-cR", str(CONTROL / ".local"), str(installation / ".local")], check=True)
    binary_hash = digest(installation / "horizon-client")
    provenance = {**provenance, "binary_sha256": binary_hash}
    (installation / "native-mods.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (installation / "source-patches.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (installation / ".installed").touch()
    os.rename(installation, destination)
    return binary_hash


def main():
    for name in ("horizon-client", "java", "cargo", "rustc"):
        result = subprocess.run(["pgrep", "-x", name], capture_output=True, timeout=10)
        if result.returncode != 1:
            raise SystemExit(f"Build preflight failed for {name} ({result.returncode})")
    if shutil.disk_usage(RUNTIME).free < 5 * 2**30:
        raise SystemExit("Need at least 5 GiB available for the cached performance build")
    if WORKSPACE.exists() or STATUS.exists():
        raise SystemExit("Performance build workspace already exists")
    if not live_group(os.getpgrp()):
        raise SystemExit("Process observer cannot see the build supervisor")
    probe = subprocess.Popen(["/usr/bin/true"])
    try:
        deadline = time.monotonic() + 5
        while not exited(probe.pid):
            if time.monotonic() > deadline:
                raise RuntimeError("Non-reaping process observer failed its preflight")
            time.sleep(0.05)
    finally:
        probe.wait(timeout=5)
    if (SOURCE / ".horizon-revision").read_text().strip() != REVISION:
        raise SystemExit("The injected source is not f42")
    control_metadata = json.loads((CONTROL / "native-mods.json").read_text())
    if (control_metadata["horizon"] != REVISION or control_metadata["profile"] != "performance" or
            digest(CONTROL / "horizon-client") != "d96a7246310077b4794892e381da75a10902059cf7ec10b7d92a1fde37ebd069"):
        raise SystemExit("Control build identity changed")
    patch_root = ROOT / "outputs/horizon-native"
    spec = importlib.util.spec_from_file_location("cloud_patch", patch_root / "cloud-prep-f42/prepare.py")
    cloud = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cloud)
    baseline = cloud.inventory(SOURCE)
    LAB.mkdir(exist_ok=True)
    subprocess.run(["/bin/cp", "-cR", str(SOURCE), str(WORKSPACE)], check=True)
    if cloud.inventory(WORKSPACE) != baseline or cloud.inventory(SOURCE) != baseline:
        raise SystemExit("Source copy did not preserve all bytes")
    transforms = {relative: cloud.render(relative, (WORKSPACE / relative).read_bytes())
                  for relative in cloud.SPEC["files"]}
    spec = importlib.util.spec_from_file_location("shadow_patch", patch_root / "shadow-scratch-f42/prepare.py")
    shadow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shadow)
    target = "crates/horizon-client-render/src/gfx.rs"
    transforms[target], _ = shadow.transform(transforms[target])
    mod_files = set()
    for name in PERF_MODS:
        spec = importlib.util.spec_from_file_location(name.replace("-", "_"), patch_root / name / "prepare.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if getattr(mod, "REVISION", REVISION) != REVISION or mod.NEW_FILES:
            raise SystemExit(f"{name}: unexpected revision or new files")
        for relative in mod.FILES:
            transforms[relative] = mod.render(relative, transforms.get(relative) or (WORKSPACE / relative).read_bytes())
            mod_files.add(relative)
    patched = {**baseline, **{relative: hashlib.sha256(data).hexdigest()
                            for relative, data in transforms.items()}}
    differences = {name: {"before": baseline[name], "after": value}
                   for name, value in patched.items() if value != baseline.get(name)}
    expected = {"crates/horizon-client-render/src/gfx.rs",
                "crates/horizon-client-render/src/gfx/pack_post.rs"} | mod_files
    if set(differences) != expected or set(patched) != set(baseline):
        raise SystemExit("Unexpected transformed source files")
    identity = hashlib.sha256(json.dumps(patched, sort_keys=True).encode()).hexdigest()
    control_identity = hashlib.sha256(json.dumps(baseline, sort_keys=True).encode()).hexdigest()
    built_control_version = f"native-f42-m1-control-{control_identity[:12]}"
    version = f"native-f42-m1-r3-{identity[:12]}"
    destination = DATA / "versions" / version
    if destination.exists():
        raise SystemExit("Candidate installation already exists")
    toolchain = DATA / "rust/1.99.1-aarch64-apple-darwin"
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("CARGO_BUILD_") and key not in {
               "RUSTFLAGS", "RUSTDOCFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_ENCODED_RUSTDOCFLAGS",
               "CARGO_INCREMENTAL", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "RUSTUP_TOOLCHAIN"}}
    env.update(PATH=str(toolchain / "bin") + os.pathsep + env["PATH"],
               RUSTC=str(toolchain / "bin/rustc"), CARGO_HOME=str(DATA / "cargo"),
               CARGO_TARGET_DIR=str(DATA / "native/target"), CARGO_BUILD_JOBS="1")
    command = [str(toolchain / "bin/cargo"), "build", "--offline", "--locked", "--profile", "fast",
               "--manifest-path", str(WORKSPACE / "Cargo.toml"), "-p", "horizon-client", "--bin", "horizon-client"]
    record = {"complete": False, "runtime_verified": False, "source_revision": REVISION,
              "control": str(CONTROL), "control_metadata": control_metadata,
              "source_files": baseline, "candidate_files": patched, "changed_files": differences,
              "candidate_source_digest": identity, "candidate_version": version, "command": command,
              "control_source_digest": control_identity, "built_control_version": built_control_version,
              "profile": "fast", "rust": "1.99.1", "samples": []}
    save(record)
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, cancellation)
    control_done = (DATA / "versions" / built_control_version).exists()  # r1 already built this exact control
    if not control_done:
        compile_client(command, env, record, "control")
    if cloud.inventory(WORKSPACE) != baseline or cloud.inventory(SOURCE) != baseline:
        raise SystemExit("Control source changed during compilation")
    control_provenance = {
        "complete": True, "build_method": "direct-cargo-control", "source_revision": REVISION,
        "source_patch_digest": control_identity, "source_files": baseline,
        "control_seed_version": CONTROL.name, "command": command, "profile": "fast", "rust": "1.99.1"}
    control_install_metadata = {**control_metadata, "build_method": "direct-cargo-control",
                               "source_patch_digest": control_identity, "control_seed_version": CONTROL.name}
    if not control_done:
        record["built_control_sha256"] = install_client(
            DATA / "versions" / built_control_version, control_install_metadata, control_provenance)
    save(record)
    if shutil.disk_usage(RUNTIME).free < 5 * 2**30:
        raise SystemExit("Less than 5 GiB available before the cached candidate rebuild")
    for relative, data in transforms.items():
        (WORKSPACE / relative).write_bytes(data)
    if cloud.inventory(WORKSPACE) != patched:
        raise SystemExit("Candidate transform differs from reviewed bytes")
    compile_client(command, env, record, "candidate")
    if cloud.inventory(WORKSPACE) != patched or cloud.inventory(SOURCE) != baseline:
        raise SystemExit("Source changed during compilation")
    metadata = {**control_metadata, "build_method": "direct-cargo-source-patches",
                "source_patch_digest": identity, "control_version": built_control_version}
    record["binary_sha256"] = digest(DATA / "native/target/fast/horizon-client")
    install_client(destination, metadata, {**record, "complete": True})
    record["complete"] = True
    save(record)
    print(json.dumps({"candidate_version": version, "binary_sha256": record["binary_sha256"], "complete": True}), flush=True)


if __name__ == "__main__":
    main()
