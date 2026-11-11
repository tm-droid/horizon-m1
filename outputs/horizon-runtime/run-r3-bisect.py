#!/usr/bin/env python3
"""r3 bisect: control / r2 / r3 / r3noqos, rotated paired rounds, one queue job.

MakeUp: control, r3, r3noqos x5 rounds. Packs (shader off): r2, r3, r3noqos x4 rounds.
Run under the framework python (needs Quartz):
  /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 run-r3-bisect.py
"""
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
import threading
import time

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parents[1]
VERSIONS = RUNTIME / "launcher-data/versions"
SPEC = importlib.util.spec_from_file_location("shader_review", RUNTIME / "run-shader-followup-f42.py")
REVIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REVIEW)

FIXED = {"control": "native-f42-m1-control-09391c2a8210",
         "r2": "native-f42-m1-r2-e7f5b3e786b6",
         "r3": "native-f42-m1-r3-6b039bd4b49f"}
ARMS = {"makeup": ["control", "r3", "r3noqos"], "packs": ["r2", "r3", "r3noqos"]}
ROUNDS = {"makeup": 5, "packs": 4}
COOLDOWN = 60
GATE_TIMEOUT = 600
GATE_POLL = 20
MIN_FREE = 5 * 2**30
TAINT = re.compile(r"input from a person", re.I)
PROTECTED = {"base-smoke", "base-auto-user-visible-r2"}


def sh(cmd, timeout=15):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def swap_mb():
    out = sh(["sysctl", "vm.swapusage"]).stdout
    return float(out.split("used = ")[1].split("M")[0])


def thermal():
    out = sh(["pmset", "-g", "therm"]).stdout
    m = re.search(r"CPU_Speed_Limit\s*=\s*(\d+)", out)
    return {"cpu_speed_limit": int(m.group(1)) if m else None, "raw": " | ".join(out.split("\n")[:5])}


def gate_problems():
    problems = []
    batt = sh(["pmset", "-g", "batt"]).stdout
    if "AC Power" not in batt.splitlines()[0]:
        problems.append("not on AC")
    try:
        import Quartz
        locked = Quartz.CGSessionCopyCurrentDictionary().get("CGSSessionScreenIsLocked", 0)
        if locked not in (0, None, False):
            problems.append("screen locked")
        if Quartz.CGDisplayIsAsleep(Quartz.CGMainDisplayID()):
            problems.append("display asleep")
    except Exception as error:  # fail closed
        problems.append(f"cannot read lock/display state: {error!r}")
    t = thermal()
    if t["cpu_speed_limit"] not in (None, 100) or re.search(r"(Thermal|Performance)[^\n]*level[^\n]*=\s*[1-9]", t["raw"]):
        problems.append("thermal throttling: " + t["raw"])
    for process in ("cargo", "rustc", "xcodebuild", "horizon-client"):
        if sh(["pgrep", "-x", process]).returncode != 1:
            problems.append(f"{process} running")
    if sh(["pgrep", "-f", "PineconeMC"]).returncode != 1:
        problems.append("PineconeMC java running")
    if shutil.disk_usage(RUNTIME).free < MIN_FREE:
        problems.append("less than 5 GiB free")
    return problems


def wait_gates(log):
    """Return (ok, problems). Block the batch if a gate stays failed for 10 minutes."""
    start = time.time()
    while True:
        problems = gate_problems()
        if not problems:
            return True, []
        if time.time() - start >= GATE_TIMEOUT:
            return False, problems
        log(f"gate waiting: {problems}")
        time.sleep(GATE_POLL)


def footprint_kb(pid):
    out = sh(["footprint", "-p", str(pid)], timeout=30).stdout
    m = re.search(r"Footprint:\s*([\d.]+)\s*(KB|MB|GB)", out)
    if not m:
        return None
    return float(m.group(1)) * {"KB": 1, "MB": 1024, "GB": 1024 * 1024}[m.group(2)]


