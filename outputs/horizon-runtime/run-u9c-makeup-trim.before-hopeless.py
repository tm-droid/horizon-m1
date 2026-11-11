#!/usr/bin/env python3
"""U9c MakeUp trim A/B (copy of run-u9b-shaders.py): r3+v4 cow, arm daily (current shader options) vs trim (R6 same-look-cheaper options via --shader-options-file), 3 rounds.

One queue job, 34 runs, interleaved rounds with rotating arm order. Gates WAIT (poll 60 s, up to 12 h)
for AC power, unlocked screen, awake display and an idle user (HIDIdleTime >= 300 s), so the job can be
queued while the user is away and starts by itself later. Gates are re-checked before every run.

Run order (most important first): 1 makeup, 3 other shaders, 4 ore glow, 2 packs (shader off).
Run under the framework python (needs Quartz):
  /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 run-u9-daily.py [--dry-run] [--resume] [--tag u9]
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

RUNTIME = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, RUNTIME / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R3 = load("r3_bisect", "run-r3-bisect.py")      # sh, digest, swap_mb, thermal, Sampler, TAINT
REVIEW = R3.REVIEW                                # run-shader-followup-f42.py helpers
ROOT, VERSIONS = R3.ROOT, R3.VERSIONS
CONVERTER = ROOT / "outputs/horizon-converter"
MIGRATIONS = {"v3": CONVERTER / "2026-11-04-Tanush-f42-v3", "v4": CONVERTER / "2026-11-05-Tanush-f42-v4"}
BUILDS = {"control": "native-f42-m1-control-09391c2a8210", "r3": "native-f42-m1-r3-6b039bd4b49f"}
SHADER_FILES = {"makeup": "MakeUp-UltraFast-9.6.zip", "mellow": "Mellow v3.4.1a.zip",
                "miniature": "miniature-shader-2.19.zip", "complementary": "ComplementaryReimagined_r5.9.3.zip",
                "ilikvanilla": "I Like Vanilla v1.5.0b.zip", "superduper": "superDuperVanilla.zip",
                "sildurs": "Sildur's Vibrant Shaders v2.02 Lite.zip", "bsl": "BSL_v10.1.8.zip",
                "bliss": "Bliss_v2.1.2_(Chocapic13_Shaders_edit).zip", "unbound": "ComplementaryUnbound_r5.9.3.zip",
                "bakedpotato": "BakedPotatoFinal.zip", "sildursdefault": "Sildur's Enhanced Default v1.20 Fancy.zip"}
# arm -> (build, migration, extra env)
ARM_DEFS = {"baseline": ("control", "v3", {}),
            "daily": ("r3", "v4", {}),
            "daily-cull": ("r3", "v4", {"HORIZON_GPU_CULL": "all"}),
            "ctrl-v4": ("control", "v4", {}),
            "trim": ("r3", "v4", {}),
            "r3-v4": ("r3", "v4", {}),
            "r3-v3": ("r3", "v3", {})}
# case -> harness case, scene, shader key, arms, rounds
CASES = {"makeup": ("makeup", "cow", "makeup", ["daily", "trim"], 3)}
# U9c: daily vs trim, rotating order per round (daily,trim / trim,daily / daily,trim)
PHASES = [["makeup"]]
# R6 "same-look-cheaper" overrides, applied on top of the daily sidecar (all names verified in MakeUp-UltraFast-9.6.zip config.glsl)
TRIM_OPTIONS = {"COLORED_SHADOW": "false", "CLOUD_REFLECTION": "false", "SHADOW_DISTANCE_SLIDER": "0",
                "CLOUD_STEPS_AVG": "8", "AOSTEPS": "4", "BLOOM_SAMPLES": "2.0"}
DAILY_SIDECAR = ROOT / "instances/Tanush-26.3/minecraft/shaderpacks" / (SHADER_FILES["makeup"] + ".txt")
TRIM_FILE = RUNTIME / "u9c-trim-options" / (SHADER_FILES["makeup"] + ".txt")


def write_trim_file():
    kv = {}
    for line in DAILY_SIDECAR.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip()
    kv.update(TRIM_OPTIONS)
    TRIM_FILE.parent.mkdir(exist_ok=True)
    TRIM_FILE.write_text("".join(f"{k}={v}\n" for k, v in sorted(kv.items())))


COOLDOWN = 30
GATE_POLL = 60
GATE_MAX_WAIT = 12 * 3600
IDLE_MIN_S = 0  # user said "just start it" 2026-11-06
MIN_FREE = 5 * 2**30
PROTECTED = {"base-smoke", "base-auto-user-visible-r2"}
sh = R3.sh


def plan():
    seq = []
    for phase in PHASES:
        for rnd in range(1, max(CASES[c][4] for c in phase) + 1):
            for case in phase:
                arms = CASES[case][3]
                if rnd > CASES[case][4]:
                    continue
                k = (rnd - 1) % len(arms)
                for arm in arms[k:] + arms[:k]:
                    seq.append((case, arm, rnd))
    return seq


def hid_idle_s():
    out = sh(["ioreg", "-c", "IOHIDSystem"]).stdout
    m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', out)
    return int(m.group(1)) / 1e9 if m else None


def gate_problems(check_idle=True):
    problems = []
    first = (sh(["pmset", "-g", "batt"]).stdout.splitlines() or [""])[0]
    if "AC Power" not in first:
        problems.append("on battery")
    try:
        import Quartz
        locked = Quartz.CGSessionCopyCurrentDictionary().get("CGSSessionScreenIsLocked", 0)
        if locked not in (0, None, False):
            problems.append("screen locked")
        if Quartz.CGDisplayIsAsleep(Quartz.CGMainDisplayID()):
            problems.append("display asleep")
    except Exception as error:  # fail closed
        problems.append(f"cannot read lock/display state: {error!r}")
    if check_idle:
        idle = hid_idle_s()
        if idle is None:
            problems.append("cannot read HIDIdleTime")
        elif idle < IDLE_MIN_S:
            problems.append(f"user active (idle {idle:.0f}s < {IDLE_MIN_S}s)")
    t = R3.thermal()
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


def wait_gates(log, poll=GATE_POLL, max_wait=GATE_MAX_WAIT, probe=gate_problems, sleep=time.sleep):
    """Block until every gate passes. Returns (ok, problems); not ok only after max_wait seconds of failing."""
    start = time.time()
    last = None
    polls = 0
    while True:
        problems = probe()
        if problems == ["display asleep"]:
            # Idle already verified; wake the display once, then re-check everything except idle.
            subprocess.run(["caffeinate", "-u", "-t", "2"])
            sleep(3)
            problems = probe(check_idle=False)
        if not problems:
            if polls:
                log(f"gates clear after {time.time() - start:.0f}s")
            return True, []
        if time.time() - start >= max_wait:
            return False, problems
        if problems != last or polls % 10 == 0:
            log(f"gate waiting: {problems}")
        last = problems
        polls += 1
        sleep(poll)


def cleanup_profile(profile):
    if profile.parent.name != "tests" or profile.name in PROTECTED or not profile.name.startswith("u9-"):
        return
    for name in (".horizon-cache", "resourcepacks"):
        shutil.rmtree(profile / name, ignore_errors=True)


def shader_source_dir(shader_key, mig):
    if shader_key in ("bakedpotato", "sildursdefault"):
        return RUNTIME / "game/shaderpacks"
    return MIGRATIONS[mig] / "shader-source" if shader_key == "mellow" else REVIEW.SOURCE_SHADERS


def review_cow(result, profile, mig_info, shader_key):
    shader = SHADER_FILES[shader_key] if shader_key else None
    selection, manifest_hash = mig_info["selection"], mig_info["manifest_hash"]
    try:
        return REVIEW.review_result(result, profile, selection, manifest_hash, shader, 260, "settled"), {}
    except ValueError as error:
        if "No shader loader report" not in str(error):
            raise
    # Loader log line not matched for this pack: keep the run, flag it, re-review without the loader check.
    patched = dict(result, shader_requested=None)
    review = REVIEW.review_result(patched, profile, selection, manifest_hash, None, 260, "settled")
    review["shader_diagnostics"] = [l for l in result.get("shader_diagnostics", []) if l.startswith(f"shader pack {shader}: ")]
    return review, {"loader_evidence_missing": True}


def review_ores(result, profile, mig_info, shader_key):
    shader = SHADER_FILES[shader_key] if shader_key else None
    REVIEW.check(result.get("complete") is True and result.get("exit_code") == 0, "Harness did not complete cleanly")
    REVIEW.check(result.get("scene") == "ores" and result["render_mode"] == "onscreen" and
                 result["shader_requested"] == shader, "Scene or shader request changed")
    REVIEW.check(result["migration_manifest_sha256"] == mig_info["manifest_hash"] and
                 result["active_resourcepacks"]["options"]["resourcePacks"]["value"] == mig_info["selection"],
                 "Active resource pack stack changed")
    fixture = result.get("ore_fixture") or {}
    REVIEW.check(fixture.get("verified") is True and fixture.get("block_readback_count") == 24, "Ore fixture not verified")
    for key in ("before", "after"):
        REVIEW.check(result[key]["screen"] == "playing" and result[key]["renderer"]["size"] == REVIEW.SIZE and
                     result[key]["renderer"]["backend"] == "Metal", "Renderer surface changed")
    header = (profile / "scene.png").read_bytes()[:24]
    REVIEW.check(header[:8] == b"\x89PNG\r\n\x1a\n" and
                 [int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")] == REVIEW.SIZE,
                 "Unexpected scene.png geometry")
    extra = {"loader_evidence": []}
    if shader:
        prefix = f"shader pack {shader}: "
        lines = [l for l in result.get("shader_diagnostics", []) if l.startswith(prefix)]
        extra["loader_evidence"] = [l for l in lines if re.match(r"folder `[^`]*`, [1-9][0-9]* programs \(", l[len(prefix):])]
        if not extra["loader_evidence"]:
            extra["loader_evidence_missing"] = True
    m = result.get("measurement") or {}
    return {"static": {k: m.get(k) for k in ("seconds", "frames", "avg_fps", "low_1pct_fps", "p99_ms")},
            "screenshots": [str(profile / "scene.png")], **extra}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="u9")
    parser.add_argument("--resume", action="store_true", help="skip runs already valid in the summary")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and check inputs, run nothing")
    args = parser.parse_args()
    summary_path = RUNTIME / f"u9-daily-{args.tag}.json"
    log_path = RUNTIME / f"u9-daily-{args.tag}.log"

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        if not args.dry_run:
            with log_path.open("a") as handle:
                handle.write(line + "\n")

    matrix = plan()
    if args.dry_run:
        print(f"u9 plan: {len(matrix)} runs")
        for i, (case, arm, rnd) in enumerate(matrix, 1):
            build, mig, env = ARM_DEFS[arm]
            hcase, scene, skey, _, _ = CASES[case]
            extra = f" env={env}" if env else ""
            print(f"{i:2d} {case:14s} r{rnd} {arm:10s} build={build:7s} mig={mig} harness-case={hcase} scene={scene}"
                  f"{' shader=' + SHADER_FILES[skey] if skey else ''}{extra}")
        problems = []
        for b, v in BUILDS.items():
            if not (VERSIONS / v / "horizon-client").is_file():
                problems.append(f"missing build {b}: {v}")
        for m, d in MIGRATIONS.items():
            if not (d / "native-settings-candidate.json").is_file() or not (d / "manifest.json").is_file():
                problems.append(f"missing migration files: {m}")
        for case, (_, _, skey, arms, _) in CASES.items():
            if skey:
                for mig in {ARM_DEFS[a][1] for a in arms}:
                    if not (shader_source_dir(skey, mig) / SHADER_FILES[skey]).is_file():
                        problems.append(f"missing shader {SHADER_FILES[skey]} for {case}/{mig}")
        if not DAILY_SIDECAR.is_file():
            problems.append(f"missing daily sidecar {DAILY_SIDECAR}")
        print("trim options:", TRIM_OPTIONS)
        print("input check:", "OK" if not problems else problems)
        return 0 if not problems else 2

    write_trim_file()
    trim_hash = R3.digest(TRIM_FILE)
    if summary_path.exists() and not args.resume:
        log("summary exists; use --resume or a fresh --tag")
        return 2
    missing = [b for b, v in BUILDS.items() if not (VERSIONS / v / "horizon-client").is_file()]
    if missing:
        log(f"missing builds: {missing}")
        return 2
    hashes = {b: R3.digest(VERSIONS / v / "horizon-client") for b, v in BUILDS.items()}
    mig_info = {}
    for name, directory in MIGRATIONS.items():
        manifest = directory / "manifest.json"
        mig_info[name] = {"manifest_hash": R3.digest(manifest),
                          "selection": json.loads(manifest.read_text())["resourcepack_selection"]}
    shader_hashes = {(case, mig): REVIEW.shader_hashes(shader_source_dir(skey, mig), SHADER_FILES[skey])
                     for case, (_, _, skey, arms, _) in CASES.items() if skey for mig in {ARM_DEFS[a][1] for a in arms}}

    summary = json.loads(summary_path.read_text()) if args.resume and summary_path.exists() else {
        "complete": False, "aborted": None, "tag": args.tag, "python": sys.executable, "builds": BUILDS,
        "migrations": {k: str(v) for k, v in MIGRATIONS.items()}, "arms": {k: [v[0], v[1], v[2]] for k, v in ARM_DEFS.items()},
        "binary_sha256": hashes, "plan": [list(m) for m in matrix], "started": time.strftime("%F %T"), "results": []}
    done = {(r["case"], r["arm"], r["round"]) for r in summary["results"] if r.get("valid")}

    def save():
        tmp = summary_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(summary, indent=2) + "\n")
        os.replace(tmp, summary_path)

    save()
    keepawake = subprocess.Popen(["caffeinate", "-i"])  # idle-sleep only while waiting; display kept awake per run
    base_env = {k: v for k, v in os.environ.items() if k != "HORIZON_GPU_CULL"}
    base_env["HORIZON_TEST_QUEUE"] = "1"
    executed = [0]

    def run_once(index, case, arm, rnd, attempt):
        build, mig, arm_env = ARM_DEFS[arm]
        hcase, scene, skey, _, _ = CASES[case]
        suffix = "" if attempt == 1 else f"-redo{attempt - 1}"
        label = f"u9-{case}-{arm}-{rnd}{suffix}"
        profile = RUNTIME / "tests" / label
        migration = MIGRATIONS[mig]
        entry = {"index": index, "case": case, "arm": arm, "round": rnd, "attempt": attempt, "label": label,
                 "native_version": BUILDS[build], "build": build, "migration": mig, "env": arm_env, "scene": scene,
                 "result": str(profile / "result.json"), "valid": False, "tainted": False}
        if executed[0]:
            time.sleep(COOLDOWN)
        ok, problems = wait_gates(log)
        entry["gate_ok"] = ok
        if not ok:
            entry["error"] = "BLOCKED: gate failed 12 h: " + "; ".join(problems)
            entry["gate_failed"] = True
            return entry
        executed[0] += 1
        display_awake = subprocess.Popen(["caffeinate", "-d", "-t", "3600"])
        entry["swap_before_M"] = R3.swap_mb()
        entry["thermal_before"] = R3.thermal()
        sampler = R3.Sampler()
        try:
            REVIEW.check(not profile.exists(), f"Profile already exists: {label}")
            REVIEW.check(R3.digest(VERSIONS / BUILDS[build] / "horizon-client") == hashes[build], "Native executable changed")
            REVIEW.check(R3.digest(migration / "manifest.json") == mig_info[mig]["manifest_hash"], "Migration manifest changed")
            if skey:
                REVIEW.check(REVIEW.shader_hashes(shader_source_dir(skey, mig), SHADER_FILES[skey]) == shader_hashes[(case, mig)],
                             "Shader source changed")
            command = [sys.executable, "tools/horizon-offline-test.py", "--runtime", REVIEW.RELEASE,
                       "--native-version", BUILDS[build], "--case", hcase, "--label", label,
                       "--migration", str(migration), "--native-options-candidate",
                       str(migration / "native-settings-candidate.json"), "--scene", scene,
                       "--width", "1280", "--height", "720", "--resolution-scale", "100",
                       "--fps-cap", "260", "--workers", "0", "--frame-pacing", "efficient"]
            command += ["--warmup", "15", "--seconds", "20", "--flight"] if scene == "cow" else ["--warmup", "5", "--seconds", "5"]
            if arm == "trim":
                REVIEW.check(R3.digest(TRIM_FILE) == trim_hash, "Trim options file changed")
                command += ["--shader-options-file", str(TRIM_FILE)]
                entry["trim_options"] = TRIM_OPTIONS
            env = {**base_env, **arm_env}
            sampler.start()
            completed = subprocess.run(command, cwd=ROOT, env=env)
            sampler.stop.set()
            sampler.join(timeout=40)
            entry["exit_code"] = completed.returncode
            entry["memory"] = sampler.summary()
            entry["swap_after_M"] = R3.swap_mb()
            entry["thermal_after"] = R3.thermal()
            console = profile / "console.log"
            if console.is_file() and R3.TAINT.search(console.read_text(errors="replace")):
                entry["tainted"] = True
            REVIEW.check(completed.returncode == 0, "Harness failed; inspect console log")
            result = json.loads((profile / "result.json").read_text())
            REVIEW.check(result.get("native_version") == BUILDS[build] and
                         result.get("native_executable_sha256") == hashes[build], "Runtime native identity mismatch")
            entry["harness_memory"] = {"system_before": result.get("system_before", {}).get("process", {}).get("output"),
                                       "system_after": result.get("system_after", {}).get("process", {}).get("output")}
            if scene == "cow":
                review, flags = review_cow(result, profile, mig_info[mig], skey)
                entry.update(review)
                entry.update(flags)
                entry["flight_frame_ms"] = result["flight"].get("frame_ms")
            else:
                entry.update(review_ores(result, profile, mig_info[mig], skey))
            entry["valid"] = not entry["tainted"]
            if entry["tainted"]:
                entry["error"] = "tainted: 'input from a person' in console log"
        except Exception as error:  # noqa: BLE001 - record and continue
            entry["error"] = f"{type(error).__name__}: {error}"
        finally:
            sampler.stop.set()
            display_awake.terminate()
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
    analyzer = RUNTIME / "analyze-u9-daily.py"
    if analyzer.is_file():
        subprocess.run([sys.executable, str(analyzer), str(summary_path)])
    return 0 if summary["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
