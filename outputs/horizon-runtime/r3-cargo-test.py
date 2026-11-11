#!/usr/bin/env python3
"""r3 Rust tests with a 4 GiB free-disk watchdog (run through the device queue)."""
import os, shutil, signal, subprocess, sys, time
from pathlib import Path
RT = Path(__file__).resolve().parent
D = RT / "launcher-data"
tc = D / "rust/1.99.1-aarch64-apple-darwin"
env = {k: v for k, v in os.environ.items() if not k.startswith("CARGO_BUILD_") and k not in {"RUSTFLAGS","RUSTDOCFLAGS","CARGO_ENCODED_RUSTFLAGS","CARGO_INCREMENTAL","RUSTC_WRAPPER","RUSTUP_TOOLCHAIN"}}
env.update(PATH=str(tc/"bin")+os.pathsep+env["PATH"], RUSTC=str(tc/"bin/rustc"), CARGO_HOME=str(D/"cargo"),
           CARGO_TARGET_DIR=str(D/"native/target"), CARGO_BUILD_JOBS="1")
cmd = [str(tc/"bin/cargo"), "test", "--offline", "--locked", "--profile", "fast", "--manifest-path",
       str(RT/"m1-performance-r3/candidate-source/Cargo.toml"), "-p", "horizon-client-render", "-p", "horizon-client",
       "--lib", "--", "sprites::", "particles::", "animate", "adaptive_upload"]
p = subprocess.Popen(cmd, cwd="/", env=env, start_new_session=True)
t0 = time.monotonic()
while p.poll() is None:
    free = shutil.disk_usage(RT).free
    if free < 4*2**30 or time.monotonic()-t0 > 3000:
        print(f"WATCHDOG: stopping (free={free}, elapsed={time.monotonic()-t0:.0f})", flush=True)
        os.killpg(p.pid, signal.SIGTERM); time.sleep(5); os.killpg(p.pid, signal.SIGKILL); break
    time.sleep(10)
p.wait()
print("EXIT", p.returncode, flush=True)
sys.exit(p.returncode)
