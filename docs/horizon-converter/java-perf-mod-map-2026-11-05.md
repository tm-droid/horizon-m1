# Java perf mods vs Horizon (2026-11-05)

Read-only static review of `outputs/horizon-runtime/m1-performance/candidate-source/crates/` (f42 + m1 transforms). Nothing built, run or profiled. Paths below are relative to that `crates/` dir. "Unverified" = searched, found nothing, but did not read the whole subsystem.

Prior notes agree: upstream says Sodium/Lithium/EntityCulling/ImmediatelyFast roles "are built into the engine (async entity/particle occlusion, GPU culling, Hidden Faces)" (`upstream-delta-2026-11-05.md:38`). Registry perf mods that exist: `dynamic_fps_for_rust`, `fast_items` (both already prepped in `perf-mods-prep-2026-11-05.md`).

## Counts
BUILT-IN 11, SETTING 7, PORTABLE 6, N/A 11 (35 mods).

## Table

| Mod | Optimizes | Horizon status | Verdict |
|---|---|---|---|
| sodium | Chunk mesh/render pipeline, occlusion graph | Own wgpu renderer. Async worker section meshing `horizon-client-render/src/streaming.rs:3`; async `SectionOcclusionGraph` `gfx/occlusion.rs:1-14`; frustum walk `gfx/resident.rs:2` | BUILT-IN |
| sodium-extra | Toggles: particles, clouds, sky, fog, weather, animated tex | `particles` u8 `settings.rs:~118`, `cloud_range`, `weather_radius`; `sky`/`fog`/`weather`/`animated_textures` `graphics.rs:579-582` (keys `sky:`, `fog:`, `weather:`, `animatedTextures:` in `graphics.rs:834`) | SETTING (`animatedTextures`, `weather`, `particles`) |
| iris | Shader packs | `horizon-shaders`, `horizon-shader-api`; `shader_pack` `graphics.rs:640` | BUILT-IN |
| immediatelyfast | Batches GL immediate-mode draws | Problem is GL immediate mode; wgpu renderer batches by design. Only related knob is `batchTranslucent` (`graphics.rs:636`, `game.rs:1027`) | N/A |
| lithium | Java game-logic/AI/collision micro-opts | Rust server/mobs (`mobs/*`, `horizon-world`) | N/A |
| ferritecore | Dedup block states/models/property maps | `BlockStateId(pub u32)` `horizon-world/src/registry.rs:16`; property keys interned at load `horizon-world/src/level/data.rs:489`; `Arc` shared tables | BUILT-IN |
| modernfix | JVM startup/memory fixes | Java-only. Related native work: sprite disk cache + sprite-compress backport | N/A |
| c2me | Threaded chunk gen/IO/light | Threaded worldgen (`horizon-world/src/worldgen/generator.rs:4521`, `generator_blocks.rs:113`, `generator_structures.rs:937`); worker pool `horizon-threads` `worker_count` `lib.rs:25`; qos-backport prepped | BUILT-IN |
| scalablelux | Fast, parallel light engine | Different design: per-chunk flood fill to fixed point over a 3x3 chunk region, no cross-thread queue `light.rs:1-20`; incremental `relight_block` for edits. Perf vs ScalableLux unmeasured | BUILT-IN (profile before touching) |
| ixeris | Moves GLFW calls off render thread | GLFW/GL thread issue | N/A |
| badoptimizations | Misc Java hot-path fixes | Java-only | N/A |
| moreculling | Skips hidden faces on non-full blocks, leaves, items | `LeafCullingMode` `graphics.rs:332` (`Off/Solid/SolidAggressive/Hollow`, impl `mesher/leaf_culling.rs:1`); "Hidden Faces" per upstream; face visibility in `mesher.rs:371` | BUILT-IN (key `leafCulling`, default Off) |
| entityculling | Occlusion-cull entities and block entities | Entities: `EntityCullingMode` `graphics.rs:94` (`off/sync/async`), key `entityCulling`, impl `horizon-client/src/game/entity_culling.rs:1`, default Off. Block entities: frustum only (`game.rs:10652`, `10704`), no occlusion test | SETTING `entityCulling:async` (BE occlusion: not present) |
| betterblockentities | Cache static block-entity geometry | `cache_shulker_boxes/signs/decorated_pots/bells/chests/banners/copper_golem_statues` `graphics.rs:559-571`; keys `blockEntityCache*`; `StaticSectionSnapshot` `block_entity_render.rs:1000-1012` | SETTING (`blockEntityCache*`) |
| vmp | Villager/mob AI + network opts | Java-only | N/A |
| ksyxis | Skips spawn-chunk preload on world load | No 11x11 spawn-chunk preload found; spawn test only needs the spawn neighbourhood (`streaming.rs:3856`). Unverified | N/A |
| structure_layout_optimizer | Structure gen speedups | Java structure code | N/A |
| zfastnoise | Faster Perlin/simplex/density noise | `horizon-core/src/noise/{perlin,simplex,stack,volume}.rs`, density graph compiler `horizon-core/src/density/graph/`. `volume.rs:78` caches strided samples; no SIMD/interp cache seen. Matters for singleplayer terrain gen only | PORTABLE (#2) |
| zfastsurface | Faster surface-rule eval | Worldgen surface in `horizon-world/src/worldgen/*`; not read in depth | PORTABLE (with #2) |
| zmatcomp | Cheaper matrix/alloc compute | Java allocation problem; glam on stack | N/A |
| smoothtexturefix | Fix mip/seam artifacts | Own `mipmap.rs:1` (`MipmapGenerator` port); `ditherCutoutMips` `graphics.rs:585`; Mipmap Levels option | BUILT-IN |
| betterbiomeblend | Faster, bigger biome blend | `biome_blend` `settings.rs:127` (`game.rs:3822`); one-biome shortcut `mesher/tint_tests.rs:1`; blend runs in mesh worker | SETTING `biomeBlendRadius` |
| async-pack-scan | Scan resource packs off-thread | `Sprites::prefetch` `sprites.rs:351`; decoded sprite disk cache `sprites.rs:94,190`, `sprite_cache.rs:72-94`; pack scan `game/packs.rs:415`; sprite-compress prepped | BUILT-IN |
| quick-pack | Cache pack data between launches | Same as above (sprite disk cache keyed by fingerprint `sprite_cache.rs:42`) | BUILT-IN |
| asynclogger | Async log4j | Java-only | N/A |
| asyncparticles | Tick particles off main thread | Particle tick/cull on game thread as far as seen (`particles.rs`, no `thread`/`spawn`); upstream claims async particle occlusion. Unverified | PORTABLE (with particle_core, #3) |
| betterrenderdistance | Render distance / LOD beyond vanilla | `lod_distance` `graphics.rs:544`, `far_detail` `graphics.rs:546` (Reduced ~1/4 far quads, `graphics.rs:269-278`); LOD disk cache `lod/cache.rs:1-40`; Distant Horizons mod in registry | SETTING `lodDistance`, `farDetail:reduced` |
| entity-view-distance | Per-entity render distance | `entity_distance` `settings.rs:125`; `Entity.setViewScale` `game/entity_culling.rs:518-530` (clamp(rd/8,1,2.5) * scaling) | SETTING `entityDistanceScaling` |
| blockentitydistance | Per-type BE render distance | Hard-coded `VIEW_DISTANCE = 64.0` at `block_entity_render.rs:1281` and `game/native_block_entity_draw.rs:24`; End gateway 256 at `block_entity_render.rs:1675`. No setting | PORTABLE (#5) |
| bobby | Keep server chunks on disk, render beyond server view dist | `lod/cache.rs` only caches Horizon-generated far terrain (`HLOD` regions), not server-sent chunks. No server-chunk cache found | PORTABLE (L; multiplayer only) |
| dynamic_fps | Throttle FPS unfocused/idle | `framerate_limit`/`throttle_reason` `horizon-client-input/src/window.rs:91-98`; `inactivity_fps_limit` `settings.rs:139`; Battery Mode (`batteryMode`, `graphics.rs:623`); `dynamic_fps_for_rust` mod prepped (bench hazard noted in prep doc) | BUILT-IN |
| soundculling | Skip inaudible sounds | Channel cap 247 static + 8 streaming `sound_engine.rs:26-27`; no occlusion/distance cull seen. Sound is not a CPU or GPU lever | BUILT-IN (channel cap; no perf value to add) |
| particle_core | Particle cap/cull/cheaper sim | `MAX_PARTICLES = 16384` `particles.rs:1220` (soft taper at `particles.rs:3490-3494`); Particles option 0/1/2 `particles.rs:1204,1509`; no frustum/distance cull seen | PORTABLE (#3) |
| chunksfadein | Fade-in new chunks | `chunk_fade` `settings.rs:132`, key `chunkSectionFadeInTime` `settings.rs:446`, default 0.75 `settings.rs:236`; fade code `gfx.rs:270`, `gfx/lod.rs:56` | SETTING `chunkSectionFadeInTime` |
| debugify | Fix vanilla bugs | Not perf | N/A |

## Settings worth setting today (no code)
- GPU-bound shader case: `leafCulling:solid` (or `solidaggressive`): moves enclosed leaves to the opaque layer, cutting cutout overdraw (`graphics.rs:332-346`). Ignored with a resource pack that may replace leaf models (`graphics.rs` `leaf_culling_effective`). `farDetail:reduced` (about 1/4 far quads, but changes the picture). `resolutionScale`, `upscaling`, `fxaa`/`taa` (`graphics.rs:592-598`) are the real GPU levers. Unmeasured.
- Flight 1% lows (stream-in spikes): `chunkUpdates` and `uploadBudgetKiB` (`graphics.rs:573-575`) cap per-frame mesh upload; lower them to spread work across frames. `chunkSectionFadeInTime` only affects look. Far terrain thread QoS is the prepared qos-backport.
- `entityCulling:async` is documented as scene-dependent, "do not sell as global CPU optimization" (`base-native-research-2026-11-03.md:17`). Flight over empty terrain will show no gain.

## Worth porting: ranked (top 5)

Gain estimates are guesses; none measured. Horizon mods inject through horizon-mixins on engine functions (`MODIFY_VARIABLE`, HEAD/RETURN, cancellable HEAD; see `perf-mods-prep-2026-11-05.md`). Function names below marked (confirm) were not opened. Prefer in-tree transforms for bench candidates.

1. **Adaptive chunk-update/upload budget** (Sodium defer-updates + C2ME scheduling idea; targets flight 1% lows).
   - Why: `chunk_updates` and `upload_budget_kib` are static knobs (`graphics.rs:573-575`). Flying into new terrain bursts mesh uploads; fixed budgets either stall a frame or lag the fill-in.
   - Sketch: in the renderer's per-frame upload loop (`gfx.rs` upload path, confirm; budget read from `Graphics`), scale the effective KiB/section budget by last-frame GPU+CPU time headroom (e.g. halve when frame time > 1.5x the median, grow back +10%/frame when under), floor at a small non-zero value so streaming never starves. Keep static values as the ceiling. Add key `adaptiveUpload` default off for bench parity.
   - Effort: S-M (1-2 days incl. A/B on the flight route). Expected on M1: the best shot at fewer 1%-low spikes; no avg-FPS change. Pairs with qos-backport.

2. **Noise/density caching for singleplayer worldgen** (zfastnoise, zfastsurface, C2ME noise caching).
   - Why: flying generates fresh terrain on the integrated server; worker CPU competes with meshing on 4P+4E cores. `volume.rs:78` shows sample caching exists in part, but no interpolation cache or SIMD in `horizon-core/src/noise/perlin.rs`.
   - Sketch: profile first (cargo flamegraph on a flight run when the device queue is free; do not port blind). If density eval dominates: cache per-cell-corner noise and lerp inside cells in the density compiler (`horizon-core/src/density/graph/compiler.rs`), add a NEON/`glam` batched Perlin path, memoize repeated `NoiseId` calls per column. Keep output bit-identical (worldgen parity tests).
   - Effort: M-L (3-5 days; parity risk). Gain: only if worldgen is on the critical path; potentially large for flight, zero on a pre-generated world. Gate behind a profile.

3. **Particle frustum/distance cull and lower cap** (particle_core, asyncparticles).
   - Why: cap is 16384 per group (`particles.rs:1220`) with only a soft taper; no view cull found. Shader packs make every drawn particle cost GPU fill; explosions/rain/campfires pile up.
   - Sketch: at particle submit (`particles.rs`, the render-collect fn, confirm), skip particles outside the view frustum (`Game.view_frustum`, `game.rs:2959`) and beyond a distance (`entity_distance`-style scale); optionally lower the hard cap to ~4096 via a setting. Skip ticking cost reduction first; do cull only. Optional: tick on a worker (asyncparticles) only if profile shows tick > 1 ms.
   - Effort: S (half a day for cull + setting). Gain: small average, helps GPU-bound scenes with heavy particles. Visual risk: low (off-screen only).

4. **Block-entity view-distance setting** (blockentitydistance, BE half of entityculling).
   - Why: `VIEW_DISTANCE = 64.0` constant at `block_entity_render.rs:1281` and `native_block_entity_draw.rs:24`; no knob. Chest/sign-heavy builds pay full draw to 64 blocks.
   - Sketch: replace the const with a field set from a new option (`blockEntityDistance`, default 64 = vanilla), keep gateway 256 override (`block_entity_render.rs:1675`). Optionally reuse the entity async occlusion test for BEs (`entity_culling.rs`) behind `entityCulling`.
   - Effort: S (2-3 hours for the knob). Gain: small, scene-dependent. Easy win and also lets the user trade distance for GPU time.

5. **Incremental/sharing light computation** (ScalableLux idea) — only if profile shows light on the critical path.
   - Why: `light.rs` re-floods a 48-wide region per chunk "to the fixed point"; neighbouring chunks repeat overlapping work. During flight every new chunk triggers it.
   - Sketch: profile (`thread_cpu()` `horizon-threads/src/lib.rs:84` is available for per-worker timing). If hot: cache border light per chunk edge, flood only the chunk plus a 15-block halo that is already resolved for loaded neighbours, reuse sky-source columns (`light.rs` sky sources). Must stay equal to vanilla `LightEngine` results (existing tests).
   - Effort: L (1 week+). Gain: unknown; skip unless measured.

Not in top 5: Bobby-style server-chunk disk cache (L effort, multiplayer only, no flight or GPU benefit); ImmediatelyFast/Lithium/VMP/ModernFix class (Java-only problems).
