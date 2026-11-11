# Native utility build plan — Zoom first, f42

Research-only preparation for the8GB M1. No compiler, launcher, game, build, test, install or device profiling was run by this unit. Root owns the device queue. Commands below describe later work after a queued capacity check; they have not been executed here.

## Feasibility and immediate blockers

A C-key hold/scroll Zoom pilot is a plausible small **source change**, but installing it requires a compiled native client. The f42 distribution contains executables/preparer support, not reusable Rust engine object libraries. No prebuilt native-engine cache service was verified. The launcher can reuse a previously built identical native version or matching local Cargo artifacts; focused checks found no `native/`, `rust/` or `cargo/` build-cache directories in this isolated launcher home. Therefore plan a **first full game dependency build**, not a small plugin link. Existing standalone Zoom tests/Rust1.95 artifacts do not provide the engine cache.

The last known8–11GiB free disk space does not establish capacity. Source is about63MB unpacked according to upstream; Rust components, Cargo crate downloads, mixin tool, staging, dependency object files, incremental data and final native version are additional. Build artifacts are the uncertain large component and can reach multiple GiB; first building both fast and release retains separate artifact sets. A conservative planning allowance is **several to more than10GiB total build working space**, explicitly an unmeasured estimate rather than a measured requirement. Current capacity and peak usage must be measured under the queue before committing to an unattended cold build. Do not delete unrelated files or original saves to make room.

On8GB RAM, start with **`CARGO_BUILD_JOBS=1`** (the launcher explicitly preserves this setting). This limits simultaneous Cargo units, not necessarily LLVM threads or linker memory; one large game crate/link can still page heavily. Peak RAM is not known. Use normal background workload only as authorized, but do not compile during another benchmark/queue turn. Leave capacity for swap; record free disk and memory pressure before/through the attempt and stop cleanly if capacity becomes unsafe. No credible completion-time promise can be made from upstream's mixed20–30minute first-build notice and faster developer-machine measurements.

## Verified source/toolchain contract

Installed official launcher is `launcher@0.2.37`, source `c1f308fe62beec70cee597b0483f1e0ee172844c`; game target is `f42ef42ef6ceccb3c6a20bea2481d87949a51c81`, installed tag `nightly-2026-11-03-f42ef42`. Both installed-launcher source and f42 source select **Rust1.99.1**, official macOSARM64 rustc/cargo/rust-std archives with SHA256 pins, under `HORIZON_LAUNCHER_HOME/rust/`; downloaded crates use that home's `cargo/`. The existing workspace Rust1.95.0 is **not automatically reused**. This is not a claim that1.95 cannot compile any manual path; the official builder chooses its own pinned compiler and scrubs compiler-wrapper/flag overrides. It leaves system HOME, shell profiles and the user's Rust installation alone.

The launcher uses the system macOS linker/Command Line Tools, builds horizon-mixins once at the chosen pinned commit, downloads a clean exact-revision source tree, stages mixins and runs a locked Cargo game build. Its built-in mixins floor is `ddd9700b21997c95d95ac6ee5ecafe3830cf622a`; bundle pins are reconciled against that floor. The game needs prepared resources before the pipeline runs. Generated build outputs live under the canonicalized isolated launcher home:

- `native/source/<commit>/`, `native/stage/`, `native/tools/<mixins-commit>/`;
- `native/target/fast/` or `native/target/release/`, `native/build.log`, build records;
- a fresh installed `versions/native-<revision>-<key>/` with resources cloned where APFS supports it and `native-mods.json` provenance.

