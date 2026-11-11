#!/usr/bin/env bash
# build-r4-mods.sh -- Horizon client = pristine f42ef42 + r4 patch stack + 8 reviewed native mods.
#
# README
#   What:   rsync pristine stage -> fresh work dir, `git apply` every patch listed in
#           outputs/horizon-native/r4-stack.txt (order kept, list is re-read on every run),
#           stage the pinned mod bundles, apply them with the launcher's own horizon-mixins tool
#           (launcher-data/native/tools/e8cd0aa38cff, the r3 launcher's pin) onto the PATCHED tree,
#           cargo build (same flags as build-m1-performance-r3.py), install as a new launcher version.
#   Usage:  HORIZON_TEST_QUEUE=<ticket> build-r4-mods.sh [--dry-run] [--no-mods] [--only a,b,...] [--keep]
#           --dry-run  patches + mixins only. No cargo build, no install. (Needs HORIZON_TEST_QUEUE too.)
#           --no-mods  patch stack only.
#           --only     comma list of mod ids (bisect compile failures), e.g. --only status_effect_hud,chatheads
#           --keep     keep the work dir after a dry-run (default: kept; flag reserved, work dir is reused only if absent)
#   Env:    HORIZON_DRY_NO_CARGO=1  dry-run skips the `horizon-mixins apply` run, because that tool shells out to
#           `cargo metadata` and `rustc --version` (read-only, no compile). Mods are then only statically checked.
#   Output: launcher-data/versions/native-f42-m1-r4-<hash12>[-nomods|-sub]/ . No instance is switched, settings.json
#           is never touched. Select it in the Horizon launcher by hand. Prints the dir name on the last line.
#   Mods (pinned, all reviewed in R14/R21; native code is unsandboxed, only these SHAs are trusted):
#           appleskin_horizon, status_effect_hud, armor_status, toggle_sprint, light_overlay, minimap,
#           held_item_info, chatheads. Fetched text-only via `gh api` and git-blob-hash verified; no mod script is
#           ever run and committed binaries (.hnmod/.jar/images) are skipped.
#   Logs:   m1-performance-r4/build-r4-mods-<stamp>.log (everything), cargo-candidate.log (cargo only).
#   Time/disk (from r3): incremental candidate compile ~520 s with CARGO_BUILD_JOBS=1 on the shared 7 GB
#           native/target; install adds ~76 MB binary (+ cloned .local); work dir ~100 MB per run (+~100 MB
#           per mod during per-mod apply checks). Aborts under 5 GiB free.
set -euo pipefail

B="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="$B/outputs/horizon-runtime"
DATA="$RUNTIME/launcher-data"
NATIVE="$B/outputs/horizon-native"
STAGE="$DATA/native/stage"
LAB="$RUNTIME/m1-performance-r4"
MIXINS="$DATA/native/tools/e8cd0aa38cff/bin/horizon-mixins"
TOOLCHAIN="$DATA/rust/1.99.1-aarch64-apple-darwin"
PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
CONTROL="$DATA/versions/native-f42ef42-898af830522b"
REVISION="f42ef42ef6ceccb3c6a20bea2481d87949a51c81"
STACK="$NATIVE/r4-stack.txt"

# id|repo|sha|path in repo (bundle dirs are <path>/mixins/<dir with horizon-mixin.toml>)
MODS=(
  "appleskin_horizon|CayMac97/appleskin|4cd8dfd05f2a911c151401dfd029432ace939c89|."
  "status_effect_hud|CayMac97/status-effect-hud|9342baed4177e278e62cdf9c618be66622768bff|."
  "armor_status|CayMac97/armor-status|b3011de34c62f8c47a1b699f0abfb6d9a1db0f1a|."
  "toggle_sprint|CayMac97/toggle-sprint|c30b952a3c130c253fbeafcec27705b59b414ec0|."
  "light_overlay|CayMac97/light-overlay|38ce37871d02744de3ae78b9a0dd54445593e2ab|."
  "minimap|horizon-rust/horizon-mods|d2de4c18de0cfc4c1e4f193f2ec09b47adb0d236|native/minimap"
  "held_item_info|AltMugen/horizon-held-item-info|406a6499b46086ac642c88dc6a6ef591abd35f26|."
  "chatheads|Domanffe/chatheads|c052d3fbd9e38dcd247c34be5e8f580de42cf94a|."
)

