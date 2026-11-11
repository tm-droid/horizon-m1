# R2: Horizon perf knobs (candidate-source, f42 + local patches)

Paths relative to `m1-performance/candidate-source/`. Perf: H/M/L. Looks: none/minor/major. TESTED = already benchmarked.
Gaps: not every game.rs/hud option was read; 610 HORIZON_* hits total, most are launcher/server/test-only (ignored). Defaults for cfg keys are from `Graphics::default()` (graphics.rs:642), Preset may override them (apply_preset graphics.rs:954, not read in detail).

## A. HORIZON_* env vars (client-relevant)

| Name | file:line | Default | Effect | Perf | Looks | Status |
|---|---|---|---|---|---|---|
| HORIZON_WORKER_THREADS | crates/horizon-threads/src/lib.rs:28 | all cores (available_parallelism) | caps worker_count() for every pool; streaming pool = all but one, far decoration = 1/3 | H | none | TESTED (4/5/6/auto; 6 no gain) |
| HORIZON_JOB_THREADS | crates/horizon-threads/src/jobs.rs:180 | worker_count-1 (min 1), or configure() value | size of general job pool "horizon-worker" (separate from worker_count pools) | H | none | UNTESTED |
| HORIZON_GPU_CULL | crates/horizon-client-render/src/gfx.rs:3940 | auto (Metal: min_sections=TILED_MIN_SECTIONS) | `0` off, `all` cull every frame, `shader` depth test in shader | M | none (bugs possible) | `all` TESTED marginal; `0` and `shader` UNTESTED |
| HORIZON_FLAT_DRAWS | gfx/flat.rs:157,164; gfx.rs:3868 | auto: ON for Metal vanilla past MIN_SECTIONS=1600 | `1` all frames flat draws, `0` none (per-section draws) | H | none | UNTESTED (A/B `0` vs default; Metal already auto-on) |
| HORIZON_SUBMIT_THREAD | gfx/submit.rs:19 | off on macOS (on Linux only) | `1` forces submit thread; comment says it stalled on Metal (10-50% FPS, 20-180ms p99) | M | none | UNTESTED, doc says bad on Metal; skip |
| HORIZON_MEMORY_LIMIT_MB | horizon-client/src/ram_limit.rs:15 (launcher/src/launch.rs:61 sets) | unset | Governor turns far terrain off and lowers render distance under pressure | H on 8GB | major when it triggers | UNTESTED; useful as swap guard |
| HORIZON_MEMORY_HARD_MB | horizon-client/src/ram_limit.rs:17 | unset | allocator ceiling, game ends past it | L | n/a | UNTESTED, safety only |
| HORIZON_GRAPHICS_API | graphics.rs:238 | auto (Metal only on macOS) | overrides graphicsApi | L | none | no-op on macOS |
| HORIZON_SPRITE_SPLIT | gfx.rs:1188 | 2048 | dev only: smaller sprite array layer split | L | none | skip |
| HORIZON_HDR_OUTPUT | gfx/hdr.rs:46 | auto | HDR surface pick | L-M | major | skip (hdr off) |
| HORIZON_HDR_LIGHTING | gfx.rs:7287 | on if HDR active; `0` disables | HDR lighting path | L | minor | skip |
| HORIZON_HDR_DEBUG | gfx/hdr.rs:292 | off | debug | L | none | skip |
| HORIZON_FRAMEGEN_DEBUG | gfx/frame_gen.rs:39 | off | debug of FSR3.1 framegen | L | none | skip |
| HORIZON_SHADER_PACK | client/src/game/shader_packs.rs:75,114 | unset | dev: force a shader pack | H (with pack) | major | n/a |
| HORIZON_SHADER_PACK_SKIP / _WITHOUT | gfx/pack_post.rs:2131,278 | empty | skip named pack passes / features | H with pack | major | UNTESTED, debug tool to find costly pack passes |
| HORIZON_SHADER_PACK_TIMING | gfx/pack_timing.rs:90 | off | logs per-pass GPU timing of shader pack | n/a (diagnostic) | none | UNTESTED, use to profile MakeUp-like packs |
| HORIZON_SHADER_PACK_DUMP | gfx/pack_images.rs:491 | unset | dump pack images | L | none | skip |
| HORIZON_STARTUP_TRACE | client-render/src/spans.rs:246 | unset | writes startup span trace to path | n/a (load time diagnostic) | none | UNTESTED, use to profile load time |
| HORIZON_SPIKES | client/src/game.rs:598 | unset | frame-spike logging threshold (parse number) | n/a (diagnostic) | none | UNTESTED, good for pacing analysis |
| HORIZON_SPLIT | client/src/game/split.rs:169 | unset | split-screen mode (doubles render) | H (negative) | major | ensure unset |
| HORIZON_NO_AUDIO / HORIZON_AUDIO=1 | client-render/src/audio.rs:672,675 | audio on | disable/force audio | L-M | none (silent) | UNTESTED; small CPU win |
| HORIZON_NO_ENTITY_SKIN | gfx/entity_skin.rs:230 | off | skips entity skin path | L | minor | skip |
| HORIZON_NO_HEARTBEAT | client/src/heartbeat.rs:24 | off | no telemetry pinger | L | none | skip |
| HORIZON_NO_DISCORD | client/src/discord_presence.rs:117 | off | no Discord presence | L | none | skip |
| HORIZON_NO_UPDATE_CHECK | server/src/supervisor.rs:424 | off | server side | L | none | skip |
| HORIZON_ENHANCED_TERRAIN, HORIZON_OLD_CHUNKS, HORIZON_TERRAIN_ONLY | examples/tests only | | not client runtime | n/a | | skip |
| HORIZON_HOME / RESOURCES / MINECRAFT_DIR / LAUNCHER_* / TELEMETRY_* / MSA_* / COSMETICS_* | launcher and paths | | not perf | n/a | | skip |

