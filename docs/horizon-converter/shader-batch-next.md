# Next combined-stack shader comparison — 2026-11-04

Target the already prepared official ARM64 Horizon `f42ef42ef6ceccb3c6a20bea2481d87949a51c81`, keeping the selected resource packs together. Test **MakeUp Ultra Fast 9.6**, then **Miniature 2.19**. These are candidate looks, not appearance-preserving replacements already approved by a visual comparison. Keep Complementary Reimagined as a later demanding reference; the user named it as an example rather than the sole goal.

## Why these two

| Candidate | Evidence and purpose | Local input |
| --- | --- | --- |
| MakeUp Ultra Fast 9.6 | Its author describes a performance-oriented shader intended for lower-spec systems. It is already the user's known Java shader according to project instructions, making a matched comparison useful. This description is not proof of Horizon/M1 speed. | ZIP SHA256 `71319ea5d0ad114143ef1c334890e315dbf1eeb2318d6bc35f3e5021fb3c8ba8`; preserve its existing `.zip.txt` sidecar. |
| Miniature 2.19 | Its author describes a lightweight, Minecraft-like appearance with blocky shadows and reflections. It provides a different simple aesthetic to compare without assuming Mellow will be chosen. | ZIP SHA256 `5f224e907657f3ffd95d37e37c27e555deef64fa56da1e13374f2c295241d7f0`; no sidecar currently present, so record defaults explicitly. |

Both files exist in the Java shaderpacks directory and have `shaders/` at the archive root. Their source stages are vertex/fragment; this inspection does not prove translation or runtime compatibility. [MakeUp author repository](https://github.com/javiergcim/MakeUpUltraFast), [Miniature author repository](https://github.com/mateuskreuch/minecraft-miniature-shader), [Miniature author's project description](https://www.curseforge.com/minecraft/shaders/miniature-shader).

## Existing evidence must not become a misleading ranking

The old `makeup-1x` result used **50% world resolution**, despite its name. Its approximately50.93FPS is not a native-resolution, quality-preserving baseline. Old Mellow runs also include50% scale cases already invalidated for layout corruption. `complementary-bare` loaded nine programs in the old c9 build and reported approximately8.93FPS, but activation/visual parity remains unverified and it is not a matched f42 combined-stack result. Do not derive comparative performance percentages from these records.

Local evidence: `outputs/horizon-runtime/tests/{makeup-1x,complementary-bare,mellow-1x,mellow-cap60-auto}/{result.json,console.log}`. MakeUp and Complementary logs both contain `gbuffers_clouds: writes no buffer; skipped`. That message alone does not distinguish an intentionally empty shader from a lost required effect; inspect the shader and images. A completed harness run does not prove complete shader activation.

## Verified f42 loading boundaries and bug signatures

Horizon-native WGSL packs and Iris/OptiFine GLSL packs use separate loaders; native shader API documentation is not evidence that an Iris pack is fully supported. The pinned Iris loader expects a root `shaders/` directory. Its program loader can skip individual programs after preprocessing/translation errors; a shader name appearing in options is insufficient acceptance. Geometry stages are supported only in the shadow terrain/entity path in this loader. Watch for `program: skipped`, source diagnostics, geometry-stage rejection, missing expected programs, empty shadow buffers and image corruption. [Pinned format distinction](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/docs/shaders.md#L1), [pinned archive loader](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-shaders/src/pack.rs#L61), [pinned program rejection paths](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-shaders/src/post.rs#L1033).

The specific `found Interpolation(Flat)` report belongs to an older c9 nightly. Upstream documents an ancestor fix in f42 for interface-block qualifiers; do not automatically classify it as an unchanged f42 limitation. This upstream report is not proof that every installed pack compiles. [Issue8174 and maintainer reproduction](https://github.com/horizon-rust/horizon/issues/8174).

The existing Mellow50% right-half streaks/quarter-size scene are consistent with its CAS final pass indexing the scaled color texture using full-surface `gl_FragCoord`. The earlier local audit records the exact source and uncertainty in `runtime-research-2026-11-02.md`. Keep100% native resolution for new comparisons. Disabling sharpening or changing resolution would change the requested appearance; neither is a validated fidelity-preserving repair. No Mellow adapter was written here.

## Small acceptance batch

1. Reuse the full-stack baseline's f42 build, pack order, FOV95, cloud range64,12/8 distances, native100% scale, auto workers, efficient pacing,60FPS cap, camera and full-terrain gate. Keep shader ZIPs/options unchanged in independent copied profiles.
2. Capture loaded programs and all skipped/error diagnostics. Review the complete frame, terrain extent, cow appearance, water/reflections, sky/clouds and shadows before judging timings. A short daytime and water view adds more value than checking every pack separately.
3. Compare static frame-time distributions and the same streaming flight; record CPU/GPU times, memory and background load. Do not infer maximum throughput from a capped60FPS run. If a shader cannot hold the cap or visibly breaks, isolate that shader or its failing stage rather than retesting every mod.
4. Preserve all failures and report appearance differences for the user's later choice. Keep GammaUtils/fullbright parity unresolved until its actual rendered state is established. Test Complementary later if useful as a demanding quality reference, without promising high FPS from the Rust rewrite alone.

No game launches, benchmarks, builds, installations or shader edits were performed by this research task.