DRY=0; NOMODS=0; ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --no-mods) NOMODS=1 ;;
    --only) ONLY="${2:?--only needs a comma list}"; shift ;;
    --keep) ;;
    -h|--help) sed -n 2,32p "$0"; exit 0 ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
  shift
done

: "${HORIZON_TEST_QUEUE:?refusing to run: HORIZON_TEST_QUEUE is not set (run as a device-queue ticket)}"

mkdir -p "$LAB"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$LAB/build-r4-mods-$STAMP.log"
exec > >(tee -a "$LOG") 2>&1
echo "[r4] start $STAMP queue=$HORIZON_TEST_QUEUE dry=$DRY nomods=$NOMODS only=${ONLY:-all} log=$LOG"

die() { echo "[r4] FAIL: $*" >&2; exit 1; }
free_gib() { df -k "$RUNTIME" | awk 'NR==2{printf "%d", $4/1048576}'; }

[ "$(cat "$STAGE/.horizon-revision")" = "$REVISION" ] || die "pristine stage is not f42ef42"
[ -f "$STACK" ] || die "missing $STACK"
[ -x "$MIXINS" ] || die "missing horizon-mixins tool $MIXINS"
[ "$(free_gib)" -ge 5 ] || die "need >= 5 GiB free, have $(free_gib)"
if [ "$DRY" = 0 ]; then
  for p in horizon-client java cargo rustc xcodebuild; do
    if pgrep -x "$p" >/dev/null; then die "preflight: $p is running (benches?)"; fi
  done
  "$PYTHON" - "$RUNTIME" <<'PY'
import importlib.util, pathlib, sys
path = pathlib.Path(sys.argv[1]) / "run-u9c-makeup-trim.py"
spec = importlib.util.spec_from_file_location("r4_gates", path)
gates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gates)
problems = gates.gate_problems(check_idle=False)
if problems:
    sys.exit("Build gates failed: " + "; ".join(problems))
PY
fi

WORK="$LAB/work-$STAMP"
[ ! -e "$WORK" ] || die "work dir exists"
echo "[r4] rsync pristine -> $WORK"
# The launcher stage already carries generated mixins metadata. It is not
# source: the mixins tool reserves these names when staging another mod set.
rsync -a --exclude target --exclude .git --exclude .horizon-mixins-stage.json \
  --exclude /native-post-build.json "$STAGE/" "$WORK/"

# ---- patch stack -------------------------------------------------------------------------------------------
TOTAL=0; OK=0; FAILS=()
while IFS= read -r name || [ -n "$name" ]; do
  name="${name%%#*}"; name="$(echo "$name" | tr -d '[:space:]')"
  [ -n "$name" ] || continue
  TOTAL=$((TOTAL+1))
  patch="$NATIVE/$name-f42/$name.patch"
  if [ ! -f "$patch" ]; then FAILS+=("$name: missing $patch"); echo "[r4] patch $name MISSING"; continue; fi
  if err="$(cd "$WORK" && git apply --whitespace=nowarn "$patch" 2>&1)"; then
    OK=$((OK+1)); echo "[r4] patch $name ok"
  else
    FAILS+=("$name: $(echo "$err" | head -1)"); echo "[r4] patch $name FAILED: $(echo "$err" | head -1)"
  fi
done < "$STACK"
echo "[r4] patches applied $OK/$TOTAL"
[ "$OK" = "$TOTAL" ] || die "patch stack incomplete: ${FAILS[*]}"

# ---- mods --------------------------------------------------------------------------------------------------
MODS_OK=(); MODS_FAIL=(); SELECTED=()
if [ "$NOMODS" = 0 ]; then
  for m in "${MODS[@]}"; do
    id="${m%%|*}"
    if [ -z "$ONLY" ] || [[ ",$ONLY," == *",$id,"* ]]; then SELECTED+=("$m"); fi
  done
  [ "${#SELECTED[@]}" -gt 0 ] || die "--only matched no mod"
fi

SRC="$LAB/mod-src"       # cache, shared across runs, keyed by repo@sha
BUNDLES="$LAB/bundles-$STAMP"
mkdir -p "$SRC" "$BUNDLES"

