# Horizon runtime guidance — 2026-11-02

Research only: no game, install, preparation, build or benchmark executed by this unit. Official GitHub release metadata and pinned source inspected over HTTPS.

## Release selection

- Launcher: `launcher@0.2.37`, `c1f308fe62beec70cee597b0483f1e0ee172844c`; staged plan remains current.
- Current published game channel: **Nightly 2026-11-01 · c9d474d**, full revision `c9d474dd9116e84c243f8992d75c11314df56f06`. Source preserved as `nightly-source/2026-11-01-c9d474d`.
- ARM64 asset: <https://github.com/horizon-rust/horizon/releases/download/nightly/horizon-macos-arm64.zip>; GitHub asset ID `699251587`, size `32177226`, SHA-256 `09736c86faf52c3015c021c02d645fccbca1a0d830d01dcfd82345c05693c150`. This URL is mutable: verify against this digest or research a changed release afresh.
- `v0.2.97` is explicitly marked outdated and its notes say shader packs were removed. Do not use it for shader validation.
- Current Nightly **does have** the rewritten GLSL shader loader, plus Horizon’s WGSL format. This does not establish full Mellow/Complementary parity. Mellow `textureGatherOffsets` fix #6177 (`55bacdf9`) is 294 commits after c9d474d; standard Iris macro fix #6934 (`2b6d855d`) is 2166 commits after it, verified with GitHub compare. Issue #6233 reports favorable Mellow/Complementary comparisons on newer main plus fixes, not the published binary. macOS colored-lighting report #6685 concerns c9d474d specifically.

## Isolation and preparation

Keep HOME unchanged. Set absolute `HORIZON_LAUNCHER_HOME`, `HORIZON_HOME`, `HORIZON_LAUNCHER_NO_SELF_UPDATE=1`, plus optional isolated XDG directories. These environment variables are supported; direct game `--home DIR` chooses logs/crash reports, while `--game-dir DIR` chooses worlds/options/packs/mods.

Launcher 0.2.37 verifies signed Nightly checksums. Its CLI uses the synthesized version-list tag `nightly-2026-11-01-c9d474d`, not GitHub alias `nightly`: root’s actual CLI rejected `install nightly` and `outputs/horizon-runtime/versions.json` confirms the exact supported tag. The code-only initial alias assumption was corrected before runtime guidance was delivered. Installed binaries live under `$HORIZON_LAUNCHER_HOME/versions/nightly-2026-11-01-c9d474d/`; preparation is `.local/horizon-client/26.3/` inside that version folder. Installation first uses `versions/.nightly-2026-11-01-c9d474d.partial` and strips the ZIP’s top directory.

```sh
horizon-launcher install nightly-2026-11-01-c9d474d
horizon-launcher prepare --version nightly-2026-11-01-c9d474d --minecraft '/Users/tanushmalhotra/Library/Application Support/ElyPrismLauncher/instances/Tanush-26.3/minecraft'
```

Exact launcher source walks ancestors to `instances` and its parent regardless of the launcher directory’s name, so this ElyPrism path discovers shared assets/libraries. Missing pinned files can still prevent preparation. First preparation needs the pinned server JAR and Java 25. Official launcher resolves/downloads requirements for the owning signed-in account.

Direct preparer interface, if diagnostics require it:

```sh
horizon-prepare --prepare --root RELEASE --output PREPARED --server-jar SERVER --version-json JSON --client-jar CLIENT --libraries-dir LIBS --assets-dir ASSETS --java-home JAVA25 --complete --progress json
horizon-prepare --check --root RELEASE --output PREPARED
```

Asset imports are `sounds`, `panorama`, `fonts`, `packs`, `languages` subcommands with `--root`, `--output`, `--assets-dir`, `--version-json`, `--minecraft-dir`. There is no verified `assets import` command. Preparation writes scratch files to `RELEASE/.local` even with separate output.

## Normal play and checks

