#!/usr/bin/env python3
"""Build Horizon nightly 6475f62 (nightly-2026-11-04) as separate version dirs, plain and with our native ports.

WRITTEN 2026-11-06, NOT EXECUTED. Mirrors build-m1-performance-r3.py (cargo --offline --locked --profile fast, jobs=1,
isolated Rust 1.99.1, disk reserve, device-queue friendly preflights) but:
  * source is the published horizon-source.tar.gz of 6475f62 (LAB/src-pristine, sha256-checked), not native/stage;
  * our f42 source patch set (r2/r3: cloud-prep ... anim-frame-compact) is NOT applied: 11 of 12 transforms fail their
    f42 anchors/SHA guards on 6475f62 (see docs/horizon-converter/nightly-6475f62-prep-2026-11-06.md);
  * native ports (zoom, cem_alias_f42 repinned) are injected with the installed horizon-mixins e8cd0aa38cff tool;
  * two installs: native-nightly-6475f62-plain-<id> (control) and native-nightly-6475f62-ports-<id>.

Subcommands:
  stage-base  download + digest-check the official nightly-2026-11-04 macOS zip, stage it as versions/nightly-2026-11-04-6475f62
              (no execution of downloaded code except the --help smoke like install-f42.py). Then PREPARE it (queue item):
              launch-isolated.command prepare --version nightly-2026-11-04-6475f62
  fetch       network: cargo fetch --locked for aarch64-apple-darwin only (needs crate mio-1.2.4, absent from the offline cache)
  build       (default) compile plain, install, apply ports, recompile (same path, incremental), install
Env: NIGHTLY_VARIANTS=plain,ports (default both).
"""
import hashlib
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
LAB = RUNTIME / "nightly-6475f62"
REVISION = "6475f62f3c834b7489e1816bf47f47ea5eb2b879"
TARBALL = LAB / "dl/horizon-source.tar.gz"
TARBALL_SHA = "cc15165a0b0e9751924e281f63a0e379e6fe54c6d42c8fe33468c4c0776c7058"
CEM_SHA = "4c7f8650070be17789d500aa86dd013fed9ddbcd0dc754d953f0208acb442cd8"   # cem_alias guard; identical at f42 and 6475f62
PRISTINE = LAB / "src-pristine"
MODS = LAB / "mods-flat"        # cem_alias_f42 (pin -> 6475f62) + zoom (pin -> 6475f62, as the launcher repins hooks-only bundles)
BUILD = LAB / "build-src"       # one fixed path for both compiles so the second is incremental
STAGE = LAB / "stage-ports"
STATUS = LAB / "build-status.json"
BASE_TAG = "nightly-2026-11-04-6475f62"
BASE = DATA / "versions" / BASE_TAG
BASE_ASSET, BASE_ZIP_SHA, BASE_ZIP_SIZE = 710139293, "62f00acd1466e4253a494d64b0fd0e0ce81f17e1520347f86d9086c92dfed6f9", 38793391
MIXINS = DATA / "native/tools/e8cd0aa38cff/bin/horizon-mixins"
TOOLCHAIN = DATA / "rust/1.99.1-aarch64-apple-darwin"
CARGO_TARGET = DATA / "native/target"
VARIANTS = os.environ.get("NIGHTLY_VARIANTS", "plain,ports").split(",")
cancelled = None


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()}


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


def cargo_env():
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("CARGO_BUILD_") and key not in {
               "RUSTFLAGS", "RUSTDOCFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_ENCODED_RUSTDOCFLAGS",
               "CARGO_INCREMENTAL", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "RUSTUP_TOOLCHAIN"}}
    env.update(PATH=str(TOOLCHAIN / "bin") + os.pathsep + env["PATH"], RUSTC=str(TOOLCHAIN / "bin/rustc"),
               CARGO_HOME=str(DATA / "cargo"), CARGO_TARGET_DIR=str(CARGO_TARGET), CARGO_BUILD_JOBS="1")
    return env