# Fetch text files of repo@sha/path via gh api (git blobs, hash-verified). Never executes anything fetched.
fetch_mod() {  # repo sha path dest
  "$PYTHON" -I - "$1" "$2" "$3" "$4" <<'PY'
import base64, hashlib, json, os, subprocess, sys
repo, sha, sub, dest = sys.argv[1:5]
skip = (".hnmod", ".jar", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".icns", ".exe", ".dll", ".so", ".dylib", ".wasm", ".hmod", ".class")
def gh(path):
    return subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True, timeout=120).stdout
tree = json.loads(gh(f"repos/{repo}/git/trees/{sha}?recursive=1"))
if tree.get("truncated"): sys.exit("tree truncated")
prefix = "" if sub in ("", ".") else sub.rstrip("/") + "/"
n = 0
for e in tree["tree"]:
    if e["type"] != "blob" or not e["path"].startswith(prefix): continue
    rel = e["path"][len(prefix):]
    if e["mode"] == "120000" or rel.lower().endswith(skip) or ".." in rel.split("/"): continue
    if e["size"] > 2_000_000: continue
    blob = json.loads(gh(f"repos/{repo}/git/blobs/{e['sha']}"))
    data = base64.b64decode(blob["content"])
    if hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() != e["sha"]:
        sys.exit(f"blob hash mismatch {e['path']}")
    out = os.path.join(dest, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(data); n += 1
if n == 0: sys.exit("no files fetched")
print(f"fetched {n} files")
PY
}

if [ "${#SELECTED[@]}" -gt 0 ]; then
  for m in "${SELECTED[@]}"; do
    IFS='|' read -r id repo sha sub <<<"$m"
    cache="$SRC/${repo//\//__}@$sha"
    if [ ! -f "$cache/.complete" ]; then
      rm -rf "$cache"; mkdir -p "$cache"
      echo "[r4] fetch $id $repo@${sha:0:7}"
      if fetch_mod "$repo" "$sha" "$sub" "$cache" && touch "$cache/.complete"; then :; else
        MODS_FAIL+=("$id: fetch failed"); rm -rf "$cache"; continue
      fi
    fi
    # bundle = the dir holding horizon-mixin.toml; copied to bundles/<id> with horizon_revision repinned to f42
    toml="$(find "$cache/mixins" -name horizon-mixin.toml -not -path '*/.*' 2>/dev/null | head -1)"
    if [ -z "$toml" ]; then MODS_FAIL+=("$id: no mixins/*/horizon-mixin.toml"); continue; fi
    mkdir -p "$BUNDLES/$id"
    rsync -a "$(dirname "$toml")/" "$BUNDLES/$id/"
    "$PYTHON" -I - "$BUNDLES/$id/horizon-mixin.toml" "$REVISION" "$id" <<'PY'
import re, sys
p, rev, want = sys.argv[1:4]
t = open(p).read()
m = re.search(r'(?m)^id\s*=\s*"([^"]+)"', t)
if not m or m.group(1) != want: sys.exit(f"bundle id {m and m.group(1)} != {want}")
t, n = re.subn(r'(?m)^(horizon_revision\s*=\s*)"[0-9a-f]+"', lambda x: x.group(1) + '"' + rev + '"', t)
if n != 1: sys.exit("no [compatibility] horizon_revision to repin")
open(p, "w").write(t)
PY
  done
fi

# static check: every injection `target = "...::fn"` must name a fn that exists in the patched source
FNS="$LAB/fns-$STAMP.txt"
static_check() {  # id -> prints first problem or nothing (fn-name index built once from the patched source)
  [ -f "$FNS" ] || "$PYTHON" -I - "$WORK/crates" "$FNS" <<'PY2'
import os, re, sys
names = set(); pat = re.compile(rb"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)")
for d, _, fs in os.walk(sys.argv[1]):
    for f in fs:
        if f.endswith(".rs"):
            names.update(m.decode() for m in pat.findall(open(os.path.join(d, f), "rb").read()))
open(sys.argv[2], "w").write("\n".join(sorted(names)))
PY2
  "$PYTHON" -I - "$BUNDLES/$1" "$FNS" <<'PY2'
import re, sys
t = open(sys.argv[1] + "/horizon-mixin.toml").read()
have = set(open(sys.argv[2]).read().split())
for tgt in re.findall(r'(?m)^target\s*=\s*"([^"]+)"', t):
    fn = tgt.split("::")[-1]
    if fn not in have: print(f"target fn {fn} not found in source ({tgt})"); break
PY2
}

