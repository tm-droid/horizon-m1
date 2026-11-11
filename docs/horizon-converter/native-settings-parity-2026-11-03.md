# Native settings parity — 2026-11-03

Target: official Horizon commit `f42ef42ef6ceccb3c6a20bea2481d87949a51c81`. Read-only audit of current closed Java instance `instances/Tanush-26.3/minecraft/`. No runtime settings, original files, installations or converter tools changed. No builds, launches, benchmarks or tests performed.

## Consequential findings

The current Java FOV is **95 degrees**, represented on disk as `fov:0.625`. A fresh native options file defaults to70 degrees. **Horizon already understands Java's normalized on-disk representation**; copying0.625 verbatim is correct. Its control/API typed value instead expects95. Confusing these two interfaces would produce an invalid or dramatically different view. The current benchmark-only12/8/60/100% preset is not an actual-setup visual baseline.

Java uses cloudRange64; native default is128. Java VSync isfalse; native default istrue. Explicitly carry these values before future parity measurements. FOV and cloud range affect visible content/work; default mismatches invalidate claims of equivalent workload.

Gamma is **absent from current Java options.txt**, while `config/gammautils.json` stores `gamma.value:15.0`, `defaultGamma:100`, `toggledGamma:1500`, `resetOnClose:false`. This is evidence of configured brightness modification, not proof of the last rendered state. Native gamma is constrained to0..1 and defaults0.5. Do not insert15, silently clamp it, infer a fullbright setting from the keybinding, or claim default brightness parity. Resolve the actual appearance against native fullbright/shader behavior separately.

## Encoding and support matrix

“Verbatim” below means exact option-file value transfer into an isolated native options file, retaining source provenance and version. It does not mean identical rendered pixels have been established.

| Feature | Current raw Java value | f42 file encoding / typed value | Support and action |
|---|---|---|---|
| FOV | `fov:0.625` | same on disk; typed/API95° | Native decode `x*40+70`, encode inverse; verbatim, not95 on disk. Default70°. |
| Dynamic FOV | `fovEffectScale:1.0` | same scalar1.0 | Parser and `game/fov.rs` consumer verified. Verbatim. |
| View bobbing | `bobView:true` | same boolean | `bob_matrix` receives view_bobbing. Verbatim. |
| Sensitivity | `mouseSensitivity:0.5` | same0..1 scalar | Settings parsed and passed into mouse input. Verbatim; feel still needs runtime comparison. |
| Gamma | **missing** | native default0.5; valid0..1 | Manual gap because GammaUtils15.0 exists. Do not fabricate a source line. |
| Entity distance | `entityDistanceScaling:1.0` | same scalar; native0.5..5 in0.25 steps | Current1.0 exactly representable. Verbatim; other values require round-trip validation, not quiet rounding. |
| Particles | `particles:0` | same enum ID0/1/2 |0=all; runtime consumes setting. Verbatim. Do not copy a performance preset's1/2. |
| Clouds | `renderClouds:"true"` | same quoted name; allowed false/fast/true | Runtime draws clouds and checks fast explicitly. Verbatim. |
| Cloud range | `cloudRange:64` | same integer2..128 | Current64 accepted; default128 is different. Verbatim. |
| Graphics | `graphicsPreset:"custom"` | same quoted enum fast/fancy/fabulous/custom | Supported metadata/config value, not one switch proving all effective quality settings. Preserve component options below. **No current graphicsMode key.** |
| Mipmaps | `mipmapLevels:4` | same integer0..4 | Renderer set_mipmap_levels consumes it. Verbatim. |
| Entity shadows | `entityShadows:true` | same boolean | Runtime shadow submission checks it; shader/native shadow route can supersede blob shadows. Verbatim, qualify route. |
| Render distance | `renderDistance:12` | same integer2..MAX_RENDER_DISTANCE | Current accepted; benchmark12 matches this field. |
| Simulation distance | `simulationDistance:8` | same integer5..32 | Current accepted; integrated server receives it. Native default12 differs. |
| Frame cap | `maxFps:60` | same integer, native validates10..260 in10-FPS steps |60 accepted. Preserve; values such as125 round to120 upstream, so preflight must report such changes. |
| VSync | `enableVsync:false` | same boolean | set_present_mode consumes with native presentMode. Native defaulttrue. Verbatim, report actual backend present mode later. |