Official launcher Play requires owning Microsoft sign-in; offline names are available alongside that account. Launch API instructs other launchers to apply the same owner gate and pass a session. Subsequent user instruction explicitly declined sign-in and requested offline tests. Root verified the installed client advertises local-world and benchmark modes and selected those unchanged built-in modes; the launcher commands below document the launcher interface, not the selected offline execution route. No authentication code changes are proposed.

```sh
horizon-launcher play --version nightly-2026-11-01-c9d474d --world Horizon-Test --creative --arg=--control --arg=--control-socket --arg=/ABSOLUTE/control.sock
horizon-ctl --socket /ABSOLUTE/control.sock state
horizon-ctl --socket /ABSOLUTE/control.sock screenshot /ABSOLUTE/frame.png
```

For persistent same-world shader/mod comparison, use this normal controlled play route, position/time/look controls, screenshot, and `bench`/`fly` (ask that binary’s help for signatures). Choose a disposable new world. Set `HORIZON_SHADER_PACK=filename.zip` before launching to force a shader under the game directory’s `shaderpacks/`; it overrides the UI selection. UI path: Options > Horizon Settings > Shader Packs.

Visible built-in benchmark:

```sh
horizon-launcher play --version nightly-2026-11-01-c9d474d --arg=--benchmark --arg=forest --arg=--control --arg=--control-socket --arg=/ABSOLUTE/control.sock
```

Scenarios: `standard` (all four), `village`, `forest`, `ocean`, `mountain`. Creates/replaces its own marked `horizon-benchmark` world, seed 1234; waits for chunks, settles 2 s, flies each scene 12 s; writes game-folder `benchmarks/` then quits. Disables VSync/frame cap/focus pausing and **skips mod loading**, so unsuitable for native Zoomify acceptance. Resource/shader packs are loaded before benchmarking. Screenshots may be requested while visible.

`--offscreen` renders to a GPU texture without visible window; `--headless` runs with no renderer and cannot measure shader FPS. For on-screen visual testing, omit both.

## Primary sources

