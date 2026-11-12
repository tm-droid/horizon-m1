#!/usr/bin/env python3
"""Sky screenshots (day, sunset, night/moon) on the real profile, for one pack substitution or none."""
import sys, types, time, subprocess
sys.argv = sys.argv[:1] + sys.argv[1:]
import real, bench as B
real.ARGS = types.SimpleNamespace(windowed=False, uncapped=True)
name, sub = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
if sub:
    real.SUB[name] = tuple(sub.split("=>"))
out = B.OUT / "shots-sky"; out.mkdir(exist_ok=True)
prof = B.PROFILES / f"sky-{name}"; subprocess.run(["rm", "-rf", str(prof)])
real.real_stage(prof, "F7", "makeup", B.TEMPLATE, name)
g = real.RealGame("F7", prof, f"sky{name}")
try:
    g.wait_socket(); g.ctl("wait-ready", "240", timeout=245); g.settle(); g.front()
    for t, yaw, pitch, tag in ((6000, 0, -60, "noon"), (12600, -90, -10, "sunset"), (18000, 0, -70, "midnight"), (13800, 90, -25, "moonrise")):
        g.ctl("time", str(t)); g.ctl("look", str(yaw), str(pitch)); time.sleep(4)
        g.ctl("screenshot", str(out / f"{tag}-{name}.png")); time.sleep(2)
    print("ok", name)
finally:
    g.quit(); B.trash(prof)
