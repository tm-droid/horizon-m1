#!/usr/bin/env python3
"""U12 native Horizon shader packs (.hshader) vs MakeUp reference, on build r3 + migration v4 (copy of run-u9b-shaders.py).

One queue job, selected packs and rounds (static cow scene + flight), with MakeUp trim as the reference.
Use --cases makeup,n-montarc,n-montarc-m1,n-daybreak011,n-daybreak011-m1 --arm r3-v4-t --rounds 3
for the U13 timing comparison. Gates WAIT (poll 60 s, up to 12 h) for AC power,
unlocked screen, awake display; idle requirement is off (IDLE_MIN_S = 0). Gates are re-checked before every run.
Native packs are picked via `pickedShaderPack:<file>` in horizon-graphics.txt with the file in the profile's shaderpacks/.
A pack the f42 client refuses ("shader pack <file> refused: ...") or fails to load is a RESULT (loaded=false), never retried.
Run under the framework python (needs Quartz):
  /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 run-u12-native-packs.py [--dry-run] [--resume] [--tag u12]
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
NATIVE_DIR = ROOT / "outputs/horizon-native-packs"
STAGE_DIR = RUNTIME / "game/shaderpacks"  # where the harness looks after the Java instance's shaderpacks dir
NATIVE_FILES = {"n-meridian": "meridian-26.3.1.hshader", "n-meridian-compat": "meridian_compat-26.3.1.hshader",
                "n-daybreak011": "daybreak-0.1.1.hshader", "n-daybreak020": "daybreak-0.2.0.hshader",
                "n-montarc": "montarc-1.1.1.hshader", "n-montarc-m1": "montarc-m1.hshader",
                "n-daybreak011-m1": "daybreak011-m1.hshader"}
IRIS_FILES = {"makeup-m1": "MakeUp-M1-HalfRes.zip", "makeup-m1r2": "MakeUp-M1-HalfRes-r2.zip"}
TRIM_CASES = {"makeup", *IRIS_FILES}
SHADER_FILES = {"makeup": "MakeUp-UltraFast-9.6.zip", **NATIVE_FILES, **IRIS_FILES}
TRIM_FILE = RUNTIME / "u9c-trim-options/MakeUp-UltraFast-9.6.zip.txt"
HARNESS = RUNTIME / "u12-harness.py"  # wrapper: registers NATIVE_FILES as extra --case values, then runs tools/horizon-offline-test.py
# arm -> (build, migration, extra env)
ARM_DEFS = {"baseline": ("control", "v3", {}),
            "daily": ("r3", "v4", {}),
            "daily-cull": ("r3", "v4", {"HORIZON_GPU_CULL": "all"}),
            "ctrl-v4": ("control", "v4", {}),
            "r3-v4": ("r3", "v4", {}),
            "r3-v4-t": ("r3", "v4", {"HORIZON_SHADER_PACK_TIMING": "1"}),
            "r3-v3": ("r3", "v3", {})}
# case -> harness case, scene, shader key, arms, rounds
CASES = {"makeup": ("makeup", "cow", "makeup", ["r3-v4"], 1),
         **{k: (k, "cow", k, ["r3-v4"], 1) for k in (*NATIVE_FILES, *IRIS_FILES)}}
PHASES = [["makeup", *NATIVE_FILES, *IRIS_FILES]]
COOLDOWN = 30
GATE_POLL = 60
GATE_MAX_WAIT = 12 * 3600
IDLE_MIN_S = 0  # user said "just start it" 2026-11-06
MIN_FREE = 5 * 2**30
PROTECTED = {"base-smoke", "base-auto-user-visible-r2"}
sh = R3.sh


def plan(cases=None, arm=None, rounds=None):
    seq = []
    for phase in ([cases] if cases is not None else PHASES):
        for rnd in range(1, (rounds or max(CASES[c][4] for c in phase)) + 1):
            for case in (phase if rnd % 2 else list(reversed(phase))):
                arms = [arm] if arm else CASES[case][3]
                if rounds is None and rnd > CASES[case][4]:
                    continue
                k = (rnd - 1) % len(arms)
                for arm in arms[k:] + arms[:k]:
                    seq.append((case, arm, rnd))
    return seq


def hid_idle_s():
    out = sh(["ioreg", "-c", "IOHIDSystem"]).stdout
    m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', out)
    return int(m.group(1)) / 1e9 if m else None


HOPELESS_FPS = 15  # user 2026-11-06: a run this slow is not worth a retry


def hopeless(entry):
    """A run under HOPELESS_FPS avg is final, including any later planned rounds."""
    try:
        fps = (json.loads(Path(entry["result"]).read_text()).get("measurement") or {}).get("avg_fps")
    except (OSError, ValueError, KeyError):
        return False
    return isinstance(fps, (int, float)) and fps < HOPELESS_FPS


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
    if sh(["pgrep", "-f", r"/CoreSimulator/Profiles/.*/SpringBoard\.app/SpringBoard"]).returncode != 1:
        problems.append("iOS Simulator device still booted (its window may be closed)")
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
    if profile.parent.name != "tests" or profile.name in PROTECTED or not profile.name.startswith("u12-"):
        return
    for name in (".horizon-cache", "resourcepacks"):
        shutil.rmtree(profile / name, ignore_errors=True)


def shader_source_dir(shader_key, mig):
    if shader_key in NATIVE_FILES:
        return STAGE_DIR
    # Match the harness's archive lookup without reading the Java options sidecar.
    return REVIEW.SOURCE_SHADERS if (REVIEW.SOURCE_SHADERS / SHADER_FILES[shader_key]).is_file() else STAGE_DIR


def shader_hashes(shader_key, mig):
    hashes = {"archive": R3.digest(shader_source_dir(shader_key, mig) / SHADER_FILES[shader_key])}
    if shader_key in TRIM_CASES:
        hashes["options"] = R3.digest(TRIM_FILE)
    return hashes


def migration_identity(directory):
    manifest = directory / "manifest.json"
    return {"manifest_hash": R3.digest(manifest),
            "native_settings_hash": R3.digest(directory / "native-settings-candidate.json"),
            "selection": json.loads(manifest.read_text())["resourcepack_selection"]}


def input_problems(matrix):
    problems = []
    for build in {ARM_DEFS[a][0] for _, a, _ in matrix}:
        if not (VERSIONS / BUILDS[build] / "horizon-client").is_file():
            problems.append(f"missing build {build}: {BUILDS[build]}")
    for mig in {ARM_DEFS[a][1] for _, a, _ in matrix}:
        if any(not (MIGRATIONS[mig] / f).is_file() for f in ("native-settings-candidate.json", "manifest.json")):
            problems.append(f"missing migration files: {mig}")
    for case in dict.fromkeys(c for c, _, _ in matrix):
        skey = CASES[case][2]
        src = NATIVE_DIR if skey in NATIVE_FILES else shader_source_dir(skey, "v4")
        if not (src / SHADER_FILES[skey]).is_file():
            problems.append(f"missing shader {SHADER_FILES[skey]} for {case}")
        if skey in TRIM_CASES and (TRIM_FILE.is_symlink() or not TRIM_FILE.is_file()):
            problems.append("missing regular MakeUp trim sidecar: " + str(TRIM_FILE))
    if not HARNESS.is_file():
        problems.append("missing wrapper " + str(HARNESS))
    return problems


def profile_label(tag, case, arm, rnd, attempt=1):
    suffix = "" if attempt == 1 else f"-redo{attempt - 1}"
    return f"u12-{tag}-{case}-{arm}-{rnd}{suffix}"


def stage_native(cases):
    """Clone the .hshader files into game/shaderpacks (additive; the harness copies from there into each profile)."""
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    for case in cases:
        if case not in NATIVE_FILES:
            continue
        name = NATIVE_FILES[case]
        dst = STAGE_DIR / name
        if not dst.is_file() or R3.digest(dst) != R3.digest(NATIVE_DIR / name):
            dst.unlink(missing_ok=True)
            subprocess.run(["/bin/cp", "-c", str(NATIVE_DIR / name), str(dst)], check=True)


LOADED_RE = re.compile(r"shader pack (?!\S+ refused)\S+ \S+: (?!folder |mc_Entity ).+ in \d+ ms")
REFUSED_RE = re.compile(r"shader pack .*(refused|failed|error)", re.I)


def native_status(lines):
    loaded = [l for l in lines if LOADED_RE.search(l)]
    refused = [l for l in lines if REFUSED_RE.search(l)]
    return {"loaded": bool(loaded) and not refused, "load_lines": loaded[-3:], "refusal_lines": refused[-5:]}


def review_cow(result, profile, mig_info, shader_key):
    shader = SHADER_FILES[shader_key]
    selection, manifest_hash = mig_info["selection"], mig_info["manifest_hash"]
    if shader_key in NATIVE_FILES:
        # No post-program loader line for .hshader: review without it, then judge loading from the log lines.
        lines = [l for l in result.get("shader_diagnostics", []) if shader in l or LOADED_RE.search(l)]
        status = native_status(lines)
        if not status["loaded"]:
            return {"shader_diagnostics": lines}, status
        review = REVIEW.review_result(dict(result, shader_requested=None), profile, selection, manifest_hash, None, 260, "settled")
        review["shader_diagnostics"] = lines
        return review, status
    # The reference must prove active MakeUp post programs; shader-off fallback FPS cannot anchor comparisons.
    return REVIEW.review_result(result, profile, selection, manifest_hash, shader, 260, "settled"), {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="u12")
    parser.add_argument("--resume", action="store_true", help="skip runs already valid in the summary")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and check inputs, run nothing")
    parser.add_argument("--cases", help="comma-separated cases, in run order (default: all)")
    parser.add_argument("--arm", choices=ARM_DEFS, help="use this arm for every selected case")
    parser.add_argument("--rounds", type=int, help="repeat each selected case this many times")
    args = parser.parse_args()
    cases = args.cases.split(",") if args.cases is not None else None
    if cases is not None and (len(set(cases)) != len(cases) or any(c not in CASES for c in cases)):
        parser.error("--cases must contain unique known cases: " + ",".join(CASES))
    if args.rounds is not None and args.rounds < 1:
        parser.error("--rounds must be positive")
    if not re.fullmatch(r"[a-z0-9-]{1,16}", args.tag):
        parser.error("--tag must have 1-16 lowercase letters, digits, or hyphens")
    summary_path = RUNTIME / f"u12-native-{args.tag}.json"
    log_path = RUNTIME / f"u12-native-{args.tag}.log"

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        if not args.dry_run:
            with log_path.open("a") as handle:
                handle.write(line + "\n")

    matrix = plan(cases, args.arm, args.rounds)
    if any(len(profile_label(args.tag, c, a, r, 2)) > 60 for c, a, r in matrix):
        parser.error("profile label exceeds 60 characters; use a shorter --tag")
    selected_cases = list(dict.fromkeys(c for c, _, _ in matrix))
    selected_arms = {a for _, a, _ in matrix}
    builds = {b: BUILDS[b] for b in {ARM_DEFS[a][0] for a in selected_arms}}
    migrations = {m: MIGRATIONS[m] for m in {ARM_DEFS[a][1] for a in selected_arms}}
    problems = input_problems(matrix)
    if args.dry_run:
        print(f"u12 plan: {len(matrix)} runs")
        for i, (case, arm, rnd) in enumerate(matrix, 1):
            build, mig, env = ARM_DEFS[arm]
            hcase, scene, skey, _, _ = CASES[case]
            extra = f" env={env}" if env else ""
            print(f"{i:2d} {case:14s} r{rnd} {arm:10s} build={build:7s} mig={mig} harness-case={hcase} scene={scene}"
                  f"{' shader=' + SHADER_FILES[skey]}{extra}"
                  f"{' options=' + str(TRIM_FILE) if skey in TRIM_CASES else ''}"
                  f" label={profile_label(args.tag, case, arm, rnd)}")
        print("input check:", "OK" if not problems else problems)
        return 0 if not problems else 2

    if summary_path.exists() and not args.resume:
        log("summary exists; use --resume or a fresh --tag")
        return 2
    if problems:
        log(f"input check failed: {problems}")
        return 2
    stage_native(selected_cases)
    hashes = {b: R3.digest(VERSIONS / v / "horizon-client") for b, v in builds.items()}
    mig_info = {name: migration_identity(directory) for name, directory in migrations.items()}
    source_hashes = {f"{case}/{ARM_DEFS[arm][1]}": shader_hashes(CASES[case][2], ARM_DEFS[arm][1])
                     for case, arm, _ in matrix}

    summary = json.loads(summary_path.read_text()) if args.resume and summary_path.exists() else {
        "complete": False, "aborted": None, "tag": args.tag, "python": sys.executable, "builds": builds,
        "migrations": {k: str(v) for k, v in migrations.items()}, "arms": {k: list(ARM_DEFS[k]) for k in selected_arms},
        "binary_sha256": hashes, "shader_sha256": source_hashes, "migration_identity": mig_info,
        "plan": [list(m) for m in matrix],
        "started": time.strftime("%F %T"), "results": []}
    if (summary["plan"] != [list(m) for m in matrix] or summary["binary_sha256"] != hashes or
            summary.get("shader_sha256") != source_hashes or summary.get("migration_identity") != mig_info):
        log("resume plan or inputs changed; use the original arguments and inputs, or a fresh --tag")
        return 2
    done = {(r["case"], r["arm"], r["round"]) for r in summary["results"] if r.get("valid") or r.get("shader_refused") or r.get("hopeless") or hopeless(r) or (r["case"] in NATIVE_FILES and not r.get("gate_failed"))}
    terminal = {(r["case"], r["arm"]) for r in summary["results"] if
                r.get("shader_refused") or r.get("hopeless") or hopeless(r) or
                (r["case"] in NATIVE_FILES and r.get("loaded") is False and not r.get("gate_failed"))}

    def save():
        tmp = summary_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(summary, indent=2) + "\n")
        os.replace(tmp, summary_path)

    save()
    keepawake = subprocess.Popen(["caffeinate", "-i"])  # idle-sleep only while waiting; display kept awake per run
    base_env = {k: v for k, v in os.environ.items() if k not in ("HORIZON_GPU_CULL", "HORIZON_SHADER_PACK_TIMING")}
    base_env["HORIZON_TEST_QUEUE"] = "1"
    executed = [0]

    def run_once(index, case, arm, rnd, attempt):
        build, mig, arm_env = ARM_DEFS[arm]
        hcase, scene, skey, _, _ = CASES[case]
        label = profile_label(args.tag, case, arm, rnd, attempt)
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
            REVIEW.check(migration_identity(migration) == mig_info[mig], "Migration manifest or native settings changed")
            if skey:
                REVIEW.check(shader_hashes(skey, mig) == source_hashes[f"{case}/{mig}"],
                             "Shader source changed")
            command = [sys.executable, str(HARNESS), "--runtime", REVIEW.RELEASE,
                       "--native-version", BUILDS[build], "--case", hcase, "--label", label,
                       "--migration", str(migration), "--native-options-candidate",
                       str(migration / "native-settings-candidate.json"), "--scene", scene,
                       "--width", "1280", "--height", "720", "--resolution-scale", "100",
                       "--fps-cap", "260", "--workers", "0", "--frame-pacing", "efficient"]
            command += ["--warmup", "15", "--seconds", "20", "--flight"]
            if skey in TRIM_CASES:
                command += ["--shader-options-file", str(TRIM_FILE)]
                entry["shader_options_sha256"] = source_hashes[f"{case}/{mig}"]["options"]
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
            if skey == "makeup":
                REVIEW.check((result.get("shader_options_override") or {}).get("sha256") ==
                             source_hashes[f"{case}/{mig}"]["options"], "MakeUp trim override missing or changed")
            entry["harness_memory"] = {"system_before": result.get("system_before", {}).get("process", {}).get("output"),
                                       "system_after": result.get("system_after", {}).get("process", {}).get("output")}
            review, flags = review_cow(result, profile, mig_info[mig], skey)
            entry.update(flags)
            if skey in NATIVE_FILES:
                REVIEW.check(entry["loaded"], "Native shader refused or missing load evidence; fallback FPS excluded")
            else:
                entry["loaded"] = True  # strict post-program loader evidence passed above
            entry.update(review)
            entry["flight_frame_ms"] = result["flight"].get("frame_ms")
            entry["valid"] = not entry["tainted"]
            if entry["tainted"]:
                entry["error"] = "tainted: 'input from a person' in console log"
        except Exception as error:  # noqa: BLE001 - record and continue
            entry["error"] = f"{type(error).__name__}: {error}"
            if skey in NATIVE_FILES and "loaded" not in entry:
                console = profile / "console.log"
                lines = [l for l in console.read_text(errors="replace").splitlines() if "shader pack" in l] if console.is_file() else []
                entry.update(native_status(lines))
                entry["shader_diagnostics"] = lines[-20:]
        finally:
            console = profile / "console.log"
            if console.is_file():
                lines = console.read_text(errors="replace").splitlines()
                entry["shader_pass_timings"] = [line for line in lines
                                                if "shader pack GPU time per pass" in line]
                refused = [line for line in lines if SHADER_FILES[skey] in line and REFUSED_RE.search(line)]
                if refused:
                    entry.update(shader_refused=True, loaded=False, valid=False, refusal_lines=refused,
                                 error="Shader refused or a pass failed; fallback metrics excluded")
            sampler.stop.set()
            display_awake.terminate()
            cleanup_profile(profile)
        return entry

    consecutive_fail = 0
    for index, (case, arm, rnd) in enumerate(matrix, 1):
        if (case, arm, rnd) in done:
            continue
        if (case, arm) in terminal:
            skipped = {"case": case, "arm": arm, "round": rnd, "reason": "earlier hopeless or unloaded run"}
            if skipped not in summary.setdefault("skipped", []):
                summary["skipped"].append(skipped)
            save()
            log("skipping " + json.dumps(skipped))
            continue
        native = case in NATIVE_FILES
        for attempt in ((1,) if native else (1, 2)):
            entry = run_once(index, case, arm, rnd, attempt)
            entry["hopeless"] = hopeless(entry)
            summary["results"].append(entry)
            save()
            log(json.dumps({k: entry.get(k) for k in ("index", "case", "arm", "round", "attempt", "valid", "error")}))
            if entry["valid"] or entry.get("gate_failed") or entry.get("shader_refused") or entry["hopeless"] or native:
                break
        if entry.get("shader_refused") or entry["hopeless"] or (native and entry.get("loaded") is False and not entry.get("gate_failed")):
            terminal.add((case, arm))
        if entry.get("gate_failed"):
            summary["aborted"] = entry["error"]
            break
        consecutive_fail = 0 if entry["valid"] or entry["hopeless"] or native else consecutive_fail + 1
        if consecutive_fail >= 3:
            summary["aborted"] = "3 consecutive invalid runs"
            break
    else:
        summary["complete"] = True
    summary["finished"] = time.strftime("%F %T")
    save()
    keepawake.terminate()
    analyzer = RUNTIME / "analyze-u12-native.py"
    if analyzer.is_file():
        subprocess.run([sys.executable, str(analyzer), str(summary_path)])
    return 0 if summary["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