The cache key includes engine revision, compiler version, mixins revision, profile/features and source bytes. Original release files remain separate; the explicitly targeted disposable instance selects the native build. Source copying/repinning happens in staging, not in the original pilot files. [Installed launcher's build pipeline](https://github.com/horizon-rust/horizon/blob/c1f308fe62beec70cee597b0483f1e0ee172844c/launcher/src/native_mods.rs), [pinned compiler/isolation/job override](https://github.com/horizon-rust/horizon/blob/c1f308fe62beec70cee597b0483f1e0ee172844c/launcher/src/rust_toolchain.rs), [exact build-cache root](https://github.com/horizon-rust/horizon/blob/c1f308fe62beec70cee597b0483f1e0ee172844c/launcher/src/backend.rs#L568).

### Profiles and comparison limits

| CLI profile | Actual Cargo build | Appropriate use |
| --- | --- | --- |
|`performance`|`--profile fast`, optimized,16codegen units, incremental, no cross-crate LTO|First playable utility pilot and incremental development|
|`dev`|fast plus `--config profile.fast.package.horizon-client.opt-level=0`|Functional iteration only; upstream reports materially slower game logic|
|`release`|`--profile release`, thin LTO, one codegen unit|Final performance validation if capacity permits; slower cold/incremental builds|

The named performance profile is not identical to the official release profile. Do not attribute an FPS difference between native-fast and official-release solely to Zoom. For overhead validation use matching-profile control/native builds, or a final release-profile pilot. Do not build every profile speculatively on the limited disk. Verified underlying game command is `cargo build --locked --profile <fast|release> [--config ...] [--features horizon-client/mods if the source defines it] -p horizon-client --bin horizon-client`, with the builder's target directory. Do not guess features or alter Cargo.lock to suppress failures. [Exact installed compiler command/profile selection](https://github.com/horizon-rust/horizon/blob/c1f308fe62beec70cee597b0483f1e0ee172844c/launcher/src/native_mods.rs#L1259).

## Resolve the existing pilot's packaging before building

Existing source is `outputs/horizon-native/zoom-pilot/source/`, preserving the official MIT Zoom subtree with C default,1.5× wheel steps and1–10range. Its `compatibility.json` says minimum hooks1 and tested engine `6f8c7a0e5d531d3834c4d0be4659a1db8e7e5c2a`. f42 declares native hooks359, satisfying that numerical minimum; this does not prove compilation or behavior.

**Important input trap:** the launcher does not consume `compatibility.json`. A raw `mixins/zoom/horizon-mixin.toml` folder sets `hooks=None` and pins its old `[compatibility] horizon_revision`. Merely adding `--version nightly-2026-11-03-f42ef42` to that raw-folder command does not guarantee an f42 engine. The launcher only reads the minimum hooks field from an unpacked `.hnmod`'s **`horizon-native.json`**.

Prepare a fresh unpacked local bundle, leaving pilot source/provenance untouched:

```
outputs/horizon-native/zoom-f42-input/
  horizon-native.json
  mixins/zoom/horizon-mixin.toml
  mixins/zoom/{runtime,key,wheel,zoom,list,settings,click}.rs
  mixins/zoom/LICENSE
```

The official packager format is `{"schema":1,"id":"zoom","version":"2.0.0","game":"26.3","horizon":"6f8c7a0e5d531d3834c4d0be4659a1db8e7e5c2a","mixins":"0d6b103c70633d8fd9443d8d0acd3aadaacedb06","hooks":1}` for this copied pilot's existing metadata. Its Horizon field must match the copied TOML's tested pin. With hooks present, the launcher can choose the explicitly requested base if its hooks suffice, then repin its own copied staging manifest. Alternatively a deliberately reviewed new raw bundle can explicitly target f42, but that is a recorded target change, not proof that it was previously tested. Do not use `--allow-version-mismatch` as the default solution. Preserve the MIT license and hash every copied file; the modified local artifact must not reuse the upstream published artifact's checksum.

Official packager source at registry commit `bc40e7bafeee66c57a2013617bf893ca8e4b2154` shows this JSON shape and puts LICENSE under `mixins/<id>/LICENSE`. It packages source without compiling; the existing partial subtree does not itself include its shared packaging script/layout. A small local deterministic packager can follow this verified format, or the pinned official script can operate in a properly staged native/ layout after review. [Official package implementation](https://github.com/horizon-rust/horizon-mods/blob/bc40e7bafeee66c57a2013617bf893ca8e4b2154/native/tools/native.py), [launcher raw/unpacked input handling](https://github.com/horizon-rust/horizon/blob/c1f308fe62beec70cee597b0483f1e0ee172844c/launcher/src/native_mods.rs#L481).

## Exact later command plan

The existing `outputs/horizon-runtime/launch-isolated.command` forwards arguments with the verified isolation environment and self-update disabled. All commands below write only within that isolated launcher/game area; no HOME/CODEX_HOME/global PATH changes are required. Run them only in a granted device-queue turn after source review and capacity checks, with no game running during the cold build. Create the disposable instance only if absent:

```sh
TASK_ROOT='/Users/tanushmalhotra/Library/Application Support/ElyPrismLauncher'
"$TASK_ROOT/outputs/horizon-runtime/launch-isolated.command" instance create Horizon-Zoom-Pilot
env CARGO_BUILD_JOBS=1 \
  "$TASK_ROOT/outputs/horizon-runtime/launch-isolated.command" native-build \
  "$TASK_ROOT/outputs/horizon-native/zoom-f42-input" \
  --instance Horizon-Zoom-Pilot \
  --version nightly-2026-11-03-f42ef42 \
  --profile performance --trust-native-code
```

The CLI arguments are verified against the **installed launcher's source**, not assumed from a newer launcher. Native code runs with the user's permissions; the trust flag describes that execution after reviewing the actual copied code. This plan does not request an additional approval solely because external docs say one is needed; root must apply the session's existing authorization and tool approval rules. [Installed CLI parser](https://github.com/horizon-rust/horizon/blob/c1f308fe62beec70cee597b0483f1e0ee172844c/launcher/src/cli.rs#L783).

Before any gameplay test, inspect the resulting `native-mods.json`: `base` must name the intended f42 Nightly and `horizon` must be the full f42 commit; copied helper/source digests, compiler, profile and mixins must match the actual build. Record its exact native version/executable SHA256. A successful build on an older commit fails this target's acceptance even if it launches. Preserve build.log before another attempt replaces it. No launch/authentication path is included in the build command.

## Zoom acceptance and deliberately unresolved gaps

Use the already owned disposable test world and isolated native profile. First prove native mod listed/enabled and the compiled f42 identity. Then verify C press starts4× zoom, wheel changes by1.5×, wheel-down reaches1×, release restores view, re-press resets to4×, hotbar does not scroll while zoom owns the wheel, and no sticky state after menu/focus transitions. Check disabled mod behavior, saved chosen key and settings persistence, slower aiming and smooth transition. Capture matching screenshots/world/hand/HUD states; keep actual physical resolution and all resource/shader settings fixed. These are future acceptance checks, not passes.

This is not a complete Zoomify conversion: f42's native zoom path still clamps1–10, gives spyglass precedence, and exposes its own smoother/turn controls. The user's Java Zoomify ten-step/high-range behavior (4×1.5¹⁰≈230.66×), exact interpolation, secondary binding/toggle semantics, hand FOV and spyglass composition remain unresolved. Do not extend only the pilot's MAX constant when the engine clamps it anyway. Reuse existing meaningful pilot unit checks, but actual native hook integration must be checked in the built game. [f42 clamp](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game/native_hooks.rs#L9799), [local detailed Zoomify evidence](zoomify-pilot.md).

Freecam and fullbright key parity come after this one pilot. Reuse the engine/compiler cache only when hashes/profile remain compatible; review each additional native source/dependency and its hooks. A built-in fullbright checkbox is not GammaUtils key/step/night-vision parity, and a detached-camera hook is not complete Freecam. No bulk port/build or runtime parity claim follows from this plan.
