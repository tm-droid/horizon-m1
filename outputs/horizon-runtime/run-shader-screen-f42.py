#!/usr/bin/env python3
"""Matched offscreen shader screening, all selected packs, native100%."""
from pathlib import Path
import json, os, shutil, subprocess, sys
root=Path(__file__).resolve().parents[2]
os.chdir(root)
runtime=root/"outputs/horizon-runtime"
migration=root/"outputs/horizon-converter/2026-11-04-Tanush-f42-v3"
os.environ["HORIZON_TEST_QUEUE"]="1"
results=[]
for case in ("packs","makeup","miniature"):
    if shutil.disk_usage(runtime).free < 4*2**30:
        raise SystemExit("Less than4GiB free; not starting shader screen")
    for name in ("horizon-client","java"):
        p=subprocess.run(["pgrep","-x",name],capture_output=True,text=True,timeout=10)
        if p.returncode!=1:raise SystemExit(f"Refusing test: {name} preflight returned{p.returncode}")
    label=f"f42-{case}-full-stack-offscreen-r1"
    command=[sys.executable,"tools/horizon-offline-test.py","--runtime","nightly-2026-11-03-f42ef42",
        "--case",case,"--label",label,"--migration",str(migration),
        "--native-options-candidate",str(migration/"native-settings-candidate.json"),
        "--scene","cow","--resolution-scale","100","--fps-cap","60","--workers","0",
        "--frame-pacing","efficient","--warmup","20","--seconds","20","--offscreen","--flight"]
    result=subprocess.run(command)
    results.append({"case":case,"exit_code":result.returncode,"profile":label})
    (runtime/"shader-screen-f42-summary.json").write_text(json.dumps({"mode":"offscreen relative screening, not on-screen gameplay FPS","results":results,"visual_parity_verified":False},indent=2)+"\n")
    if result.returncode:
        print("Stopping matched comparison after failure; no winner accepted",flush=True)
        break
raise SystemExit(0 if len(results)==3 and all(item["exit_code"]==0 for item in results) else 1)