apply_tool() {  # modsdir out
  PATH="$TOOLCHAIN/bin:$PATH" RUSTC="$TOOLCHAIN/bin/rustc" CARGO_HOME="$DATA/cargo" \
    "$MIXINS" apply --workspace "$WORK" --mods "$1" --out "$2" 2>&1
}

GOOD=()
if [ "${#SELECTED[@]}" -gt 0 ]; then
  for m in "${SELECTED[@]}"; do
    id="${m%%|*}"
    [ -d "$BUNDLES/$id" ] || continue
    if [ "${HORIZON_DRY_NO_CARGO:-0}" = 1 ] && [ "$DRY" = 1 ]; then
      s="$(static_check "$id")"
      if [ -n "$s" ]; then MODS_FAIL+=("$id: $s"); else MODS_OK+=("$id (static only)"); GOOD+=("$id"); fi
      continue
    fi
    one="$LAB/one-$STAMP"; rm -rf "$one" "$LAB/one-mods-$STAMP"; mkdir "$LAB/one-mods-$STAMP"
    cp -R "$BUNDLES/$id" "$LAB/one-mods-$STAMP/$id"
    if err="$(apply_tool "$LAB/one-mods-$STAMP" "$one")"; then MODS_OK+=("$id"); GOOD+=("$id")
    else
      echo "[r4] full mixin diagnostic for $id:"
      printf '%s\n' "$err"
      MODS_FAIL+=("$id: $(echo "$err" | grep -m1 -E 'E_[A-Z_]+|error' || echo "$err" | head -1)")
    fi
    rm -rf "$one" "$LAB/one-mods-$STAMP"
  done
  if [ "${#GOOD[@]}" -gt 0 ] && ! { [ "${HORIZON_DRY_NO_CARGO:-0}" = 1 ] && [ "$DRY" = 1 ]; }; then
    all="$LAB/all-mods-$STAMP"; mkdir "$all"
    for id in "${GOOD[@]}"; do cp -R "$BUNDLES/$id" "$all/$id"; done
    out="$LAB/applied-$STAMP"
    if err="$(apply_tool "$all" "$out")"; then
      rm -rf "$WORK"; mv "$out" "$WORK"
    else
      die "combined mixin apply failed: $(echo "$err" | head -3 | tr '\n' ' ')"
    fi
    rm -rf "$all"
  fi
fi
echo "[r4] mods applied ${#MODS_OK[@]}/${#SELECTED[@]}"
for f in "${MODS_FAIL[@]:-}"; do [ -n "$f" ] && echo "[r4] mod FAIL $f"; done
echo "[r4] summary: patches $OK/$TOTAL, mods ${#MODS_OK[@]}/${#SELECTED[@]}"

# ---- identity (same idea as r3: hash of the final file inventory) ----------------------------------------
IDENT="$("$PYTHON" -I - "$WORK" <<'PY'
import hashlib, json, os, sys
root = sys.argv[1]; inv = {}
for d, ds, fs in os.walk(root):
    ds[:] = [x for x in ds if x not in ("target", ".git")]
    for f in fs:
        p = os.path.join(d, f)
        if os.path.islink(p): continue
        inv[os.path.relpath(p, root)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
print(hashlib.sha256(json.dumps(inv, sort_keys=True).encode()).hexdigest())
PY
)"
SUFFIX=""; [ "$NOMODS" = 1 ] && SUFFIX="-nomods"; [ -n "$ONLY" ] && SUFFIX="-sub"
VERSION="native-f42-m1-r4-${IDENT:0:12}$SUFFIX"
DEST="$DATA/versions/$VERSION"
echo "[r4] source digest $IDENT -> $VERSION"
[ ! -e "$DEST" ] || die "$VERSION already installed"

[ "${#MODS_FAIL[@]}" = 0 ] || die "some mods failed to apply; rerun with --only or --no-mods"
if [ "$DRY" = 1 ]; then
  echo "[r4] DRY RUN done: no cargo, no install. work tree: $WORK"
  echo "$VERSION"
  exit 0
fi