class Sampler(threading.Thread):
    """Poll the horizon-client for RSS, footprint and swap while a run executes."""

    def __init__(self):
        super().__init__(daemon=True)
        self.stop = threading.Event()
        self.rss_kb = []
        self.fp_kb = []
        self.swap = []
        self.pid = None

    def run(self):
        tick = 0
        while not self.stop.wait(3):
            try:
                found = sh(["pgrep", "-x", "horizon-client"]).stdout.split()
                if not found:
                    continue
                self.pid = int(found[0])
                rss = sh(["ps", "-o", "rss=", "-p", str(self.pid)]).stdout.strip()
                if rss:
                    self.rss_kb.append(int(rss))
                self.swap.append(swap_mb())
                tick += 1
                if tick % 3 == 0:
                    fp = footprint_kb(self.pid)
                    if fp:
                        self.fp_kb.append(fp)
            except Exception:
                pass

    def summary(self):
        return {"pid": self.pid, "rss_peak_kb": max(self.rss_kb, default=None),
                "footprint_peak_kb": max(self.fp_kb, default=None),
                "footprint_last_kb": self.fp_kb[-1] if self.fp_kb else None,
                "swap_peak_M": max(self.swap, default=None), "samples": len(self.rss_kb)}


def cleanup_profile(profile):
    """Drop heavy regenerable dirs; keep result.json, logs, pngs, saves."""
    if profile.parent.name != "tests" or profile.name in PROTECTED or not profile.name.startswith("r3b-"):
        return
    for name in (".horizon-cache", "resourcepacks"):
        shutil.rmtree(profile / name, ignore_errors=True)


def resolve_versions():
    versions = dict(FIXED)
    found = sorted(p.name for p in VERSIONS.glob("native-f42-m1-r3noqos-*")
                   if (p / ".installed").is_file() and os.access(p / "horizon-client", os.X_OK))
    if found:
        versions["r3noqos"] = found[-1]
    return versions