def compile_client(command, env, record, role):
    if cancelled:
        raise SystemExit(128 + cancelled)
    started = time.monotonic()
    record["phase"] = role
    with (LAB / f"cargo-{role}.log").open("w") as log:
        process = subprocess.Popen(command, cwd="/", env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
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


def preflight(need_gib):
    for name in ("horizon-client", "java", "cargo", "rustc"):
        result = subprocess.run(["pgrep", "-x", name], capture_output=True, timeout=10)
        if result.returncode != 1:
            raise SystemExit(f"Build preflight failed for {name} ({result.returncode})")
    if shutil.disk_usage(RUNTIME).free < need_gib * 2**30:
        raise SystemExit(f"Need at least {need_gib} GiB available")
    if not live_group(os.getpgrp()):
        raise SystemExit("Process observer cannot see the build supervisor")


def verify_tarball():
    if digest(TARBALL) != TARBALL_SHA:
        raise SystemExit("horizon-source.tar.gz digest changed")
    if (PRISTINE / "crates/horizon-client/src/mobs/cem.rs").exists() is False or \
            digest(PRISTINE / "crates/horizon-client/src/mobs/cem.rs") != CEM_SHA:
        raise SystemExit("src-pristine cem.rs differs from reviewed 6475f62 bytes")
    if (PRISTINE / ".horizon-revision").exists():
        raise SystemExit("src-pristine must stay pristine (no .horizon-revision)")


def stage_base():
    if BASE.exists():
        raise SystemExit("Base nightly already staged")
    archive = LAB / "dl/horizon-macos-arm64-6475f62.zip"
    if not archive.exists():
        with archive.open("xb") as output:
            subprocess.run(["gh", "api", f"repos/horizon-rust/horizon/releases/assets/{BASE_ASSET}",
                            "-H", "Accept: application/octet-stream"], stdout=output, check=True)
    actual = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
    if actual != BASE_ZIP_SHA or archive.stat().st_size != BASE_ZIP_SIZE:
        raise SystemExit("Publisher size/digest verification failed; no extraction or execution")
    import importlib.util
    spec = importlib.util.spec_from_file_location("prepare_horizon", ROOT / "tools/prepare-horizon.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.extract_archive(archive, BASE)
    payload = BASE / "horizon-macos-arm64"
    for item in list(payload.iterdir()):
        item.rename(BASE / item.name)
    payload.rmdir()
    architecture = subprocess.check_output(["/usr/bin/file", "-b", str(BASE / "horizon-client")], text=True).strip()
    if "Mach-O" not in architecture or "arm64" not in architecture:
        raise SystemExit("Unexpected executable architecture")
    record = {"status": "staged-not-prepared", "runtime_release": "nightly-2026-11-04", "runtime_revision": REVISION,
              "asset_id": BASE_ASSET, "asset_sha256": actual, "asset_size": BASE_ZIP_SIZE, "architecture": architecture}
    (BASE / "runtime-record.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"event": "base-staged", "release": str(BASE)}), flush=True)
    print("Next (queue): launch-isolated.command prepare --version " + BASE_TAG, flush=True)


def fetch():
    """Only crate missing offline is mio-1.2.4 (new in 6475f62 Cargo.lock). Fetch for the macOS target only."""
    command = [str(TOOLCHAIN / "bin/cargo"), "fetch", "--locked", "--target", "aarch64-apple-darwin",
               "--manifest-path", str(PRISTINE / "Cargo.toml")]
    subprocess.run(command, cwd="/", env=cargo_env(), check=True)


def clone_clean(destination):
    subprocess.run(["/bin/cp", "-cR", str(PRISTINE), str(destination)], check=True)
    for link in [p for p in destination.rglob("*") if p.is_symlink()]:   # CLAUDE.md -> AGENTS.md; mixins refuse symlinks
        link.unlink()
    (destination / ".horizon-revision").write_text(REVISION)


def install(variant, destination, metadata, provenance):
    if destination.exists():
        raise SystemExit("Installation already exists")
    installation = destination.with_name(destination.name + ".new")
    subprocess.run(["/bin/cp", "-cR", str(BASE), str(installation)], check=True)   # APFS clone: .local costs no space
    shutil.copy2(CARGO_TARGET / "fast/horizon-client", installation / "horizon-client")
    binary_hash = digest(installation / "horizon-client")
    (installation / "native-mods.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (installation / "source-patches.json").write_text(json.dumps({**provenance, "binary_sha256": binary_hash}, indent=2) + "\n")
    (installation / ".installed").touch()
    os.rename(installation, destination)
    return binary_hash


def build():
    preflight(5)
    if LAB.joinpath("build-src").exists() or STATUS.exists():
        raise SystemExit("Nightly build workspace already exists")
    verify_tarball()
    if not (BASE / ".local").is_dir() or not (BASE / "horizon-ctl").exists():
        raise SystemExit(f"Base {BASE_TAG} must be staged and prepared first (stage-base, then launcher prepare)")
    if not any((DATA / "cargo/registry/cache").glob("*/mio-1.2.4.crate")):
        raise SystemExit("mio-1.2.4.crate missing from the offline cache: run `fetch` first")
    pristine_inventory = inventory(PRISTINE)
    clone_clean(BUILD)
    mods_digest = hashlib.sha256(json.dumps(inventory(MODS), sort_keys=True).encode()).hexdigest()
    command = [str(TOOLCHAIN / "bin/cargo"), "build", "--offline", "--locked", "--profile", "fast",
               "--manifest-path", str(BUILD / "Cargo.toml"), "-p", "horizon-client", "--bin", "horizon-client"]
    env = cargo_env()
    record = {"complete": False, "source_revision": REVISION, "tarball_sha256": TARBALL_SHA, "command": command,
              "profile": "fast", "rust": "1.99.1", "base": BASE_TAG, "mods_digest": mods_digest, "variants": VARIANTS,
              "installed": {}, "samples": []}
    save(record)
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, cancellation)
    base_metadata = {"base": BASE_TAG, "horizon": REVISION, "horizon_mixins": "e8cd0aa38cffef49cb2e088ef716baa107148c02",
                     "hooks": 359, "rust": "1.99.1", "profile": "performance", "target": "client"}
    if "plain" in VARIANTS:
        compile_client(command, env, record, "plain")
        plain_id = hashlib.sha256(json.dumps(inventory(BUILD), sort_keys=True).encode()).hexdigest()[:12]
        version = f"native-nightly-6475f62-plain-{plain_id}"
        metadata = {**base_metadata, "mods": [], "build_method": "direct-cargo-plain-nightly"}
        record["installed"]["plain"] = {"version": version, "binary_sha256": install(
            "plain", DATA / "versions" / version, metadata, {**record, "complete": True})}
        save(record)
    if "ports" in VARIANTS:
        preflight(5)
        mixin_env = {**env, "PATH": env["PATH"]}
        if STAGE.exists():
            raise SystemExit("stage-ports already exists")
        result = subprocess.run([str(MIXINS), "apply", "--workspace", str(PRISTINE_WITH_REV()), "--mods", str(MODS), "--out", str(STAGE)],
                                cwd="/", env=mixin_env, capture_output=True, text=True, timeout=600)
        summary = json.loads(result.stdout or "{}")
        if result.returncode or summary.get("status") != "ok" or summary.get("injections") != 7:
            raise SystemExit(f"horizon-mixins apply failed or unexpected plan: {result.stdout} {result.stderr}")
        staged = inventory(STAGE)
        for relative, value in staged.items():            # rewrite only changed files so the compile stays incremental
            target = BUILD / relative
            if not target.exists() or digest(target) != value:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(STAGE / relative, target)
        if inventory(BUILD) != staged:
            raise SystemExit("Build source does not match the staged ports source")
        compile_client(command, env, record, "ports")
        ports_id = hashlib.sha256(json.dumps(staged, sort_keys=True).encode()).hexdigest()[:12]
        version = f"native-nightly-6475f62-ports-{ports_id}"
        metadata = {**base_metadata, "build_method": "direct-cargo-mixins-ports", "mods_digest": mods_digest,
                    "mods": [{"id": "cem_alias_f42", "version": "0.1.0"}, {"id": "zoom", "version": "2.0.0"}]}
        record["installed"]["ports"] = {"version": version, "binary_sha256": install(
            "ports", DATA / "versions" / version, metadata, {**record, "complete": True})}
    if inventory(PRISTINE) != pristine_inventory:
        raise SystemExit("src-pristine changed during build")
    record["complete"] = True
    save(record)
    print(json.dumps({"installed": record["installed"], "complete": True}), flush=True)


def PRISTINE_WITH_REV():
    """horizon-mixins needs .horizon-revision and no symlinks; use a throwaway clean clone, never the pristine tree."""
    clean = LAB / "src-clean-for-mixins"
    if not clean.exists():
        clone_clean(clean)
    return clean


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "build"
    {"build": build, "fetch": fetch, "stage-base": stage_base}[action]()
