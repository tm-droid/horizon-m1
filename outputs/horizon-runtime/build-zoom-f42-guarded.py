#!/usr/bin/env python3
"""One isolated native build with a free-space reserve; invoke under shared queue."""
from pathlib import Path
import argparse, hashlib, json, os, signal, shutil, subprocess, time
root = Path(__file__).resolve().parents[2]
os.chdir(root)
runtime = root / "outputs/horizon-runtime"
parser=argparse.ArgumentParser()
parser.add_argument("--candidate",type=Path,default=root/"outputs/horizon-native/zoom-f42-candidate")
candidate=parser.parse_args().candidate.resolve()
plan = json.loads((candidate / "build-plan.json").read_text())
provenance = json.loads((candidate / "provenance.json").read_text())
status_path = runtime / "zoom-build-status-2026-11-04.json"
log_path = runtime / "zoom-native-build-2026-11-04.log"
status = {"argv": plan["argv"], "profile": "performance", "environment": {"CARGO_BUILD_JOBS":"1"},
          "desired_engine_revision":plan["desired_engine_revision"], "runtime_verified":False,
          "minimum_free_bytes":4*2**30, "samples":[], "complete":False}
def save():
    status_path.write_text(json.dumps(status, indent=2)+"\n")
for name in ("horizon-client", "java"):
    check = subprocess.run(["pgrep", "-x", name], capture_output=True, text=True, timeout=10)
    if check.returncode != 1:
        raise SystemExit(f"Refusing build: {name} check returned {check.returncode}")
for item in provenance["source_files"]:
    actual=hashlib.sha256((candidate/item["candidate"]).read_bytes()).hexdigest()
    if actual != item["sha256"]:
        raise SystemExit("Reviewed source digest changed: "+item["candidate"])
if hashlib.sha256((candidate/"bundle/horizon-native.json").read_bytes()).hexdigest() != provenance["candidate_manifest_sha256"]:
    raise SystemExit("Reviewed bundle manifest changed")
for path, expected in plan.get("additional_reviewed_inputs", {}).items():
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
        raise SystemExit("Additional reviewed input changed: "+path)
free=shutil.disk_usage(runtime).free
status["initial_free_bytes"]=free
cached_toolchain=(runtime/"launcher-data/rust/1.99.1-aarch64-apple-darwin/bin/rustc").is_file()
cached_source=(runtime/"launcher-data/native/source"/plan["desired_engine_revision"] / "Cargo.lock").is_file()
status["toolchain_and_source_cached"]=cached_toolchain and cached_source
status["minimum_start_bytes"]=(5 if status["toolchain_and_source_cached"] else 8)*2**30
if free < status["minimum_start_bytes"]:
    status["error"]="Insufficient initial space for cached/cold build; not started";save();raise SystemExit(2)
# Match the official installer's completion registration for the verified,
# manually extracted publisher release. Preparation is a separate condition.
release=runtime/"launcher-data/versions/nightly-2026-11-03-f42ef42"
archive=runtime/"downloads/horizon-macos-arm64-f42ef42.zip"
if hashlib.sha256(archive.read_bytes()).hexdigest() != "58432a760b6af8195a543b520daea89be9396a76633753db61eae3553b762593":
    raise SystemExit("Publisher archive hash mismatch")
if not (release/"horizon-client").is_file() or not (release/".local/horizon-client/26.3/horizon-resources.json").is_file():
    raise SystemExit("Verified runtime payload/preparation missing")
(release/".installed").touch(exist_ok=True)
status["publisher_release_registered"]=True
env=os.environ.copy();env.update(plan["environment"])
cancel_signal = None


def request_cancel(signum, _frame):
    global cancel_signal
    if cancel_signal is None:
        cancel_signal = signum


def build_exited(pid):
    # Keep the session leader's PID reserved until the last group check.
    # Popen.poll() and wait() would reap it and permit PID/PGID reuse.
    return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None


def group_has_live_processes(pgid):
    listing = subprocess.run(
        ["/bin/ps", "-ax", "-o", "pgid=,stat="],
        capture_output=True, text=True, timeout=10, check=True,
    )
    return any(
        int(group) == pgid and not state.startswith("Z")
        for group, state in (line.split() for line in listing.stdout.splitlines())
    )


