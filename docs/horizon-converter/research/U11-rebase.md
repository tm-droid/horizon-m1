# U11 — r5 stack on nightly 66f3981

2026-11-06. Source revision `66f3981f522b24c250b21523a70080965b940424` at
`outputs/horizon-src-nightly/nightly-2026-11-05-66f3981` remains pristine.
The rebase is source-validated, not compiled or runtime-validated. No game, Cargo,
rustc, or device workload was started for this preparation.

## Result and original-stack accounting

`outputs/horizon-native/r5-stack.txt` contains thirteen patches in application
order. All thirteen passed `git apply --check` followed by actual sequential
`git apply --whitespace=nowarn` on a second fresh source copy. The other four
original r4 patches are already upstream; applying them again would overwrite
newer behavior or duplicate fields/functions.

| Original r4 patch | r5 handling |
|---|---|
| cloud-prep | Existing 66f3981 port retained |
| shadow-scratch | Existing port retained; before shadow-dedup |
| qos-backport | Upstream-covered; no duplicate patch |
| jobpool-qos | Existing 66f3981 port retained |
| sprite-compress | Upstream-covered; no duplicate patch |
| emissive-bsearch | Existing 66f3981 port retained |
| pass-merge | Existing 66f3981 port retained |
| shadow-dedup | Existing 66f3981 port retained |
| particle-cull | Existing 66f3981 port retained |
| adaptive-upload | Existing 66f3981 port retained |
| pbr-cpu-drop | Existing 66f3981 port retained |
| anim-frame-compact | Hand-ported; keeps nightly material animation state |
| colortex-lazy-b | Upstream-covered, including newer single-side clear handling |
| arena-thresholds | Original patch applies unchanged; copied to 66f3981 directory |
| audio-cache | Original patch applies unchanged; copied to 66f3981 directory |
| a66f8fa2 | Upstream-covered, with newer shadow reach/margin behavior retained |
| composite-overwrite | Hand-ported conservatively to the newer render path |

## Upstream coverage evidence

- **QoS:** nightly `horizon-client-render/src/lod.rs` has `Shared.near_loading`,
  `step_behind`, startup `far_terrain_current` calls for far sampling/meshing, and
  the shared-state update from `set_near_loading`. `horizon-threads/src/lib.rs`
  has utility QoS on Apple and the matching default-QoS restoration. This covers
  the complete f42 backport's behavior, while leaving newer LOD logic intact.
- **Sprite compression:** nightly `horizon-client-render/src/assets.rs` already
  contains `SpritePixels` with shared raw/compressed storage and reconstruction.
  `horizon-client/src/game.rs` calls `pixels.pack()` after renderer creation and
  uses `pixels.get()` for both prepared textures and renderer recreation.
- **Lazy B textures:** nightly `gfx/pack_post.rs` tracks `doubled` and
  `shadow_doubled` from alternate render writes and explicit flips. It shares A
  with B when no alternate texture is needed and passes the shadow mask into
  `ShadowTargets::new`. `gfx/pack_shadow.rs` likewise shares shadowcolor views.
  Nightly additionally avoids redundant single-side initialization/clear work.
- **Shadow caster culling:** nightly `gfx.rs` has `ShadowCull`, `shadow_casters`,
  the `Cull::tight` hook and the camera-view caster test. `gfx/resident.rs`
  respects the hook. Native packs use `view_casters: false`; translated packs use
  `true`. Nightly adds reach and a measured 1.15-block caster margin, so the older
  patch must not replace that implementation.

## Port adaptations

Animation-frame compression wraps only the color frame store. It preserves
nightly's `materials` field, material accessors, material-animation collection,
and all newer animation tests. The GPU animator takes its color mip chains
before `pack_animations` compresses the shared CPU copy. The original four
round-trip/sharing/compression tests are carried in the new patch.

Composite-overwrite keeps nightly's forced-flip XOR semantics. The discard scan
was inserted before its newer texture-target helper. Full coverage still
requires an unmoved quad, no geometry stage, full scale, no fragment kill and
no blending. Additionally, every target must write **all RGBA channels**:
nightly can mask alpha writes for emulated RGB buffers, so those passes retain
`Load` even if their quad covers the screen. The original quad-coverage test is
carried in the patch. This deliberately trades a few possible optimizations for
safe preservation of attachment contents.

## Build entry point

`outputs/horizon-runtime/build-r5-nightly.py` is a new queue-only driver. It pins
the source commit, refuses a dirty pristine tree, applies the thirteen ordered
patches in a fresh work directory, hashes the resulting source, and installs
`native-66f3981-m1-r5-<digest12>` without changing launcher selection. It uses the
existing build supervisor from `build-nightly-6475f62.py` for process-group
cleanup, cancellation, a 45-minute deadline, a 4 GiB in-build reserve, cleaned
compiler environment, jobs=1, and isolated Rust 1.99.1. It checks the standard
AC/lock/display/thermal/build/game/5 GiB gates before a real build. Matching
nightly resources and `horizon-ctl` are cloned from the already installed and
prepared `nightly-2026-11-05-66f3981`; it never borrows f42 resources.