## B. horizon-graphics.txt keys (parser: crates/horizon-client-render/src/graphics.rs:717-830; defaults from graphics.rs:642)

| Key | parse line | Default | Effect | Perf | Looks | Status |
|---|---|---|---|---|---|---|
| preset | :731 | custom | performance/balanced/quality/ultra/custom, applies bundle via apply_preset :954 | M | varies | UNTESTED, read apply_preset before use |
| lodDistance | :732 (cap for Apple GPUs: lod_distance_capped :486, INTEGRATED_LOD_DISTANCE=128) | 0 | far terrain (LOD) distance | H | major | far terrain UNTESTED |
| farDetail | :735 | full | `reduced` = coarser LOD levels start at half distance, ~1/4 far quads | H when LOD on | minor-major (changes picture) | UNTESTED |
| caveCulling | :742 | true | cave/occlusion visibility culling of sections | M | none | UNTESTED off (keep on) |
| entityCulling | :743 | off | off / sync / async. Async = async occlusion results only hide a mesh when camera/bounds still match | M-H in entity-heavy | none-minor | UNTESTED, try `async` |
| leafCulling | :744 | off | off / solid / solid_aggressive / hollow: drop interior leaf faces in mesher | M-H in forests | none (solid) / minor (aggressive, hollow) | UNTESTED, try `solid` |
| blockEntityCache | :745 | (master toggle; sub-defaults: signs=true, others false) | caches block entity models | M | none | UNTESTED |
| blockEntityCacheShulkerBoxes / Signs / DecoratedPots / Bells / Chests / Banners / CopperGolemStatues | :755-765 | false (signs true) | per-type cache | M in chest-heavy bases | none | UNTESTED |
| chunkUpdates | :768 (max 512) | 0 (all ready per frame) | sections uploaded per frame; cap smooths spikes | H for pacing | minor (pop-in) | UNTESTED, try 4-8 |
| uploadBudgetKiB | :769 | 0 (unlimited) | mesh bytes uploaded per frame | H pacing | minor | TESTED 2048 |
| textureBudgetMiB | :770 | 0 (Horizon default sprites::DEFAULT_TEXTURE_BUDGET) | block texture VRAM (top mip); applies on resource reload | M (memory) | minor-major at low | UNTESTED |
| sky / fog / weather | :773-775 | true | toggles | L-M (weather M in rain) | minor-major | UNTESTED |
| animatedTextures | :776 | true | animated block textures | L-M | minor | UNTESTED |
| ditherCutoutMips | :777 | false | dither small mips of cutouts | L | minor | skip |
| presentMode | :778 | auto (VSync) | fifo/mailbox/immediate/auto | M | none (tearing) | TESTED |
| framePacing | :779 | efficient (sleep whole wait); `precise` = sleep+spin | limiter | M | none | TESTED |
| workers | :786 (max 64) | 0 = all cores but one | chunk worker threads, applies next start | H | none | persistent equivalent of WORKER_THREADS (TESTED via env) |
| resolutionScale | :787 (50..200) | 100 | world render resolution percent | H (GPU bound) | major | UNTESTED, user may dislike |
| fxaa / taa / upscaling | :788-790 | false/false/native | AA and TAA upscaling (upscaling != native implies taa) | M | major | UNTESTED; taa+upscaling lets you lower resolutionScale |
| frameGeneration | :796 | off | FSR 3.1 frame interpolation | H (perceived) | minor (artifacts), adds latency | UNTESTED |
| hdr* | :797-814 | false | HDR output | L | major | skip |
| batteryMode | :815 | false | battery saver | M | minor | UNTESTED |
| shadowCache | :816 | false | shadow-pass cache (pack_post.rs:3721) | M with shader pack | none | TESTED true |
| batchTranslucent | :817 | true | batch translucent draws | M | none | UNTESTED off (keep on) |
| graphicsApi | :818 | auto | macOS only Metal | n/a | | skip |
| pickedShaderPack | :819 | empty | shader pack | H | major | user choice |
| overlay | :820 | off | fps/graph overlay | L | | for benches |
| blueMapRadius / blueMapAutoDetect | :736-741 | | BlueMap far map, servers | L-M | | skip |