def clean_build_group(process):
    pgid = process.pid
    # The queue holds its lease while this supervisor is alive. If the group
    # cannot be inspected or signaled, keep checking until it is proven clear.
    last_warning = None
    term_deadline = None
    while True:
        try:
            if build_exited(pgid) and not group_has_live_processes(pgid):
                process.wait()
                return
            if term_deadline is None:
                term_deadline = time.monotonic() + 20
                os.killpg(pgid, signal.SIGTERM)
            elif time.monotonic() >= term_deadline:
                os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            warning = f"Retaining queue while build group {pgid} is unverified: {error}"
            if warning != last_warning:
                try:
                    print(warning, flush=True)
                except OSError:
                    pass
                last_warning = warning
        time.sleep(1)


for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
    signal.signal(signum, request_cancel)

try:
    if not all(hasattr(os, name) for name in ("waitid", "P_PID", "WEXITED", "WNOHANG", "WNOWAIT")):
        raise RuntimeError("waitid without reaping is unavailable")
    if not group_has_live_processes(os.getpgrp()):
        raise RuntimeError("process listing did not include the supervisor's group")
except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as error:
    status["error"] = f"Build process observer unavailable: {error}"
    save()
    raise SystemExit(2)

with log_path.open("w") as log:
    if (runtime/"game/instances/horizon-zoom-pilot/options.txt").is_file():
        status["instance_reused"]=True
    else:
        created=subprocess.run(plan["instance_create_argv_if_absent"], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60)
        status["instance_create_exit_code"]=created.returncode
        if created.returncode:
            status["error"]="Isolated pilot instance creation failed";save();raise SystemExit(2)
    if cancel_signal is not None:
        status["error"] = f"Cancelled by {signal.Signals(cancel_signal).name} before native build"
        save()
        raise SystemExit(128 + cancel_signal)
    started=time.monotonic()
    process=subprocess.Popen(plan["argv"], env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        status["pid"]=process.pid;save()
        while not build_exited(process.pid):
            free=shutil.disk_usage(runtime).free
            elapsed=time.monotonic()-started
            status["samples"].append({"seconds":round(elapsed,1),"free_bytes":free})
            if free < status["minimum_free_bytes"]:
                status["error"] = f"Owned build stopped at disk reserve ({free} free bytes)"
            elif elapsed > 2700:
                status["error"] = "Owned build stopped at 45-minute limit"
            elif cancel_signal is not None:
                status["error"] = f"Cancelled by {signal.Signals(cancel_signal).name}"
            save()
            if "error" in status:
                break
            sample_deadline = time.monotonic() + 20
            while cancel_signal is None and time.monotonic() < sample_deadline:
                if build_exited(process.pid):
                    break
                time.sleep(1)
    except Exception as error:
        status.setdefault("error", f"Build monitoring failed: {type(error).__name__}: {error}")
        save()
    finally:
        try:
            if cancel_signal is not None and "error" not in status:
                status["error"] = f"Cancelled by {signal.Signals(cancel_signal).name}"
                save()
        finally:
            clean_build_group(process)
        final_cancel_signal = cancel_signal
        status["cleanup_verified"] = True
        if final_cancel_signal is not None and "error" not in status:
            status["error"] = f"Cancelled by {signal.Signals(final_cancel_signal).name}"
        status["exit_code"]=process.returncode
        if process.returncode and "error" not in status:
            status["error"]="Native launcher exited unsuccessfully; see preserved build log"
        status["seconds"]=time.monotonic()-started
        status["complete"]=process.returncode==0 and "error" not in status
        status["final_free_bytes"]=shutil.disk_usage(runtime).free
        save()
print(json.dumps({"status":str(status_path),"complete":status["complete"],"exit_code":status["exit_code"],"error":status.get("error")}))
if final_cancel_signal is not None:
    raise SystemExit(128 + final_cancel_signal)
raise SystemExit(0 if status["complete"] else 1)