def plan(versions):
    """Interleave rounds across cases; rotate arm order each round."""
    seq = []
    for i in range(max(ROUNDS.values())):
        for case in ("makeup", "packs"):
            if i >= ROUNDS[case]:
                continue
            arms = [a for a in ARMS[case] if a in versions]
            k = i % len(arms)
            for arm in arms[k:] + arms[:k]:
                seq.append((case, arm, i + 1))
    return seq


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="r3b")
    parser.add_argument("--resume", action="store_true", help="skip runs already valid in the summary")
    args = parser.parse_args()
    summary_path = RUNTIME / f"r3-bisect-{args.tag}.json"
    log_path = RUNTIME / f"r3-bisect-{args.tag}.log"

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        with log_path.open("a") as handle:
            handle.write(line + "\n")

    if summary_path.exists() and not args.resume:
        log("summary exists; use --resume or a fresh --tag")
        return 2
    versions = resolve_versions()
    missing = [a for a in ("control", "r2", "r3") if not (VERSIONS / versions[a] / "horizon-client").is_file()]
    if missing:
        log(f"missing builds: {missing}")
        return 2
    if "r3noqos" not in versions:
        log("WARNING: r3noqos build absent; running r3 vs control/r2 only")
    hashes = {a: digest(VERSIONS / v / "horizon-client") for a, v in versions.items()}
    manifest_path = REVIEW.MIGRATION / "manifest.json"
    manifest_hash = digest(manifest_path)
    selection = json.loads(manifest_path.read_text())["resourcepack_selection"]
    shader = REVIEW.SHADERS["makeup"]
    shader_hashes = REVIEW.shader_hashes(REVIEW.SOURCE_SHADERS, shader)

    matrix = plan(versions)
    summary = json.loads(summary_path.read_text()) if args.resume and summary_path.exists() else {
        "complete": False, "aborted": None, "tag": args.tag, "python": sys.executable, "versions": versions,
        "binary_sha256": hashes, "plan": [list(m) for m in matrix], "started": time.strftime("%F %T"),
        "has_r3noqos": "r3noqos" in versions, "results": []}
    done = {(r["case"], r["arm"], r["round"]) for r in summary["results"] if r.get("valid")}

    def save():
        tmp = summary_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(summary, indent=2) + "\n")
        os.replace(tmp, summary_path)

    save()
    # Keep the display awake for the batch; wake it once first.
    subprocess.run(["caffeinate", "-u", "-t", "2"])
    keepawake = subprocess.Popen(["caffeinate", "-d", "-i"])
    env = {**os.environ, "HORIZON_TEST_QUEUE": "1"}

    def run_once(index, case, arm, rnd, attempt):
        suffix = "" if attempt == 1 else f"-redo{attempt - 1}"
        label = f"r3b-{case}-{arm}-{rnd}{suffix}"
        profile = RUNTIME / "tests" / label
        entry = {"index": index, "case": case, "arm": arm, "round": rnd, "attempt": attempt, "label": label,
                 "native_version": versions[arm], "result": str(profile / "result.json"), "valid": False,
                 "tainted": False}
        if index > 1 or attempt > 1:
            time.sleep(COOLDOWN)
        ok, problems = wait_gates(log)
        entry["gate_ok"] = ok
        if not ok:
            entry["error"] = "BLOCKED: gate failed 10 min: " + "; ".join(problems)
            entry["gate_failed"] = True
            return entry
        entry["swap_before_M"] = swap_mb()
        entry["thermal_before"] = thermal()
        sampler = Sampler()
        try:
            REVIEW.check(not profile.exists(), f"Profile already exists: {label}")
            REVIEW.check(digest(VERSIONS / versions[arm] / "horizon-client") == hashes[arm], "Native executable changed")
            REVIEW.check(digest(manifest_path) == manifest_hash and
                         REVIEW.shader_hashes(REVIEW.SOURCE_SHADERS, shader) == shader_hashes,
                         "Migration or shader source changed")
            command = [sys.executable, "tools/horizon-offline-test.py", "--runtime", REVIEW.RELEASE,
                       "--native-version", versions[arm], "--case", case, "--label", label,
                       "--migration", str(REVIEW.MIGRATION), "--native-options-candidate",
                       str(REVIEW.MIGRATION / "native-settings-candidate.json"), "--scene", "cow",
                       "--width", "1280", "--height", "720", "--resolution-scale", "100",
                       "--fps-cap", "260", "--workers", "0", "--frame-pacing", "efficient",
                       "--warmup", "15", "--seconds", "20", "--flight"]
            sampler.start()
            completed = subprocess.run(command, cwd=ROOT, env=env)
            sampler.stop.set()
            sampler.join(timeout=40)
            entry["exit_code"] = completed.returncode
            entry["memory"] = sampler.summary()
            entry["swap_after_M"] = swap_mb()
            entry["thermal_after"] = thermal()
            console = profile / "console.log"
            if console.is_file() and TAINT.search(console.read_text(errors="replace")):
                entry["tainted"] = True
            REVIEW.check(completed.returncode == 0, "Harness failed; inspect console log")
            result = json.loads((profile / "result.json").read_text())
            REVIEW.check(result.get("native_version") == versions[arm] and
                         result.get("native_executable_sha256") == hashes[arm], "Runtime native identity mismatch")
            entry["harness_memory"] = {"system_before": result.get("system_before", {}).get("process", {}).get("output"),
                                       "system_after": result.get("system_after", {}).get("process", {}).get("output")}
            entry.update(REVIEW.review_result(result, profile, selection, manifest_hash,
                                              shader if case == "makeup" else None, 260, "settled"))
            # keep full flight series + gpu p99 compactly alongside the summary stats
            entry["flight_frame_ms"] = result["flight"].get("frame_ms")
            entry["valid"] = not entry["tainted"]
            if entry["tainted"]:
                entry["error"] = "tainted: 'input from a person' in console log"
        except Exception as error:  # noqa: BLE001 - record and continue
            entry["error"] = f"{type(error).__name__}: {error}"
        finally:
            sampler.stop.set()
            cleanup_profile(profile)
        return entry

    consecutive_fail = 0
    for index, (case, arm, rnd) in enumerate(matrix, 1):
        if (case, arm, rnd) in done:
            continue
        for attempt in (1, 2):
            entry = run_once(index, case, arm, rnd, attempt)
            summary["results"].append(entry)
            save()
            log(json.dumps({k: entry.get(k) for k in ("index", "case", "arm", "round", "attempt", "valid", "error")}))
            if entry["valid"] or entry.get("gate_failed"):
                break
        if entry.get("gate_failed"):
            summary["aborted"] = entry["error"]
            break
        consecutive_fail = 0 if entry["valid"] else consecutive_fail + 1
        if consecutive_fail >= 3:
            summary["aborted"] = "3 consecutive invalid runs"
            break
    else:
        summary["complete"] = True
    summary["finished"] = time.strftime("%F %T")
    save()
    keepawake.terminate()
    analyzer = RUNTIME / "analyze-r3-bisect.py"
    if analyzer.is_file():
        subprocess.run([sys.executable, str(analyzer), str(summary_path)])
    return 0 if summary["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