Sources: [option schema/defaults](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/options_file.rs#L128), [decode/validation/encode](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/options_file.rs#L314), [typed Settings mapping](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/settings.rs#L413), [API typed update](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/settings.rs#L627), [FOV/bobbing consumers](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game/fov.rs#L35), [renderer settings](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game/options.rs#L474), [cloud rendering](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game.rs#L15890), [particle level](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game/render_tick.rs#L425).

## Transfer contract and appearance gaps

For **these current values**, a narrow verified verbatim allowlist is `fov,fovEffectScale,bobView,mouseSensitivity,entityDistanceScaling,particles,renderClouds,cloudRange,graphicsPreset,mipmapLevels,entityShadows,renderDistance,simulationDistance,maxFps,enableVsync`. Keep `version:5023` provenance: the native parser runs historical option fixers based on version before decoding. Copying selected modern settings without a suitable source version can trigger old graphics migrations. Native serialization writes its own DATA_VERSION; preserve the original source separately rather than requiring identical serialized bytes.

For a reusable converter, accept a field only if the exact version's codec decodes and validates it without default fallback or quantization. Invalid values, absent source values, unsupported keys and parser failures must produce evidence-bearing gaps, not automatic clamps. Horizon can abort the remainder of the load on syntax error, and a fixer failure leaves defaults; a syntactically valid output plus explicit migrated-value report is necessary. Preserve source files and source hashes; do not merge blindly into a live game file.

Additional current appearance settings needing explicit treatment before “actual setup” testing: `ao:true`, `biomeBlendRadius:2`, `cutoutLeaves:true`, `improvedTransparency:false`, `textureFiltering:0`, `maxAnisotropyBit:1`, `vignette:true`, `weatherRadius:10`, `screenEffectScale:1.0`, `damageTiltStrength:1.0`, `chunkSectionFadeInTime:0.0`. Their parser presence alone is not a verified full conversion contract. In particular graphicsPreset custom does not carry these choices by itself.

Do **not** apply native Balanced/Performance presets as fidelity-preserving optimizations. Exact f42 apply_preset changes clouds, particles, mipmaps, biome blend, entity distance, shadows, leaves and weather radius. Balanced specifically chooses fast clouds, decreased particles,2 mip levels and0.75 entity distance. [Preset assignments](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/graphics.rs#L953).

Sodium current quality config: hidden_fluid_culling/improved_fluid_shaping true, pixel_filtering_mode NEAREST; performance chunk_builder_threads3, animate_only_visible_textures/use_entity_culling/use_fog_occlusion/use_block_face_culling true. These are Java mod settings, not native option keys. No1:1 implementation-equivalence claim is established by this focused audit. Sodium Extra `reduce_resolution_on_mac:true` is a framebuffer-sizing preference, not evidence that native resolutionScale50 reproduces Java's actual pixel dimensions. Native100 is a separate rendering scale; record actual framebuffer/window dimensions later.

EMF current allowedCEM ALL; disabled models empty; modelUpdateFrequency Average; animationLODDistance20; retainDetailOnLowFps/retainDetailOnLargerMobs true; animationFrameSkipDuringIrisShadowPass true. These do not transfer as options.txt values. Native f42 CEM evaluates animations per draw and guards persistent-state commit once per entity/frame; that is not equivalent to Java's Average/LOD/shadow skip policies. These remain explicit compatibility/performance gaps; see the versioned CEM preflight and native visual matrix.

## Bounded verification and next acceptance checks

Only targeted current option keys and small Sodium/Extra/EMF/GammaUtils configs were read. Pinned source was fetched with `gh api .../contents/<path>?ref=f42...` and examined through bounded `rg`/`sed`. Commands completed with exit0; no executable behavior test was run. A final documentation integrity check checked this file's source pin and required topics; it is not a native options round-trip test.

Next implementation acceptance: an isolated generated settings report should show raw0.625 → typed95 → serialized0.625, dynamic FOV1, bobbing true, sensitivity0.5, entity1, particles0, cloudstrue/range64, custom graphics, mipmaps4, shadows true,12/8/60 and VSyncfalse. Test missing gamma remains missing with a visible GammaUtils manual gap. Invalid gamma15, cap125, malformed JSON and missing version must not silently produce “parity”. Runtime acceptance later needs matched camera, framebuffer dimensions, brightness, pack order and effective shader configuration; source support is not measured visual equivalence.