- [Nightly metadata](https://api.github.com/repos/horizon-rust/horizon/releases/tags/nightly), [outdated stable notes](https://github.com/horizon-rust/horizon/releases/tag/v0.2.97).
- [Exact launcher installation](https://github.com/horizon-rust/horizon/blob/c1f308fe62beec70cee597b0483f1e0ee172844c/launcher/src/backend.rs), [source discovery](https://github.com/horizon-rust/horizon/blob/c1f308fe62beec70cee597b0483f1e0ee172844c/launcher/src/sources.rs).
- [Nightly launch API](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/docs/api/launch.md), [CLI parser](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client/src/game.rs), [benchmark implementation](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client/src/benchmark.rs).
- [Shader guide](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/docs/shaders.md), [Mellow fix](https://github.com/horizon-rust/horizon/pull/6177), [Iris macros](https://github.com/horizon-rust/horizon/pull/6934), [scene-suite evidence](https://github.com/horizon-rust/horizon/issues/6233), [Mac report](https://github.com/horizon-rust/horizon/issues/6685).

## Preparation failure follow-up (read-only diagnosis)

`prepare-nightly.log` stops at missing required `jtracy-1.14.38-natives-macos-arm64.jar`; Netty kqueue native is optional. The installed `artifacts.rs` already checks both official Maven classifier layout and Prism’s classifier-in-artifact layout. Both jtracy paths are absent, so this is a missing artifact rather than unrecognized Prism naming.

Read-only scan applying manifest OS/ARM rules and both layouts: **67 selected artifacts, 2 missing**: jtracy native and optional Netty kqueue. Official version JSON names required jtracy URL <https://libraries.minecraft.net/com/mojang/jtracy/1.14.38/jtracy-1.14.38-natives-macos-arm64.jar>, size `230827`, SHA1 `e5cad241e2c018c39d2b5e767e201ead40f93309`.

`launcher-data/linked-minecraft/libraries` is a symlink to original ElyPrism `libraries`: never write through it. Root can clone/copy the library tree into an isolated real directory, add the verified official missing jar at `com/mojang/jtracy/1.14.38/jtracy-1.14.38-natives-macos-arm64.jar`, and pass preparer `--libraries-dir ABS/isolated-libraries`. `--minecraft-dir ABS/linked-minecraft` can continue supplying other read-only inputs. `--root RELEASE` keeps imported client/server/scratch cache inside the isolated runtime. `--prepare` resumes checksum-checked import. Do not alter research-lock or weaken native-library requirements. No preparation/download performed by this research unit.

## CPU/GPU attribution: exact c9d474d source

Source facts: macOS uses wgpu’s Metal backend. CPU worker threads generate/load chunks, calculate lighting and construct meshes; GPU passes draw terrain, entities and shader effects. Shader translation/pipeline setup also has CPU work, so a shader change is not exclusively GPU work. Source architecture alone cannot establish this M1’s bottleneck.

Collect with the existing control socket, without another game:

```sh
horizon-ctl --socket /ABSOLUTE/control.sock state
horizon-ctl --socket /ABSOLUTE/control.sock bench 10
horizon-ctl --socket /ABSOLUTE/control.sock stats
```

`state.renderer` reports actual GPU, backend, surface size and present mode. `bench SECONDS` resets statistics, waits that duration and returns frame FPS/percentiles plus `cpu` and `gpu` timing objects (`avg_ms`, `p50_ms`, `p95_ms`, `p99_ms`, `max_ms`). `stats` returns the current summary; `stats reset` returns it then resets. `phases_avg_ms`/`slow_phases_avg_ms` split CPU frame phases into `update`, `tick`, `prepare`, `render`. These are render-thread elapsed phases, not whole-process CPU utilization or total background worker CPU. CPU frame elapsed subtracts acquire/present/pacing waits; FPS still reflects presentation/frame limits. A high CPU timing can include synchronization or scheduling, not exclusively executed instructions.

GPU frame time uses timestamp queries, read back asynchronously a few frames late; unsupported or no samples yields `gpu: null`. Metal pass-boundary markers and delayed query resolution are explicitly implemented. Not every frame necessarily has a GPU sample. F3 debug enables per-pass timing; when available, summaries additionally contain `gpu_passes` (Horizon’s own pass medians). Normal `fly ... raw` and built-in benchmark preserve separate raw CPU/GPU/frame samples.

Inference protocol: compare warm, matched camera/world/render-distance/resolution runs shader OFF versus each shader ON; inspect CPU/GPU times and frame limit/present mode together. Higher GPU time near frame duration suggests GPU constraint; CPU phases near frame duration suggest CPU/synchronization constraint. Neither is a proven bottleneck without these measurements. New-chunk CPU worker pressure and M1 shared-memory/swap contention need separate observations.

Pinned sources: [backend choice](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/gfx.rs#L1302), [chunk workers](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/streaming.rs), [statistics schema](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client/src/control.rs#L419), [control commands](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client/src/game/control.rs#L854), [CPU timing subtraction](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client/src/game.rs#L17198), [Metal GPU timestamps](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/gfx/timing.rs).

## Exact shader activation (c9d474d)

Place the unchanged ZIP under isolated game-dir `shaderpacks/`. Persistent selection is **`horizon-graphics.txt`**, line **`pickedShaderPack:ExactPackFile.zip`**; empty `pickedShaderPack:` disables. Edit only with that game stopped. `shaderPack:` is explicitly ignored as a pre-rewrite key. Iris’s `iris.properties` is not consulted by this selection path. The environment variable `HORIZON_SHADER_PACK=ExactPackFile.zip` overrides persisted selection and is cached once, so restart to change a forced pack. Pack-specific options use `shaderpacks/<pack>.txt`, `NAME=value` lines.

For live UI selection use `horizon-ctl --socket PATH options shader-packs`, then `ui`, and click the row ID the UI returns. `options-get`/`options-set` cover vanilla `options.txt`, explicitly excluding Horizon graphics/controller/extras/mod settings, so they cannot select shaders. Keep resource pack selection in vanilla `resourcePacks` independently.

Sources: [exact key/parser and old-key rejection](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/graphics.rs#L535), [options-set scope](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/settings.rs#L627), [selection precedence](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client/src/game/shader_packs.rs#L71), [live page command](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client/src/game/control.rs#L800).

## Full resource-pack startup timeout: source trace, not a diagnosed crash

Root observed full 52-pack starts exceeding its 120-second deadline before resource-load logs, with roughly 20 MB RSS; root terminated those tests. Those observations do not prove memory exhaustion or an inherent game crash.

Exact synchronous path: `game.rs:19894` calls `game/packs.rs:60 startup_root` before `load_resources`. This **discovers every ZIP/folder in resourcepacks**, reads pack metadata even for unselected packs, selects enabled entries, then calls render `packs.rs:916 resource_root`. This builds/checks `.horizon-cache/resourcepacks/<selection-hash>` through `packs/cache.rs:299`. Cache build first acquires a blocking advisory file lock (`lock.lock()`, line 311), computes selected-pack signatures, validates dependencies, and builds the resource overlay if needed. Only afterward does game resource loading call `Assets::load`, models/UI tables and eventually `load items` logging. Absence of `load items` therefore does not isolate a particular loader function.

Hypotheses to distinguish with a sample captured **before the external deadline**:

1. Advisory cache lock wait: stack in file-lock syscall, with another live holder of that cache lock inode. The mere leftover `.lock` file cannot block: closing/killing its holder releases the OS lock. Never delete lock files while a process might hold them.
2. Discovery/signature/ZIP IO: stack in filesystem reads, SHA256, ZIP central-directory parse or deflate. ZIPs <=250 MiB are hashed in full; larger ones use directory+stamp. Rebuild validates signatures again. Cache growth/overlay file creation distinguishes build progress from pre-build scan.
3. Resource/model work after overlay: stack in asset/model/UI loader. Existing `load items` log occurs later than several core-load operations, so absence alone cannot exclude it.

A proposed recursive ZIP mutex deadlock has **no support in this revision**: render `zip.rs` stores no mutex; clones share immutable directory/tail and each reader has its own position, with Unix positional file reads. Resource overlay has an OS file lock, not a recursive ZIP lock. Pack-folder signature traversal also has canonical active-path cycle detection.

For a true one-pack bisect, put only one ZIP in that run’s resourcepacks directory. Leaving all 52 ZIPs present while changing only the selected list still scans all metadata. Source evidence cannot yet identify which hypothesis caused the deadline.

Sources: [startup ordering](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client/src/game.rs#L19894), [discover then select](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client/src/game/packs.rs#L60), [cache lock and signatures](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/packs/cache.rs#L299), [ZIP reader](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/zip.rs#L171).

## Retina resolution matching (read-only source/bytecode check)

Installed Sodium Extra is `0.9.4+mc26.3`; original `sodium-extra-options.json` has `reduce_resolution_on_mac:true`. Exact installed JAR bytecode, inspected with `java/java-runtime-epsilon/bin/javap -c -p -classpath instances/Tanush-26.3/minecraft/mods/sodium-extra-fabric-0.9.4+mc26.3.jar me.flashyreese.mods.sodiumextra.mixin.reduce_resolution_on_mac.MixinWindow`, checks macOS and that setting, then returns window flags `flags & -8193`. Verbose annotations show it modifies argument 3 of `GpuBackend.createWindow(String,int,int,long)`. This clears bit8192. Installed LWJGL SDL3 binding confirms `SDL_WINDOW_HIGH_PIXEL_DENSITY=8192`; SDL’s official header describes it as enabling a high-pixel-density backbuffer. Thus the setting disables Retina backbuffer request; it is not merely a GUI-scale change.

Horizon c9 creates its window with winit `LogicalSize`, so 1280×720 logical can become 2560×1440 surface pixels on a 2× display. Exact `horizon-graphics.txt` controls are `resolutionScale:50`, `upscaling:native`, `taa:false`; the resolution percentage is clamped50..200, default100. This keeps the logical window size and reduces world rendering to half each surface dimension (1280×720 for a 2560×1440 surface), while HUD remains at the surface resolution. This is the best source-supported world-pixel comparison with the existing Java reduction setting, **pending actual Java framebuffer/F3 confirmation**. It does not establish identical filtering/HUD quality or a measured bottleneck. Surface size reported by `state.renderer.size` can remain 2560×1440 despite reduced world scale.

Sources: [Horizon resolution scale/parser](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/graphics.rs#L494), [world-post scaling](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/gfx.rs#L4552), [logical window size](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client/src/game.rs#L15868), [official SDL flag](https://github.com/libsdl-org/SDL/blob/main/include/SDL3/SDL_video.h), plus installed JAR bytecode (version-specific evidence; no modifications).

## Overlay-build follow-up and shader sidecars

Exact c9 `packs/cache.rs::build` opens/acquires one OS file lock, synchronously hashes/checks, calls `build_overlay_uncached`, revalidates and writes the cache marker, then drops the lock. No `horizon-prepare`, child process, thread spawn, or recursive `cache::build` call exists in that production path. Thus same-path recursive-lock deadlock is not supported by this traced call graph.

A concrete later performance fix is [3ffb7b066385](https://github.com/horizon-rust/horizon/commit/3ffb7b066385), **188 commits after c9**, verified by GitHub compare. Old overlay `mirror` scans every override filename for every visited directory and inflates/writes ZIP entries serially. Fix limits traversal to a BTreeMap prefix range and parallelizes extraction. This supports a falsifiable slow cold-overlay explanation for large selections: sample should show `mirror`, map traversal, ZIP inflation/file IO, and overlay files should advance. It does not establish that this caused the observed timeout. Single physically isolated panorama pack succeeding only narrows the failure to selection size/content or subsequent work.

Shader `.zip.txt` sidecars are supported directly: `chosen_file(name)` returns `name + ".txt"`; parser accepts trimmed `NAME=value` lines, ignores blanks and `#` comments. Actual GLSL loading calls `Pack::open(...).with_chosen(chosen_shader_options(name))` before `load_post`. Read-only check of isolated `Mellow v3.4.1a.zip.txt` found `SMAA=true`, `IMAGE_SHARPENING=true`, `GODRAYS=true`, `COLORED_SHADOWS=true`, `LM_FLICKER=true`, `STAR_STRENGTH=0.75`. These options feed the shader loader; this does not prove every requested shader pass translated or executed correctly. Sources: [sidecar naming/parser](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-shaders/src/options.rs#L328), [actual load with chosen options](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client/src/game/shader_packs.rs#L191).

## Existing settings and RAM audit (exact c9 source)

Horizon’s game is a native Rust executable using `horizon_threads::Allocator`; Prism’s Java heap/GC settings do not cap it. Java25 is used by resource preparation/exporters. Consequently Java `MinMemAlloc`, `MaxMemAlloc`, G1 flags and AlwaysPreTouch preferences are relevant to the existing Java client, not Horizon runtime memory. No verified user-facing global native RAM limit was found in this c9 client’s options/graphics parser; do not invent one.

Read-only actual isolated `mellow-1x`/`makeup-1x` configurations contain selected shader plus `resolutionScale:50`, `upscaling:native`, `taa:false`; omitted settings retain the following source defaults:

| Setting | Default and scope | Quality/performance implications |
|---|---|---|
| `textureBudgetMiB` | 0 means256MiB, block texture array **top mip only**, not total GPU/process RAM | Chooses largest power-of-two sprite size fitting budget. Reducing can downsample high-resolution packs; minimum vanilla16px remains. Raising may preserve pack detail but use more memory. |
| `workers` | 0 means available logical cores minus1, minimum1; battery mode halves auto count | Explicitly reducing concurrency may lower worker scratch/CPU/bandwidth pressure, but slow new chunks. Not a render-detail reduction. |
| `lodDistance` | 0, disabled | Enabling far terrain adds work/memory and visible distance. |
| `chunkUpdates` / `uploadBudgetKiB` | 0, unlimited ready mesh count/bytes per frame | Throttles per-frame uploads, not total resident RAM; may improve pacing or delay terrain appearance. |
| `resolutionScale` |100% surface axes; current tests50% | Render-target/shader cost and world resolution change.50% already justified against existing Java Retina reduction, pending actual Java framebuffer confirmation. |
| `taa` / `upscaling` / `fxaa` |false/native/false | History/render targets and visual filtering; do not change silently. |
| `translucentBatching` |false | True allocates separate translucent arenas for fewer draw calls, trading extra GPU memory. |
| `shadowCache` |false | Optional shadow reuse affects shader work; enabling must be visually validated for stale shadows. |
| `hdr` / `screenshotQuality` |false /1 | HDR formats/targets and scaled screenshot peaks, not a blanket memory cap. |

Resident world columns and protochunks unload by streaming/render radius, with extra/forced bands; no separate user-facing resident-byte budget appeared in these controls. Render/simulation-distance reductions alter scene coverage or world behavior and must be presented as quality changes. Worker threads automatically release idle generator/mesher buffers and return free allocator pages when all workers idle. Disk caches (overlay/sprites/derived tables) improve reuse; deleting them is not a demonstrated RAM optimization and may worsen startup.

Default256MiB block budget excludes other GPU textures, mip levels, animation frames, shader render targets, meshes and CPU-side structures, so it cannot be compared directly with Java’s3GiB heap. On unified-memory M1, process RSS alone likewise does not fully describe GPU/system pressure. No bottleneck conclusion follows from settings alone. Existing Xcode background workload remains authorized by the user; measure stability under that workload.

Sources: [graphics fields/defaults/parser](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/graphics.rs#L460), [workers](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/graphics.rs#L755), [texture budget](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/sprites.rs#L103), [range unloading and idle buffer release](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/streaming.rs#L673), [native allocator](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client/src/main.rs#L7).

## Mellow50% visual failure: source-supported cause

User/root confirmed Mellow at50% shows world only in bottom-left quarter with streaks; Mellow100% fills frame correctly; MakeUp50% fills frame. Mellow50% FPS observations are invalid as successful-rendering benchmarks.

Exact unchanged Mellow3.4.1a ZIP source `shaders/program/final.fsh`: with `IMAGE_SHARPENING=true`, line472 executes `CAS(colortex0)`. CAS line384 sets `ivec2 Coords=ivec2(gl_FragCoord.xy)` and line385 directly `texelFetch(Sampler,Coords,0)` plus neighboring integer fetches. With sharpening disabled, line474 instead uses normalized `texture(colortex0,texcoord)`.

Exact c9 `gfx/pack_post.rs::run` receives scaled world size and full surface/window size separately: line3588 resizes its colortex targets to scaled `size`; line3616 updates uniforms using scaled `size`; final-pass output line3801 chooses `window` and line3814 attaches full screen. Consequently at50%, final’s pixel coordinates range over2560×1440 while sampled colortex0 is1280×720. Direct integer fetches are valid only across the lower-left quarter. This mismatch closely explains observed region/streaks and why normalized-sampling MakeUp can differ. Source reasoning is strong; one controlled option diagnostic can confirm its role rather than assuming every artifact shares this cause.

Diagnostic, not a recommendation: same camera/time/50% scale, change only copied sidecar `IMAGE_SHARPENING=false`, preserve SMAA and every other setting, capture frame, then restore. Correct normalized-UV image supports the CAS-coordinate explanation; remaining corruption requires checking SMAA/other gl_FragCoord consumers. Disabling sharpening changes requested appearance, so it is **not** a fidelity-preserving fix. Current option-preserving workaround is Mellow100%; its world resolution/cost differs from the Java1× target and must be reported. No ZIP edits made by this research unit.

Targeted upstream issue search found no matching specific fix. Current main `pack_post.rs` still chooses `window` for final output (observed around line3952); therefore merely moving to main is not established as a fix. A proper engine correction could render final at world size before world-to-surface upscale, but that requires implementation and shader tests; it is not a verified workaround here.

Sources: [c9 final target selection](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/gfx/pack_post.rs#L3798), [c9 target size/uniform update](https://github.com/horizon-rust/horizon/blob/c9d474dd9116e84c243f8992d75c11314df56f06/crates/horizon-client-render/src/gfx/pack_post.rs#L3588), unchanged local Mellow ZIP and copied option sidecar. No device tests or source changes performed.
