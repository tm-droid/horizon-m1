#!/usr/bin/env python3
"""Daily4 = daily3 stack (daily2 + terrain-single-draw + fullbright-shaderpack + player-lean) with minimap -> minimap_worldmap_waypoints_reworked 0.5.0): nightly fdc87ae + ported M1 patch stack + native mods compiled in. Never selects a version.

Flow = build-r5-nightly.py (patch stack, pinned toolchain, install layout) + build-r4-mods.sh
(horizon-mixins plan/apply per mod, then combined). Usage:
  HORIZON_TEST_QUEUE=u4 python3 build-daily1-fdc87ae.py --dry-run   # patches + mods only, no cargo
  HORIZON_TEST_QUEUE=u4 python3 build-daily1-fdc87ae.py             # + cargo build + install
  ... --tests    run cargo test for the patched crates on the final tree (no install)
  ... --only a,b restrict mods
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parents[1]
DATA = Path.home() / "Library/Application Support/horizon-launcher"
NATIVE = ROOT / "outputs/horizon-native"
SOURCE = ROOT / "outputs/horizon-src-nightly/nightly-2026-11-08-fdc87ae"
LAB = RUNTIME / "m1-performance-r12"
MODSRC = LAB / "mod-src"
BASE_TAG = "nightly-2026-11-08-fdc87ae"
BASE = DATA / "versions" / BASE_TAG
REVISION = "fdc87aecdbd116bf1e08adcd062fcbaea8c2e2ca"
TOOLCHAIN = DATA / "rust/1.99.1-aarch64-apple-darwin"
CARGO_TARGET = DATA / "native/target"
MIXINS = DATA / "native/tools/5a64af938ec8/bin/horizon-mixins"
STACK = NATIVE / "daily4-stack.txt"
JOBS = os.environ.get("DAILY1_JOBS", "2")

# id, bundle dir inside mod-src (the dir holding horizon-mixin.toml), repo
MODS = [
    ("appleskin", "soufied__AppleSkin-Horizon/mixins/appleskin", "soufied/AppleSkin-Horizon"),
    ("zoom", "horizon-rust__horizon-mods/native/zoom/mixins/zoom", "horizon-rust/horizon-mods"),
    ("minimap", "horizon-rust__horizon-mods/native/minimap/mixins/minimap", "horizon-rust/horizon-mods"),
    ("minimap_worldmap_waypoints_reworked", "daniliammo__Minimap-Worldmap-and-waypoints-reworked/mixins/minimap_worldmap_waypoints_reworked", "daniliammo/Minimap-Worldmap-and-waypoints-reworked@20f1d56"),
    ("fps_overlay", "horizon-rust__horizon-mods/native/fps-overlay/mixins/fps_overlay", "horizon-rust/horizon-mods"),
    ("fullbright_horizon", "CayMac97__fullbright/mixins/fullbright_horizon", "CayMac97/fullbright"),
    ("armor_status", "CayMac97__armor-status/mixins/armor_status", "CayMac97/armor-status"),
    ("status_effect_hud", "CayMac97__status-effect-hud/mixins/status_effect_hud", "CayMac97/status-effect-hud"),
    ("toggle_sprint", "CayMac97__toggle-sprint/mixins/toggle_sprint", "CayMac97/toggle-sprint"),
    ("light_overlay", "CayMac97__light-overlay/mixins/light_overlay", "CayMac97/light-overlay"),
    ("chatheads", "Domanffe__chatheads/mixins/chatheads", "Domanffe/chatheads"),
    ("held_item_info", "AltMugen__horizon-held-item-info/mixins/held_item_info", "AltMugen/horizon-held-item-info"),
    ("jade", "Joeypc6__Jade-Horizon/mixins/jade", "Joeypc6/Jade-Horizon"),
    ("dynamic_fps_for_rust", "Lyvt-Dev__dynamic-fps-for-rust/mixins/dynamic_fps_for_rust", "Lyvt-Dev/dynamic-fps-for-rust"),
    ("crosshair_indicator", "CayMac97__crosshair-indicator/mixins/crosshair_indicator", "CayMac97/crosshair-indicator"),
    ("dynamiclights", "DeportedToHell__MCRE-Mods/dynamiclights/mixins/dynamiclights", "DeportedToHell/MCRE-Mods"),
    ("cem_alias", None, "local: outputs/horizon-native/cem-alias-fdc87ae"),
]


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def clean_env():
    env = {k: v for k, v in os.environ.items()
           if k not in ("RUSTFLAGS", "RUSTDOCFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_ENCODED_RUSTDOCFLAGS",
                        "CARGO_INCREMENTAL", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "RUSTUP_TOOLCHAIN")
           and not k.startswith("CARGO_BUILD_")}
    env.update(PATH=f"{TOOLCHAIN}/bin:{env['PATH']}", RUSTC=str(TOOLCHAIN / "bin/rustc"),
               CARGO_HOME=str(DATA / "cargo"), CARGO_TARGET_DIR=str(CARGO_TARGET),
               CARGO_BUILD_JOBS=JOBS, CARGO_INCREMENTAL="0", DYLD_FALLBACK_LIBRARY_PATH=str(TOOLCHAIN / "lib"))
    return env


def tree_digest(root):
    inv = {}
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in ("target", ".git")]
        for f in files:
            p = Path(d, f)
            if not p.is_symlink():
                inv[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(inv, sort_keys=True).encode()).hexdigest()


def bundle_digest(path):
    h = hashlib.sha256()
    for p in sorted(Path(path).rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(path)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


def mixins_apply(work, mods, out):
    env = clean_env()
    r = subprocess.run([str(MIXINS), "apply", "--workspace", str(work), "--mods", str(mods), "--out", str(out)],
                       env=env, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)


def repin(toml, mid):
    t = toml.read_text()
    m = re.search(r'(?m)^id\s*=\s*"([^"]+)"', t)
    assert m and m.group(1) == mid, f"bundle id {m and m.group(1)} != {mid}"
    t, n = re.subn(r'(?m)^(horizon_revision\s*=\s*)"[0-9a-f]+"', lambda x: x.group(1) + f'"{REVISION}"', t)
    assert n == 1, "no horizon_revision"
    toml.write_text(t)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tests", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--no-mods", action="store_true")
    a = ap.parse_args()
    if not os.environ.get("HORIZON_TEST_QUEUE"):
        sys.exit("set HORIZON_TEST_QUEUE")
    if shutil.disk_usage(RUNTIME).free < 5 * 2**30:
        sys.exit("need 5 GiB")
    rev = run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], capture_output=True).stdout.strip()
    if rev != REVISION or run(["git", "-C", str(SOURCE), "status", "--porcelain"], capture_output=True).stdout:
        sys.exit("pristine source changed")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    lab = LAB / stamp
    lab.mkdir(parents=True)
    work = lab / "source"
    run(["rsync", "-a", "--exclude=.git", "--exclude=/CLAUDE.md", str(SOURCE) + "/", str(work) + "/"])
    names = [l.split("#", 1)[0].strip() for l in STACK.read_text().splitlines()]
    names = [n for n in names if n]
    hashes = {}
    for n in names:
        p = NATIVE / f"{n}-fdc87ae" / f"{n}.patch"
        run(["git", "apply", "--check", str(p)], cwd=work)
        run(["git", "apply", "--whitespace=nowarn", str(p)], cwd=work)
        hashes[n] = hashlib.sha256(p.read_bytes()).hexdigest()
        print(f"patch {n}: ok", flush=True)
    patched_digest = tree_digest(work)
    (work / ".horizon-revision").write_text(REVISION)
    mods_ok, mods_fail, bundles = [], [], lab / "bundles"
    bundles.mkdir()
    if not a.no_mods:
        for mid, sub, repo in MODS:
            if a.only and mid not in a.only.split(","):
                continue
            src = NATIVE / "cem-alias-fdc87ae" if sub is None else MODSRC / sub
            dst = bundles / mid
            shutil.copytree(src, dst)
            repin(dst / "horizon-mixin.toml", mid)
            one = lab / "one-mods"
            shutil.rmtree(one, ignore_errors=True); one.mkdir()
            shutil.copytree(dst, one / mid)
            ok, log = mixins_apply(work, one, lab / "one-out")
            shutil.rmtree(lab / "one-out", ignore_errors=True)
            shutil.rmtree(one, ignore_errors=True)
            if ok:
                mods_ok.append(mid); print(f"mod {mid}: apply ok", flush=True)
            else:
                short = re.findall(r'"(?:code|message)": "([^"]+)"', log)
                mods_fail.append((mid, " | ".join(short)[:300] or log[-300:]))
                shutil.rmtree(dst); print(f"mod {mid}: FAIL {mods_fail[-1][1]}", flush=True)
        if mods_ok:
            ok, log = mixins_apply(work, bundles, lab / "applied")
            if not ok:
                sys.exit("combined apply failed: " + log[-800:])
            shutil.rmtree(work); shutil.move(str(lab / "applied"), str(work))
    for stray in (".horizon-mixins-stage.json",):
        pass
    print(json.dumps({"mods_ok": mods_ok, "mods_fail": mods_fail}), flush=True)
    identity = tree_digest(work)
    version = f"native-fdc87ae-m1-daily4-{identity[:12]}"
    (lab / "mods.json").write_text(json.dumps({"ok": mods_ok, "fail": mods_fail, "patches": hashes}, indent=2))
    if a.dry_run:
        print(json.dumps({"dry_run": True, "version": version, "work": str(work)}))
        return
    env = clean_env()
    if a.tests:
        crates = ["horizon-client-render", "horizon-client", "horizon-threads"]
        cmd = [str(TOOLCHAIN / "bin/cargo"), "test", "--no-fail-fast", "--locked", "--profile", "fast",
               "--manifest-path", str(work / "Cargo.toml")] + [x for c in crates for x in ("-p", c)] + ["--lib", "--bins", "--tests"]
        with open(lab / "cargo-test.log", "w") as log:
            rc = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        print(json.dumps({"tests_rc": rc, "log": str(lab / "cargo-test.log")}))
        return
    dest = DATA / "versions" / version
    if dest.exists():
        sys.exit(f"exists: {version}")
    cmd = [str(TOOLCHAIN / "bin/cargo"), "build", "--locked", "--profile", "fast",
           "--manifest-path", str(work / "Cargo.toml"), "-p", "horizon-client", "--bin", "horizon-client"]
    t0 = time.time()
    with open(lab / "cargo-build.log", "w") as log:
        rc = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True).returncode
    print(json.dumps({"build_rc": rc, "seconds": round(time.time() - t0), "log": str(lab / "cargo-build.log")}), flush=True)
    if rc:
        sys.exit("cargo failed")
    new = dest.with_name(dest.name + ".new")
    shutil.rmtree(new, ignore_errors=True)
    run(["/bin/cp", "-cR", str(BASE), str(new)])
    shutil.copy2(CARGO_TARGET / "fast/horizon-client", new / "horizon-client")
    binary = hashlib.sha256((new / "horizon-client").read_bytes()).hexdigest()
    base_meta = {}
    meta = {"base": BASE_TAG, "horizon": REVISION, "base_horizon": REVISION, "hooks": 411, "rust": "1.99.1",
            "profile": "performance", "target": "client", "mods": [],
            "build_method": "direct-cargo-source-patches", "source_patch_digest": identity}
    for mid in mods_ok:
        v = re.search(r'(?m)^version\s*=\s*"([^"]+)"', (bundles / mid / "horizon-mixin.toml").read_text()).group(1)
        meta["mods"].append({"id": mid, "version": v, "sha256": bundle_digest(bundles / mid)})
    (new / "native-mods.json").write_text(json.dumps(meta, indent=2) + "\n")
    (new / "source-patches.json").write_text(json.dumps({
        "complete": True, "runtime_verified": False, "version": version, "source_revision": REVISION,
        "base_version": BASE_TAG, "patches": hashes, "patched_tree_digest": patched_digest,
        "mods": mods_ok, "mods_failed": mods_fail, "profile": "fast", "rust": "1.99.1",
        "source": str(work), "binary_sha256": binary, "build_seconds": round(time.time() - t0)}, indent=2) + "\n")
    (new / ".installed").touch()
    os.rename(new, dest)
    print(json.dumps({"installed": str(dest), "selected": False}))


if __name__ == "__main__":
    main()