# ---- cargo (flags identical to build-m1-performance-r3.py) ---------------------------------------------------
CLEAN=(env -u RUSTFLAGS -u RUSTDOCFLAGS -u CARGO_ENCODED_RUSTFLAGS -u CARGO_ENCODED_RUSTDOCFLAGS
       -u CARGO_INCREMENTAL -u RUSTC_WRAPPER -u RUSTC_WORKSPACE_WRAPPER -u RUSTUP_TOOLCHAIN)
for v in $(env | grep -o '^CARGO_BUILD_[A-Z_]*'); do CLEAN+=(-u "$v"); done
CLEAN+=(PATH="$TOOLCHAIN/bin:$PATH" RUSTC="$TOOLCHAIN/bin/rustc" CARGO_HOME="$DATA/cargo"
        CARGO_TARGET_DIR="$DATA/native/target" CARGO_BUILD_JOBS=1)
echo "[r4] cargo build --offline --locked --profile fast -p horizon-client --bin horizon-client"
# Own a process group so timeout/cancellation drains Cargo and its rustc children.
CP=""
stop_build() {
  if [ -n "$CP" ] && kill -0 -- "-$CP" 2>/dev/null; then
    kill -TERM -- "-$CP" 2>/dev/null || true
    sleep 5
    kill -KILL -- "-$CP" 2>/dev/null || true
    wait "$CP" 2>/dev/null || true
  fi
}
trap stop_build EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
( cd / && exec "$PYTHON" -c 'import os,sys; os.setsid(); os.execvpe(sys.argv[1], sys.argv[1:], os.environ)' \
    "${CLEAN[@]}" "$TOOLCHAIN/bin/cargo" build --offline --locked --profile fast \
    --manifest-path "$WORK/Cargo.toml" -p horizon-client --bin horizon-client ) > "$LAB/cargo-candidate.log" 2>&1 &
CP=$!; START=$SECONDS
while kill -0 "$CP" 2>/dev/null; do
  if [ $((SECONDS-START)) -gt 2700 ] || [ "$(free_gib)" -lt 4 ]; then die "build stopped (deadline or disk reserve); see $LAB/cargo-candidate.log"; fi
  sleep 10
done
wait "$CP" || die "cargo failed; tail of $LAB/cargo-candidate.log: $(tail -5 "$LAB/cargo-candidate.log" | tr '\n' ' ')"
stop_build
CP=""
echo "[r4] cargo done in $((SECONDS-START)) s"

# ---- install (layout of install_client in the r3 script); does NOT select it ------------------------------
NEW="$DEST.new"; rm -rf "$NEW"; mkdir "$NEW"
cp -p "$DATA/native/target/fast/horizon-client" "$NEW/horizon-client"
cp -p "$CONTROL/horizon-ctl" "$NEW/horizon-ctl"
/bin/cp -cR "$CONTROL/.local" "$NEW/.local"
"$PYTHON" -I - "$CONTROL/native-mods.json" "$NEW" "$IDENT" "$VERSION" "$LAB/mod-src" "${GOOD[*]:-}" "$OK" "$TOTAL" <<'PY'
import hashlib, json, sys
ctl, new, ident, version, _src, good, ok, total = sys.argv[1:9]
meta = json.load(open(ctl))
binary = hashlib.sha256(open(new + "/horizon-client", "rb").read()).hexdigest()
inherited = meta.get("mods", [])
inherited_ids = {m["id"] for m in inherited}
meta.update(build_method="direct-cargo-source-patches", source_patch_digest=ident,
            control_version="native-f42-m1-control-09391c2a8210",
            mods=inherited + [{"id": i, "pinned": True} for i in good.split() if i not in inherited_ids])
json.dump(meta, open(new + "/native-mods.json", "w"), indent=2); open(new + "/native-mods.json", "a").write("\n")
json.dump({"complete": True, "version": version, "source_revision": "f42ef42ef6ceccb3c6a20bea2481d87949a51c81",
           "patches_applied": f"{ok}/{total}", "mods": good.split(), "profile": "fast",
           "rust": "1.99.1", "source_digest": ident, "binary_sha256": binary},
          open(new + "/source-patches.json", "w"), indent=2)
PY
touch "$NEW/.installed"
mv "$NEW" "$DEST"
echo "[r4] installed $DEST (not selected; settings.json untouched)"
echo "$VERSION"