## C. options.txt keys read (settings.rs:423-455, options_file.rs:146-155)

| Key | Default | Effect | Perf | Looks | Status |
|---|---|---|---|---|---|
| renderDistance, simulationDistance | | chunk count | H | major | user 12/8 |
| maxFps, enableVsync, inactivityFpsLimit | | limiter | M | none | pacing TESTED |
| renderClouds | | clouds on/off | M | minor | TESTED false |
| cloudRange | | cloud range | L-M | minor | TESTED |
| particles | | 0 all/1 decreased/2 minimal | M | minor | UNTESTED |
| entityDistanceScaling | | entity render distance factor | M-H in mob farms | minor | UNTESTED |
| entityShadows | | entity shadows | L-M | minor | UNTESTED |
| biomeBlendRadius | | blend kernel in mesher | M (mesh time) | minor | UNTESTED, try 0-1 |
| mipmapLevels | | texture mip levels | M (VRAM, GPU) | minor (distant shimmer) | UNTESTED |
| textureFiltering, maxAnisotropyBit | | 0 none / 1 RGSS / 2 anisotropic; max aniso clamp (gfx.rs:979-982) | M GPU | minor | UNTESTED, RGSS costly |
| weatherRadius | | rain radius | L-M | minor | UNTESTED |
| chunkSectionFadeInTime | | fade-in on chunk appearance | L | minor | UNTESTED, 0 to skip |
| cutoutLeaves | | cutout vs opaque leaves | M | minor-major | UNTESTED |
| improvedTransparency | | OIT-style translucency | M-H | minor | UNTESTED, off if on |
| ao | | smooth lighting | L (mesh) | minor | UNTESTED |
| prioritizeChunkUpdates | | chunk update priority | L-M | none | UNTESTED |
| graphicsPreset | | vanilla graphics preset name | M | varies | UNTESTED |
| menuBackgroundBlurriness | | menu blur | L | minor | UNTESTED |
| guiScale, fov, gamma, vignette | | | L | | skip |

Not found: any env var for mesher/chunk-builder thread count other than HORIZON_WORKER_THREADS / `workers`; no standalone "mipmaps" or "anisotropy" HORIZON_* env var (those are options.txt only); no `HORIZON_*` env for entity culling or block-entity caches (cfg only).