Future invocation through the shared queue (framework Python):

```sh
env HORIZON_TEST_QUEUE=1 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
  outputs/horizon-runtime/build-r5-nightly.py --dry-run
# Same command without --dry-run compiles and installs; do not overlap benchmarks.
```

`--dry-run` still creates a disposable source/status directory; it runs no
Cargo and installs nothing. Without the queue environment, the driver exits
before filesystem changes. Missing offline dependencies are a reported build
failure; the driver does not fetch them automatically.

The trial explicitly has **no injected native mods**. It does not claim to carry
f42's zoom/CEM aliases or the seven optional QoL mods. Keep r3 selected until
runtime/visual checks and any desired mod porting are complete.

## Checks and artifacts

- Fresh sequential `git apply --check` + `git apply --whitespace=nowarn`:
  **13/13 pass**, no reject files. Verification source:
  `outputs/horizon-native/u11-verify-66f3981`.
- Python `ast.parse` on the new driver: **pass**.
- `build-r5-nightly.py --help`: **exit 0**.
- No-queue `build-r5-nightly.py --dry-run`: **exit 1**, expected refusal before
  source staging.
- `git -C outputs/horizon-src-nightly/nightly-2026-11-05-66f3981 status --porcelain`:
  **empty**, pristine source unchanged.
- Earlier nine ports checkpointed under
  `outputs/horizon-native/u11-checkpoint-20261106` before edits. Original f42
  patches and the existing nine nightly ports were not modified.
- Rust compilation, Rust tests, shader loading, screenshots, and performance
  remain unverified; the coordinator owns queued device execution.

## Overnight build preparation update (2026-11-07)
The initial real build stopped before compilation because the isolated offline Cargo cache lacked mio1.2.4. Cargo fetch --locked --target aarch64-apple-darwin subsequently completed through the device queue over normal TLS, including the remaining lockfile-pinned dependencies. No lockfile/source edits were made for fetching. The build driver now uses a stable candidate-source workspace so Cargo path dependencies can reuse compilation state across revisions, while checkpointing the prior source and keeping a fresh APFS source snapshot for every attempt. Pristine source identity checks, ordered patch application, before/after inventories, and unselected atomic installation remain enforced. Actual incremental-build time savings are unmeasured.

## Shared Cargo cache correction
The next attempt failed with E0599 at material_condition/library.rs164, despite positive_y_bounds existing in pristine/candidate horizon-core graph/mod.rs719 (identical SHA af1ef59a8ab0f8fe503b10f92698b4f0e28118f5080d147273bdbbcfbc131330). The reused horizon-core fingerprint was from r4 at23:18:30; source mtimes were19:23:00. Cargo used workspace-relative depfiles and checksum:false. Consequently stable-path reuse alone was insufficient. The driver now touches every copied local input after patching, before snapshot/inventory/build, forcing local crate freshness against the shared target while retaining registry caches. No Rust code or pristine tree was changed. The toolchain lib path is supplied for rust-objcopy's existing libLLVM.dylib. AST passed; corrected ticket158 explicitly compiled horizon-core and world. Runtime/build completion remains pending.

## Corrected build passed
Ticket158 completed exit0, cleanup_verified:true,847.14seconds (Cargo14m06s). Installed native-66f3981-m1-r5-b8923717b90c, unselected. BinarySHA256376fcaa5875b5d17322efc9aa17cb761351fc2e9a1c4569b9a48d55bcd2d1e17. No stripping/libLLVM warning in corrected build. All13patches applied and source content remained unchanged during compilation. Installed wrapper `--cases=n-daybreak020 --rounds 1 --tag r5screen1107 --dry-run` exit0: exactly1run, inputcheckOK. Ticket159 runs MakeUp+Daybreak020 isolated screen next. Rust unit tests remain unrun; successful client compilation is not a test-suite claim.

## Runtime result and verdict
`run-r5-native-packs.py --version native-66f3981-m1-r5-b8923717b90c --rounds 1 --tag r5screen1107` followed by `--resume`:2/2valid, each client exit0. MakeUp52.57static/41.03flightFPS; Daybreak02046.8/43.5. Positive MakeUp6program and nativeDaybreak6stage loading evidence; screenshots inspected, no blank/fallback render. Tables at outputs/horizon-runtime/u12-native-r5screen1107.tables.md. A disk gate paused before the second case; old generatedHorizon incremental caches were removed through ticket160 and successfulMakeUp was not repeated. Daily stays r3+MakeUptrim: this is compatibility screening, not paired proof of a nightly speedup, and this trial lacks injectedZoom/CEM/QoL. Rustunit tests remain unrun. Finalqueueidle, no game/cargo/rustc,8.28GiBfree.
